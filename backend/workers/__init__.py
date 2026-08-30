from backend.workers.celery_app import celery_app, get_celery_app
from backend.workers.research_worker import (
    start_research_task,
    collect_sources_task,
    verify_claims_task,
    synthesize_report_task,
    generate_report_task,
    cancel_research_task,
    cleanup_stale_research,
)
from backend.workers.job_worker import (
    sync_job_listings,
    update_job_recommendations,
    sync_job_from_source,
    cleanup_old_jobs,
    reindex_jobs,
)
from backend.workers.document_worker import (
    parse_document_task,
    extract_entities_task,
    extract_resume_sections_task,
    cleanup_old_documents,
)
from backend.workers.embedding_worker import (
    generate_embedding_task,
    generate_batch_embeddings_task,
    generate_document_embeddings,
    generate_query_embedding,
    generate_pending_embeddings,
)
from backend.workers.notification_worker import (
    send_email_notification,
    send_push_notification,
    send_in_app_notification,
    send_bulk_notifications,
    send_daily_digest,
    send_weekly_digest,
    send_job_alerts,
    send_application_status_notification,
    send_application_submitted_notification,
    send_interview_scheduled_notification,
    send_offer_notification,
    cleanup_old_notifications,
    generate_daily_digest,
)
from backend.workers.maintenance import (
    cleanup_expired_tasks,
    cleanup_old_results,
    cleanup_old_sessions,
    cleanup_temp_files,
    optimize_database,
    backup_database,
    health_check,
)

__all__ = [
    "celery_app",
    "get_celery_app",
    # Research tasks
    "start_research_task",
    "collect_sources_task",
    "verify_claims_task",
    "synthesize_report_task",
    "generate_report_task",
    "cancel_research_task",
    "cleanup_stale_research",
    # Job tasks
    "sync_job_listings",
    "update_job_recommendations",
    "sync_job_from_source",
    "cleanup_old_jobs",
    "reindex_jobs",
    # Document tasks
    "parse_document_task",
    "extract_entities_task",
    "extract_resume_sections_task",
    "cleanup_old_documents",
    # Embedding tasks
    "generate_embedding_task",
    "generate_batch_embeddings_task",
    "generate_document_embeddings",
    "generate_query_embedding",
    "generate_pending_embeddings",
    # Notification tasks
    "send_email_notification",
    "send_push_notification",
    "send_in_app_notification",
    "send_bulk_notifications",
    "send_daily_digest",
    "send_weekly_digest",
    "send_job_alerts",
    "send_application_status_notification",
    "send_application_submitted_notification",
    "send_interview_scheduled_notification",
    "send_offer_notification",
    "cleanup_old_notifications",
    "generate_daily_digest",
    # Maintenance tasks
    "cleanup_expired_tasks",
    "cleanup_old_results",
    "cleanup_old_sessions",
    "cleanup_temp_files",
    "optimize_database",
    "backup_database",
    "health_check",
]