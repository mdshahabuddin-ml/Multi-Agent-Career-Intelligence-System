import time
import hashlib
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from fastapi import Request, HTTPException, status, Depends

from backend.database import get_db
from backend.models.organization import Organization, OrganizationPlan
from backend.models.user import User
from backend.dependencies import get_current_active_user
from backend.config import settings


@dataclass
class RateLimitRule:
    """A rate limit rule."""
    name: str
    max_requests: int
    window_seconds: int
    scope: str  # "user", "ip", "organization", "api_key", "global"
    endpoints: Optional[list] = None  # None = all endpoints
    methods: Optional[list] = None    # None = all methods
    bypass_roles: list = field(default_factory=lambda: ["admin", "super_admin"])


@dataclass
class QuotaRule:
    """A quota rule for resource usage."""
    name: str
    resource: str  # "jobs", "research", "api_calls", "storage", "members"
    limit: int
    period: str  # "hourly", "daily", "monthly", "yearly"
    scope: str  # "user", "organization"
    plan_overrides: Dict[str, int] = field(default_factory=dict)


class RateLimiter:
    """Advanced rate limiter with multiple strategies."""
    
    def __init__(self):
        self.rules: List[RateLimitRule] = []
        self.quotas: List[QuotaRule] = []
        self._memory_store: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        
        # Initialize default rules
        self._init_default_rules()
    
    def _init_default_rules(self):
        """Initialize default rate limit and quota rules."""
        self.rules = [
            # API rate limits
            RateLimitRule(
                name="api_global",
                max_requests=1000,
                window_seconds=60,
                scope="global",
            ),
            RateLimitRule(
                name="api_per_ip",
                max_requests=100,
                window_seconds=60,
                scope="ip",
            ),
            RateLimitRule(
                name="api_per_user",
                max_requests=500,
                window_seconds=60,
                scope="user",
            ),
            RateLimitRule(
                name="auth_login",
                max_requests=5,
                window_seconds=300,  # 5 per 5 minutes
                scope="ip",
                endpoints=["/auth/login", "/auth/register"],
                methods=["POST"],
            ),
            RateLimitRule(
                name="auth_password_reset",
                max_requests=3,
                window_seconds=3600,  # 3 per hour
                scope="ip",
                endpoints=["/auth/forgot-password", "/auth/reset-password"],
                methods=["POST"],
            ),
            RateLimitRule(
                name="search_api",
                max_requests=30,
                window_seconds=60,
                scope="user",
                endpoints=["/jobs/search", "/jobs/search"],
                methods=["GET", "POST"],
            ),
            RateLimitRule(
                name="research_api",
                max_requests=10,
                window_seconds=3600,  # 10 per hour
                scope="user",
                endpoints=["/research", "/research/"],
                methods=["POST"],
            ),
            RateLimitRule(
                name="research_status",
                max_requests=60,
                window_seconds=60,  # 60 per minute
                scope="user",
                endpoints=["/research/", "/research/status", "/research/report", "/research/export"],
                methods=["GET"],
            ),
            RateLimitRule(
                name="research_ws",
                max_requests=5,
                window_seconds=3600,  # 5 WebSocket connections per hour
                scope="user",
                endpoints=["/research/ws/"],
                methods=["GET"],
            ),
            RateLimitRule(
                name="file_upload",
                max_requests=20,
                window_seconds=3600,  # 20 per hour
                scope="user",
                endpoints=["/resume/upload", "/resume/"],
                methods=["POST"],
            ),
        ]
        
        self.quotas = [
            QuotaRule(
                name="jobs_monthly",
                resource="jobs",
                limit=100,  # overridden by plan
                period="monthly",
                scope="organization",
                plan_overrides={
                    "free": 10,
                    "starter": 100,
                    "professional": 1000,
                    "enterprise": 10000,
                    "custom": 100000,
                }
            ),
            QuotaRule(
                name="research_monthly",
                resource="research",
                limit=5,
                period="monthly",
                scope="organization",
                plan_overrides={
                    "free": 5,
                    "starter": 50,
                    "professional": 500,
                    "enterprise": 5000,
                    "custom": 50000,
                }
            ),
            QuotaRule(
                name="api_calls_monthly",
                resource="api_calls",
                limit=1000,
                period="monthly",
                scope="organization",
                plan_overrides={
                    "free": 1000,
                    "starter": 10000,
                    "professional": 100000,
                    "enterprise": 1000000,
                    "custom": 10000000,
                }
            ),
            QuotaRule(
                name="members",
                resource="members",
                limit=5,
                period="monthly",  # effectively permanent limit
                scope="organization",
                plan_overrides={
                    "free": 5,
                    "starter": 10,
                    "professional": 50,
                    "enterprise": 500,
                    "custom": 10000,
                }
            ),
        ]
    
    def add_rule(self, rule: RateLimitRule):
        """Add a custom rate limit rule."""
        self.rules.append(rule)
    
    def add_quota(self, quota: QuotaRule):
        """Add a custom quota rule."""
        self.quotas.append(quota)
    
    def _get_identifier(self, request: Request, scope: str, user: Optional[User] = None) -> str:
        """Get rate limit identifier based on scope."""
        if scope == "global":
            return "global"
        elif scope == "ip":
            # Get real IP considering proxies
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.client.host if request.client else "unknown"
            return f"ip:{ip}"
        elif scope == "user":
            if user:
                return f"user:{user.id}"
            # Fallback to IP if no user
            forwarded = request.headers.get("X-Forwarded-For")
            ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
            return f"ip:{ip}"
        elif scope == "organization":
            # Would need organization context
            return "org:unknown"
        elif scope == "api_key":
            api_key = request.headers.get("X-API-Key")
            if api_key:
                return f"apikey:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
            return "apikey:unknown"
        return "unknown"
    
    def _get_window_key(self, identifier: str, window_seconds: int) -> str:
        """Generate window key for sliding window."""
        window = int(time.time() / window_seconds)
        return f"{identifier}:{window}"
    
    def _cleanup_old_entries(self):
        """Clean up expired entries from memory store."""
        if time.time() - self._last_cleanup < self._cleanup_interval:
            return
        
        now = time.time()
        for key in list(self._memory_store.keys()):
            # Remove entries older than 1 hour
            expired_keys = [
                k for k, v in self._memory_store[key].items()
                if isinstance(v, dict) and v.get("expires_at", 0) < now
            ]
            for k in expired_keys:
                del self._memory_store[key][k]
        
        self._last_cleanup = now
    
    def check_rate_limit(
        self,
        request: Request,
        user: Optional[User] = None,
        organization: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Check rate limits for request."""
        self._cleanup_old_entries()
        
        path = request.url.path
        method = request.method
        user_roles = getattr(user, "roles", []) if user else []
        
        results = {
            "allowed": True,
            "limits": [],
            "retry_after": None,
        }
        
        for rule in self.rules:
            # Check if rule applies to this request
            if rule.endpoints and path not in rule.endpoints:
                continue
            if rule.methods and method not in rule.methods:
                continue
            if any(role in user_roles for role in rule.bypass_roles):
                continue
            
            identifier = self._get_identifier(request, rule.scope, user)
            window_key = self._get_window_key(identifier, rule.window_seconds)
            
            # Get current count
            current = self._memory_store.get(rule.name, {}).get(window_key, 0)
            
            if current >= rule.max_requests:
                # Rate limited
                results["allowed"] = False
                retry_after = rule.window_seconds - (int(time.time()) % rule.window_seconds)
                results["retry_after"] = retry_after
                results["limits"].append({
                    "rule": rule.name,
                    "limit": rule.max_requests,
                    "remaining": 0,
                    "reset_in": retry_after,
                    "scope": rule.scope,
                })
                break
            
            # Increment counter
            self._memory_store[rule.name][window_key] = current + 1
            
            results["limits"].append({
                "rule": rule.name,
                "limit": rule.max_requests,
                "remaining": rule.max_requests - current - 1,
                "reset_in": rule.window_seconds - (int(time.time()) % rule.window_seconds),
                "scope": rule.scope,
            })
        
        return results
    
    def check_quota(
        self,
        organization: Any,
        resource: str,
        quantity: int = 1,
    ) -> Dict[str, Any]:
        """Check if organization has quota for resource."""
        org_plan = organization.plan.value if hasattr(organization.plan, 'value') else organization.plan
        
        for quota in self.quotas:
            if quota.resource != resource:
                continue
            
            # Get limit for this plan
            limit = quota.plan_overrides.get(org_plan, quota.limit)
            
            # Get current usage
            if resource == "jobs":
                used = organization.jobs_used_this_month
            elif resource == "research":
                used = organization.research_used_this_month
            elif resource == "api_calls":
                used = organization.api_calls_used_this_month
            elif resource == "members":
                used = organization.current_members
            else:
                continue
            
            remaining = max(0, limit - used)
            allowed = (used + quantity) <= limit
            
            return {
                "allowed": allowed,
                "resource": resource,
                "limit": limit,
                "used": used,
                "remaining": remaining,
                "quantity_requested": quantity,
                "plan": org_plan,
            }
        
        return {"allowed": True, "resource": resource}
    
    def consume_quota(
        self,
        organization: Any,
        resource: str,
        quantity: int = 1,
    ) -> bool:
        """Consume quota for resource."""
        quota_check = self.check_quota(organization, resource, quantity)
        if not quota_check["allowed"]:
            return False
        
        # Update usage
        if resource == "jobs":
            organization.jobs_used_this_month += quantity
        elif resource == "research":
            organization.research_used_this_month += quantity
        elif resource == "api_calls":
            organization.api_calls_used_this_month += quantity
        elif resource == "members":
            organization.current_members += quantity
        
        return True
    
    def get_quota_status(self, organization: Any) -> Dict[str, Any]:
        """Get all quota statuses for organization."""
        statuses = {}
        for quota in self.quotas:
            quota_check = self.check_quota(organization, quota.resource)
            if quota_check:
                statuses[quota.resource] = quota_check
        return statuses


class QuotaManager:
    """Manages resource quotas for organizations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_organization_quotas(self, org_id: int) -> Dict[str, Any]:
        """Get all quota statuses for an organization."""
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            return {}
        
        limiter = RateLimiter()
        return limiter.get_quota_status(org)
    
    def check_and_consume(self, org_id: int, resource: str, quantity: int = 1) -> bool:
        """Check and consume quota atomically."""
        org = self.db.query(Organization).filter(Organization.id == org_id).with_for_update().first()
        if not org:
            return False
        
        limiter = RateLimiter()
        return limiter.consume_quota(organization=org, resource=resource, quantity=quantity)
    
    def get_quota_status(self, org_id: int) -> Dict[str, Any]:
        """Get quota status for organization."""
        return self.get_organization_quotas(org_id)
    
    def reset_monthly_quotas(self, org_id: int) -> Organization:
        """Reset monthly quotas for organization."""
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if org:
            org.jobs_used_this_month = 0
            org.research_used_this_month = 0
            org.api_calls_used_this_month = 0
            org.usage_reset_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(org)
        return org
    
    def update_organization_plan(self, org_id: int, new_plan: OrganizationPlan) -> Organization:
        """Update organization plan and apply new limits."""
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise ValueError("Organization not found")
        
        org.plan = new_plan
        
        # Apply new plan limits
        limits = {
            OrganizationPlan.FREE: {"max_members": 5, "max_jobs_per_month": 10, "max_research_per_month": 5, "max_api_calls_per_month": 1000},
            OrganizationPlan.STARTER: {"max_members": 10, "max_jobs_per_month": 100, "max_research_per_month": 50, "max_api_calls_per_month": 10000},
            OrganizationPlan.PROFESSIONAL: {"max_members": 50, "max_jobs_per_month": 1000, "max_research_per_month": 500, "max_api_calls_per_month": 100000},
            OrganizationPlan.ENTERPRISE: {"max_members": 500, "max_jobs_per_month": 10000, "max_research_per_month": 5000, "max_api_calls_per_month": 1000000},
            OrganizationPlan.CUSTOM: {"max_members": 10000, "max_jobs_per_month": 100000, "max_research_per_month": 50000, "max_api_calls_per_month": 10000000},
        }
        
        new_limits = limits.get(new_plan, limits[OrganizationPlan.FREE])
        for key, value in new_limits.items():
            setattr(org, key, value)
        
        self.db.commit()
        self.db.refresh(org)
        return org


# Global rate limiter instance
rate_limiter = RateLimiter()
quota_manager: Optional[QuotaManager] = None


def get_rate_limiter() -> RateLimiter:
    return rate_limiter


def get_quota_manager(db: Session = Depends(get_db)) -> QuotaManager:
    global quota_manager
    if quota_manager is None:
        quota_manager = QuotaManager(db)
    return quota_manager


def rate_limit_dependency(
    request: Request,
    current_user = Depends(get_current_active_user),
    limiter: RateLimiter = Depends(get_rate_limiter),
):
    """FastAPI dependency for rate limiting."""
    result = limiter.check_rate_limit(request, current_user)
    
    # Add rate limit headers
    for limit in result["limits"]:
        # In production, would add to response headers
        pass
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(result["retry_after"] or 60)},
        )
    
    return result


def create_quota_dependency(resource: str, quantity: int = 1):
    """Create a quota checking dependency for a specific resource."""
    async def quota_dependency(
        current_user = Depends(get_current_active_user),
        quota_mgr: QuotaManager = Depends(get_quota_manager),
    ):
        """FastAPI dependency for quota checking."""
        # Get user's organization
        org_id = getattr(current_user, "organization_id", None)
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not associated with an organization",
            )
        
        allowed = quota_mgr.check_and_consume(org_id, resource, quantity)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quota exceeded for {resource}",
            )
        
        return True
    
    return quota_dependency


# Backwards compatibility - removed, use create_quota_dependency instead
# def quota_check_dependency(...):
#     pass