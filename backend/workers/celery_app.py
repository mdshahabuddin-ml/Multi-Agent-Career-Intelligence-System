from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from kombu import Queue
import os
from dotenv import load_dotenv

load_dotenv()

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Create Celery app
celery_app = Celery(
    "careerintel",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "backend.workers.research_worker",
        "backend.workers.job_worker",
        "backend.workers.document_worker",
        "backend.workers.embedding_worker",
        "backend.workers.notification_worker",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "backend.workers.research_worker.*": {"queue": "research"},
        "backend.workers.job_worker.*": {"queue": "jobs"},
        "backend.workers.document_worker.*": {"queue": "documents"},
        "backend.workers.embedding_worker.*": {"queue": "embeddings"},
        "backend.workers.notification_worker.*": {"queue": "notifications"},
    },
    
    # Queue configuration
    task_create_missing_queues=True,
    task_default_queue="default",
    task_queues={
        "default": Queue("default", routing_key="default"),
        "research": Queue("research", routing_key="research"),
        "jobs": Queue("jobs", routing_key="jobs"),
        "documents": Queue("documents", routing_key="documents"),
        "embeddings": Queue("embeddings", routing_key="embeddings"),
        "notifications": Queue("notifications", routing_key="notifications"),
    },
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=4,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    
    # Result settings
    result_expires=86400,  # 24 hours
    result_compression="gzip",
    
    # Serialization
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    
    # Worker settings
    worker_max_tasks_per_child=100,
    worker_disable_rate_limits=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-tasks": {
            "task": "backend.workers.maintenance.cleanup_expired_tasks",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-results": {
            "task": "backend.workers.maintenance.cleanup_old_results",
            "schedule": 86400.0,  # Daily
        },
        "sync-job-listings": {
            "task": "backend.workers.job_worker.sync_job_listings",
            "schedule": 14400.0,  # Every 4 hours
        },
        "generate-embeddings": {
            "task": "backend.workers.embedding_worker.generate_pending_embeddings",
            "schedule": 1800.0,  # Every 30 minutes
        },
        "send-notifications": {
            "task": "backend.workers.notification_worker.send_pending_notifications",
            "schedule": 300.0,  # Every 5 minutes
        },
        "update-job-recommendations": {
            "task": "backend.workers.job_worker.update_job_recommendations",
            "schedule": 3600.0,  # Every hour
        },
    },
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
)


@worker_ready.connect
def on_worker_ready(**kwargs):
    print("Worker ready")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    print("Worker shutting down")


def get_celery_app():
    """Get the Celery app instance."""
    return celery_app


if __name__ == "__main__":
    celery_app.start()