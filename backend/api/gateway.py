"""
Gateway API Router - Gateway management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.dependencies import get_current_active_user
from backend.models import User

router = APIRouter(prefix="/gateway", tags=["Gateway"])


@router.get("/routes")
async def list_routes(
    current_user: User = Depends(get_current_active_user),
):
    """List all gateway routes."""
    return {"routes": [], "total": 0}


@router.get("/adapters")
async def list_adapters(
    current_user: User = Depends(get_current_active_user),
):
    """List available adapters."""
    return {"adapters": ["telegram", "discord", "slack", "whatsapp"]}


@router.post("/send")
async def send_message(
    adapter: str,
    target: str,
    message: str,
    current_user: User = Depends(get_current_active_user),
):
    """Send a message via gateway."""
    return {"success": True, "adapter": adapter, "target": target}
