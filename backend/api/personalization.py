from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.api import auth
from backend.services.personalization_service import PersonalizationService
from backend.schemas.preference import (
    UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceResponse,
    UserBehaviorLogCreate, UserBehaviorLogResponse,
    UserInteractionCreate, UserInteractionResponse,
    PersonalizationProfileResponse, PreferenceImportExport
)

router = APIRouter(prefix="/personalization", tags=["Personalization"])


def get_personalization_service(db: Session = Depends(get_db)) -> PersonalizationService:
    return PersonalizationService(db)


# ============= Preferences =============

@router.get("/preferences", response_model=UserPreferenceResponse)
async def get_preferences(
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get current user's preferences."""
    preferences = service.get_preferences(current_user.id)
    if not preferences:
        # Return defaults
        return UserPreferenceResponse(
            id=0,
            user_id=current_user.id,
            job_preferences={},
            notification_preferences={},
            content_ui_preferences={},
            privacy_preferences={},
            learning_preferences={},
            recommendation_weights={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    return preferences


@router.post("/preferences", response_model=UserPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def create_preferences(
    preferences: UserPreferenceCreate,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Create user preferences."""
    try:
        return service.create_preferences(current_user.id, preferences)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/preferences", response_model=UserPreferenceResponse)
async def update_preferences(
    preferences: UserPreferenceUpdate,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Update user preferences."""
    result = service.update_preferences(current_user.id, preferences)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found")
    return result


@router.delete("/preferences", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preferences(
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Delete user preferences."""
    service.delete_preferences(current_user.id)


@router.get("/preferences/export", response_model=PreferenceImportExport)
async def export_preferences(
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Export user preferences as JSON."""
    data = service.export_preferences(current_user.id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No preferences to export")
    return data


@router.post("/preferences/import", response_model=UserPreferenceResponse)
async def import_preferences(
    data: PreferenceImportExport,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Import user preferences from JSON."""
    return service.import_preferences(current_user.id, data.dict())


# ============= Behavior Logging =============

@router.post("/behavior/log", response_model=UserBehaviorLogResponse, status_code=status.HTTP_201_CREATED)
async def log_behavior(
    log: UserBehaviorLogCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Log a user behavior event."""
    # Process in background for performance
    background_tasks.add_task(service.log_behavior, current_user.id, log)
    return UserBehaviorLogResponse(
        id=0,
        user_id=current_user.id,
        **log.dict(),
        created_at=datetime.utcnow(),
    )


@router.post("/behavior/log/batch", response_model=List[UserBehaviorLogResponse])
async def log_behavior_batch(
    logs: List[UserBehaviorLogCreate],
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Log multiple behavior events in batch."""
    # Process in background
    background_tasks.add_task(service.log_behavior_batch, current_user.id, logs)
    return [
        UserBehaviorLogResponse(
            id=0,
            user_id=current_user.id,
            **log.dict(),
            created_at=datetime.utcnow(),
        )
        for log in logs
    ]


@router.get("/behavior/logs", response_model=List[UserBehaviorLogResponse])
async def get_behavior_logs(
    event_type: Optional[str] = Query(None),
    event_category: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get user behavior logs with filters."""
    logs = service.get_behavior_logs(
        current_user.id,
        event_type=event_type,
        event_category=event_category,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return logs


# ============= Interactions =============

@router.post("/interactions", response_model=UserInteractionResponse, status_code=status.HTTP_201_CREATED)
async def record_interaction(
    interaction: UserInteractionCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Record user interaction with an entity."""
    background_tasks.add_task(service.record_interaction, current_user.id, interaction)
    return UserInteractionResponse(
        id=0,
        user_id=current_user.id,
        **interaction.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@router.get("/interactions", response_model=List[UserInteractionResponse])
async def get_interactions(
    interaction_type: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get user interactions with filters."""
    return service.get_interactions(
        current_user.id,
        interaction_type=interaction_type,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )


@router.get("/interactions/stats")
async def get_interaction_stats(
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get interaction statistics for the current user."""
    return service.get_interaction_stats(current_user.id)


# ============= Personalization Profile =============

@router.get("/profile", response_model=PersonalizationProfileResponse)
async def get_personalization_profile(
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get user's personalization profile."""
    profile = service.get_personalization_profile(current_user.id)
    if not profile:
        # Return empty profile
        return PersonalizationProfileResponse(
            id=0,
            user_id=current_user.id,
            inferred_skills=[],
            inferred_interests=[],
            inferred_seniority=None,
            inferred_job_functions=[],
            inferred_industries=[],
            inferred_work_style=None,
            job_search_engagement=0.0,
            learning_engagement=0.0,
            research_engagement=0.0,
            community_engagement=0.0,
            last_updated=datetime.utcnow(),
            model_version="1.0",
            confidence_score=0.0,
            is_active=True,
            manual_override=False,
        )
    return profile


@router.post("/profile/rebuild", response_model=PersonalizationProfileResponse)
async def rebuild_personalization_profile(
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Rebuild personalization profile from user behavior."""
    background_tasks.add_task(service.rebuild_personalization_profile, current_user.id)
    return {"message": "Profile rebuild started in background"}


# ============= Recommendations =============

@router.get("/recommendations/jobs")
async def get_job_recommendations(
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get personalized job recommendations."""
    return service.get_personalized_job_recommendations(current_user.id, limit, offset)


@router.get("/recommendations/learning")
async def get_learning_recommendations(
    limit: int = Query(10, le=20),
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get personalized learning recommendations."""
    return service.get_personalized_learning_recommendations(current_user.id, limit)


# ============= Adaptive UI =============

@router.get("/ui/config")
async def get_adaptive_ui_config(
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Get adaptive UI configuration."""
    return service.get_adaptive_ui_config(current_user.id)


# ============= Bulk Operations =============

class BulkBehaviorLog(BaseModel):
    logs: List[UserBehaviorLogCreate]

class BulkInteraction(BaseModel):
    interactions: List[UserInteractionCreate]

@router.post("/behavior/log/bulk")
async def bulk_log_behavior(
    data: BulkBehaviorLog,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Bulk log behavior events."""
    background_tasks.add_task(service.log_behavior_batch, current_user.id, data.logs)
    return {"message": f"Queued {len(data.logs)} events for processing"}


@router.post("/interactions/bulk")
async def bulk_record_interactions(
    data: BulkInteraction,
    background_tasks: BackgroundTasks,
    current_user = Depends(auth.get_current_active_user),
    service: PersonalizationService = Depends(get_personalization_service),
):
    """Bulk record interactions."""
    for interaction in data.interactions:
        background_tasks.add_task(service.record_interaction, current_user.id, interaction)
    return {"message": f"Queued {len(data.interactions)} interactions for processing"}