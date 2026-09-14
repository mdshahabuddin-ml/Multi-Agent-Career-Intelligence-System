"""
Video Pipeline API - Content → Script → Scenes → Veo → MP4.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User
from backend.models.content import Content
from backend.models.social_account import SocialAccount
from backend.models.video_pipeline import VideoPipeline, VideoScene

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video-pipeline", tags=["Video Pipeline"])


# ── Request / Response schemas ──────────────────────────────

class StartPipelineRequest(BaseModel):
    content_id: int


class SceneResponse(BaseModel):
    id: int
    scene_index: int
    description: str
    prompt: str
    duration_seconds: int
    status: str
    video_url: Optional[str] = None
    error_message: Optional[str] = None


class PipelineResponse(BaseModel):
    id: int
    content_id: int
    status: str
    script: Optional[str] = None
    scenes: Optional[List[Dict[str, Any]]] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────

def _pipeline_to_dict(p: VideoPipeline) -> Dict[str, Any]:
    return {
        "id": p.id,
        "content_id": p.content_id,
        "status": p.status,
        "script": p.script,
        "scenes": p.scenes,
        "video_url": p.video_url,
        "thumbnail_url": p.thumbnail_url,
        "veo_model": p.veo_model,
        "aspect_ratio": p.aspect_ratio,
        "approval_status": p.approval_status,
        "approved_at": p.approved_at.isoformat() if p.approved_at else None,
        "rejected_at": p.rejected_at.isoformat() if p.rejected_at else None,
        "rejection_reason": p.rejection_reason,
        "youtube_video_id": p.youtube_video_id,
        "youtube_video_url": p.youtube_video_url,
        "youtube_published_at": p.youtube_published_at.isoformat() if p.youtube_published_at else None,
        "youtube_status": p.youtube_status,
        "error_message": p.error_message,
        "retry_count": p.retry_count,
        "metadata_json": p.metadata_json,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "started_at": p.started_at.isoformat() if p.started_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
    }


def _scene_to_dict(s: VideoScene) -> Dict[str, Any]:
    return {
        "id": s.id,
        "scene_index": s.scene_index,
        "description": s.description,
        "prompt": s.prompt,
        "duration_seconds": s.duration_seconds,
        "status": s.status,
        "video_url": s.video_url,
        "error_message": s.error_message,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


# ── Background task ─────────────────────────────────────────

async def _run_pipeline_background(pipeline_id: int, content_id: int, user_id: int):
    """Run the video pipeline in background."""
    from backend.database import SessionLocal
    from backend.hermes_engine.skills.video_generation import VideoGenerationSkill

    db = SessionLocal()
    try:
        skill = VideoGenerationSkill(db)
        await skill.run_pipeline(content_id, user_id)
        logger.info("Video pipeline %d completed for content %d", pipeline_id, content_id)
    except Exception as e:
        logger.error("Video pipeline %d failed: %s", pipeline_id, e)
    finally:
        db.close()


def _run_pipeline_background_sync(pipeline_id: int, content_id: int, user_id: int):
    """Sync wrapper for background task."""
    asyncio.get_event_loop().run_until_complete(
        _run_pipeline_background(pipeline_id, content_id, user_id)
    )


# ── Endpoints ───────────────────────────────────────────────

@router.post("/start", response_model=PipelineResponse)
async def start_pipeline(
    request: StartPipelineRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Start video generation pipeline for approved content.

    Flow: Content → Script → Scenes → Veo → MP4
    Runs asynchronously in background.
    """
    # Verify content exists and is approved
    content = db.query(Content).filter(
        Content.id == request.content_id,
        Content.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Content must be approved before video generation (current: {content.status})",
        )

    # Check for existing active pipeline
    existing = db.query(VideoPipeline).filter(
        VideoPipeline.content_id == request.content_id,
        VideoPipeline.status.in_(["pending", "script_generating", "script_ready",
                                   "scenes_generating", "scenes_ready", "video_generating"]),
    ).first()
    if existing:
        return _pipeline_to_dict(existing)

    # Create pipeline record
    pipeline = VideoPipeline(
        user_id=current_user.id,
        content_id=request.content_id,
        status="pending",
        veo_model=settings.VEO_MODEL,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    # Run pipeline - in mock mode run synchronously, otherwise background
    from backend.config import settings as _cfg
    if _cfg.MOCK_VIDEO_GENERATION:
        from backend.hermes_engine.skills.video_generation import VideoGenerationSkill
        skill = VideoGenerationSkill(db)
        try:
            await skill.run_pipeline(request.content_id, current_user.id, pipeline=pipeline)
            db.refresh(pipeline)
        except Exception as e:
            logger.error("Mock pipeline failed: %s", e)
            pipeline.status = "failed"
            pipeline.error_message = str(e)[:2000]
            db.commit()
    else:
        background_tasks.add_task(
            _run_pipeline_background_sync,
            pipeline.id, request.content_id, current_user.id,
        )

    return _pipeline_to_dict(pipeline)


@router.get("/list")
async def list_pipelines(
    status_filter: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List video pipelines for the current user."""
    query = db.query(VideoPipeline).filter(
        VideoPipeline.user_id == current_user.id
    )
    if status_filter:
        query = query.filter(VideoPipeline.status == status_filter)
    pipelines = query.order_by(VideoPipeline.created_at.desc()).limit(limit).all()
    return {
        "pipelines": [_pipeline_to_dict(p) for p in pipelines],
        "total": len(pipelines),
    }


@router.get("/{pipeline_id}")
async def get_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get pipeline details including scenes."""
    pipeline = db.query(VideoPipeline).filter(
        VideoPipeline.id == pipeline_id,
        VideoPipeline.user_id == current_user.id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    scenes = db.query(VideoScene).filter(
        VideoScene.pipeline_id == pipeline_id
    ).order_by(VideoScene.scene_index).all()

    result = _pipeline_to_dict(pipeline)
    result["scene_details"] = [_scene_to_dict(s) for s in scenes]
    return result


@router.post("/{pipeline_id}/retry")
async def retry_pipeline(
    pipeline_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retry a failed pipeline."""
    pipeline = db.query(VideoPipeline).filter(
        VideoPipeline.id == pipeline_id,
        VideoPipeline.user_id == current_user.id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed pipelines can be retried")

    pipeline.status = "pending"
    pipeline.error_message = None
    pipeline.retry_count += 1
    db.commit()

    from backend.config import settings as _cfg
    if _cfg.MOCK_VIDEO_GENERATION:
        from backend.hermes_engine.skills.video_generation import VideoGenerationSkill
        skill = VideoGenerationSkill(db)
        try:
            await skill.run_pipeline(pipeline.content_id, current_user.id)
            db.refresh(pipeline)
        except Exception as e:
            logger.error("Mock pipeline retry failed: %s", e)
    else:
        background_tasks.add_task(
            _run_pipeline_background_sync,
            pipeline.id, pipeline.content_id, current_user.id,
        )

    return _pipeline_to_dict(pipeline)


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a video pipeline and its scenes."""
    pipeline = db.query(VideoPipeline).filter(
        VideoPipeline.id == pipeline_id,
        VideoPipeline.user_id == current_user.id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.status in ("video_generating",):
        raise HTTPException(status_code=400, detail="Cannot delete a running pipeline")

    # Delete scenes first
    db.query(VideoScene).filter(VideoScene.pipeline_id == pipeline_id).delete()
    db.delete(pipeline)
    db.commit()
    return {"success": True, "message": f"Pipeline {pipeline_id} deleted"}


class ApproveRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/{pipeline_id}/approve")
async def approve_video(
    pipeline_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Approve a generated video and auto-publish to YouTube if connected."""
    from datetime import datetime as dt
    pipeline = db.query(VideoPipeline).filter(
        VideoPipeline.id == pipeline_id,
        VideoPipeline.user_id == current_user.id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if pipeline.status != "video_ready":
        raise HTTPException(
            status_code=400,
            detail=f"Video must be ready before approval (current: {pipeline.status})",
        )
    pipeline.approval_status = "approved"
    pipeline.approved_at = dt.utcnow()
    db.commit()
    db.refresh(pipeline)

    # Auto-publish to YouTube if connected and video has URL
    is_mock_url = "mock" in (pipeline.video_url or "").lower()
    if pipeline.video_url and is_mock_url:
        # Skip YouTube upload for mock videos
        logger.info("Skipping YouTube upload for mock video URL")
    elif pipeline.video_url:
        youtube_account = db.query(SocialAccount).filter(
            SocialAccount.user_id == current_user.id,
            SocialAccount.platform == "youtube",
            SocialAccount.enabled == True,
        ).first()

        if youtube_account:
            # Get content for title/description
            content = db.query(Content).filter(Content.id == pipeline.content_id).first()
            title = content.title if content else f"Video {pipeline.id}"
            description = (content.body or "")[:500] if content else ""

            # Start YouTube upload in background
            pipeline.youtube_status = "uploading"
            db.commit()

            try:
                from backend.social_integrations.publisher import publish_youtube
                from backend.social_integrations.token_crypto import decrypt_token
                from backend.services.social_account_service import provider_credentials
                from backend.social_integrations import oauth as _oauth

                access_token = decrypt_token(youtube_account.access_token or "")

                # Try upload, refresh token if expired
                try:
                    result = await publish_youtube(
                        access_token=access_token,
                        title=title,
                        description=description,
                        video_url=pipeline.video_url,
                        tags=["career", "AI", "generated"],
                        privacy="unlisted",
                    )
                except Exception as e:
                    if "401" in str(e) or "token" in str(e).lower():
                        # Refresh token and retry
                        client_id, secret, _ = provider_credentials("youtube")
                        stored_refresh = decrypt_token(youtube_account.refresh_token) if youtube_account.refresh_token else None
                        tokens = await _oauth.refresh_access_token(
                            "youtube", client_id, secret,
                            refresh_token=stored_refresh, current_access_token=access_token,
                        )
                        from backend.social_integrations.token_crypto import encrypt_token
                        from backend.services.social_account_service import _expiry_timestamp
                        youtube_account.access_token = encrypt_token(tokens["access_token"])
                        if tokens.get("refresh_token"):
                            youtube_account.refresh_token = encrypt_token(tokens["refresh_token"])
                        youtube_account.token_expires_at = _expiry_timestamp(tokens.get("expires_in"))
                        db.commit()

                        result = await publish_youtube(
                            access_token=tokens["access_token"],
                            title=title,
                            description=description,
                            video_url=pipeline.video_url,
                            tags=["career", "AI", "generated"],
                            privacy="unlisted",
                        )
                    else:
                        raise

                pipeline.youtube_video_id = result.get("platform_post_id")
                pipeline.youtube_video_url = result.get("platform_post_url")
                pipeline.youtube_published_at = dt.utcnow()
                pipeline.youtube_status = "published"
                db.commit()
                db.refresh(pipeline)

                logger.info("Auto-published pipeline %d to YouTube: %s", pipeline_id, result.get("platform_post_id"))

            except Exception as e:
                logger.error("YouTube auto-publish failed for pipeline %d: %s", pipeline_id, e)
                pipeline.youtube_status = "failed"
                db.commit()

    return _pipeline_to_dict(pipeline)


@router.post("/{pipeline_id}/reject")
async def reject_video(
    pipeline_id: int,
    request: ApproveRequest = ApproveRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Reject a generated video."""
    from datetime import datetime as dt
    pipeline = db.query(VideoPipeline).filter(
        VideoPipeline.id == pipeline_id,
        VideoPipeline.user_id == current_user.id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    pipeline.approval_status = "rejected"
    pipeline.rejected_at = dt.utcnow()
    pipeline.rejection_reason = request.reason
    db.commit()
    db.refresh(pipeline)
    return _pipeline_to_dict(pipeline)


@router.post("/{pipeline_id}/regenerate")
async def regenerate_video(
    pipeline_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Regenerate video from the same content."""
    pipeline = db.query(VideoPipeline).filter(
        VideoPipeline.id == pipeline_id,
        VideoPipeline.user_id == current_user.id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Reset pipeline for regeneration
    pipeline.status = "pending"
    pipeline.approval_status = "pending"
    pipeline.script = None
    pipeline.scenes = None
    pipeline.video_url = None
    pipeline.thumbnail_url = None
    pipeline.error_message = None
    pipeline.retry_count += 1
    db.commit()
    db.refresh(pipeline)

    from backend.config import settings as _cfg
    if _cfg.MOCK_VIDEO_GENERATION:
        from backend.hermes_engine.skills.video_generation import VideoGenerationSkill
        skill = VideoGenerationSkill(db)
        try:
            await skill.run_pipeline(pipeline.content_id, current_user.id, pipeline=pipeline)
            db.refresh(pipeline)
        except Exception as e:
            logger.error("Mock regenerate failed: %s", e)
            pipeline.status = "failed"
            pipeline.error_message = str(e)[:2000]
            db.commit()
    else:
        background_tasks.add_task(
            _run_pipeline_background_sync,
            pipeline.id, pipeline.content_id, current_user.id,
        )

    return _pipeline_to_dict(pipeline)


# ── Short-form Video Pipeline (YouTube Shorts) ─────────────

class StartShortPipelineRequest(BaseModel):
    content_id: int


@router.post("/short/start", response_model=PipelineResponse)
async def start_short_pipeline(
    request: StartShortPipelineRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Start short-form video generation pipeline for YouTube Shorts.

    Converts long-form research content to 60-second vertical video.
    Flow: Long-form Content → Short Script → Short Scenes → 9:16 Video → YouTube Shorts
    """
    # Verify content exists and is approved
    content = db.query(Content).filter(
        Content.id == request.content_id,
        Content.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    if content.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Content must be approved before short video generation (current: {content.status})",
        )

    # Check for existing active short pipeline
    existing = db.query(VideoPipeline).filter(
        VideoPipeline.content_id == request.content_id,
        VideoPipeline.status.in_(["pending", "script_generating", "script_ready",
                                   "scenes_generating", "scenes_ready", "video_generating"]),
        VideoPipeline.metadata_json["format"].as_string() == "short",
    ).first()
    if existing:
        return _pipeline_to_dict(existing)

    # Create pipeline record with short-form metadata
    pipeline = VideoPipeline(
        user_id=current_user.id,
        content_id=request.content_id,
        status="pending",
        veo_model=settings.VEO_MODEL,
        aspect_ratio="9:16",
        metadata_json={"format": "short", "aspect_ratio": "9:16", "duration": 60},
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    # Run pipeline
    from backend.config import settings as _cfg
    if _cfg.MOCK_VIDEO_GENERATION:
        from backend.hermes_engine.skills.short_video_generation import ShortVideoGenerationSkill
        skill = ShortVideoGenerationSkill(db)
        try:
            await skill.run_pipeline(request.content_id, current_user.id, pipeline=pipeline)
            db.refresh(pipeline)
        except Exception as e:
            logger.error("Mock short pipeline failed: %s", e)
            pipeline.status = "failed"
            pipeline.error_message = str(e)[:2000]
            db.commit()
    else:
        async def _run_short_background(pid: int, cid: int, uid: int):
            from backend.database import SessionLocal
            from backend.hermes_engine.skills.short_video_generation import ShortVideoGenerationSkill
            db_session = SessionLocal()
            try:
                skill = ShortVideoGenerationSkill(db_session)
                await skill.run_pipeline(cid, uid)
                logger.info("Short pipeline %d completed for content %d", pid, cid)
            except Exception as e:
                logger.error("Short pipeline %d failed: %s", pid, e)
            finally:
                db_session.close()

        background_tasks.add_task(_run_short_background, pipeline.id, request.content_id, current_user.id)

    return _pipeline_to_dict(pipeline)


@router.get("/short/list")
async def list_short_pipelines(
    status_filter: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List short-form video pipelines for the current user."""
    query = db.query(VideoPipeline).filter(
        VideoPipeline.user_id == current_user.id,
        VideoPipeline.metadata_json["format"].as_string() == "short",
    )
    if status_filter:
        query = query.filter(VideoPipeline.status == status_filter)
    pipelines = query.order_by(VideoPipeline.created_at.desc()).limit(limit).all()
    return {
        "pipelines": [_pipeline_to_dict(p) for p in pipelines],
        "total": len(pipelines),
    }


# Need to import settings at module level for _pipeline_to_dict
from backend.config import settings
