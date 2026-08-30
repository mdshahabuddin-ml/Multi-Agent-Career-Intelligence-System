import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional, Callable, Awaitable

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord
from backend.data_pipeline.normalization.job_normalizer import JobNormalizer, NormalizedJob
from backend.data_pipeline.deduplication.duplicate_detector import DuplicateDetector, DuplicateMatch
from backend.data_pipeline.sources.source_registry import SourceRegistry, SourceConfig, DataSource
from backend.evaluation.data_quality import DataQualityScorer, DataQualityResult
from backend.database import get_db
from backend.models import Job, Company

logger = logging.getLogger(__name__)


class PipelineStage(str, PyEnum):
    """Stages in the ingestion pipeline."""
    COLLECT = "collect"
    NORMALIZE = "normalize"
    DEDUPLICATE = "deduplicate"
    VALIDATE = "validate"
    QUALITY_SCORE = "quality_score"
    PERSIST = "persist"
    RAG_INGEST = "rag_ingest"


@dataclass
class PipelineStageResult:
    """Result of a single pipeline stage."""
    stage: PipelineStage
    success: bool
    records_in: int
    records_out: int
    duration_ms: int
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Complete result of a pipeline run."""
    run_id: str
    source_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    stages: List[PipelineStageResult]
    total_records_received: int
    total_records_normalized: int
    total_records_rejected: int
    total_duplicates_found: int
    total_records_saved: int
    total_rag_documents_created: int
    overall_success: bool
    error_summary: str = ""

    @property
    def total_duration_ms(self) -> int:
        return sum(s.duration_ms for s in self.stages)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_id": self.source_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "stages": [
                {
                    "stage": s.stage.value,
                    "success": s.success,
                    "records_in": s.records_in,
                    "records_out": s.records_out,
                    "duration_ms": s.duration_ms,
                    "errors": s.errors,
                    "metadata": s.metadata,
                }
                for s in self.stages
            ],
            "total_records_received": self.total_records_received,
            "total_records_normalized": self.total_records_normalized,
            "total_records_rejected": self.total_records_rejected,
            "total_duplicates_found": self.total_duplicates_found,
            "total_records_saved": self.total_records_saved,
            "total_rag_documents_created": self.total_rag_documents_created,
            "overall_success": self.overall_success,
            "error_summary": self.error_summary,
        }


class IngestionPipeline:
    """
    Orchestrates the complete data ingestion pipeline:
    collect → normalize → deduplicate → validate → quality_score → persist → rag_ingest
    """

    def __init__(
        self,
        source_registry: Optional[SourceRegistry] = None,
        normalizer: Optional[JobNormalizer] = None,
        deduplicator: Optional[DuplicateDetector] = None,
        quality_scorer: Optional[DataQualityScorer] = None,
        db_session=None,
    ):
        self.source_registry = source_registry
        self.normalizer = normalizer or JobNormalizer()
        self.deduplicator = deduplicator or DuplicateDetector()
        self.quality_scorer = quality_scorer or DataQualityScorer()
        self._db = db_session
        self._collectors: Dict[str, BaseCollector] = {}

    def register_collector(self, collector: BaseCollector):
        """Register a collector for a source."""
        self._collectors[collector.source_name] = collector

    def get_collector(self, source_name: str) -> Optional[BaseCollector]:
        """Get collector by source name."""
        return self._collectors.get(source_name)

    async def run(
        self,
        source_id: str,
        collector: Optional[BaseCollector] = None,
        collector_kwargs: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> PipelineResult:
        """
        Run the complete ingestion pipeline for a source.
        
        Args:
            source_id: Source identifier from registry
            collector: Optional collector instance (will use registered if not provided)
            collector_kwargs: Arguments to pass to collector.fetch()
            limit: Maximum records to process
            
        Returns:
            PipelineResult with complete statistics
        """
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow()
        
        logger.info(f"Starting ingestion pipeline run {run_id} for source {source_id}")
        
        stages = []
        records: List[RawDataRecord] = []
        normalized: List[NormalizedJob] = []
        saved_count = 0
        rag_count = 0
        errors = []
        
        collector_kwargs = collector_kwargs or {}
        if limit:
            collector_kwargs["limit"] = limit

        # Stage 1: COLLECT
        stage_start = datetime.utcnow()
        try:
            if collector is None:
                collector = self._collectors.get(source_id)
            if collector is None:
                raise ValueError(f"No collector registered for source: {source_id}")
            
            records = await collector.collect(**collector_kwargs)
            if limit and len(records) > limit:
                records = records[:limit]
            
            stages.append(PipelineStageResult(
                stage=PipelineStage.COLLECT,
                success=True,
                records_in=0,
                records_out=len(records),
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                metadata={"collector": collector.source_name}
            ))
            logger.info(f"Collected {len(records)} raw records from {source_id}")
        except Exception as e:
            error_msg = f"Collection failed: {e}"
            logger.error(error_msg)
            stages.append(PipelineStageResult(
                stage=PipelineStage.COLLECT,
                success=False,
                records_in=0,
                records_out=0,
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                errors=[error_msg]
            ))
            return self._finalize_result(run_id, source_id, started_at, stages, 0, 0, 0, 0, 0, 0, False, error_msg)

        # Stage 2: NORMALIZE
        stage_start = datetime.utcnow()
        try:
            normalized = self.normalizer.normalize_batch(records)
            stages.append(PipelineStageResult(
                stage=PipelineStage.NORMALIZE,
                success=True,
                records_in=len(records),
                records_out=len(normalized),
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                metadata={"normalizer": self.normalizer.name}
            ))
            logger.info(f"Normalized {len(normalized)} records")
        except Exception as e:
            error_msg = f"Normalization failed: {e}"
            logger.error(error_msg)
            stages.append(PipelineStageResult(
                stage=PipelineStage.NORMALIZE,
                success=False,
                records_in=len(records),
                records_out=0,
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                errors=[error_msg]
            ))
            return self._finalize_result(run_id, source_id, started_at, stages, len(records), 0, 0, 0, 0, 0, False, error_msg)

        # Stage 3: DEDUPLICATE
        stage_start = datetime.utcnow()
        try:
            original_count = len(normalized)
            normalized = self.deduplicator.deduplicate(normalized)
            duplicates_found = original_count - len(normalized)
            stages.append(PipelineStageResult(
                stage=PipelineStage.DEDUPLICATE,
                success=True,
                records_in=original_count,
                records_out=len(normalized),
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                metadata={"duplicates_removed": duplicates_found, "deduplicator": self.deduplicator.name}
            ))
            logger.info(f"Deduplicated: {original_count} -> {len(normalized)} ({duplicates_found} duplicates)")
        except Exception as e:
            error_msg = f"Deduplication failed: {e}"
            logger.error(error_msg)
            stages.append(PipelineStageResult(
                stage=PipelineStage.DEDUPLICATE,
                success=False,
                records_in=len(normalized),
                records_out=0,
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                errors=[error_msg]
            ))
            return self._finalize_result(run_id, source_id, started_at, stages, len(records), len(normalized), 0, 0, 0, 0, False, error_msg)

        # Stage 4: VALIDATE
        stage_start = datetime.utcnow()
        validation_errors = []
        valid_normalized = []
        required_fields = ["title", "company_name", "source_url", "source_job_id"]
        
        for norm_job in normalized:
            missing = [f for f in required_fields if not getattr(norm_job, f, None)]
            if missing:
                validation_errors.append(f"Job {norm_job.source_job_id}: missing {missing}")
                continue
            if not norm_job.source_url or not norm_job.source_url.startswith(("http://", "https://")):
                validation_errors.append(f"Job {norm_job.source_job_id}: invalid source_url")
                continue
            valid_normalized.append(norm_job)
        
        rejected = len(normalized) - len(valid_normalized)
        normalized = valid_normalized
        
        stages.append(PipelineStageResult(
            stage=PipelineStage.VALIDATE,
            success=True,
            records_in=len(normalized) + rejected,
            records_out=len(normalized),
            duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
            metadata={"rejected": rejected, "validation_errors": validation_errors}
        ))
        logger.info(f"Validated: {len(normalized)} valid, {rejected} rejected")

        # Stage 5: QUALITY SCORE
        stage_start = datetime.utcnow()
        quality_results: List[DataQualityResult] = []
        try:
            for norm_job in normalized:
                # Convert NormalizedJob to dict for quality assessment
                job_dict = {
                    "title": norm_job.title,
                    "company": norm_job.company_name,
                    "location": norm_job.location,
                    "description": norm_job.description,
                    "requirements": norm_job.requirements,
                    "salary_min": norm_job.salary_min,
                    "salary_max": norm_job.salary_max,
                    "experience_years": self._extract_experience_years(norm_job.experience_level),
                    "skills": norm_job.skills,
                    "source_url": norm_job.source_url,
                    "posted_date": norm_job.posted_date,
                }
                
                result = self.quality_scorer.assess(
                    data=job_dict,
                    data_identifier=norm_job.source_job_id,
                    data_type="job_posting",
                    required_fields=["title", "company", "location"],
                    optional_fields=["salary_min", "salary_max", "experience_years", "description", "skills"],
                    source_type=norm_job.raw_record.source_type if hasattr(norm_job, 'raw_record') else "unknown",
                    source_metadata={"source_url": norm_job.source_url},
                    data_timestamp=norm_job.posted_date or datetime.utcnow(),
                    validation_rules=[
                        {"field": "salary_min", "rule": "gte", "value": 0},
                        {"field": "salary_max", "rule": "gte", "value": 0},
                    ],
                    cross_field_checks=[
                        {"fields": ["salary_min", "salary_max"], "rule": "lte", "message": "Min salary must be <= max salary"}
                    ]
                )
                quality_results.append(result)
                # Attach quality score to normalized job
                norm_job.quality_score = result.overall_score
            
            stages.append(PipelineStageResult(
                stage=PipelineStage.QUALITY_SCORE,
                success=True,
                records_in=len(normalized),
                records_out=len(normalized),
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                metadata={"avg_quality_score": sum(r.overall_score for r in quality_results) / len(quality_results) if quality_results else 0}
            ))
            logger.info(f"Quality scored {len(quality_results)} records")
        except Exception as e:
            error_msg = f"Quality scoring failed: {e}"
            logger.error(error_msg)
            stages.append(PipelineStageResult(
                stage=PipelineStage.QUALITY_SCORE,
                success=False,
                records_in=len(normalized),
                records_out=len(normalized),
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                errors=[error_msg]
            ))

        # Stage 6: PERSIST
        stage_start = datetime.utcnow()
        try:
            db = self._db or next(get_db())
            saved_count = self._persist_jobs(db, normalized)
            db.commit()
            stages.append(PipelineStageResult(
                stage=PipelineStage.PERSIST,
                success=True,
                records_in=len(normalized),
                records_out=saved_count,
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                metadata={"saved": saved_count}
            ))
            logger.info(f"Persisted {saved_count} jobs to database")
        except Exception as e:
            error_msg = f"Persistence failed: {e}"
            logger.error(error_msg)
            stages.append(PipelineStageResult(
                stage=PipelineStage.PERSIST,
                success=False,
                records_in=len(normalized),
                records_out=0,
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                errors=[error_msg]
            ))

        # Stage 7: RAG INGEST
        stage_start = datetime.utcnow()
        try:
            rag_count = await self._ingest_to_rag(normalized)
            stages.append(PipelineStageResult(
                stage=PipelineStage.RAG_INGEST,
                success=True,
                records_in=saved_count,
                records_out=rag_count,
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                metadata={"documents_created": rag_count}
            ))
            logger.info(f"Ingested {rag_count} documents to RAG")
        except Exception as e:
            error_msg = f"RAG ingestion failed: {e}"
            logger.warning(error_msg)
            stages.append(PipelineStageResult(
                stage=PipelineStage.RAG_INGEST,
                success=False,
                records_in=saved_count,
                records_out=0,
                duration_ms=int((datetime.utcnow() - stage_start).total_seconds() * 1000),
                errors=[error_msg]
            ))

        completed_at = datetime.utcnow()
        overall_success = all(s.success for s in stages)
        error_summary = "; ".join(
            f"{s.stage.value}: {', '.join(s.errors)}"
            for s in stages if s.errors
        )

        return self._finalize_result(
            run_id, source_id, started_at, stages,
            len(records), len(normalized), rejected,
            sum(1 for s in stages if s.stage == PipelineStage.DEDUPLICATE for s in [s] if s.metadata.get("duplicates_removed", 0)),
            saved_count, rag_count, overall_success, error_summary
        )

    def _finalize_result(
        self,
        run_id: str,
        source_id: str,
        started_at: datetime,
        stages: List[PipelineStageResult],
        total_received: int,
        total_normalized: int,
        total_rejected: int,
        total_duplicates: int,
        total_saved: int,
        total_rag: int,
        overall_success: bool,
        error_summary: str,
    ) -> PipelineResult:
        completed_at = datetime.utcnow()
        return PipelineResult(
            run_id=run_id,
            source_id=source_id,
            started_at=started_at,
            completed_at=completed_at,
            stages=stages,
            total_records_received=total_received,
            total_records_normalized=total_normalized,
            total_records_rejected=total_rejected,
            total_duplicates_found=total_duplicates,
            total_records_saved=total_saved,
            total_rag_documents_created=total_rag,
            overall_success=overall_success,
            error_summary=error_summary,
        )

    def _persist_jobs(self, db, jobs: List[NormalizedJob]) -> int:
        """Persist normalized jobs to database."""
        saved = 0
        for norm_job in jobs:
            try:
                # Check if job already exists
                existing = db.query(Job).filter(
                    Job.source == norm_job.source,
                    Job.source_job_id == norm_job.source_job_id,
                ).first()
                
                if existing:
                    # Update existing
                    self._update_job(existing, norm_job)
                else:
                    # Create new job with company
                    company = self._get_or_create_company(db, norm_job)
                    job = Job(
                        title=norm_job.title,
                        company_id=company.id,
                        location=norm_job.location,
                        is_remote=norm_job.is_remote,
                        remote_type=norm_job.remote_type,
                        description=norm_job.description,
                        requirements=norm_job.requirements,
                        responsibilities=norm_job.responsibilities,
                        salary_min=norm_job.salary_min,
                        salary_max=norm_job.salary_max,
                        salary_currency=norm_job.salary_currency,
                        salary_period=norm_job.salary_period,
                        experience_level=norm_job.experience_level,
                        employment_type=norm_job.employment_type,
                        source=norm_job.source,
                        source_url=norm_job.source_url,
                        source_job_id=norm_job.source_job_id,
                        posted_date=norm_job.posted_date,
                        expires_date=norm_job.expires_date,
                        application_url=norm_job.application_url,
                        application_email=norm_job.application_email,
                        skills=norm_job.skills,
                        keywords=norm_job.keywords,
                        quality_score=norm_job.quality_score,
                    )
                    db.add(job)
                saved += 1
            except Exception as e:
                logger.error(f"Failed to persist job {norm_job.source_job_id}: {e}")
                db.rollback()
                continue
        return saved

    def _get_or_create_company(self, db, norm_job: NormalizedJob) -> Company:
        """Get existing company or create new one."""
        company = db.query(Company).filter(
            Company.normalized_name == norm_job.company_name.lower()
        ).first()
        
        if company:
            return company
        
        company = Company(
            name=norm_job.company_name,
            normalized_name=norm_job.company_name.lower(),
            domain=norm_job.company_domain,
        )
        db.add(company)
        db.flush()
        return company

    def _update_job(self, job: Job, norm_job: NormalizedJob):
        """Update existing job with new data."""
        job.title = norm_job.title
        job.location = norm_job.location
        job.is_remote = norm_job.is_remote
        job.remote_type = norm_job.remote_type
        job.description = norm_job.description
        job.requirements = norm_job.requirements
        job.responsibilities = norm_job.responsibilities
        job.salary_min = norm_job.salary_min
        job.salary_max = norm_job.salary_max
        job.salary_currency = norm_job.salary_currency
        job.salary_period = norm_job.salary_period
        job.experience_level = norm_job.experience_level
        job.employment_type = norm_job.employment_type
        job.posted_date = norm_job.posted_date
        job.expires_date = norm_job.expires_date
        job.application_url = norm_job.application_url
        job.application_email = norm_job.application_email
        job.skills = norm_job.skills
        job.keywords = norm_job.keywords
        job.quality_score = norm_job.quality_score
        job.updated_at = datetime.utcnow()

    def _extract_experience_years(self, level: Optional[str]) -> int:
        """Extract years from experience level."""
        if not level:
            return 0
        level = level.lower()
        if "intern" in level or "entry" in level:
            return 0
        if "junior" in level:
            return 1
        if "mid" in level:
            return 3
        if "senior" in level:
            return 5
        if "lead" in level or "principal" in level or "staff" in level:
            return 7
        return 3

    async def _ingest_to_rag(self, jobs: List[NormalizedJob]) -> int:
        """Ingest jobs into RAG system."""
        try:
            from backend.rag.ingestion.loaders import DocumentLoaderFactory, JobLoader
            from backend.rag.vector_store import VectorStore
            from backend.research_engine.state.research_context import SourceMetadata, ResearchSourceType
            
            loader = JobLoader()
            vector_store = VectorStore()
            
            count = 0
            for job in jobs:
                source_meta = SourceMetadata(
                    url=job.source_url,
                    title=job.title,
                    source_type=ResearchSourceType.JOB_BOARD,
                    domain=job.company_domain or "unknown",
                    custom_metadata={
                        "structured_data": {
                            "title": job.title,
                            "company": job.company_name,
                            "location": job.location,
                            "description": job.description,
                            "requirements": job.requirements,
                            "skills": job.skills,
                        }
                    }
                )
                
                loaded_doc = loader.load(source_meta)
                if loaded_doc.chunks:
                    await vector_store.add_documents(loaded_doc.chunks)
                    count += 1
            
            return count
        except Exception as e:
            logger.warning(f"RAG ingestion error (may be expected if not configured): {e}")
            return 0