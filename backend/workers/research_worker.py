from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime
import asyncio
import logging

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def start_research_task(self, research_id: int):
    """Start a research task in the background."""
    try:
        logger.info(f"Starting research task for research_id: {research_id}")
        
        # Import here to avoid circular imports
        from backend.services.research_service import ResearchService
        from backend.database import get_db
        
        db = next(get_db())
        research_service = ResearchService(db)
        
        # Run the async research
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                research_service._run_research(research_id)
            )
            logger.info(f"Research completed for research_id: {research_id}")
            return {"status": "completed", "research_id": research_id, "result": result}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Research task failed for research_id {research_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def collect_sources_task(self, research_id: int, queries: list):
    """Collect sources for a research task."""
    try:
        logger.info(f"Collecting sources for research_id: {research_id}")
        
        from backend.research_engine.sources.source_manager import SourceManager
        
        source_manager = SourceManager()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            sources = loop.run_until_complete(
                source_manager.collect_sources(queries)
            )
            logger.info(f"Collected {len(sources)} sources for research_id: {research_id}")
            return {"status": "completed", "sources_count": len(sources)}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Source collection failed for research_id {research_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def verify_claims_task(self, research_id: int, claims: list):
    """Verify claims for a research task."""
    try:
        logger.info(f"Verifying claims for research_id: {research_id}")
        
        from backend.research_engine.verification.fact_checker import FactChecker
        
        fact_checker = FactChecker()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            verification_results = loop.run_until_complete(
                fact_checker.verify_claims(claims)
            )
            logger.info(f"Verified {len(verification_results)} claims for research_id: {research_id}")
            return {"status": "completed", "verifications": verification_results}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Claim verification failed for research_id {research_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def synthesize_report_task(self, research_id: int):
    """Synthesize final research report."""
    try:
        logger.info(f"Synthesizing report for research_id: {research_id}")
        
        from backend.research_engine.synthesis.research_synthesizer import ResearchSynthesizer
        
        synthesizer = ResearchSynthesizer()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report = loop.run_until_complete(
                synthesizer.synthesize(research_id)
            )
            logger.info(f"Report synthesized for research_id: {research_id}")
            return {"status": "completed", "report": report}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Report synthesis failed for research_id {research_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def generate_report_task(self, research_id: int, format: str = "markdown"):
    """Generate final report in specified format."""
    try:
        logger.info(f"Generating {format} report for research_id: {research_id}")
        
        from backend.agents.research.report_agent import ReportAgent
        from backend.database import get_db
        from backend.models import Research
        
        db = next(get_db())
        research = db.query(Research).filter(Research.id == research_id).first()
        
        if not research:
            raise ValueError(f"Research {research_id} not found")
        
        report_agent = ReportAgent()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report = loop.run_until_complete(
                ReportAgent().generate_report(
                    research_id=research_id,
                    query=research.query,
                    research_type=research.research_type.value,
                    synthesis_result={},
                    sources=research.sources or [],
                    verification_results=[],
                )
            )
            
            if format == "html":
                content = asyncio.run(ReportAgent().export_html(report))
            elif format == "pdf":
                content = asyncio.run(ReportAgent().export_pdf(report))
            else:
                content = asyncio.run(ReportAgent().export_markdown(report))
            
            logger.info(f"Report generated for research_id: {research_id}")
            return {"status": "completed", "format": format, "content_length": len(content)}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Report generation failed for research_id {research_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cancel_research_task(research_id: int):
    """Cancel a running research task."""
    logger.info(f"Cancelling research task for research_id: {research_id}")
    # Implementation would mark research as cancelled in DB
    return {"status": "cancelled", "research_id": research_id}


# Periodic tasks
@shared_task
def cleanup_stale_research():
    """Clean up stale research tasks that have been running too long."""
    logger.info("Cleaning up stale research tasks")
    # Implementation would check for tasks running > threshold and mark as failed
    return {"status": "completed", "cleaned": 0}