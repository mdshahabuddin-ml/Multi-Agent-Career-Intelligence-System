from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import asyncio
import logging

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_data_pipeline(self, source_id: str, collector_kwargs: dict = None, limit: int = None):
    """
    Run the data ingestion pipeline for a specific source.
    
    This task runs the complete pipeline: collect → normalize → deduplicate 
    → validate → quality_score → persist → rag_ingest
    """
    try:
        logger.info(f"Starting data pipeline for source: {source_id}")
        
        from backend.data_pipeline import IngestionPipeline
        from backend.data_pipeline.collectors import (
            MockJobCollector, MockCompanyCollector, MockNewsCollector,
            MockResearchCollector, MockSkillCollector, MockCourseCollector,
            MockMarketTrendCollector,
        )
        from backend.database import get_db
        from backend.config import settings
        
        db = next(get_db())
        
        # Initialize pipeline
        pipeline = IngestionPipeline(db_session=db)
        
        # Register collectors if in mock mode
        if settings.MOCK_DATA:
            collectors = {
                "mock_jobs": MockJobCollector(),
                "mock_companies": MockCompanyCollector(),
                "mock_news": MockNewsCollector(),
                "mock_research": MockResearchCollector(),
                "mock_skills": MockSkillCollector(),
                "mock_courses": MockCourseCollector(),
                "mock_market_trends": MockMarketTrendCollector(),
            }
            for name, collector in collectors.items():
                pipeline.register_collector(collector)
        
        # Check if source exists
        from backend.data_pipeline.sources.source_registry import SourceRegistry
        registry = SourceRegistry(db_session=db)
        source_config = registry.get(source_id)
        if not source_config:
            raise ValueError(f"Source not found: {source_id}")
        
        if not source_config.enabled:
            raise ValueError(f"Source is disabled: {source_id}")
        
        # Run pipeline
        collector_kwargs = collector_kwargs or {}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                pipeline.run(
                    source_id=source_id,
                    collector_kwargs=collector_kwargs,
                    limit=limit,
                )
            )
        finally:
            loop.close()
        
        # Update source registry status
        registry.update_status(source_id, result.overall_success)
        
        logger.info(
            f"Data pipeline completed for {source_id}: "
            f"{result.total_records_saved} saved, "
            f"{result.total_duplicates_found} duplicates, "
            f"{result.total_records_rejected} rejected"
        )
        
        return result.to_dict()
        
    except Exception as exc:
        logger.error(f"Data pipeline failed for {source_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def run_all_enabled_pipelines(self):
    """Run data pipeline for all enabled sources."""
    try:
        logger.info("Starting data pipeline for all enabled sources")
        
        from backend.data_pipeline import IngestionPipeline
        from backend.data_pipeline.collectors import (
            MockJobCollector, MockCompanyCollector, MockNewsCollector,
            MockResearchCollector, MockSkillCollector, MockCourseCollector,
            MockMarketTrendCollector,
        )
        from backend.database import get_db
        from backend.config import settings
        
        db = next(get_db())
        registry = SourceRegistry(db_session=db)
        enabled_sources = registry.list_enabled()
        
        if not enabled_sources:
            logger.warning("No enabled sources found")
            return {"status": "completed", "message": "No enabled sources", "results": []}
        
        results = []
        for source in enabled_sources:
            try:
                pipeline = IngestionPipeline(db_session=db)
                
                # Register collectors if in mock mode
                if settings.MOCK_DATA:
                    collectors = {
                        "mock_jobs": MockJobCollector(),
                        "mock_companies": MockCompanyCollector(),
                        "mock_news": MockNewsCollector(),
                        "mock_research": MockResearchCollector(),
                        "mock_skills": MockSkillCollector(),
                        "mock_courses": MockCourseCollector(),
                        "mock_market_trends": MockMarketTrendCollector(),
                    }
                    for name, collector in collectors.items():
                        pipeline.register_collector(collector)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        pipeline.run(
                            source_id=source.source_id,
                            limit=None,  # Use source's default
                        )
                    )
                finally:
                    loop.close()
                
                registry.update_status(source.source_id, result.overall_success)
                results.append(result.to_dict())
                
            except Exception as e:
                logger.error(f"Pipeline failed for source {source.source_id}: {e}")
                results.append({
                    "source_id": source.source_id,
                    "error": str(e),
                    "success": False,
                })
        
        success_count = sum(1 for r in results if r.get("overall_success", False))
        logger.info(f"Completed pipelines for {success_count}/{len(enabled_sources)} sources")
        
        return {
            "status": "completed",
            "total_sources": len(enabled_sources),
            "successful": success_count,
            "failed": len(enabled_sources) - success_count,
            "results": results,
        }
        
    except Exception as exc:
        logger.error(f"Batch pipeline run failed: {exc}")
        raise


@shared_task
def cleanup_pipeline_data():
    """Clean up old pipeline data (optional maintenance task)."""
    logger.info("Cleaning up old pipeline data")
    
    from backend.database import get_db
    from datetime import datetime, timedelta
    
    db = next(get_db())
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    # This would clean up old pipeline run records, etc.
    # For now, just return success
    logger.info("Pipeline data cleanup completed")
    return {"status": "completed", "cleaned": 0}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_source_health_checks(self):
    """Run health checks on all configured sources."""
    try:
        logger.info("Running source health checks")
        
        from backend.data_pipeline.collectors import (
            MockJobCollector, MockCompanyCollector, MockNewsCollector,
            MockResearchCollector, MockSkillCollector, MockCourseCollector,
            MockMarketTrendCollector,
        )
        from backend.database import get_db
        from backend.config import settings
        
        db = next(get_db())
        registry = SourceRegistry(db_session=db)
        all_sources = registry.list_all()
        
        collectors = {}
        if settings.MOCK_DATA:
            collectors = {
                "mock_jobs": MockJobCollector(),
                "mock_companies": MockCompanyCollector(),
                "mock_news": MockNewsCollector(),
                "mock_research": MockResearchCollector(),
                "mock_skills": MockSkillCollector(),
                "mock_courses": MockCourseCollector(),
                "mock_market_trends": MockMarketTrendCollector(),
            }
        
        health_results = []
        for source in all_sources:
            collector = collectors.get(source.source_id)
            if collector:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    health = loop.run_until_complete(collector.health_check())
                finally:
                    loop.close()
                
                health_results.append({
                    "source_id": source.source_id,
                    "name": source.name,
                    "status": health.value,
                    "enabled": source.enabled,
                    "last_success": source.last_success.isoformat() if source.last_success else None,
                    "consecutive_failures": source.consecutive_failures,
                })
            else:
                health_results.append({
                    "source_id": source.source_id,
                    "name": source.name,
                    "status": "unknown",
                    "message": "No collector registered",
                })
        
        logger.info(f"Health checks completed for {len(health_results)} sources")
        return {"status": "completed", "sources": health_results}
        
    except Exception as exc:
        logger.error(f"Health checks failed: {exc}")
        raise