"""
Video Worker - Celery tasks for async video generation pipeline.
"""

from __future__ import annotations

import asyncio
import logging

from backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="backend.workers.video_worker.generate_video",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_video(self, pipeline_id: int, content_id: int, user_id: int):
    """Generate video for a pipeline (sync wrapper for async skill)."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _generate_video_async(pipeline_id, content_id, user_id)
            )
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error("Video generation failed for pipeline %d: %s", pipeline_id, exc)
        raise self.retry(exc=exc)


async def _generate_video_async(pipeline_id: int, content_id: int, user_id: int):
    """Async video generation using the VideoGenerationSkill."""
    from backend.database import SessionLocal
    from backend.hermes_engine.skills.video_generation import VideoGenerationSkill

    db = SessionLocal()
    try:
        skill = VideoGenerationSkill(db)
        pipeline = await skill.run_pipeline(content_id, user_id)
        return {
            "success": True,
            "pipeline_id": pipeline.id,
            "status": pipeline.status,
            "video_url": pipeline.video_url,
        }
    finally:
        db.close()


@celery_app.task(name="backend.workers.video_worker.retry_failed_pipelines")
def retry_failed_pipelines():
    """Periodic task to retry failed video pipelines."""
    from backend.database import SessionLocal
    from backend.models.video_pipeline import VideoPipeline

    db = SessionLocal()
    try:
        failed = db.query(VideoPipeline).filter(
            VideoPipeline.status == "failed",
            VideoPipeline.retry_count < 3,
        ).all()

        for pipeline in failed:
            generate_video.delay(
                pipeline.id, pipeline.content_id, pipeline.user_id
            )
            logger.info("Retrying video pipeline %d", pipeline.id)

        return {"retried": len(failed)}
    finally:
        db.close()
