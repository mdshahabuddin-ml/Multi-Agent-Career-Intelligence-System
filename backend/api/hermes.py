"""
Hermes API Router - Agent management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.models import User

router = APIRouter(prefix="/hermes", tags=["Hermes"])


class AgentExecuteRequest(BaseModel):
    task: str
    input_data: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None


class AgentResponse(BaseModel):
    agent_id: str
    name: str
    state: str
    task_count: int
    error_count: int


@router.get("/agents")
async def list_agents(
    current_user: User = Depends(get_current_active_user),
):
    """List all registered agents."""
    return {"agents": [], "total": 0}


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get agent details."""
    return {"agent_id": agent_id, "name": "hermes-agent", "state": "idle"}


@router.post("/agents/execute")
async def execute_agent_task(
    request: AgentExecuteRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Execute a task with an agent."""
    return {
        "success": True,
        "task_id": "task_001",
        "result": {"status": "processed"},
        "agent_id": request.agent_id or "hermes-supervisor",
    }


@router.get("/agents/{agent_id}/state")
async def get_agent_state(
    agent_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get agent state."""
    return {"agent_id": agent_id, "state": "idle", "context": {}}


@router.get("/agents/{agent_id}/memory")
async def get_agent_memory(
    agent_id: str,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
):
    """Get agent memory."""
    return {"agent_id": agent_id, "memories": [], "total": 0}


class ContextResolveRequest(BaseModel):
    content_id: int


@router.post("/context/resolve")
async def resolve_content_context(
    request: ContextResolveRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Resolve a Content Item ID into the full Hermes context.

    Returns the original question, content metadata, and career context
    that Hermes uses for downstream generation (video scripts, scenes, etc.).
    """
    from backend.hermes_engine.memory.content_context import ContentContextResolver

    resolver = ContentContextResolver(db)
    try:
        context = resolver.resolve(request.content_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "content_id": request.content_id,
        "original_question": context.get("content", {}).get("original_question"),
        "title": context.get("content", {}).get("title"),
        "body_preview": context.get("content", {}).get("body", "")[:200],
        "tags": context.get("content", {}).get("tags", []),
        "career_context": context.get("career", {}),
    }


class BlueprintRequest(BaseModel):
    content_id: int


@router.post("/blueprint/generate")
async def generate_blueprint(
    request: BlueprintRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate a Content Blueprint from a Content Item.

    Transforms the customer's question + career context into a structured
    learning blueprint. The blueprint is stored in Content.metadata_json
    under the "blueprint" key.
    """
    from backend.models.content import Content
    from backend.hermes_engine.skills.content_blueprint_generator import ContentBlueprintGenerator

    # Verify content exists and belongs to user
    content = db.query(Content).filter(
        Content.id == request.content_id,
        Content.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    generator = ContentBlueprintGenerator(db)
    try:
        blueprint = generator.generate(request.content_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Persist blueprint in Content.metadata_json
    meta = content.metadata_json or {}
    meta["blueprint"] = blueprint.to_dict()
    content.metadata_json = meta
    db.commit()
    db.refresh(content)

    return {
        "content_id": content.id,
        "blueprint": blueprint.to_dict(),
        "stored": True,
    }


@router.get("/blueprint/{content_id}")
async def get_blueprint(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve the stored blueprint for a Content Item."""
    from backend.models.content import Content
    from backend.hermes_engine.models.content_blueprint import ContentBlueprint

    content = db.query(Content).filter(
        Content.id == content_id,
        Content.user_id == current_user.id,
    ).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    meta = content.metadata_json or {}
    blueprint_data = meta.get("blueprint")
    if not blueprint_data:
        raise HTTPException(status_code=404, detail="No blueprint found for this content")

    return {
        "content_id": content.id,
        "blueprint": blueprint_data,
    }
