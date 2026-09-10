from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api import auth
from backend.database import get_db
from backend.models import (
    Notification,
    UserPreference,
    NotificationChannel,
    NotificationType,
    NotificationPriority,
    NotificationFrequency,
    JobAlertFrequency,
    ThemeMode,
    ContentDensity,
)
from backend.services.notification_service import NotificationService, get_notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ==========================================
# Pydantic Schemas
# ==========================================

class NotificationResponse(BaseModel):
    id: int
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    action_url: Optional[str]
    action_label: Optional[str]
    notification_metadata: Optional[Dict[str, Any]]
    is_read: bool
    read_at: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_ids: List[int]


class NotificationPreferencesRequest(BaseModel):
    # Email
    email_notifications: Optional[bool] = None
    # Push
    push_notifications: Optional[bool] = None
    # In-app
    in_app_notifications: Optional[bool] = None
    # Channels
    notification_channels: Optional[List[str]] = None
    notification_frequency: Optional[NotificationFrequency] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: Optional[str] = None
    # Telegram
    telegram_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_notification_types: Optional[List[str]] = None
    # Discord
    discord_enabled: Optional[bool] = None
    discord_webhook_url: Optional[str] = None
    discord_notification_types: Optional[List[str]] = None


class NotificationPreferencesResponse(BaseModel):
    email_notifications: bool
    push_notifications: bool
    in_app_notifications: bool
    notification_channels: Optional[List[str]]
    notification_frequency: NotificationFrequency
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    timezone: str
    telegram_enabled: bool
    telegram_chat_id: Optional[str]
    telegram_bot_token: Optional[str]  # Masked for security
    telegram_notification_types: Optional[List[str]]
    discord_enabled: bool
    discord_webhook_url: Optional[str]  # Masked for security
    discord_notification_types: Optional[List[str]]

    model_config = {"from_attributes": True}


class TestNotificationRequest(BaseModel):
    channel: NotificationChannel
    title: str = "Test Notification"
    message: str = "This is a test notification from CareerIntel AI"


class JobAlertPreferencesRequest(BaseModel):
    job_alert_enabled: Optional[bool] = None
    job_alert_frequency: Optional[JobAlertFrequency] = None
    preferred_job_types: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferred_remote_types: Optional[List[str]] = None
    min_salary: Optional[int] = None
    preferred_industries: Optional[List[str]] = None
    excluded_companies: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None


# ==========================================
# Helper
# ==========================================

def get_preferences(db: Session, user_id: int) -> UserPreference:
    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not prefs:
        prefs = UserPreference(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


# ==========================================
# Notification Endpoints
# ==========================================

@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """List user notifications."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    total = query.count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    notifications = query.order_by(Notification.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=Dict[str, int])
async def get_unread_count(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get unread notification count."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.post("/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    request: MarkReadRequest,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark notifications as read."""
    db.query(Notification).filter(
        Notification.id.in_(request.notification_ids),
        Notification.user_id == current_user.id,
    ).update({
        Notification.is_read: True,
        Notification.read_at: datetime.utcnow(),
    }, synchronize_session=False)
    db.commit()


@router.post("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({
        Notification.is_read: True,
        Notification.read_at: datetime.utcnow(),
    }, synchronize_session=False)
    db.commit()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notification)
    db.commit()


# ==========================================
# Notification Preferences Endpoints
# ==========================================

@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user notification preferences."""
    prefs = get_preferences(db, current_user.id)
    
    # Mask sensitive data
    telegram_token = prefs.telegram_bot_token
    if telegram_token:
        telegram_token = telegram_token[:8] + "..." + telegram_token[-4:] if len(telegram_token) > 12 else "***"
    
    discord_url = prefs.discord_webhook_url
    if discord_url:
        discord_url = discord_url[:20] + "..." + discord_url[-10:] if len(discord_url) > 30 else "***"

    return NotificationPreferencesResponse(
        email_notifications=prefs.email_notifications,
        push_notifications=prefs.push_notifications,
        in_app_notifications=prefs.in_app_notifications,
        notification_channels=prefs.notification_channels,
        notification_frequency=prefs.notification_frequency,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end,
        timezone=prefs.timezone,
        telegram_enabled=prefs.telegram_enabled,
        telegram_chat_id=prefs.telegram_chat_id,
        telegram_bot_token=telegram_token,
        telegram_notification_types=prefs.telegram_notification_types,
        discord_enabled=prefs.discord_enabled,
        discord_webhook_url=discord_url,
        discord_notification_types=prefs.discord_notification_types,
    )


@router.patch("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    request: NotificationPreferencesRequest,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update user notification preferences."""
    prefs = get_preferences(db, current_user.id)
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "telegram_bot_token" and value and value.startswith("..."):
            # Don't update masked token
            continue
        if field == "discord_webhook_url" and value and value.startswith("..."):
            # Don't update masked URL
            continue
        setattr(prefs, field, value)

    prefs.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prefs)
    
    return await get_notification_preferences(current_user, db)


@router.post("/preferences/test", response_model=Dict[str, str])
async def test_notification(
    request: TestNotificationRequest,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Send a test notification via specified channel."""
    prefs = get_preferences(db, current_user.id)
    
    # Temporarily enable the channel for testing
    original_channels = prefs.notification_channels or []
    
    try:
        if request.channel == NotificationChannel.TELEGRAM:
            if not prefs.telegram_enabled or not prefs.telegram_chat_id:
                raise HTTPException(status_code=400, detail="Telegram not configured")
            await notification_service._send_telegram(prefs, Notification(
                title=request.title,
                message=request.message,
            ))
        elif request.channel == NotificationChannel.DISCORD:
            if not prefs.discord_enabled or not prefs.discord_webhook_url:
                raise HTTPException(status_code=400, detail="Discord not configured")
            await notification_service._send_discord(prefs, Notification(
                title=request.title,
                message=request.message,
            ))
        elif request.channel == NotificationChannel.EMAIL:
            await notification_service._send_email(current_user, Notification(
                title=request.title,
                message=request.message,
            ))
        else:
            raise HTTPException(status_code=400, detail=f"Test not supported for channel: {request.channel}")
        
        return {"message": f"Test notification sent via {request.channel.value}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")


# ==========================================
# Job Alert Preferences
# ==========================================

@router.get("/job-alerts", response_model=Dict[str, Any])
async def get_job_alert_preferences(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get job alert preferences."""
    prefs = get_preferences(db, current_user.id)
    return {
        "job_alert_enabled": prefs.job_alert_enabled,
        "job_alert_frequency": prefs.job_alert_frequency,
        "preferred_job_types": prefs.preferred_job_types,
        "preferred_locations": prefs.preferred_locations,
        "preferred_remote_types": prefs.preferred_remote_types,
        "min_salary": prefs.min_salary,
        "preferred_industries": prefs.preferred_industries,
        "excluded_companies": prefs.excluded_companies,
        "excluded_keywords": prefs.excluded_keywords,
    }


@router.patch("/job-alerts", response_model=Dict[str, Any])
async def update_job_alert_preferences(
    request: JobAlertPreferencesRequest,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update job alert preferences."""
    prefs = get_preferences(db, current_user.id)
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    prefs.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prefs)
    
    return await get_job_alert_preferences(current_user, db)


# ==========================================
# Notification Types & Channels (for UI)
# ==========================================

@router.get("/types", response_model=List[Dict[str, str]])
async def get_notification_types():
    """Get available notification types."""
    return [
        {"value": t.value, "label": t.value.replace("_", " ").title()}
        for t in NotificationType
    ]


@router.get("/channels", response_model=List[Dict[str, str]])
async def get_notification_channels():
    """Get available notification channels."""
    return [
        {"value": c.value, "label": c.value.replace("_", " ").title()}
        for c in NotificationChannel
    ]


@router.get("/priorities", response_model=List[Dict[str, str]])
async def get_notification_priorities():
    """Get available notification priorities."""
    return [
        {"value": p.value, "label": p.value.title()}
        for p in NotificationPriority
    ]


@router.get("/frequencies", response_model=List[Dict[str, str]])
async def get_notification_frequencies():
    """Get available notification frequencies."""
    return [
        {"value": f.value, "label": f.value.replace("_", " ").title()}
        for f in NotificationFrequency
    ]