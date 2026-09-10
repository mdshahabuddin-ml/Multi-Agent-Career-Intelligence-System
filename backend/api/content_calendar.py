from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api import auth
from backend.database import get_db
from backend.models import ContentCalendar, ContentAnalytics, SocialPlatform, ContentStatus, ContentType, User
from backend.models.content_pipeline_run import ContentPipelineRun
from backend.services.content_scheduler import (
    ContentScheduler,
    DuplicateScheduleError,
    SchedulingError,
)
from backend.services.publishing_service import PublishingService
from backend.social_integrations.publisher import PermanentPublishError
from backend.state_machine.guards import TransitionNotAllowed, require_publishable

router = APIRouter(prefix="/content-calendar", tags=["Content Calendar"])


# ==========================================
# Pydantic Schemas
# ==========================================

class ContentCalendarCreate(BaseModel):
    title: str = Field(..., max_length=255)
    content: str
    content_type: ContentType = ContentType.POST
    platform: SocialPlatform
    platform_specific_data: Optional[dict] = None
    media_urls: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class ContentCalendarUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    content_type: Optional[ContentType] = None
    platform_specific_data: Optional[dict] = None
    media_urls: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[ContentStatus] = None
    is_recurring: Optional[bool] = None
    recurrence_rule: Optional[str] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class ContentCalendarResponse(BaseModel):
    id: int
    title: str
    content: str
    content_type: ContentType
    platform: SocialPlatform
    platform_specific_data: Optional[dict]
    media_urls: Optional[List[str]]
    thumbnail_url: Optional[str]
    pipeline_run_id: Optional[int] = None
    status: ContentStatus
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    is_recurring: bool
    recurrence_rule: Optional[str]
    hashtags: Optional[List[str]]
    mentions: Optional[List[str]]
    meta_title: Optional[str]
    meta_description: Optional[str]
    platform_post_id: Optional[str]
    platform_post_url: Optional[str]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentAnalyticsResponse(BaseModel):
    id: int
    content_id: int
    platform: SocialPlatform
    platform_post_id: str
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    clicks: int
    impressions: int
    reach: int
    watch_time_seconds: int
    average_watch_time: float
    completion_rate: float
    engagement_rate: float
    click_through_rate: float
    raw_data: Optional[dict]
    recorded_at: datetime

    model_config = {"from_attributes": True}


class ContentCalendarListResponse(BaseModel):
    items: List[ContentCalendarResponse]
    total: int
    page: int
    page_size: int


class CalendarViewResponse(BaseModel):
    date: str
    items: List[ContentCalendarResponse]


class AnalyticsSummaryResponse(BaseModel):
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_impressions: int
    avg_engagement_rate: float
    by_platform: dict
    by_content_type: dict


# ==========================================
# Helper
# ==========================================

def get_content(db: Session, content_id: int, user_id: int) -> Optional[ContentCalendar]:
    return db.query(ContentCalendar).filter(
        ContentCalendar.id == content_id,
        ContentCalendar.user_id == user_id
    ).first()


def get_scheduler(db: Session = Depends(get_db)) -> ContentScheduler:
    return ContentScheduler(db)


def get_publisher(db: Session = Depends(get_db)) -> PublishingService:
    return PublishingService(db)


def _schedule_error(exc: SchedulingError) -> HTTPException:
    message = str(exc)
    if message == "Content not found" or "no longer" in message.lower():
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    if isinstance(exc, DuplicateScheduleError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class ScheduleFromRunRequest(BaseModel):
    pipeline_run_id: int
    platform: SocialPlatform
    scheduled_at: Optional[datetime] = None


class RetryRequest(BaseModel):
    scheduled_at: Optional[datetime] = None


# ==========================================
# CRUD Endpoints
# ==========================================

@router.post("/", response_model=ContentCalendarResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    request: ContentCalendarCreate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new content calendar entry."""
    content = ContentCalendar(
        user_id=current_user.id,
        **request.model_dump()
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return ContentCalendarResponse.model_validate(content)


@router.get("/", response_model=ContentCalendarListResponse)
async def list_content(
    platform: Optional[SocialPlatform] = Query(None),
    status: Optional[ContentStatus] = Query(None),
    content_type: Optional[ContentType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """List content calendar entries with filters."""
    query = db.query(ContentCalendar).filter(ContentCalendar.user_id == current_user.id)

    if platform:
        query = query.filter(ContentCalendar.platform == platform)
    if status:
        query = query.filter(ContentCalendar.status == status)
    if content_type:
        query = query.filter(ContentCalendar.content_type == content_type)
    if start_date:
        query = query.filter(ContentCalendar.scheduled_at >= start_date)
    if end_date:
        query = query.filter(ContentCalendar.scheduled_at <= end_date)

    query = query.order_by(ContentCalendar.scheduled_at.desc().nullslast(), ContentCalendar.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return ContentCalendarListResponse(
        items=[ContentCalendarResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/calendar", response_model=List[CalendarViewResponse])
async def get_calendar_view(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get content calendar view for date range (for calendar UI)."""
    items = db.query(ContentCalendar).filter(
        ContentCalendar.user_id == current_user.id,
        ContentCalendar.scheduled_at >= start_date,
        ContentCalendar.scheduled_at <= end_date,
    ).order_by(ContentCalendar.scheduled_at).all()

    # Group by date
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in items:
        if item.scheduled_at:
            date_key = item.scheduled_at.date().isoformat()
            grouped[date_key].append(ContentCalendarResponse.model_validate(item))

    return [
        CalendarViewResponse(date=date, items=items)
        for date, items in sorted(grouped.items())
    ]


@router.get("/upcoming", response_model=List[ContentCalendarResponse])
async def get_upcoming_content(
    limit: int = Query(10, ge=1, le=50),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get upcoming scheduled content."""
    items = db.query(ContentCalendar).filter(
        ContentCalendar.user_id == current_user.id,
        ContentCalendar.status == ContentStatus.SCHEDULED,
        ContentCalendar.scheduled_at >= datetime.utcnow(),
    ).order_by(ContentCalendar.scheduled_at).limit(limit).all()

    return [ContentCalendarResponse.model_validate(item) for item in items]


@router.get("/{content_id}", response_model=ContentCalendarResponse)
async def get_content_detail(
    content_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get content calendar entry detail."""
    content = get_content(db, content_id, current_user.id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return ContentCalendarResponse.model_validate(content)


@router.patch("/{content_id}", response_model=ContentCalendarResponse)
async def update_content(
    content_id: int,
    request: ContentCalendarUpdate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update content calendar entry."""
    content = get_content(db, content_id, current_user.id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    update_data = request.model_dump(exclude_unset=True)
    if update_data.get("status") == ContentStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content cannot be marked published directly; it must pass scheduling/publishing",
        )
    for field, value in update_data.items():
        setattr(content, field, value)

    content.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(content)
    return ContentCalendarResponse.model_validate(content)


@router.post("/{content_id}/publish", response_model=ContentCalendarResponse)
async def publish_content(
    content_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
    publisher: PublishingService = Depends(get_publisher),
):
    """Publish content now through official platform APIs.

    Approval gate: items linked to a pipeline run require an APPROVED run;
    unlinked items must already be SCHEDULED or RETRY. Drafts are never
    published. Failures are recorded on the item (FAILED + error).
    """
    content = get_content(db, content_id, current_user.id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    _require_publishable(db, current_user.id, content)
    item = await publisher.publish_item(current_user.id, content_id)
    return ContentCalendarResponse.model_validate(item)


@router.post("/{content_id}/publish/dry-run")
async def publish_dry_run(
    content_id: int,
    current_user = Depends(auth.get_current_active_user),
    publisher: PublishingService = Depends(get_publisher),
):
    """DRY-RUN: validate everything without any network calls or writes."""
    try:
        return publisher.dry_run_item(current_user.id, content_id)
    except PermanentPublishError as exc:
        if "content not found" in str(exc):
            raise HTTPException(status_code=404, detail="Content not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _require_publishable(db: Session, user_id: int, content: ContentCalendar) -> None:
    """Enforce publish gating rules before any platform call.

    Delegates to the central guard (``backend.state_machine``); contract
    is unchanged (404 missing run, 400 otherwise, identical messages).
    """
    if content.pipeline_run_id is not None:
        run = db.query(ContentPipelineRun).filter(
            ContentPipelineRun.id == content.pipeline_run_id,
            ContentPipelineRun.user_id == user_id,
        ).first()
        if not run:
            raise HTTPException(status_code=404, detail="Linked pipeline run not found")
        try:
            require_publishable(run_status=run.status)
        except TransitionNotAllowed as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )
        return
    try:
        require_publishable(item_status=content.status)
    except TransitionNotAllowed as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/from-approved", response_model=ContentCalendarResponse, status_code=status.HTTP_201_CREATED)
async def schedule_from_approved(
    request: ScheduleFromRunRequest,
    current_user = Depends(auth.get_current_active_user),
    scheduler: ContentScheduler = Depends(get_scheduler),
):
    """Schedule an APPROVED pipeline run (PENDING without time, SCHEDULED with time).

    Rejected runs, drafts, and failed verification can never be scheduled.
    Repeating the same (run, platform) returns 409 instead of duplicating.
    """
    try:
        item = scheduler.schedule_from_run(
            current_user.id, request.pipeline_run_id, request.platform, request.scheduled_at
        )
    except SchedulingError as exc:
        raise _schedule_error(exc)
    return ContentCalendarResponse.model_validate(item)


@router.post("/{content_id}/schedule", response_model=ContentCalendarResponse)
async def schedule_content(
    content_id: int,
    scheduled_at: datetime,
    current_user = Depends(auth.get_current_active_user),
    scheduler: ContentScheduler = Depends(get_scheduler),
):
    """Assign a date/time slot (idempotent: same slot twice is a no-op)."""
    try:
        item = scheduler.assign_slot(current_user.id, content_id, scheduled_at)
    except SchedulingError as exc:
        raise _schedule_error(exc)
    return ContentCalendarResponse.model_validate(item)


@router.post("/{content_id}/retry", response_model=ContentCalendarResponse)
async def retry_content(
    content_id: int,
    request: RetryRequest,
    current_user = Depends(auth.get_current_active_user),
    scheduler: ContentScheduler = Depends(get_scheduler),
):
    """Retry a FAILED item (→ RETRY, or SCHEDULED when a new slot is given)."""
    try:
        item = scheduler.request_retry(current_user.id, content_id, request.scheduled_at)
    except SchedulingError as exc:
        raise _schedule_error(exc)
    return ContentCalendarResponse.model_validate(item)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete content calendar entry."""
    content = get_content(db, content_id, current_user.id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    db.delete(content)
    db.commit()


# ==========================================
# Analytics Endpoints
# ==========================================

@router.get("/{content_id}/analytics", response_model=List[ContentAnalyticsResponse])
async def get_content_analytics(
    content_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get analytics for a specific content."""
    content = get_content(db, content_id, current_user.id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    analytics = db.query(ContentAnalytics).filter(
        ContentAnalytics.content_id == content_id
    ).order_by(ContentAnalytics.recorded_at.desc()).all()

    return [ContentAnalyticsResponse.model_validate(a) for a in analytics]


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    platform: Optional[SocialPlatform] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get aggregated analytics summary."""
    query = db.query(ContentAnalytics).filter(ContentAnalytics.user_id == current_user.id)

    if start_date:
        query = query.filter(ContentAnalytics.recorded_at >= start_date)
    if end_date:
        query = query.filter(ContentAnalytics.recorded_at <= end_date)
    if platform:
        query = query.filter(ContentAnalytics.platform == platform)

    analytics = query.all()

    if not analytics:
        return AnalyticsSummaryResponse(
            total_posts=0,
            total_views=0,
            total_likes=0,
            total_comments=0,
            total_shares=0,
            total_impressions=0,
            avg_engagement_rate=0.0,
            by_platform={},
            by_content_type={}
        )

    # Aggregate
    total_posts = len(set(a.content_id for a in analytics))
    total_views = sum(a.views for a in analytics)
    total_likes = sum(a.likes for a in analytics)
    total_comments = sum(a.comments for a in analytics)
    total_shares = sum(a.shares for a in analytics)
    total_impressions = sum(a.impressions for a in analytics)
    avg_engagement_rate = sum(a.engagement_rate for a in analytics) / len(analytics) if analytics else 0

    # By platform
    by_platform = {}
    for a in analytics:
        p = a.platform.value
        if p not in by_platform:
            by_platform[p] = {"posts": 0, "views": 0, "likes": 0, "engagement_rate": 0.0}
        by_platform[p]["posts"] += 1
        by_platform[p]["views"] += a.views
        by_platform[p]["likes"] += a.likes
        by_platform[p]["engagement_rate"] += a.engagement_rate

    for p in by_platform:
        by_platform[p]["engagement_rate"] /= by_platform[p]["posts"]

    # By content type (need to join with content_calendar)
    by_content_type = {}
    for a in analytics:
        content = db.query(ContentCalendar).filter(ContentCalendar.id == a.content_id).first()
        if content:
            ct = content.content_type.value
            if ct not in by_content_type:
                by_content_type[ct] = {"posts": 0, "views": 0, "engagement_rate": 0.0}
            by_content_type[ct]["posts"] += 1
            by_content_type[ct]["views"] += a.views
            by_content_type[ct]["engagement_rate"] += a.engagement_rate

    for ct in by_content_type:
        by_content_type[ct]["engagement_rate"] /= by_content_type[ct]["posts"]

    return AnalyticsSummaryResponse(
        total_posts=total_posts,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
        total_impressions=total_impressions,
        avg_engagement_rate=round(avg_engagement_rate, 2),
        by_platform=by_platform,
        by_content_type=by_content_type
    )


@router.post("/analytics/sync", response_model=dict)
async def sync_analytics(
    content_id: int,
    platform_post_id: str,
    platform: SocialPlatform,
    metrics: dict,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Sync analytics from platform (webhook or manual)."""
    content = get_content(db, content_id, current_user.id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Update content with platform info
    content.platform_post_id = platform_post_id
    content.platform_post_url = metrics.get("post_url")
    content.status = ContentStatus.PUBLISHED
    content.published_at = datetime.utcnow()

    # Create analytics record
    analytics = ContentAnalytics(
        content_id=content_id,
        user_id=current_user.id,
        platform=platform,
        platform_post_id=platform_post_id,
        views=metrics.get("views", 0),
        likes=metrics.get("likes", 0),
        comments=metrics.get("comments", 0),
        shares=metrics.get("shares", 0),
        saves=metrics.get("saves", 0),
        clicks=metrics.get("clicks", 0),
        impressions=metrics.get("impressions", 0),
        reach=metrics.get("reach", 0),
        watch_time_seconds=metrics.get("watch_time_seconds", 0),
        average_watch_time=metrics.get("average_watch_time", 0.0),
        completion_rate=metrics.get("completion_rate", 0.0),
        engagement_rate=metrics.get("engagement_rate", 0.0),
        click_through_rate=metrics.get("click_through_rate", 0.0),
        raw_data=metrics,
    )

    # Calculate rates if not provided
    if analytics.impressions > 0:
        analytics.engagement_rate = round(
            ((analytics.likes + analytics.comments + analytics.shares) / analytics.impressions) * 100, 2
        )
    if analytics.impressions > 0 and analytics.clicks > 0:
        analytics.click_through_rate = round((analytics.clicks / analytics.impressions) * 100, 2)

    db.add(analytics)
    db.commit()

    return {"message": "Analytics synced successfully", "analytics_id": analytics.id}