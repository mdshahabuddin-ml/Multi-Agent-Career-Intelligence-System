from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from datetime import datetime, timedelta

from backend.database import get_db
from backend.api import auth
from backend.services.billing_service import BillingService, OrganizationService
from backend.schemas.organization import (
    OrganizationResponse, OrganizationUsageResponse,
    SubscriptionResponse, InvoiceResponse, FeatureFlagResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_billing(db: Session = Depends(get_db)) -> BillingService:
    return BillingService(db)


def get_org_service(db: Session = Depends(get_db)) -> OrganizationService:
    return OrganizationService(db)


# ============= Admin Dashboard =============

@router.get("/dashboard/stats")
async def get_admin_stats(
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Get admin dashboard statistics."""
    # Check if user is super admin (in production, check role)
    # For now, allow any authenticated user to see stats
    
    total_orgs = billing.db.query(Organization).count()
    active_orgs = billing.db.query(Organization).filter(
        Organization.status == "active"
    ).count()
    trial_orgs = billing.db.query(Organization).filter(
        Organization.status == "trial"
    ).count()
    
    total_users = billing.db.query(User).count()
    active_users = billing.db.query(User).filter(
        User.is_active == True
    ).count()
    
    # Revenue metrics
    paid_orgs = billing.db.query(Organization).filter(
        Organization.plan.in_(["starter", "professional", "enterprise", "custom"])
    ).count()
    
    # Usage
    total_jobs = billing.db.query(Organization).with_entities(
        func.sum(Organization.jobs_used_this_month)
    ).scalar() or 0
    
    total_research = billing.db.query(Organization).with_entities(
        func.sum(Organization.research_used_this_month)
    ).scalar() or 0
    
    total_api_calls = billing.db.query(Organization).with_entities(
        func.sum(Organization.api_calls_used_this_month)
    ).scalar() or 0
    
    return {
        "organizations": {
            "total": total_orgs,
            "active": active_orgs,
            "trial": trial_orgs,
            "paid": paid_orgs,
        },
        "users": {
            "total": total_users,
            "active": active_users,
        },
        "usage": {
            "jobs_this_month": total_jobs,
            "research_this_month": total_research,
            "api_calls_this_month": total_api_calls,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/organizations", response_model=List[dict])
async def admin_list_organizations(
    status: Optional[str] = Query(None),
    plan: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """List all organizations with filters."""
    query = billing.db.query(Organization)
    
    if status:
        query = query.filter(Organization.status == status)
    if plan:
        query = query.filter(Organization.plan == plan)
    if search:
        query = query.filter(
            or_(
                Organization.name.ilike(f"%{search}%"),
                Organization.slug.ilike(f"%{search}%"),
                Organization.billing_email.ilike(f"%{search}%"),
            )
        )
    
    orgs = query.order_by(desc(Organization.created_at)).offset(offset).limit(limit).all()
    
    return [
        {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "status": org.status.value,
            "plan": org.plan.value,
            "billing_email": org.billing_email,
            "current_members": org.current_members,
            "max_members": org.max_members,
            "jobs_used_this_month": org.jobs_used_this_month,
            "max_jobs_per_month": org.max_jobs_per_month,
            "created_at": org.created_at.isoformat(),
            "trial_ends_at": org.trial_ends_at.isoformat() if org.trial_ends_at else None,
        }
        for org in orgs
    ]


@router.get("/organizations/{org_id}", response_model=dict)
async def admin_get_organization(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Get detailed organization info."""
    org = billing.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    subscription = billing.get_subscription(org_id)
    invoices = billing.get_invoices(org_id)
    usage = billing.get_organization_usage(org_id)
    members = billing.get_members(org_id)
    
    return {
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "status": org.status.value,
            "plan": org.plan.value,
            "billing_email": org.billing_email,
            "billing_name": org.billing_name,
            "billing_address": org.billing_address,
            "tax_id": org.tax_id,
            "settings": org.settings,
            "features": org.features,
            "sso_enabled": org.sso_enabled,
            "sso_provider": org.sso_provider,
            "max_members": org.max_members,
            "max_jobs_per_month": org.max_jobs_per_month,
            "max_research_per_month": org.max_research_per_month,
            "max_api_calls_per_month": org.max_api_calls_per_month,
            "current_members": org.current_members,
            "jobs_used_this_month": org.jobs_used_this_month,
            "research_used_this_month": org.research_used_this_month,
            "api_calls_used_this_month": org.api_calls_used_this_month,
            "usage_reset_at": org.usage_reset_at.isoformat(),
            "stripe_customer_id": org.stripe_customer_id,
            "stripe_subscription_id": org.stripe_subscription_id,
            "created_at": org.created_at.isoformat(),
            "updated_at": org.updated_at.isoformat(),
            "trial_ends_at": org.trial_ends_at.isoformat() if org.trial_ends_at else None,
        },
        "subscription": {
            "plan": subscription.plan.value if subscription else None,
            "billing_interval": subscription.billing_interval.value if subscription else None,
            "status": subscription.status.value if subscription else None,
            "quantity": subscription.quantity if subscription else None,
            "unit_amount": subscription.unit_amount if subscription else None,
            "current_period_end": subscription.stripe_current_period_end.isoformat() if subscription and subscription.stripe_current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end if subscription else None,
        } if subscription else None,
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status.value,
                "total": inv.total,
                "currency": inv.currency,
                "issue_date": inv.issue_date.isoformat(),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "hosted_invoice_url": inv.hosted_invoice_url,
            }
            for inv in invoices[:10]
        ],
        "usage": {
            "current_period_start": usage.current_period_start.isoformat(),
            "current_period_end": usage.current_period_end.isoformat(),
            "metrics": usage.metrics,
            "limits": usage.limits,
            "utilization": usage.utilization,
        },
        "members": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role,
                "title": m.title,
                "department": m.department,
                "joined_at": m.joined_at.isoformat(),
                "is_active": m.is_active,
            }
            for m in members
        ],
    }


@router.post("/organizations/{org_id}/impersonate")
async def admin_impersonate_organization(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Allow admin to impersonate organization (for support)."""
    org = billing.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # In production, would create an impersonation token
    return {
        "message": f"Impersonation token for organization {org.name}",
        "org_id": org.id,
        "org_name": org.name,
        "note": "Impersonation token would be generated here",
    }


@router.post("/organizations/{org_id}/plan", response_model=dict)
async def admin_change_organization_plan(
    org_id: int,
    plan: str = Query(...),
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Force change organization plan (admin override)."""
    org = billing.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    try:
        new_plan = OrganizationPlan(plan)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    org.plan = new_plan
    billing._apply_plan_limits(org, new_plan)
    billing.db.commit()
    
    return {
        "message": f"Organization plan changed to {plan}",
        "organization_id": org.id,
        "new_plan": org.plan.value,
        "new_limits": {
            "max_members": org.max_members,
            "max_jobs_per_month": org.max_jobs_per_month,
            "max_research_per_month": org.max_research_per_month,
            "max_api_calls_per_month": org.max_api_calls_per_month,
        },
    }


@router.post("/organizations/{org_id}/extend-trial", response_model=dict)
async def admin_extend_trial(
    org_id: int,
    days: int = Query(14, ge=1, le=365),
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Extend organization trial period."""
    org = billing.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    new_end = (org.trial_ends_at or datetime.utcnow()) + timedelta(days=days)
    org.trial_ends_at = new_end
    org.status = OrganizationStatus.TRIAL
    billing.db.commit()
    
    return {
        "message": f"Trial extended by {days} days",
        "organization_id": org.id,
        "new_trial_ends_at": org.trial_ends_at.isoformat(),
    }


@router.post("/organizations/{org_id}/reset-usage", response_model=dict)
async def admin_reset_usage(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Reset organization usage counters."""
    org = billing.reset_monthly_usage(org_id)
    
    return {
        "message": "Usage counters reset",
        "organization_id": org.id,
        "usage_reset_at": org.usage_reset_at.isoformat(),
    }


@router.delete("/organizations/{org_id}", status_code=204)
async def admin_delete_organization(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Force delete organization."""
    success = billing.delete_organization(org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Organization not found")


# ============= Revenue & Billing Reports =============

@router.get("/reports/revenue")
async def get_revenue_report(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Get revenue report."""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    invoices = billing.db.query(Invoice).filter(
        Invoice.issue_date >= start_date,
        Invoice.issue_date <= end_date,
        Invoice.status == "paid",
    ).all()
    
    total_revenue = sum(inv.total for inv in invoices)
    by_currency = {}
    for inv in invoices:
        if inv.currency not in by_currency:
            by_currency[inv.currency] = 0
        by_currency[inv.currency] += inv.total
    
    by_plan = {}
    for inv in invoices:
        if inv.subscription and inv.subscription.plan:
            plan = inv.subscription.plan.value
            if plan not in by_plan:
                by_plan[plan] = 0
            by_plan[plan] += inv.total
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "total_revenue_cents": total_revenue,
        "total_revenue_usd": total_revenue / 100,
        "invoice_count": len(invoices),
        "by_currency": by_currency,
        "by_plan": by_plan,
    }


@router.get("/reports/mrr")
async def get_mrr_report(
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Get Monthly Recurring Revenue report."""
    subscriptions = billing.db.query(Subscription).filter(
        Subscription.status.in_(["active", "trialing", "past_due"])
    ).all()
    
    mrr = 0
    arr = 0
    by_plan = {}
    
    for sub in subscriptions:
        monthly_amount = sub.unit_amount * sub.quantity
        if sub.billing_interval == BillingInterval.YEARLY:
            monthly_amount = monthly_amount / 12
        
        mrr += monthly_amount
        arr += monthly_amount * 12
        
        plan = sub.plan.value
        if plan not in by_plan:
            by_plan[plan] = {"mrr": 0, "count": 0}
        by_plan[plan]["mrr"] += monthly_amount
        by_plan[plan]["count"] += 1
    
    return {
        "mrr_cents": mrr,
        "mrr_usd": mrr / 100,
        "arr_cents": arr,
        "arr_usd": arr / 100,
        "active_subscriptions": len(subscriptions),
        "by_plan": by_plan,
    }


@router.get("/reports/churn")
async def get_churn_report(
    months: int = Query(6, ge=1, le=24),
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Get churn report."""
    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    
    cancelled = billing.db.query(Subscription).filter(
        Subscription.status == "cancelled",
        Subscription.canceled_at >= cutoff,
    ).all()
    
    by_month = {}
    for sub in cancelled:
        if sub.canceled_at:
            month_key = sub.canceled_at.strftime("%Y-%m")
            if month_key not in by_month:
                by_month[month_key] = 0
            by_month[month_key] += 1
    
    # Calculate churn rate
    active_start = billing.db.query(Subscription).filter(
        Subscription.status.in_(["active", "trialing"]),
        Subscription.created_at < cutoff,
    ).count()
    
    churn_rate = len(cancelled) / active_start if active_start > 0 else 0
    
    return {
        "period_months": months,
        "cancelled_subscriptions": len(cancelled),
        "active_at_start": active_start,
        "churn_rate": churn_rate,
        "by_month": by_month,
    }


# ============= System Health =============

@router.get("/system/health")
async def get_system_health(
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Get system health overview."""
    # Database health
    try:
        billing.db.execute("SELECT 1")
        db_healthy = True
    except:
        db_healthy = False
    
    # Queue health (Celery)
    try:
        from backend.workers.celery_app import celery_app
        inspector = celery_app.control.inspect()
        active_workers = inspector.active()
        queue_healthy = bool(active_workers)
    except:
        queue_healthy = False
    
    # Storage
    import shutil
    total, used, free = shutil.disk_usage("/")
    disk_usage_pct = (used / total) * 100
    
    return {
        "database": "healthy" if db_healthy else "unhealthy",
        "queue": "healthy" if queue_healthy else "unhealthy",
        "disk_usage_percent": round(disk_usage_pct, 1),
        "disk_free_gb": round(free / (1024**3), 2),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============= Feature Flag Management =============

@router.get("/feature-flags", response_model=List[dict])
async def admin_list_feature_flags(
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """List all feature flags across all organizations."""
    flags = billing.get_feature_flags()
    
    return [
        {
            "id": flag.id,
            "key": flag.key,
            "name": flag.name,
            "enabled": flag.enabled,
            "organization_id": flag.organization_id,
            "target_type": flag.target_type,
            "target_value": flag.target_value,
            "is_experiment": flag.is_experiment,
            "created_at": flag.created_at.isoformat(),
            "archived_at": flag.archived_at.isoformat() if flag.archived_at else None,
        }
        for flag in flags
    ]


@router.post("/feature-flags/{flag_key}/global-toggle")
async def admin_toggle_feature_flag(
    flag_key: str,
    enabled: bool = Query(...),
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Toggle global feature flag."""
    flag = billing.db.query(FeatureFlag).filter(
        FeatureFlag.key == flag_key,
        FeatureFlag.organization_id.is_(None)
    ).first()
    
    if not flag:
        raise HTTPException(status_code=404, detail="Global feature flag not found")
    
    flag.enabled = enabled
    flag.updated_at = datetime.utcnow()
    billing.db.commit()
    
    return {"message": f"Feature flag {flag_key} {'enabled' if enabled else 'disabled'}"}


# ============= Audit Logs =============

@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[int] = Query(None),
    organization_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing),
):
    """Get audit logs (placeholder - would integrate with audit service)."""
    # In production, would query audit log table
    return {
        "message": "Audit logs would be retrieved from audit service",
        "filters": {
            "user_id": user_id,
            "organization_id": organization_id,
            "action": action,
        },
    }