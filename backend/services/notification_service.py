import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx

from sqlalchemy.orm import Session
from fastapi import Depends

from backend.models import Notification, User, UserPreference, NotificationChannel, NotificationType, NotificationPriority
from backend.database import get_db
from backend.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via multiple channels."""

    def __init__(self, db: Session):
        self.db = db

    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create and send notification via all enabled channels."""
        # Create in-app notification
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            action_url=action_url,
            action_label=action_label,
            notification_metadata=metadata or {},
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        # Get user preferences
        preferences = self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()

        if not preferences:
            return notification

        # Send via enabled channels
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return notification

        channels_to_send = self._get_enabled_channels(preferences, notification_type)

        for channel in channels_to_send:
            try:
                await self._send_via_channel(
                    channel=channel,
                    user=user,
                    preferences=preferences,
                    notification=notification,
                )
            except Exception as e:
                logger.error(f"Failed to send notification via {channel}: {e}")

        return notification

    def _get_enabled_channels(
        self,
        preferences: UserPreference,
        notification_type: NotificationType,
    ) -> List[NotificationChannel]:
        """Determine which channels to send notification to."""
        channels = []

        if preferences.email_notifications:
            channels.append(NotificationChannel.EMAIL)
        if preferences.push_notifications:
            channels.append(NotificationChannel.PUSH)
        if preferences.in_app_notifications:
            channels.append(NotificationChannel.IN_APP)
        if preferences.telegram_enabled and preferences.telegram_chat_id:
            telegram_types = preferences.telegram_notification_types or []
            if not telegram_types or notification_type.value in telegram_types:
                channels.append(NotificationChannel.TELEGRAM)
        if preferences.discord_enabled and preferences.discord_webhook_url:
            discord_types = preferences.discord_notification_types or []
            if not discord_types or notification_type.value in discord_types:
                channels.append(NotificationChannel.DISCORD)

        return channels

    async def _send_via_channel(
        self,
        channel: NotificationChannel,
        user: User,
        preferences: UserPreference,
        notification: Notification,
    ):
        """Send notification via specific channel."""
        if channel == NotificationChannel.EMAIL:
            await self._send_email(user, notification)
        elif channel == NotificationChannel.TELEGRAM:
            await self._send_telegram(preferences, notification)
        elif channel == NotificationChannel.DISCORD:
            await self._send_discord(preferences, notification)
        elif channel == NotificationChannel.WEBHOOK:
            await self._send_webhook(preferences, notification)

    async def _send_email(self, user: User, notification: Notification):
        """Send email notification."""
        # TODO: Implement email sending
        logger.info(f"Email notification sent to {user.email}: {notification.title}")

    async def _send_telegram(self, preferences: UserPreference, notification: Notification):
        """Send Telegram notification."""
        if not preferences.telegram_bot_token or not preferences.telegram_chat_id:
            return

        url = f"https://api.telegram.org/bot{preferences.telegram_bot_token}/sendMessage"
        
        text = f"🔔 *{notification.title}*\n\n{notification.message}"
        if notification.action_url and notification.action_label:
            text += f"\n\n[👉 {notification.action_label}]({notification.action_url})"

        payload = {
            "chat_id": preferences.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            response.raise_for_status()

        logger.info(f"Telegram notification sent to chat {preferences.telegram_chat_id}")

    async def _send_discord(self, preferences: UserPreference, notification: Notification):
        """Send Discord notification via webhook."""
        if not preferences.discord_webhook_url:
            return

        # Determine color based on priority
        color_map = {
            NotificationPriority.LOW: 0x95a5a6,      # Gray
            NotificationPriority.MEDIUM: 0x3498db,   # Blue
            NotificationPriority.HIGH: 0xf39c12,     # Orange
            NotificationPriority.URGENT: 0xe74c3c,   # Red
        }

        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": color_map.get(notification.priority, 0x3498db),
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "CareerIntel AI"},
        }

        if notification.action_url and notification.action_label:
            embed["fields"] = [{
                "name": "Action",
                "value": f"[{notification.action_label}]({notification.action_url})",
                "inline": False,
            }]

        payload = {
            "embeds": [embed],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(preferences.discord_webhook_url, json=payload, timeout=10)
            response.raise_for_status()

        logger.info("Discord notification sent via webhook")

    async def _send_webhook(self, preferences: UserPreference, notification: Notification):
        """Send generic webhook notification."""
        # TODO: Implement generic webhook
        pass

    # Convenience methods for common notification types
    async def notify_job_match(
        self,
        user_id: int,
        job_title: str,
        company_name: str,
        match_score: float,
        job_url: str,
    ):
        """Notify user about a job match."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.JOB_MATCH,
            title=f"New Job Match: {job_title}",
            message=f"Found a {match_score:.0%} match at {company_name}",
            priority=NotificationPriority.HIGH,
            action_url=job_url,
            action_label="View Job",
            metadata={"job_title": job_title, "company": company_name, "match_score": match_score},
        )

    async def notify_application_update(
        self,
        user_id: int,
        job_title: str,
        company_name: str,
        new_status: str,
        application_url: str,
    ):
        """Notify user about application status update."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.APPLICATION_UPDATE,
            title=f"Application Update: {job_title}",
            message=f"Your application at {company_name} is now: {new_status}",
            priority=NotificationPriority.MEDIUM,
            action_url=application_url,
            action_label="View Application",
            metadata={"job_title": job_title, "company": company_name, "status": new_status},
        )

    async def notify_interview_reminder(
        self,
        user_id: int,
        job_title: str,
        company_name: str,
        interview_time: datetime,
        meeting_url: Optional[str] = None,
    ):
        """Notify user about upcoming interview."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.INTERVIEW_REMINDER,
            title=f"Interview Reminder: {job_title}",
            message=f"Interview with {company_name} at {interview_time.strftime('%Y-%m-%d %H:%M')}",
            priority=NotificationPriority.HIGH,
            action_url=meeting_url,
            action_label="Join Meeting",
            metadata={"job_title": job_title, "company": company_name, "interview_time": interview_time.isoformat()},
        )

    async def notify_research_complete(
        self,
        user_id: int,
        research_topic: str,
        research_url: str,
    ):
        """Notify user when research is complete."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.RESEARCH_COMPLETE,
            title=f"Research Complete: {research_topic}",
            message=f"Your research on '{research_topic}' is ready to view",
            priority=NotificationPriority.MEDIUM,
            action_url=research_url,
            action_label="View Research",
            metadata={"topic": research_topic},
        )

    async def notify_resume_analysis(
        self,
        user_id: int,
        ats_score: float,
        resume_url: str,
    ):
        """Notify user about resume analysis results."""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.RESUME_ANALYSIS,
            title="Resume Analysis Complete",
            message=f"Your resume scored {ats_score:.0f}/100 on ATS compatibility",
            priority=NotificationPriority.MEDIUM,
            action_url=resume_url,
            action_label="View Analysis",
            metadata={"ats_score": ats_score},
        )


# Dependency for FastAPI
def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db)