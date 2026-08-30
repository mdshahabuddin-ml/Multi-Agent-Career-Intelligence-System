from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
import asyncio
import logging

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(self, to_email: str, subject: str, body: str, template: str = None):
    """Send an email notification."""
    try:
        logger.info(f"Sending email to {to_email}")
        
        from backend.services.notification_service import NotificationService
        from backend.database import get_db
        
        db = next(get_db())
        notification_service = NotificationService(db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                notification_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    template=template
                )
            )
            return {"status": "sent", "email": to_email}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Email sending failed to {to_email}: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_push_notification(self, user_id: int, title: str, body: str, data: dict = None):
    """Send push notification to user."""
    try:
        logger.info(f"Sending push notification to user {user_id}")
        
        # Would integrate with Firebase/OneSignal/APNs
        # For now, just log
        logger.info(f"Push notification sent to user {user_id}: {title}")
        
        return {"status": "sent", "user_id": user_id}
        
    except Exception as exc:
        logger.error(f"Push notification failed for user {user_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_in_app_notification(self, user_id: int, title: str, message: str, 
                              action_url: str = None, notification_type: str = "info"):
    """Create in-app notification."""
    try:
        logger.info(f"Creating in-app notification for user {user_id}")
        
        from backend.services.notification_service import NotificationService
        from backend.database import get_db
        
        db = next(get_db())
        notification_service = NotificationService(db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            notification = loop.run_until_complete(
                notification_service.create_notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    action_url=action_url,
                    notification_type=notification_type
                )
            )
            return {"status": "created", "notification_id": notification.id}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"In-app notification creation failed: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_bulk_notifications(self, user_ids: list, title: str, message: str, 
                            notification_type: str = "info", action_url: str = None):
    """Send notifications to multiple users."""
    try:
        logger.info(f"Sending bulk notifications to {len(user_ids)} users")
        
        from backend.services.notification_service import NotificationService
        from backend.database import get_db
        
        db = next(get_db())
        notification_service = NotificationService(db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                notification_service.send_bulk_notifications(
                    user_ids=user_ids,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    action_url=action_url
                )
            )
            return {"status": "completed", "sent": len(results)}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Bulk notification failed: {exc}")
        raise


@shared_task
def send_daily_digest():
    """Send daily digest emails to users."""
    logger.info("Sending daily digests")
    
    from backend.services.notification_service import NotificationService
    from backend.database import get_db
    from backend.models import User
    
    db = next(get_db())
    notification_service = NotificationService(db)
    
    # Get users who want daily digests
    users = db.query(User).filter(
        User.is_active == True,
        User.email_notifications == True
    ).all()
    
    sent = 0
    for user in users:
        try:
            # Generate personalized digest
            digest = generate_daily_digest(user)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    notification_service.send_email(
                        to_email=user.email,
                        subject="Your Daily Career Digest",
                        body=digest,
                        template="daily_digest"
                    )
                )
                sent += 1
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Failed to send digest to {user.email}: {e}")
    
    logger.info(f"Sent daily digests to {sent} users")
    return {"status": "completed", "sent": sent}


@shared_task
def send_weekly_digest():
    """Send weekly digest emails."""
    logger.info("Sending weekly digests")
    # Similar to daily digest but weekly
    return {"status": "completed", "sent": 0}


@shared_task
def send_job_alerts():
    """Send job alert notifications to users."""
    logger.info("Sending job alerts")
    
    from backend.services.job_service import JobService
    from backend.services.notification_service import NotificationService
    from backend.database import get_db
    from backend.models import User, JobAlert
    
    db = next(get_db())
    job_service = JobService(db)
    notification_service = NotificationService(db)
    
    # Get active job alerts
    alerts = db.query(JobAlert).filter(JobAlert.is_active == True).all()
    
    sent = 0
    for alert in alerts:
        try:
            # Find matching jobs
            jobs = job_service.search_jobs(
                query=alert.query,
                location=alert.location,
                remote=alert.remote,
                limit=10
            )
            
            if jobs:
                # Send notification
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        notification_service.send_job_alert(
                            user_id=alert.user_id,
                            jobs=jobs[:5],  # Top 5 matches
                            alert_name=alert.name
                        )
                    )
                    sent += 1
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"Failed to send job alert to user {alert.user_id}: {e}")
    
    return {"status": "completed", "alerts_sent": sent}


@shared_task
def send_application_status_notification(application_id: int, old_status: str, new_status: str):
    """Notify user of application status change."""
    try:
        from backend.database import get_db
        from backend.models import Application, User
        from backend.services.notification_service import NotificationService
        
        db = next(get_db())
        app = db.query(Application).filter(Application.id == application_id).first()
        
        if not app:
            return {"status": "error", "message": "Application not found"}
        
        user = db.query(User).filter(User.id == app.user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Generate notification message
        messages = {
            "submitted": "Your application has been submitted successfully.",
            "under_review": "Your application is under review.",
            "interview_scheduled": "An interview has been scheduled!",
            "interview_completed": "Your interview has been completed.",
            "offer_received": "Congratulations! You received an offer!",
            "offer_accepted": "Offer accepted! Congratulations!",
            "rejected": "Your application was not selected this time.",
        }
        
        message = messages.get(new_status, f"Your application status changed to {new_status}.")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from backend.services.notification_service import NotificationService
            from backend.database import get_db
            db = next(get_db())
            notification_service = NotificationService(db)
            
            loop.run_until_complete(
                notification_service.create_notification(
                    user_id=app.user_id,
                    title=f"Application Update: {app.job.title}",
                    message=message,
                    action_url=f"/applications/{application_id}",
                    notification_type="application_update"
                )
            )
        finally:
            loop.close()
        
        return {"status": "sent", "application_id": application_id}
        
    except Exception as exc:
        logger.error(f"Application status notification failed: {exc}")
        raise


@shared_task
def send_application_submitted_notification(application_id: int):
    """Notify user that application was submitted."""
    return send_application_status_notification(application_id, "draft", "submitted")


@shared_task
def send_interview_scheduled_notification(application_id: int, interview_date: str, interview_type: str):
    """Notify user of scheduled interview."""
    try:
        from backend.database import get_db
        from backend.models import Application, User
        from backend.services.notification_service import NotificationService
        
        db = next(get_db())
        app = db.query(Application).filter(Application.id == application_id).first()
        
        if not app:
            return {"status": "error", "message": "Application not found"}
        
        user = db.query(User).filter(User.id == app.user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        message = f"Interview scheduled for {interview_date} ({interview_type}). Good luck!"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from backend.services.notification_service import NotificationService
            from backend.database import get_db
            db = next(get_db())
            notification_service = NotificationService(db)
            
            loop.run_until_complete(
                notification_service.create_notification(
                    user_id=app.user_id,
                    title=f"Interview Scheduled: {app.job.title}",
                    message=message,
                    action_url=f"/applications/{application_id}",
                    notification_type="interview_scheduled"
                )
            )
        finally:
            loop.close()
        
        return {"status": "sent", "application_id": application_id}
        
    except Exception as exc:
        logger.error(f"Interview notification failed: {exc}")
        raise


@shared_task
def send_offer_notification(application_id: int, offer_details: dict):
    """Notify user of job offer."""
    try:
        from backend.database import get_db
        from backend.models import Application, User
        from backend.services.notification_service import NotificationService
        
        db = next(get_db())
        app = db.query(Application).filter(Application.id == application_id).first()
        
        if not app:
            return {"status": "error", "message": "Application not found"}
        
        user = db.query(User).filter(User.id == app.user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        message = f"Congratulations! You received an offer for {app.job.title}. Details: {offer_details}"
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from backend.services.notification_service import NotificationService
            from backend.database import get_db
            db = next(get_db())
            notification_service = NotificationService(db)
            
            loop.run_until_complete(
                notification_service.create_notification(
                    user_id=app.user_id,
                    title=f"Job Offer: {app.job.title}",
                    message=f"Congratulations! You received an offer for {app.job.title}. Details: {offer_details}",
                    action_url=f"/applications/{application_id}",
                    notification_type="offer_received"
                )
            )
        finally:
            loop.close()
        
        return {"status": "sent", "application_id": application_id}
        
    except Exception as exc:
        logger.error(f"Offer notification failed: {exc}")
        raise


@shared_task
def cleanup_old_notifications():
    """Clean up old read notifications."""
    logger.info("Cleaning up old notifications")
    
    from backend.database import get_db
    from backend.models import Notification
    from datetime import datetime, timedelta
    
    db = next(get_db())
    cutoff = datetime.utcnow() - timedelta(days=90)
    
    # Delete old read notifications
    deleted = db.query(Notification).filter(
        Notification.is_read == True,
        Notification.read_at < cutoff
    ).delete()
    
    db.commit()
    
    logger.info(f"Cleaned up {deleted} old notifications")
    return {"status": "completed", "deleted": deleted}


def generate_daily_digest(user):
    """Generate daily digest content for user."""
    # Would generate personalized digest
    return f"Daily digest for {user.full_name}"