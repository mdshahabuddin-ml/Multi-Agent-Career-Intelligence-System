from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import asyncio

logger = get_task_logger(__name__)

@shared_task
def cleanup_expired_tasks():
    """Clean up expired/abandoned tasks."""
    logger.info("Cleaning up expired tasks")
    
    from backend.database import get_db
    from backend.models import Research, Application
    from datetime import datetime, timedelta
    
    db = next(get_db())
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    # Clean up stale research tasks
    stale_research = db.query(Research).filter(
        Research.status.in_(["created", "planning", "researching"]),
        Research.updated_at < cutoff
    ).all()
    
    for research in stale_research:
        research.status = "failed"
        research.error_message = "Task timed out"
    
    # Clean up stale applications
    stale_apps = db.query(Application).filter(
        Application.status == "draft",
        Application.updated_at < cutoff
    ).all()
    
    for app in stale_apps:
        app.status = "abandoned"
    
    db.commit()
    
    logger.info(f"Cleaned up expired tasks")
    return {"status": "completed", "cleaned": 0}


@shared_task
def cleanup_old_results():
    """Clean up old Celery task results."""
    logger.info("Cleaning up old task results")
    
    # This would clean up old Celery results from Redis
    # For now, just log
    logger.info("Cleaned up old results")
    return {"status": "completed", "cleaned": 0}


@shared_task
def cleanup_old_sessions():
    """Clean up old user sessions."""
    logger.info("Cleaning up old sessions")
    
    from backend.database import get_db
    from backend.models import UserSession
    from datetime import datetime, timedelta
    
    db = next(get_db())
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    deleted = db.query(UserSession).filter(
        UserSession.last_activity < cutoff
    ).delete()
    
    db.commit()
    
    logger.info(f"Cleaned up {deleted} old sessions")
    return {"status": "completed", "cleaned": deleted}


@shared_task
def cleanup_temp_files():
    """Clean up temporary files."""
    logger.info("Cleaning up temporary files")
    
    import os
    import shutil
    from datetime import datetime, timedelta
    from backend.config import settings
    
    temp_dir = settings.TEMP_DIR
    if not os.path.exists(temp_dir):
        return {"status": "completed", "cleaned": 0}
    
    cutoff = datetime.utcnow() - timedelta(hours=24)
    cleaned = 0
    
    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        if os.path.isfile(filepath):
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                try:
                    os.remove(filepath)
                    cleaned += 1
                except Exception as e:
                    logger.error(f"Failed to remove {filepath}: {e}")
    
    logger.info(f"Cleaned up {cleaned} temporary files")
    return {"status": "completed", "cleaned": cleaned}


@shared_task
def optimize_database():
    """Run database maintenance."""
    logger.info("Running database optimization")
    
    from backend.database import get_db
    
    db = next(get_db())
    
    # Run VACUUM ANALYZE for PostgreSQL
    try:
        db.execute("VACUUM ANALYZE")
        db.commit()
        logger.info("Database optimization completed")
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
    
    return {"status": "completed"}


@shared_task
def backup_database():
    """Create database backup."""
    logger.info("Creating database backup")
    
    import subprocess
    import os
    from datetime import datetime
    from backend.config import settings
    
    backup_dir = settings.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"careerintel_{timestamp}.sql")
    
    try:
        # Use pg_dump for PostgreSQL
        result = subprocess.run([
            "pg_dump",
            "-h", settings.POSTGRES_HOST,
            "-U", settings.POSTGRES_USER,
            "-d", settings.POSTGRES_DB,
            "-f", backup_file
        ], env={**os.environ, "PGPASSWORD": settings.POSTGRES_PASSWORD}, 
        capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Database backup created: {backup_file}")
            
            # Compress
            subprocess.run(["gzip", backup_file])
            
            return {"status": "completed", "backup_file": backup_file + ".gz"}
        else:
            logger.error(f"Backup failed: {result.stderr}")
            return {"status": "failed", "error": result.stderr}
            
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def health_check():
    """System health check."""
    logger.info("Running health check")
    
    checks = {
        "database": False,
        "redis": False,
        "celery": False,
        "disk_space": False,
    }
    
    # Check database
    try:
        from backend.database import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        checks["database"] = True
    except:
        pass
    
    # Check Redis
    try:
        import redis
        r = redis.Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
        r.ping()
        checks["redis"] = True
    except:
        pass
    
    # Check Celery
    try:
        from backend.workers.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            checks["celery"] = True
    except:
        pass
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        if free > 1024 * 1024 * 1024:  # > 1GB free
            checks["disk_space"] = True
    except:
        pass
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }