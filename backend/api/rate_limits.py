from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.api import auth
from backend.services.rate_limit_service import (
    RateLimiter, QuotaManager, RateLimitRule, QuotaRule,
    get_rate_limiter, get_quota_manager, rate_limit_dependency, create_quota_dependency,
)
from backend.models.organization import Organization

router = APIRouter(prefix="/rate-limits", tags=["Rate Limits & Quotas"])


def get_limiter(db: Session = Depends(get_db)) -> RateLimiter:
    return get_rate_limiter()


def get_qm(db: Session = Depends(get_db)) -> QuotaManager:
    return get_quota_manager(db)


# ============= Rate Limit Rules =============

class RateLimitRuleCreate(BaseModel):
    name: str
    max_requests: int
    window_seconds: int
    scope: str
    endpoints: Optional[List[str]] = None
    methods: Optional[List[str]] = None
    bypass_roles: List[str] = ["admin", "super_admin"]


class RateLimitRuleResponse(BaseModel):
    name: str
    max_requests: int
    window_seconds: int
    scope: str
    endpoints: Optional[List[str]]
    methods: Optional[List[str]]
    bypass_roles: List[str]


@router.get("/rules", response_model=List[RateLimitRuleResponse])
async def list_rate_limit_rules(
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """List all rate limit rules."""
    return [
        RateLimitRuleResponse(
            name=rule.name,
            max_requests=rule.max_requests,
            window_seconds=rule.window_seconds,
            scope=rule.scope,
            endpoints=rule.endpoints,
            methods=rule.methods,
            bypass_roles=rule.bypass_roles,
        )
        for rule in limiter.rules
    ]


@router.post("/rules", response_model=RateLimitRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rate_limit_rule(
    rule: RateLimitRuleCreate,
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """Create a custom rate limit rule."""
    # Check if rule name already exists
    existing = next((r for r in limiter.rules if r.name == rule.name), None)
    if existing:
        raise HTTPException(status_code=400, detail="Rule with this name already exists")
    
    new_rule = RateLimitRule(
        name=rule.name,
        max_requests=rule.max_requests,
        window_seconds=rule.window_seconds,
        scope=rule.scope,
        endpoints=rule.endpoints,
        methods=rule.methods,
        bypass_roles=rule.bypass_roles,
    )
    limiter.add_rule(new_rule)
    
    return RateLimitRuleResponse(
        name=new_rule.name,
        max_requests=new_rule.max_requests,
        window_seconds=new_rule.window_seconds,
        scope=new_rule.scope,
        endpoints=new_rule.endpoints,
        methods=new_rule.methods,
        bypass_roles=new_rule.bypass_roles,
    )


@router.delete("/rules/{rule_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rate_limit_rule(
    rule_name: str,
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """Delete a custom rate limit rule (cannot delete built-in rules)."""
    # Prevent deletion of built-in rules
    built_in = {"api_global", "api_per_ip", "api_per_user", "auth_login", "auth_password_reset", 
                "search_api", "research_api", "file_upload"}
    if rule_name in built_in:
        raise HTTPException(status_code=400, detail="Cannot delete built-in rule")
    
    rule = next((r for r in limiter.rules if r.name == rule_name), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    limiter.rules.remove(rule)


# ============= Quota Rules =============

class QuotaRuleCreate(BaseModel):
    name: str
    resource: str
    limit: int
    period: str
    scope: str
    plan_overrides: Dict[str, int] = {}


class QuotaRuleResponse(BaseModel):
    name: str
    resource: str
    limit: int
    period: str
    scope: str
    plan_overrides: Dict[str, int]


@router.get("/quotas/rules", response_model=List[QuotaRuleResponse])
async def list_quota_rules(
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """List all quota rules."""
    return [
        QuotaRuleResponse(
            name=q.name,
            resource=q.resource,
            limit=q.limit,
            period=q.period,
            scope=q.scope,
            plan_overrides=q.plan_overrides,
        )
        for q in limiter.quotas
    ]


@router.post("/quotas/rules", response_model=QuotaRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_quota_rule(
    quota: QuotaRuleCreate,
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """Create a custom quota rule."""
    existing = next((q for q in limiter.quotas if q.name == quota.name), None)
    if existing:
        raise HTTPException(status_code=400, detail="Quota rule with this name already exists")
    
    new_quota = QuotaRule(
        name=quota.name,
        resource=quota.resource,
        limit=quota.limit,
        period=quota.period,
        scope=quota.scope,
        plan_overrides=quota.plan_overrides,
    )
    limiter.add_quota(new_quota)
    
    return QuotaRuleResponse(
        name=new_quota.name,
        resource=new_quota.resource,
        limit=new_quota.limit,
        period=new_quota.period,
        scope=new_quota.scope,
        plan_overrides=new_quota.plan_overrides,
    )


@router.delete("/quotas/rules/{quota_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quota_rule(
    quota_name: str,
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """Delete a custom quota rule."""
    quota = next((q for q in limiter.quotas if q.name == quota_name), None)
    if not quota:
        raise HTTPException(status_code=404, detail="Quota rule not found")
    
    limiter.quotas.remove(quota)


# ============= Quota Status & Management =============

class QuotaStatusResponse(BaseModel):
    resource: str
    limit: int
    used: int
    remaining: int
    plan: str
    percentage: float


@router.get("/organizations/{org_id}/quotas", response_model=List[QuotaStatusResponse])
async def get_organization_quotas(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    qm: QuotaManager = Depends(get_qm),
):
    """Get all quota statuses for an organization."""
    statuses = qm.get_organization_quotas(org_id)
    return [
        QuotaStatusResponse(
            resource=k,
            limit=v["limit"],
            used=v["used"],
            remaining=v["remaining"],
            plan=v["plan"],
            percentage=(v["used"] / v["limit"] * 100) if v["limit"] > 0 else 0,
        )
        for k, v in statuses.items()
    ]


@router.get("/organizations/{org_id}/quotas/{resource}", response_model=Dict[str, Any])
async def get_organization_quota(
    org_id: int,
    resource: str,
    current_user = Depends(auth.get_current_active_user),
    qm: QuotaManager = Depends(get_qm),
):
    """Get quota status for a specific resource."""
    statuses = qm.get_organization_quotas(org_id)
    if resource not in statuses:
        raise HTTPException(status_code=404, detail=f"Quota for {resource} not found")
    return statuses[resource]


@router.post("/organizations/{org_id}/quotas/{resource}/consume")
async def consume_quota(
    org_id: int,
    resource: str,
    quantity: int = Query(1, ge=1),
    current_user = Depends(auth.get_current_active_user),
    qm: QuotaManager = Depends(get_qm),
):
    """Consume quota for a resource."""
    allowed = qm.check_and_consume(org_id, resource, quantity)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Quota exceeded for {resource}")
    return {"allowed": True, "resource": resource, "quantity": quantity}


@router.post("/organizations/{org_id}/quotas/reset")
async def reset_monthly_quotas(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    qm: QuotaManager = Depends(get_qm),
):
    """Reset monthly quotas for organization."""
    org = qm.reset_monthly_quotas(org_id)
    return {
        "message": "Monthly quotas reset",
        "organization_id": org.id,
        "reset_at": org.usage_reset_at.isoformat(),
    }


# ============= Rate Limit Status =============

class RateLimitStatusResponse(BaseModel):
    allowed: bool
    limits: List[Dict[str, Any]]
    retry_after: Optional[int]


@router.get("/status", response_model=RateLimitStatusResponse)
async def get_rate_limit_status(
    request: Request,
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """Get current rate limit status for the request."""
    result = limiter.check_rate_limit(request, current_user)
    return RateLimitStatusResponse(**result)


@router.get("/test/{rule_name}")
async def test_rate_limit(
    rule_name: str,
    requests: int = Query(10),
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """Test a rate limit rule by making simulated requests."""
    rule = next((r for r in limiter.rules if r.name == rule_name), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Create mock request
    mock_request = Request(scope={
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
        "client": ("127.0.0.1", 8000),
    })
    
    results = []
    for i in range(requests):
        result = limiter.check_rate_limit(mock_request, None)
        results.append({
            "request": i + 1,
            "allowed": result["allowed"],
            "limits": result["limits"],
        })
        if not result["allowed"]:
            break
    
    return {
        "rule": rule_name,
        "total_requests": len(results),
        "allowed": sum(1 for r in results if r["allowed"]),
        "denied": sum(1 for r in results if not r["allowed"]),
        "results": results,
    }


# ============= Admin Quota Management =============

class PlanLimitUpdate(BaseModel):
    plan: str
    resource: str
    limit: int


@router.post("/admin/plan-limits")
async def update_plan_limit(
    update: PlanLimitUpdate,
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """Update quota limit for a specific plan (admin only)."""
    quota = next((q for q in limiter.quotas if q.resource == update.resource), None)
    if not quota:
        raise HTTPException(status_code=404, detail=f"Quota rule for {update.resource} not found")
    
    quota.plan_overrides[update.plan] = update.limit
    return {"message": f"Updated {update.resource} limit for {update.plan} plan to {update.limit}"}


@router.get("/admin/plan-limits")
async def list_plan_limits(
    current_user = Depends(auth.get_current_active_user),
    limiter: RateLimiter = Depends(get_limiter),
):
    """List all plan limits for all quota rules."""
    result = {}
    for quota in limiter.quotas:
        result[quota.resource] = {
            "default": quota.limit,
            "by_plan": quota.plan_overrides,
        }
    return result