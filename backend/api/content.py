"""
Content API Router - Content management endpoints.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User
from backend.models.content import Content

router = APIRouter(prefix="/content", tags=["Content"])


class ContentCreateRequest(BaseModel):
    title: str
    content_type: str = "post"
    body: str = ""
    tags: Optional[List[str]] = None
    original_question: Optional[str] = None


def _content_to_dict(item: Content) -> Dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "original_question": item.original_question,
        "content_type": item.content_type,
        "body": item.body,
        "summary": item.summary,
        "tags_json": item.tags_json or [],
        "status": item.status,
        "quality_score": item.quality_score,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.get("/content")
async def list_content(
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List content items for the current user."""
    query = db.query(Content).filter(Content.user_id == current_user.id)
    if content_type:
        query = query.filter(Content.content_type == content_type)
    if status:
        query = query.filter(Content.status == status)
    items = query.order_by(Content.created_at.desc()).limit(limit).all()
    return {"content": [_content_to_dict(i) for i in items], "total": len(items)}


@router.post("/content")
async def create_content(
    request: ContentCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new content item."""
    item = Content(
        user_id=current_user.id,
        title=request.title,
        original_question=request.original_question,
        content_type=request.content_type,
        body=request.body,
        tags_json=request.tags,
        status="draft",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "success": True,
        "content_id": item.id,
        "title": item.title,
    }


@router.get("/content/{content_id}")
async def get_content(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get content details for the current user."""
    item = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return _content_to_dict(item)


@router.put("/content/{content_id}")
async def update_content(
    content_id: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update content for the current user."""
    item = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    allowed_fields = {"title", "content_type", "body", "tags_json", "status", "original_question"}
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return {"success": True, "content_id": item.id}


@router.delete("/content/{content_id}")
async def delete_content(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete content for the current user."""
    item = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.delete(item)
    db.commit()
    return {"success": True, "message": f"Content {content_id} deleted"}


@router.post("/content/{content_id}/publish")
async def publish_content(
    content_id: int,
    platforms: List[str] = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Publish content to platforms. Only approved content can be published."""
    item = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    if item.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content must be approved before publishing",
        )
    return {"success": True, "content_id": item.id, "platforms": platforms}
