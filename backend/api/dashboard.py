from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel

from backend.database import get_db
from backend.api import auth
from backend.models import (
    User, Organization, Job, Application, Research, Profile,
    OrganizationStatus, OrganizationPlan, Subscription, SubscriptionStatus,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_organizations: int
    active_organizations: int
    total_jobs: int
    active_jobs: int
    total_applications: int
    pending_applications: int
    total_research: int
    completed_research: int
    total_revenue_cents: int
    mrr_cents: int


class UserStats(BaseModel):
    total: int
    active: int
    new_this_week: int
    new_this_month: int
    by_role: Dict[str, int]


class OrganizationStats(BaseModel):
    total: int
    active: int
    trial: int
    by_plan: Dict[str, int]
    by_status: Dict[str, int]


class JobStats(BaseModel):
    total: int
    active: int
    expired: int
    by_type: Dict[str, int]
    by_location: Dict[str, int]


class ApplicationStats(BaseModel):
    total: int
    pending: int
    reviewed: int
    accepted: int
    rejected: int
    by_status: Dict[str, int]


class ResearchStats(BaseModel):
    total: int
    in_progress: int
    completed: int
    failed: int
    by_type: Dict[str, int]


class RevenueStats(BaseModel):
    total_revenue_cents: int
    mrr_cents: int
    arr_cents: int
    active_subscriptions: int
    by_plan: Dict[str, int]
    by_month: Dict[str, int]


class ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str]
    user_id: Optional[int]
    organization_id: Optional[int]
    created_at: datetime


class DashboardResponse(BaseModel):
    stats: DashboardStats
    users: UserStats
    organizations: OrganizationStats
    jobs: JobStats
    applications: ApplicationStats
    research: ResearchStats
    revenue: RevenueStats
    recent_activity: List[ActivityItem]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get overview dashboard statistics."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    total_orgs = db.query(Organization).count()
    active_orgs = db.query(Organization).filter(Organization.status == OrganizationStatus.ACTIVE).count()
    
    total_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.is_active == True).count()
    
    total_apps = db.query(Application).count()
    pending_apps = db.query(Application).filter(Application.status == "pending").count()
    
    total_research = db.query(Research).count()
    completed_research = db.query(Research).filter(Research.status == "completed").count()
    
    subscriptions = db.query(Subscription).filter(
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
    ).all()
    total_revenue = sum(s.unit_amount * s.quantity for s in subscriptions)
    mrr = sum(
        (s.unit_amount * s.quantity) / (12 if s.billing_interval == "yearly" else 1)
        for s in subscriptions
    )
    
    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_organizations=total_orgs,
        active_organizations=active_orgs,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applications=total_apps,
        pending_applications=pending_apps,
        total_research=total_research,
        completed_research=completed_research,
        total_revenue_cents=total_revenue,
        mrr_cents=int(mrr),
    )


@router.get("/users", response_model=UserStats)
async def get_user_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get user statistics."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()
    new_week = db.query(User).filter(User.created_at >= week_ago).count()
    new_month = db.query(User).filter(User.created_at >= month_ago).count()
    
    # Role distribution (if role field exists)
    by_role = {"user": total}
    
    return UserStats(
        total=total,
        active=active,
        new_this_week=new_week,
        new_this_month=new_month,
        by_role=by_role,
    )


@router.get("/organizations", response_model=OrganizationStats)
async def get_organization_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get organization statistics."""
    total = db.query(Organization).count()
    active = db.query(Organization).filter(Organization.status == OrganizationStatus.ACTIVE).count()
    trial = db.query(Organization).filter(Organization.status == OrganizationStatus.TRIAL).count()
    
    by_plan = {}
    for plan in OrganizationPlan:
        count = db.query(Organization).filter(Organization.plan == plan).count()
        by_plan[plan.value] = count
    
    by_status = {}
    for status in OrganizationStatus:
        count = db.query(Organization).filter(Organization.status == status).count()
        by_status[status.value] = count
    
    return OrganizationStats(
        total=total,
        active=active,
        trial=trial,
        by_plan=by_plan,
        by_status=by_status,
    )


@router.get("/jobs", response_model=JobStats)
async def get_job_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get job statistics."""
    total = db.query(Job).count()
    active = db.query(Job).filter(Job.is_active == True).count()
    expired = db.query(Job).filter(Job.is_active == False).count()
    
    by_type = {}
    for jt in ["full-time", "part-time", "contract", "internship", "remote"]:
        count = db.query(Job).filter(Job.employment_type == jt).count()
        if count > 0:
            by_type[jt] = count
    
    by_location = {}
    locations = db.query(Job.location, func.count(Job.id)).group_by(Job.location).all()
    for loc, count in locations:
        if loc:
            by_location[loc] = count
    
    return JobStats(
        total=total,
        active=active,
        expired=expired,
        by_type=by_type,
        by_location=by_location,
    )


@router.get("/applications", response_model=ApplicationStats)
async def get_application_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get application statistics."""
    total = db.query(Application).count()
    pending = db.query(Application).filter(Application.status == "pending").count()
    reviewed = db.query(Application).filter(Application.status == "reviewed").count()
    accepted = db.query(Application).filter(Application.status == "accepted").count()
    rejected = db.query(Application).filter(Application.status == "rejected").count()
    
    by_status = {}
    for status in ["pending", "reviewed", "accepted", "rejected", "withdrawn"]:
        count = db.query(Application).filter(Application.status == status).count()
        if count > 0:
            by_status[status] = count
    
    return ApplicationStats(
        total=total,
        pending=pending,
        reviewed=reviewed,
        accepted=accepted,
        rejected=rejected,
        by_status=by_status,
    )


@router.get("/research", response_model=ResearchStats)
async def get_research_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get research statistics."""
    total = db.query(Research).count()
    in_progress = db.query(Research).filter(Research.status == "in_progress").count()
    completed = db.query(Research).filter(Research.status == "completed").count()
    failed = db.query(Research).filter(Research.status == "failed").count()
    
    by_type = {}
    for rt in ["market", "company", "role", "skill", "salary"]:
        count = db.query(Research).filter(Research.research_type == rt).count()
        if count > 0:
            by_type[rt] = count
    
    return ResearchStats(
        total=total,
        in_progress=in_progress,
        completed=completed,
        failed=failed,
        by_type=by_type,
    )


@router.get("/revenue", response_model=RevenueStats)
async def get_revenue_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get revenue statistics."""
    subscriptions = db.query(Subscription).filter(
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE])
    ).all()
    
    total_revenue = sum(s.unit_amount * s.quantity for s in subscriptions)
    mrr = sum(
        (s.unit_amount * s.quantity) / (12 if s.billing_interval == "yearly" else 1)
        for s in subscriptions
    )
    arr = mrr * 12
    
    by_plan = {}
    by_month = {}
    for sub in subscriptions:
        plan_key = sub.plan.value if sub.plan else "unknown"
        monthly = (sub.unit_amount * sub.quantity) / (12 if sub.billing_interval == "yearly" else 1)
        by_plan[plan_key] = by_plan.get(plan_key, 0) + monthly
        
        if sub.created_at:
            month_key = sub.created_at.strftime("%Y-%m")
            by_month[month_key] = by_month.get(month_key, 0) + monthly
    
    return RevenueStats(
        total_revenue_cents=total_revenue,
        mrr_cents=int(mrr),
        arr_cents=int(arr),
        active_subscriptions=len(subscriptions),
        by_plan=by_plan,
        by_month=by_month,
    )


@router.get("/activity", response_model=List[ActivityItem])
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get recent activity across the platform."""
    activities = []
    
    recent_users = db.query(User).order_by(desc(User.created_at)).limit(5).all()
    for u in recent_users:
        activities.append(ActivityItem(
            id=f"user_{u.id}",
            type="user_created",
            title=f"New user registered",
            description=f"{u.email} joined",
            user_id=u.id,
            organization_id=None,
            created_at=u.created_at,
        ))
    
    recent_orgs = db.query(Organization).order_by(desc(Organization.created_at)).limit(5).all()
    for o in recent_orgs:
        activities.append(ActivityItem(
            id=f"org_{o.id}",
            type="org_created",
            title=f"New organization created",
            description=f"{o.name} ({o.plan.value})",
            user_id=None,
            organization_id=o.id,
            created_at=o.created_at,
        ))
    
    recent_jobs = db.query(Job).order_by(desc(Job.created_at)).limit(5).all()
    for j in recent_jobs:
        activities.append(ActivityItem(
            id=f"job_{j.id}",
            type="job_created",
            title=f"New job posted",
            description=j.title,
            user_id=None,
            organization_id=None,
            created_at=j.created_at,
        ))
    
    recent_apps = db.query(Application).order_by(desc(Application.created_at)).limit(5).all()
    for a in recent_apps:
        activities.append(ActivityItem(
            id=f"app_{a.id}",
            type="application_submitted",
            title=f"New application",
            description=f"Applied to job {a.job_id}",
            user_id=a.user_id,
            organization_id=None,
            created_at=a.created_at,
        ))
    
    activities.sort(key=lambda x: x.created_at.replace(tzinfo=None) if x.created_at and x.created_at.tzinfo else x.created_at, reverse=True)
    return activities[:limit]


@router.get("/overview", response_model=DashboardResponse)
async def get_dashboard_overview(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get complete dashboard overview."""
    stats = await get_dashboard_stats(current_user, db)
    users = await get_user_stats(current_user, db)
    organizations = await get_organization_stats(current_user, db)
    jobs = await get_job_stats(current_user, db)
    applications = await get_application_stats(current_user, db)
    research = await get_research_stats(current_user, db)
    revenue = await get_revenue_stats(current_user, db)
    activity = await get_recent_activity(10, current_user, db)
    
    return DashboardResponse(
        stats=stats,
        users=users,
        organizations=organizations,
        jobs=jobs,
        applications=applications,
        research=research,
        revenue=revenue,
        recent_activity=activity,
    )


@router.get("/my-stats")
async def get_my_dashboard_stats(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get dashboard stats for current user's organization."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if not profile or not current_user.organization_id:
        return {"message": "User not part of an organization"}
    
    org_id = current_user.organization_id
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return {"message": "Organization not found"}
    
    my_jobs = db.query(Job).filter(Job.is_active == True).count()
    my_apps = db.query(Application).filter(Application.user_id == current_user.id).count()
    my_research = db.query(Research).count()
    
    members = db.query(User).filter(User.organization_id == org_id).count()
    
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == org_id,
        Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
    ).first()
    
    return {
        "organization": {
            "id": org.id,
            "name": org.name,
            "plan": org.plan.value,
            "status": org.status.value,
            "members": members,
        },
        "usage": {
            "active_jobs": my_jobs,
            "total_applications": my_apps,
            "research_projects": my_research,
        },
        "subscription": {
            "plan": subscription.plan.value if subscription else None,
            "status": subscription.status.value if subscription else None,
            "billing_interval": subscription.billing_interval.value if subscription else None,
        } if subscription else None,
    }