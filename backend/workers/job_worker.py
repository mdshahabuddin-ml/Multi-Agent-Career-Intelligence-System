from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import asyncio
import logging

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_job_listings(self):
    """Sync job listings from external sources."""
    try:
        logger.info("Starting job listings sync")
        
        from backend.services.job_service import JobService
        from backend.database import get_db
        
        db = next(get_db())
        job_service = JobService(db)
        
        # This would call external APIs to fetch jobs
        # For now, we'll simulate the sync
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # In production, this would call external APIs like:
            # - LinkedIn Jobs API
            # - Indeed API
            # - Glassdoor API
            # - Company career pages
            # - Job board APIs
            
            synced_count = 0
            # Example: synced_count = await job_service.sync_from_sources()
            
            logger.info(f"Job listings sync completed. Synced {synced_count} jobs.")
            return {"status": "completed", "synced_count": synced_count}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Job listings sync failed: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_job_recommendations(self):
    """Update job recommendations for all users."""
    try:
        logger.info("Updating job recommendations for all users")
        
        from backend.services.job_service import JobService
        from backend.database import get_db
        from backend.models import User
        
        db = next(get_db())
        job_service = JobService(db)
        
        users = db.query(User).filter(User.is_active == True).all()
        updated_count = 0
        
        for user in users:
            try:
                # Get personalized recommendations
                recommendations = job_service.get_personalized_recommendations(
                    user_id=user.id,
                    limit=20
                )
                # Store/update recommendations in DB or cache
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update recommendations for user {user.id}: {e}")
        
        logger.info(f"Updated job recommendations for {updated_count} users")
        return {"status": "completed", "updated_count": updated_count}
        
    except Exception as exc:
        logger.error(f"Job recommendations update failed: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_job_from_source(self, source: str, params: dict = None):
    """Sync jobs from a specific source."""
    try:
        logger.info(f"Syncing jobs from source: {source}")
        
        from backend.agents.jobs.job_search_agent import JobSearchAgent
        
        search_agent = JobSearchAgent()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            jobs = loop.run_until_complete(
                search_agent.search(
                    query=params.get("query", ""),
                    location=params.get("location"),
                    remote=params.get("remote"),
                    limit=params.get("limit", 50)
                )
            )
            
            # Save jobs to database
            from backend.services.job_service import JobService
            from backend.database import get_db
            
            db = next(get_db())
            job_service = JobService(db)
            
            saved_count = 0
            for job in jobs:
                # Save or update job
                pass  # Implementation would save jobs
                saved_count += 1
            
            logger.info(f"Synced {saved_count} jobs from {source}")
            return {"status": "completed", "source": source, "saved_count": saved_count}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Job sync from {source} failed: {exc}")
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def update_job_recommendations(self, user_id: int = None):
    """Update job recommendations for a specific user or all users."""
    try:
        logger.info(f"Updating job recommendations for user_id: {user_id or 'all'}")
        
        from backend.services.job_service import JobService
        from backend.database import get_db
        from backend.models import User
        
        db = next(get_db())
        job_service = JobService(db)
        
        if user_id:
            users = [db.query(User).filter(User.id == user_id).first()]
        else:
            users = db.query(User).filter(User.is_active == True).all()
        
        updated = 0
        for user in users:
            if not user:
                continue
            try:
                recommendations = job_service.get_personalized_recommendations(
                    user_id=user.id,
                    limit=20
                )
                # Cache recommendations
                updated += 1
            except Exception as e:
                logger.error(f"Failed to update recommendations for user {user.id}: {e}")
        
        logger.info(f"Updated recommendations for {updated} users")
        return {"status": "completed", "updated": updated}
        
    except Exception as exc:
        logger.error(f"Job recommendations update failed: {exc}")
        raise


@shared_task
def cleanup_old_jobs():
    """Clean up old/expired job listings."""
    logger.info("Cleaning up old job listings")
    
    from backend.database import get_db
    from backend.models import Job
    from datetime import datetime, timedelta
    
    db = next(get_db())
    cutoff = datetime.utcnow() - timedelta(days=90)
    
    # Deactivate old jobs
    old_jobs = db.query(Job).filter(
        Job.posted_date < cutoff,
        Job.is_active == True
    ).all()
    
    count = 0
    for job in old_jobs:
        job.is_active = False
        count += 1
    
    db.commit()
    
    logger.info(f"Deactivated {count} old job listings")
    return {"status": "completed", "deactivated_count": count}


@shared_task
def reindex_jobs():
    """Reindex jobs in search index."""
    logger.info("Reindexing jobs")
    # Would integrate with Elasticsearch/Meilisearch
    return {"status": "completed", "reindexed": 0}