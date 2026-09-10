import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from sqlalchemy.orm import Session

from backend.agents.research import (
    ResearchOrchestrator,
    PipelineState,
    PipelinePhase,
    ReportAgent,
)
from backend.models import Research, ResearchStatus, ResearchType, User
from backend.models.research_source import ResearchSource
from backend.models.research_claim import ResearchClaim
from backend.models.research_evidence import ResearchEvidence
from backend.database import get_db
from backend.services.websocket_manager import notify_research_progress

logger = logging.getLogger(__name__)


class ResearchService:
    """Service for managing research workflows using the multi-agent orchestrator."""

    def __init__(self, db: Session):
        self.db = db
        self.orchestrator = ResearchOrchestrator()
        self.report_agent = ReportAgent()

    async def start_research(
        self,
        user_id: int,
        query: str,
        research_type: ResearchType = ResearchType.GENERAL,
        target_role: Optional[str] = None,
        target_company: Optional[str] = None,
        target_location: Optional[str] = None,
        max_sources: int = 10,
        timeout_seconds: int = 300,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Research:
        """Start a new research task."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        research = Research(
            user_id=user_id,
            query=query,
            research_type=research_type,
            target_role=target_role,
            target_company=target_company,
            target_location=target_location,
            max_sources=max_sources,
            timeout_seconds=timeout_seconds,
            status=ResearchStatus.CREATED,
        )

        self.db.add(research)
        self.db.commit()
        self.db.refresh(research)

        # Start research in background with progress callback
        asyncio.create_task(self._run_research(research.id, progress_callback))

        logger.info(f"Started research #{research.id} for user {user_id}")
        return research

    async def _run_research(
        self,
        research_id: int,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """Run the complete research workflow using the orchestrator."""
        db = next(get_db())
        try:
            research = db.query(Research).filter(Research.id == research_id).first()
            if not research:
                logger.error(f"Research {research_id} not found")
                return

            # Update status to planning
            research.status = ResearchStatus.PLANNING
            research.started_at = datetime.utcnow()
            db.commit()

            # Define progress callback wrapper
            def pipeline_progress(state: PipelineState):
                """Convert pipeline state to research status updates."""
                research.status = self._map_phase_to_status(state.phase)
                research.progress = state.progress
                db.commit()

                # Create progress update for WebSocket
                pipeline_status = self.orchestrator.get_pipeline_status(state)
                progress_update = {
                    "research_id": pipeline_status["research_id"],
                    "phase": pipeline_status["phase"],
                    "progress": pipeline_status["progress"],
                    "stats": pipeline_status["stats"],
                    "error": pipeline_status.get("error"),
                    "warnings": pipeline_status.get("warnings", []),
                }
                
                # Send to WebSocket (fire and forget)
                asyncio.create_task(notify_research_progress(state.research_id, progress_update))

                if progress_callback:
                    try:
                        progress_callback(pipeline_status)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

            # Execute the full pipeline
            state = await self.orchestrator.execute_pipeline(
                research=research,
                db_session=db,
                progress_callback=pipeline_progress,
            )

            # Save final results
            if state.phase == PipelinePhase.COMPLETED and state.synthesis_result:
                await self._save_results(research, state, db)
            elif state.phase == PipelinePhase.FAILED:
                research.status = ResearchStatus.FAILED
                research.error_message = state.error or "Pipeline execution failed"
                db.commit()

            logger.info(f"Research #{research_id} completed with status: {state.phase.value}")

        except Exception as e:
            logger.error(f"Research {research_id} failed: {e}", exc_info=True)
            research = db.query(Research).filter(Research.id == research_id).first()
            if research:
                research.status = ResearchStatus.FAILED
                research.error_message = str(e)
                db.commit()

    def _map_phase_to_status(self, phase: PipelinePhase) -> ResearchStatus:
        """Map pipeline phase to research status."""
        mapping = {
            PipelinePhase.DECOMPOSING: ResearchStatus.PLANNING,
            PipelinePhase.RESEARCHING: ResearchStatus.RESEARCHING,
            PipelinePhase.MANAGING_SOURCES: ResearchStatus.COLLECTING_EVIDENCE,
            PipelinePhase.EXTRACTING_CLAIMS: ResearchStatus.COLLECTING_EVIDENCE,
            PipelinePhase.COLLECTING_EVIDENCE: ResearchStatus.COLLECTING_EVIDENCE,
            PipelinePhase.RANKING_EVIDENCE: ResearchStatus.COLLECTING_EVIDENCE,
            PipelinePhase.VERIFYING: ResearchStatus.VERIFYING,
            PipelinePhase.ANALYZING: ResearchStatus.ANALYZING,
            PipelinePhase.SYNTHESIZING: ResearchStatus.SYNTHESIZING,
            PipelinePhase.SCORING_CONFIDENCE: ResearchStatus.SYNTHESIZING,
            PipelinePhase.BUILDING_REPORT: ResearchStatus.SYNTHESIZING,
            PipelinePhase.COMPLETED: ResearchStatus.COMPLETED,
            PipelinePhase.FAILED: ResearchStatus.FAILED,
        }
        return mapping.get(phase, ResearchStatus.CREATED)

    async def _save_results(self, research: Research, state: PipelineState, db: Session):
        """Save final research results to database."""
        synthesis = state.synthesis_result
        confidence = state.confidence_result
        report = state.report

        # Save sources
        if state.source_collection:
            for src in state.source_collection.sources:
                db_source = ResearchSource(
                    research_id=research.id,
                    url=src.url,
                    title=src.title,
                    snippet=src.snippet,
                    source_type=src.source_type,
                    domain=src.domain,
                    credibility=src.credibility,
                    relevance=src.relevance,
                    author=src.author,
                    published_date=src.published_date,
                    metadata=src.metadata,
                )
                db.add(db_source)

        # Save claims and evidence
        if state.claims and state.verification_results:
            for i, claim_text in enumerate(state.claims):
                claim_id = f"claim_{i}"
                verification = next(
                    (v for v in state.verification_results if v.claim_id == claim_id),
                    None,
                )

                db_claim = ResearchClaim(
                    research_id=research.id,
                    claim_text=claim_text,
                    claim_id=claim_id,
                    status=verification.status if verification else "uncertain",
                    confidence=verification.confidence if verification else 0.0,
                    supporting_sources=verification.supporting_sources if verification else 0,
                    conflicting_sources=verification.conflicting_sources if verification else 0,
                    verification_details=verification.verification_details if verification else {},
                )
                db.add(db_claim)
                db.flush()  # Get claim ID

                # Save evidence for this claim
                if state.ranked_evidence:
                    ranked = next((r for r in state.ranked_evidence if r.claim_id == claim_id), None)
                    if ranked:
                        for ev in ranked.top_evidence:
                            db_evidence = ResearchEvidence(
                                research_id=research.id,
                                claim_id=db_claim.id,
                                source_url=ev.source_url,
                                source_title=ev.source_title,
                                source_type=ev.source_type,
                                evidence_text=ev.evidence_text,
                                evidence_type=ev.evidence_type,
                                supports_claim=ev.supports_claim,
                                relevance_score=ev.relevance_score,
                                confidence_score=ev.confidence_score,
                                quality_score=ev.quality_score,
                                authority_score=ev.authority_score,
                                recency_score=ev.recency_score,
                                specificity_score=ev.specificity_score,
                                corroboration_score=ev.corroboration_score,
                                final_score=ev.final_score,
                                rank=ev.rank,
                                citation_context=ev.citation_context,
                                metadata=ev.metadata,
                            )
                            db.add(db_evidence)

        # Save final research fields
        research.report = synthesis.executive_summary
        research.executive_summary = synthesis.executive_summary
        research.key_findings = synthesis.key_findings
        research.recommendations = synthesis.recommendations
        research.confidence_score = confidence.confidence_percentage / 100.0 if confidence else synthesis.confidence
        research.verified_claim_count = sum(
            1 for v in state.verification_results if v.status in ["verified", "likely"]
        )
        research.source_count = state.source_collection.total_count if state.source_collection else 0
        research.status = ResearchStatus.COMPLETED
        research.completed_at = datetime.utcnow()

        # Save detailed report as JSON
        if report:
            research.report_data = {
                "title": report.title,
                "executive_summary": report.executive_summary,
                "key_findings": report.key_findings,
                "detailed_findings": report.detailed_findings,
                "recommendations": report.recommendations,
                "methodology": report.methodology,
                "limitations": report.limitations,
                "sources": report.sources,
                "citations": report.citations,
                "confidence": report.confidence,
                "word_count": report.word_count,
                "page_count": report.page_count,
            }

        db.commit()

    async def get_research(self, research_id: int, user_id: int) -> Optional[Research]:
        """Get research by ID for user."""
        return self.db.query(Research).filter(
            Research.id == research_id,
            Research.user_id == user_id,
        ).first()

    async def get_research_status(self, research_id: int, user_id: int) -> Dict[str, Any]:
        """Get research status and progress."""
        research = await self.get_research(research_id, user_id)
        if not research:
            return {"error": "Research not found"}

        # Calculate progress from status if not set
        progress = getattr(research, 'progress', None)
        if progress is None:
            progress = self._calculate_progress(research.status)

        return {
            "id": research.id,
            "query": research.query,
            "status": research.status.value,
            "progress": progress,
            "source_count": research.source_count,
            "verified_claim_count": research.verified_claim_count,
            "confidence_score": research.confidence_score,
            "started_at": research.started_at.isoformat() if research.started_at else None,
            "completed_at": research.completed_at.isoformat() if research.completed_at else None,
            "error_message": research.error_message,
        }

    def _calculate_progress(self, status: ResearchStatus) -> int:
        """Calculate progress percentage."""
        progress_map = {
            ResearchStatus.CREATED: 0,
            ResearchStatus.PLANNING: 10,
            ResearchStatus.RESEARCHING: 30,
            ResearchStatus.COLLECTING_EVIDENCE: 50,
            ResearchStatus.VERIFYING: 65,
            ResearchStatus.ANALYZING: 80,
            ResearchStatus.SYNTHESIZING: 90,
            ResearchStatus.COMPLETED: 100,
            ResearchStatus.FAILED: 0,
        }
        return progress_map.get(status, 0)

    async def list_user_research(self, user_id: int) -> List[Research]:
        """List all research for a user."""
        return self.db.query(Research).filter(
            Research.user_id == user_id
        ).order_by(Research.created_at.desc()).all()

    async def get_research_report(self, research_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get full research report."""
        research = await self.get_research(research_id, user_id)
        if not research or research.status != ResearchStatus.COMPLETED:
            return None

        report_data = getattr(research, 'report_data', None)
        if report_data:
            return report_data

        # Fallback to basic fields
        return {
            "id": research.id,
            "query": research.query,
            "research_type": research.research_type.value,
            "executive_summary": research.executive_summary,
            "key_findings": research.key_findings,
            "recommendations": research.recommendations,
            "confidence_score": research.confidence_score,
            "source_count": research.source_count,
            "verified_claim_count": research.verified_claim_count,
            "completed_at": research.completed_at.isoformat() if research.completed_at else None,
        }

    async def get_research_details(self, research_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed research data including claims, evidence, sources."""
        research = await self.get_research(research_id, user_id)
        if not research:
            return None

        # Get sources
        sources = self.db.query(ResearchSource).filter(
            ResearchSource.research_id == research_id
        ).all()

        # Get claims
        claims = self.db.query(ResearchClaim).filter(
            ResearchClaim.research_id == research_id
        ).all()

        # Get evidence
        evidence = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.research_id == research_id
        ).all()

        return {
            "id": research.id,
            "user_id": research.user_id,
            "query": research.query,
            "research_type": research.research_type.value,
            "status": research.status.value,
            "progress": research.progress,
            "error_message": research.error_message,
            "executive_summary": research.executive_summary,
            "key_findings": research.key_findings,
            "recommendations": research.recommendations,
            "confidence_score": research.confidence_score,
            "source_count": len(sources),
            "verified_claim_count": len([
                c for c in claims
                if (c.status.value if hasattr(c.status, "value") else c.status) == "verified"
            ]),
            "sources": [
                {
                    "id": s.id,
                    "url": s.url,
                    "title": s.title,
                    "source_type": s.source_type.value if hasattr(s.source_type, "value") else s.source_type,
                    "domain": s.domain,
                    "credibility": s.credibility_score,
                    "relevance": s.relevance_score,
                    "author": s.author,
                    "published_date": s.published_date.isoformat() if s.published_date else None,
                }
                for s in sources
            ],
            "claims": [
                {
                    "id": c.id,
                    "claim_text": c.claim_text,
                    "claim_type": c.claim_type,
                    "status": c.status.value if hasattr(c.status, "value") else c.status,
                    "verified_by_sources": c.verified_by_sources,
                    "conflicting_sources": c.conflicting_sources,
                }
                for c in claims
            ],
            "evidence": [
                {
                    "id": e.id,
                    "claim_id": e.claim_id,
                    "evidence_text": e.evidence_text,
                    "evidence_type": e.evidence_type.value if hasattr(e.evidence_type, "value") else e.evidence_type,
                    "supports_claim": e.supports_claim,
                    "relevance_score": e.relevance_score,
                    "confidence_score": e.confidence_score,
                }
                for e in evidence
            ],
            "started_at": research.started_at.isoformat() if research.started_at else None,
            "completed_at": research.completed_at.isoformat() if research.completed_at else None,
            "created_at": research.created_at.isoformat() if research.created_at else None,
            "updated_at": research.updated_at.isoformat() if research.updated_at else None,
        }

    async def export_research_report(
        self,
        research_id: int,
        user_id: int,
        format: str = "markdown",
    ) -> Optional[str]:
        """Export research report in specified format."""
        research = await self.get_research(research_id, user_id)
        if not research or research.status != ResearchStatus.COMPLETED:
            return None

        # Get report data from either report_data field or report field (JSON string)
        report_data = None
        if getattr(research, 'report_data', None):
            report_data = research.report_data
        elif research.report:
            import json
            try:
                report_data = json.loads(research.report)
            except json.JSONDecodeError:
                pass
        
        if not report_data:
            return None

        # Reconstruct ResearchReport object
        from backend.agents.research.report_agent import ResearchReport
        report = ResearchReport(
            research_id=research.id,
            query=research.query,
            research_type=research.research_type.value,
            title=report_data.get("title", ""),
            executive_summary=report_data.get("executive_summary", ""),
            key_findings=report_data.get("key_findings", []),
            detailed_findings=report_data.get("detailed_findings", []),
            recommendations=report_data.get("recommendations", []),
            methodology=report_data.get("methodology", ""),
            limitations=report_data.get("limitations", []),
            sources=report_data.get("sources", []),
            citations=report_data.get("citations", []),
            confidence=report_data.get("confidence", 0.5),
        )

        if format == "markdown":
            return await self.report_agent.export_markdown(report)
        elif format == "html":
            return await self.report_agent.export_html(report)
        elif format == "pdf":
            pdf_bytes = await self.report_agent.export_pdf(report)
            return pdf_bytes.decode('utf-8') if isinstance(pdf_bytes, bytes) else str(pdf_bytes)

        return None

    async def cancel_research(self, research_id: int, user_id: int) -> bool:
        """Cancel a running research."""
        research = await self.get_research(research_id, user_id)
        if not research:
            return False

        if research.status in [ResearchStatus.COMPLETED, ResearchStatus.FAILED]:
            return False

        research.status = ResearchStatus.FAILED
        research.error_message = "Cancelled by user"
        self.db.commit()
        return True