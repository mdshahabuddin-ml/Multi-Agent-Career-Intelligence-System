"""
Skills API Router - Agent skills endpoints backed by the real skill backend.

Wiring (Step 4):
- One ``hermes`` ``SkillManager`` (registry + timeout-guarded executor)
  per user id. Per-user managers reuse the EXISTING manager class — no new
  registry, no new service — and give user isolation: a caller only ever
  sees skills registered under their own id.
- Registry presence is the approval record: only human-registered or
  promotion-approved skills can exist in a manager, so unapproved names
  404. ``enabled`` is enforced on every execute (403 when disabled).
- Read operations (list/get/search/stats) never execute anything.
- Response shapes keep the original keys; only previously-impossible
  error cases gain statuses (404 unknown, 403 disabled, 504 timeout).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_active_user
from backend.hermes.skills.manager import SkillManager
from backend.hermes.skills.registry import SkillDisabledError
from backend.models import User
from backend.models.hermes_skill import HermesSkill, HermesSkillExecution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["Skills"])


class SkillExecuteRequest(BaseModel):
    params: Optional[Dict[str, Any]] = None
    timeout: Optional[float] = None


_managers: Dict[int, SkillManager] = {}
_managers_lock = threading.Lock()
_reconciled: set[int] = set()


def get_skill_manager(user_id: int) -> SkillManager:
    """Return the calling user's skill manager (created on first use)."""
    with _managers_lock:
        manager = _managers.get(user_id)
        if manager is None:
            manager = SkillManager()
            _managers[user_id] = manager
        return manager


def _resolve_persisted_handler(row: HermesSkill) -> Optional[Any]:
    """Re-resolve a persisted skill's handler. None = skip (fail closed).

    Module-addressed rows go through the Step-1 allowlisted loader.
    Template-addressed rows cannot resolve (no persistent template store
    exists) and are skipped with a log line — re-promote to restore.
    """
    from backend.hermes_engine.skills.skill_loader import (
        SkillLoader,
        is_allowed_module,
    )

    if row.module_path and row.function_name:
        if not is_allowed_module(row.module_path):
            logger.warning("Skipping skill %r: module outside allowlist", row.name)
            return None
        try:
            return SkillLoader().load_from_module(row.module_path, row.function_name)
        except Exception as exc:
            logger.warning("Skipping skill %r: reload failed: %s", row.name, exc)
            return None
    if row.template:
        logger.info("Skipping template skill %r: no persistent template store", row.name)
    return None


def _ensure_reconciled(manager: SkillManager, user_id: int, db: Session) -> None:
    """Rehydrate owned+enabled rows after restart (once per user per process).

    Only rows owned by this user rehydrate (isolation); disabled,
    ownerless legacy, and unresolvable rows are skipped. Failures defer
    (unmarked) so a later call retries; per-row skips never abort others.
    """
    with _managers_lock:
        if user_id in _reconciled:
            return
    try:
        rows = (
            db.query(HermesSkill)
            .filter(HermesSkill.user_id == user_id, HermesSkill.enabled == True)  # noqa: E712
            .all()
        )
    except Exception as exc:
        logger.warning("Skill reconcile deferred for user %s: %s", user_id, exc)
        return
    with _managers_lock:
        _reconciled.add(user_id)
    for row in rows:
        if manager.get(row.name):
            continue
        handler = _resolve_persisted_handler(row)
        if handler is None or not callable(handler):
            continue
        try:
            manager.register(
                row.name, handler,
                description=row.description or "",
                parameters=dict(row.parameters_json or {}),
                tags=list(row.tags_json or []),
            )
        except ValueError:
            continue  # duplicate race: existing entry wins


def _for_user(current_user: User, db: Session) -> SkillManager:
    manager = get_skill_manager(int(current_user.id))
    _ensure_reconciled(manager, int(current_user.id), db)
    return manager


@router.get("/skills")
async def list_skills(
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all registered skills."""
    skills = _for_user(current_user, db).list_skills(tag=tag)
    return {"skills": skills, "total": len(skills)}


# NOTE: static routes are declared BEFORE "/skills/{skill_name}" so they
# are not shadowed by the path parameter.


@router.get("/skills/search")
async def search_skills(
    query: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Search skills."""
    results = _for_user(current_user, db).search(query)
    return {"results": results, "total": len(results)}


@router.get("/skills/stats")
async def get_skill_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get skill execution statistics."""
    manager = _for_user(current_user, db)
    totals = manager.get_stats()
    skills = manager.list_skills()
    return {
        "total_skills": len(skills),
        "total_executions": totals["total_executions"],
        "successful": totals["total_executions"] - totals["total_errors"],
        "failed": totals["total_errors"],
    }


@router.get("/skills/{skill_name}")
async def get_skill(
    skill_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get skill details."""
    skill = _for_user(current_user, db).get(skill_name)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_name}' not found",
        )
    return {
        "name": skill["name"],
        "description": skill["description"],
        "execution_count": skill["execution_count"],
    }


def _record_execution(
    db: Session,
    user_id: int,
    skill_name: str,
    params: Dict[str, Any],
    success: bool,
    result: Any = None,
    error: Optional[str] = None,
) -> None:
    """Best-effort execution audit + counter write-back. Never raises.

    Only owned persisted rows are touched (legacy ownerless rows get no
    history — same fail-closed rule as rehydration). Failures here must
    never break the execution response itself.
    """
    import json as _json

    try:
        row = (
            db.query(HermesSkill)
            .filter(HermesSkill.name == skill_name, HermesSkill.user_id == user_id)
            .first()
        )
        if row is None:
            return
        try:
            output = _json.loads(_json.dumps({"result": result}, default=str))
        except Exception:
            output = {"result": str(result)[:2000]}
        db.add(HermesSkillExecution(
            skill_id=row.id,
            agent_id="api",
            user_id=user_id,
            success=success,
            duration_ms=None,
            error_message=(str(error)[:2000] if error else None),
            input_json=dict(params),
            output_json=output if success else None,
        ))
        if success:
            row.execution_count = (row.execution_count or 0) + 1
        else:
            row.error_count = (row.error_count or 0) + 1
        db.commit()
    except Exception as exc:  # noqa: BLE001 - audit must not break execution
        logger.warning("Skill execution audit skipped for %r: %s", skill_name, exc)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001 - defensive
            pass


def _db_enabled(db: Session, user_id: int, skill_name: str) -> Optional[bool]:
    """Authoritative DB enabled-state for an owned persisted skill.

    Returns None when there is no owned row (ephemeral/human-session
    skills stay governed by the in-memory flag) or when the lookup itself
    fails (DB trouble must not block execution the memory gate allows).
    An explicit False denies execution regardless of memory state.
    """
    try:
        row = (
            db.query(HermesSkill)
            .filter(HermesSkill.name == skill_name, HermesSkill.user_id == user_id)
            .first()
        )
    except Exception as exc:  # noqa: BLE001 - availability over audit strictness
        logger.warning("Skill enabled lookup deferred for %r: %s", skill_name, exc)
        return None
    if row is None:
        return None
    return bool(row.enabled)


@router.post("/skills/{skill_name}/execute")
async def execute_skill(
    skill_name: str,
    request: SkillExecuteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Execute a skill (registered + enabled only; never on read paths)."""
    manager = _for_user(current_user, db)
    params = request.params or {}
    db_state = _db_enabled(db, int(current_user.id), skill_name)
    if db_state is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Skill '{skill_name}' is disabled",
        )
    try:
        result = await manager.execute(
            skill_name,
            params=params,
            timeout=request.timeout,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_name}' not found",
        )
    except SkillDisabledError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Skill '{skill_name}' is disabled",
        )
    except TimeoutError as exc:
        _record_execution(db, int(current_user.id), skill_name, params,
                          success=False, error=f"timed out: {exc}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Skill '{skill_name}' execution timed out",
        )
    except Exception as exc:
        # Unexpected handler failures still propagate (500), but the audit
        # trail records them first.
        _record_execution(db, int(current_user.id), skill_name, params,
                          success=False, error=str(exc))
        raise
    _record_execution(db, int(current_user.id), skill_name, params,
                      success=True, result=result)
    return {
        "success": True,
        "skill": skill_name,
        "result": result,
    }
