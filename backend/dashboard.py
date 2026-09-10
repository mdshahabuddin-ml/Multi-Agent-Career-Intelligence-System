"""
Dashboard module for backend.
Provides shared dashboard utilities, widgets, and data aggregation functions.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, desc


@dataclass
class MetricCard:
    """Dashboard metric card."""
    title: str
    value: Any
    change: Optional[float] = None
    trend: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


@dataclass
class ChartData:
    """Chart data for dashboard."""
    labels: List[str]
    datasets: List[Dict[str, Any]]


class DashboardAggregator:
    """Aggregates data for dashboard widgets."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_metric_cards(self) -> List[MetricCard]:
        """Get key metric cards for dashboard."""
        from backend.models import User, Organization, Job, Application, Research
        
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        prev_week_start = week_ago - timedelta(days=7)
        
        # Users
        total_users = self.db.query(User).count()
        new_users_week = self.db.query(User).filter(User.created_at >= week_ago).count()
        new_users_prev_week = self.db.query(User).filter(
            User.created_at >= prev_week_start,
            User.created_at < week_ago
        ).count()
        
        # Organizations
        total_orgs = self.db.query(Organization).count()
        
        # Jobs
        active_jobs = self.db.query(Job).filter(Job.is_active == True).count()
        
        # Applications
        pending_apps = self.db.query(Application).filter(Application.status == "pending").count()
        
        # Research
        active_research = self.db.query(Research).filter(Research.status == "in_progress").count()
        
        return [
            MetricCard(
                title="Total Users",
                value=total_users,
                change=self._calc_change(new_users_week, new_users_prev_week),
                trend="up" if new_users_week >= new_users_prev_week else "down",
                icon="users",
                color="blue",
            ),
            MetricCard(
                title="Active Jobs",
                value=active_jobs,
                icon="briefcase",
                color="green",
            ),
            MetricCard(
                title="Pending Applications",
                value=pending_apps,
                icon="file-text",
                color="yellow",
            ),
            MetricCard(
                title="Active Research",
                value=active_research,
                icon="search",
                color="purple",
            ),
            MetricCard(
                title="Organizations",
                value=total_orgs,
                icon="building",
                color="indigo",
            ),
        ]
    
    def get_user_growth_chart(self, days: int = 30) -> ChartData:
        """Get user growth chart data."""
        from backend.models import User
        
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        results = self.db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= start_date
        ).group_by(
            func.date(User.created_at)
        ).order_by(
            func.date(User.created_at)
        ).all()
        
        labels = []
        data = []
        for r in results:
            labels.append(r.date.isoformat() if r.date else "")
            data.append(r.count)
        
        return ChartData(
            labels=labels,
            datasets=[{
                "label": "New Users",
                "data": data,
                "borderColor": "rgb(59, 130, 246)",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
            }]
        )
    
    def get_job_type_distribution(self) -> ChartData:
        """Get job type distribution."""
        from backend.models import Job
        
        results = self.db.query(
            Job.job_type,
            func.count(Job.id)
        ).filter(
            Job.is_active == True
        ).group_by(Job.job_type).all()
        
        labels = []
        data = []
        for job_type, count in results:
            labels.append(job_type or "Unknown")
            data.append(count)
        
        colors = [
            "rgba(59, 130, 246, 0.8)",
            "rgba(16, 185, 129, 0.8)",
            "rgba(245, 158, 11, 0.8)",
            "rgba(239, 68, 68, 0.8)",
            "rgba(139, 92, 246, 0.8)",
        ]
        
        return ChartData(
            labels=labels,
            datasets=[{
                "label": "Jobs by Type",
                "data": data,
                "backgroundColor": colors[:len(data)],
            }]
        )
    
    def get_application_funnel(self) -> ChartData:
        """Get application funnel chart."""
        from backend.models import Application
        
        stages = ["pending", "reviewed", "interview", "accepted", "rejected"]
        labels = []
        data = []
        
        for stage in stages:
            count = self.db.query(Application).filter(Application.status == stage).count()
            labels.append(stage.title())
            data.append(count)
        
        return ChartData(
            labels=labels,
            datasets=[{
                "label": "Applications",
                "data": data,
                "backgroundColor": "rgba(59, 130, 246, 0.8)",
            }]
        )
    
    def get_revenue_chart(self, months: int = 12) -> ChartData:
        """Get revenue chart by month."""
        from backend.models import Subscription, SubscriptionStatus, BillingInterval
        
        now = datetime.utcnow()
        start_date = now - timedelta(days=months * 30)
        
        subs = self.db.query(Subscription).filter(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            Subscription.created_at >= start_date
        ).all()
        
        monthly_revenue = {}
        for sub in subs:
            monthly = (sub.unit_amount * sub.quantity) / (12 if sub.billing_interval == BillingInterval.YEARLY else 1)
            if sub.created_at:
                month_key = sub.created_at.strftime("%Y-%m")
                monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + monthly
        
        labels = []
        data = []
        for i in range(months):
            month = (now - timedelta(days=i * 30)).strftime("%Y-%m")
            labels.insert(0, month)
            data.insert(0, monthly_revenue.get(month, 0))
        
        return ChartData(
            labels=labels,
            datasets=[{
                "label": "Monthly Revenue (USD)",
                "data": [round(d / 100, 2) for d in data],
                "borderColor": "rgb(16, 185, 129)",
                "backgroundColor": "rgba(16, 185, 129, 0.1)",
            }]
        )
    
    def get_top_companies(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top companies by job postings."""
        from backend.models import Job, Company
        
        results = self.db.query(
            Company.name,
            func.count(Job.id).label('job_count')
        ).join(Job, Company.id == Job.company_id).filter(
            Job.is_active == True
        ).group_by(Company.id, Company.name).order_by(
            desc('job_count')
        ).limit(limit).all()
        
        return [
            {"name": name, "job_count": count}
            for name, count in results
        ]
    
    def get_top_skills(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top skills from job postings."""
        from backend.models import Job
        
        jobs = self.db.query(Job.skills_required).filter(
            Job.is_active == True,
            Job.skills_required.isnot(None)
        ).all()
        
        skill_count = {}
        for (skills,) in jobs:
            if skills:
                for skill in skills:
                    skill_count[skill] = skill_count.get(skill, 0) + 1
        
        sorted_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)
        return [
            {"skill": skill, "count": count}
            for skill, count in sorted_skills[:limit]
        ]
    
    def _calc_change(self, current: int, previous: int) -> Optional[float]:
        """Calculate percentage change."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)


def get_dashboard_data(db: Session) -> Dict[str, Any]:
    """Get all dashboard data in one call."""
    aggregator = DashboardAggregator(db)
    
    return {
        "metric_cards": aggregator.get_metric_cards(),
        "charts": {
            "user_growth": aggregator.get_user_growth_chart(),
            "job_types": aggregator.get_job_type_distribution(),
            "application_funnel": aggregator.get_application_funnel(),
            "revenue": aggregator.get_revenue_chart(),
        },
        "tables": {
            "top_companies": aggregator.get_top_companies(),
            "top_skills": aggregator.get_top_skills(),
        },
    }