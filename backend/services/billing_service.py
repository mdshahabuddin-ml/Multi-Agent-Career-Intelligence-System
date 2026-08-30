import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from backend.models.organization import (
    Organization, OrganizationMember, Team, TeamMember,
    Invitation, Subscription, Invoice, UsageRecord, FeatureFlag,
    OrganizationStatus, OrganizationPlan, SubscriptionStatus,
    InvoiceStatus, TeamRole, InvitationStatus, BillingInterval
)
from backend.models.user import User
from backend.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationMemberCreate, OrganizationMemberUpdate, OrganizationMemberResponse,
    TeamCreate, TeamUpdate, TeamResponse, TeamMemberCreate, TeamMemberResponse,
    InvitationCreate, InvitationResponse,
    SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse,
    InvoiceResponse, UsageRecordCreate, UsageRecordResponse,
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    FeatureFlagEvaluation, OrganizationUsageResponse,
    BillingPortalSession, CheckoutSession
)

logger = logging.getLogger(__name__)

# Plan pricing (in cents)
PLAN_PRICING = {
    OrganizationPlan.FREE: {"monthly": 0, "yearly": 0},
    OrganizationPlan.STARTER: {"monthly": 2900, "yearly": 29000},  # $29/mo, $290/yr
    OrganizationPlan.PROFESSIONAL: {"monthly": 9900, "yearly": 99000},  # $99/mo, $990/yr
    OrganizationPlan.ENTERPRISE: {"monthly": 49900, "yearly": 499000},  # $499/mo, $4990/yr
    OrganizationPlan.CUSTOM: {"monthly": 0, "yearly": 0},  # Custom pricing
}

# Plan limits
PLAN_LIMITS = {
    OrganizationPlan.FREE: {
        "max_members": 5,
        "max_jobs_per_month": 10,
        "max_research_per_month": 5,
        "max_api_calls_per_month": 1000,
    },
    OrganizationPlan.STARTER: {
        "max_members": 10,
        "max_jobs_per_month": 100,
        "max_research_per_month": 50,
        "max_api_calls_per_month": 10000,
    },
    OrganizationPlan.PROFESSIONAL: {
        "max_members": 50,
        "max_jobs_per_month": 1000,
        "max_research_per_month": 500,
        "max_api_calls_per_month": 100000,
    },
    OrganizationPlan.ENTERPRISE: {
        "max_members": 500,
        "max_jobs_per_month": 10000,
        "max_research_per_month": 5000,
        "max_api_calls_per_month": 1000000,
    },
    OrganizationPlan.CUSTOM: {
        "max_members": 10000,
        "max_jobs_per_month": 100000,
        "max_research_per_month": 50000,
        "max_api_calls_per_month": 10000000,
    },
}


class BillingService:
    """Service for handling billing, subscriptions, and invoices."""

    def __init__(self, db: Session):
        self.db = db
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    # ============= Organization Management =============

    def create_organization(self, creator_id: int, org_data: OrganizationCreate) -> Organization:
        """Create a new organization with the creator as owner."""
        # Check if slug is available
        existing = self.db.query(Organization).filter(Organization.slug == org_data.slug).first()
        if existing:
            raise ValueError("Organization slug already taken")

        # Create organization
        org = Organization(
            name=org_data.name,
            slug=org_data.slug,
            description=org_data.description,
            website=org_data.website,
            billing_email=org_data.billing_email,
            billing_name=org_data.billing_name,
            billing_address=org_data.billing_address,
            tax_id=org_data.tax_id,
            status=OrganizationStatus.TRIAL,
            plan=OrganizationPlan.FREE,
            trial_ends_at=datetime.utcnow() + timedelta(days=14),
        )

        # Apply free plan limits
        self._apply_plan_limits(org, OrganizationPlan.FREE)

        self.db.add(org)
        self.db.flush()

        # Add creator as owner
        member = OrganizationMember(
            organization_id=org.id,
            user_id=creator_id,
            role="owner",
            joined_at=datetime.utcnow(),
        )
        self.db.add(member)

        # Create default team
        default_team = Team(
            organization_id=org.id,
            name="General",
            slug="general",
            description="Default team for all members",
            is_default=True,
        )
        self.db.add(default_team)
        self.db.flush()

        # Add creator to default team
        team_member = TeamMember(
            team_id=default_team.id,
            user_id=creator_id,
            role=TeamRole.OWNER,
            added_by=creator_id,
        )
        self.db.add(team_member)

        self.db.commit()
        self.db.refresh(org)
        return org

    def _apply_plan_limits(self, org: Organization, plan: OrganizationPlan) -> None:
        """Apply plan limits to organization."""
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[OrganizationPlan.FREE])
        org.max_members = limits["max_members"]
        org.max_jobs_per_month = limits["max_jobs_per_month"]
        org.max_research_per_month = limits["max_research_per_month"]
        org.max_api_calls_per_month = limits["max_api_calls_per_month"]
        org.plan = plan

    def get_organization(self, org_id: int) -> Optional[Organization]:
        """Get organization by ID."""
        return self.db.query(Organization).filter(Organization.id == org_id).first()

    def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        return self.db.query(Organization).filter(Organization.slug == slug).first()

    def update_organization(self, org_id: int, updates: OrganizationUpdate) -> Optional[Organization]:
        """Update organization settings."""
        org = self.get_organization(org_id)
        if not org:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            if hasattr(org, field):
                setattr(org, field, value)

        org.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(org)
        return org

    def delete_organization(self, org_id: int) -> bool:
        """Delete organization (soft delete - mark as cancelled)."""
        org = self.get_organization(org_id)
        if not org:
            return False
        org.status = OrganizationStatus.CANCELLED
        org.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    # ============= Member Management =============

    def add_member(self, org_id: int, member_data: OrganizationMemberCreate, invited_by: int) -> OrganizationMember:
        """Add a member to organization."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        # Check if user already a member
        existing = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == member_data.user_id
        ).first()
        if existing:
            if existing.is_active:
                raise ValueError("User is already a member")
            # Reactivate
            existing.is_active = True
            existing.role = member_data.role
            existing.title = member_data.title
            existing.department = member_data.department
            self.db.commit()
            return existing

        # Check member limit
        active_count = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True
        ).count()
        if active_count >= org.max_members:
            raise ValueError("Organization member limit reached")

        member = OrganizationMember(
            organization_id=org_id,
            user_id=member_data.user_id,
            role=member_data.role,
            title=member_data.title,
            department=member_data.department,
            invited_by=invited_by,
        )
        self.db.add(member)
        org.current_members = active_count + 1
        self.db.commit()
        self.db.refresh(member)
        return member

    def update_member(self, org_id: int, user_id: int, updates: OrganizationMemberUpdate) -> Optional[OrganizationMember]:
        """Update member details."""
        member = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id
        ).first()
        if not member:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            setattr(member, field, value)

        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, org_id: int, user_id: int) -> bool:
        """Remove a member from organization."""
        member = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id
        ).first()
        if not member:
            return False

        # Prevent removing owner
        if member.role == "owner":
            raise ValueError("Cannot remove organization owner")

        member.is_active = False
        org = self.get_organization(org_id)
        if org:
            org.current_members = max(0, org.current_members - 1)
        self.db.commit()
        return True

    def get_members(self, org_id: int) -> List[OrganizationMember]:
        """Get all members of an organization."""
        return self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True
        ).all()

    # ============= Team Management =============

    def create_team(self, org_id: int, team_data: TeamCreate, creator_id: int) -> Team:
        """Create a new team."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        team = Team(
            organization_id=org_id,
            name=team_data.name,
            description=team_data.description,
            slug=team_data.slug,
            is_private=team_data.is_private,
        )
        self.db.add(team)
        self.db.flush()

        # Add creator as team owner
        member = TeamMember(
            team_id=team.id,
            user_id=creator_id,
            role=TeamRole.OWNER,
            added_by=creator_id,
        )
        self.db.add(member)

        self.db.commit()
        self.db.refresh(team)
        return team

    def update_team(self, org_id: int, team_id: int, updates: TeamUpdate) -> Optional[Team]:
        """Update team settings."""
        team = self.db.query(Team).filter(
            Team.id == team_id,
            Team.organization_id == org_id
        ).first()
        if not team:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            setattr(team, field, value)

        team.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(team)
        return team

    def add_team_member(self, team_id: int, user_id: int, role: TeamRole, added_by: int) -> TeamMember:
        """Add member to team."""
        team = self.db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise ValueError("Team not found")

        existing = self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        if existing:
            existing.role = role
            self.db.commit()
            return existing

        member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role=role,
            added_by=added_by,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_team_member(self, team_id: int, user_id: int) -> bool:
        """Remove member from team."""
        member = self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        ).first()
        if not member:
            return False

        if member.role == TeamRole.OWNER:
            raise ValueError("Cannot remove team owner")

        self.db.delete(member)
        self.db.commit()
        return True

    def get_teams(self, org_id: int) -> List[Team]:
        """Get all teams in organization."""
        return self.db.query(Team).filter(Team.organization_id == org_id).all()

    # ============= Invitations =============

    def create_invitation(self, org_id: int, invitation_data: InvitationCreate, invited_by: int) -> Invitation:
        """Create an invitation."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        # Check if already invited
        existing = self.db.query(Invitation).filter(
            Invitation.organization_id == org_id,
            Invitation.email == invitation_data.email,
            Invitation.status == InvitationStatus.PENDING
        ).first()
        if existing:
            raise ValueError("Invitation already pending for this email")

        # Check if already a member
        user = self.db.query(User).filter(User.email == invitation_data.email).first()
        if user:
            existing_member = self.db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user.id
            ).first()
            if existing_member and existing_member.is_active:
                raise ValueError("User is already a member")

        import secrets
        token = secrets.token_urlsafe(32)

        invitation = Invitation(
            organization_id=org_id,
            team_id=invitation_data.team_id,
            email=invitation_data.email,
            role=invitation_data.role,
            team_role=invitation_data.team_role,
            invited_by=invited_by,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=invitation_data.expires_in_days),
        )
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        return invitation

    def accept_invitation(self, token: str, user_id: int) -> Optional[Invitation]:
        """Accept an invitation."""
        invitation = self.db.query(Invitation).filter(
            Invitation.token == token,
            Invitation.status == InvitationStatus.PENDING
        ).first()
        if not invitation:
            return None

        if invitation.expires_at < datetime.utcnow():
            invitation.status = InvitationStatus.EXPIRED
            self.db.commit()
            return None

        # Add as member
        member = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=user_id,
            role=invitation.role,
            invitation_id=invitation.id,
            invited_by=invitation.invited_by,
        )
        self.db.add(member)

        # Add to team if specified
        if invitation.team_id:
            team_member = TeamMember(
                team_id=invitation.team_id,
                user_id=user_id,
                role=invitation.team_role or TeamRole.MEMBER,
                added_by=invitation.invited_by,
            )
            self.db.add(team_member)

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()
        invitation.accepted_by = user_id

        org = self.get_organization(invitation.organization_id)
        if org:
            org.current_members += 1

        self.db.commit()
        self.db.refresh(invitation)
        return invitation

    def revoke_invitation(self, invitation_id: int) -> bool:
        """Revoke an invitation."""
        invitation = self.db.query(Invitation).filter(Invitation.id == invitation_id).first()
        if not invitation:
            return False
        invitation.status = InvitationStatus.REVOKED
        self.db.commit()
        return True

    def get_invitations(self, org_id: int) -> List[Invitation]:
        """Get all invitations for organization."""
        return self.db.query(Invitation).filter(
            Invitation.organization_id == org_id
        ).order_by(Invitation.created_at.desc()).all()

    # ============= Subscription & Billing =============

    def create_subscription(self, org_id: int, sub_data: SubscriptionCreate) -> Subscription:
        """Create or update subscription."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        # Check for existing active subscription
        existing = self.db.query(Subscription).filter(
            Subscription.organization_id == org_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE])
        ).first()

        if existing:
            # Update existing
            existing.plan = sub_data.plan
            existing.billing_interval = sub_data.billing_interval
            existing.quantity = sub_data.quantity
            existing.unit_amount = PLAN_PRICING[sub_data.plan][sub_data.billing_interval.value]
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            self._apply_plan_limits(org, sub_data.plan)
            return existing

        # Create new subscription
        subscription = Subscription(
            organization_id=org_id,
            plan=sub_data.plan,
            billing_interval=sub_data.billing_interval,
            quantity=sub_data.quantity,
            unit_amount=PLAN_PRICING[sub_data.plan][sub_data.billing_interval.value],
            status=SubscriptionStatus.INCOMPLETE,
        )
        self.db.add(subscription)
        self.db.flush()

        self._apply_plan_limits(org, sub_data.plan)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def cancel_subscription(self, org_id: int, cancel_at_period_end: bool = True) -> Optional[Subscription]:
        """Cancel subscription."""
        subscription = self.db.query(Subscription).filter(
            Subscription.organization_id == org_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE])
        ).first()
        if not subscription:
            return None

        subscription.cancel_at_period_end = cancel_at_period_end
        if not cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.canceled_at = datetime.utcnow()
        subscription.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def get_subscription(self, org_id: int) -> Optional[Subscription]:
        """Get active subscription for organization."""
        return self.db.query(Subscription).filter(
            Subscription.organization_id == org_id,
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELLED])
        ).order_by(Subscription.created_at.desc()).first()

    # ============= Invoices =============

    def create_invoice(self, org_id: int, subscription_id: Optional[int], line_items: List[Dict], currency: str = "USD") -> Invoice:
        """Create an invoice."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        import uuid
        invoice_number = f"INV-{org.slug.upper()}-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        subtotal = sum(item.get("amount", 0) * item.get("quantity", 1) for item in line_items)
        tax = int(subtotal * 0.1)  # 10% tax
        total = subtotal + tax

        invoice = Invoice(
            organization_id=org_id,
            subscription_id=subscription_id,
            invoice_number=invoice_number,
            status=InvoiceStatus.OPEN,
            subtotal=subtotal,
            tax=tax,
            total=total,
            amount_due=total,
            currency=currency,
            line_items=line_items,
            issue_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=30),
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_invoices(self, org_id: int) -> List[Invoice]:
        """Get all invoices for organization."""
        return self.db.query(Invoice).filter(
            Invoice.organization_id == org_id
        ).order_by(Invoice.created_at.desc()).all()

    # ============= Usage Tracking =============

    def record_usage(self, org_id: int, usage_data: UsageRecordCreate) -> UsageRecord:
        """Record usage metric."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        # Update organization usage counters
        if usage_data.metric_name == "jobs":
            org.jobs_used_this_month += usage_data.quantity
        elif usage_data.metric_name == "research":
            org.research_used_this_month += usage_data.quantity
        elif usage_data.metric_name == "api_calls":
            org.api_calls_used_this_month += usage_data.quantity

        usage = UsageRecord(
            organization_id=org_id,
            **usage_data.dict()
        )
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        return usage

    def get_usage(self, org_id: int, metric_name: Optional[str] = None,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> List[UsageRecord]:
        """Get usage records."""
        query = self.db.query(UsageRecord).filter(UsageRecord.organization_id == org_id)

        if metric_name:
            query = query.filter(UsageRecord.metric_name == metric_name)
        if start_date:
            query = query.filter(UsageRecord.period_start >= start_date)
        if end_date:
            query = query.filter(UsageRecord.period_end <= end_date)

        return query.order_by(UsageRecord.period_start.desc()).all()

    def get_organization_usage(self, org_id: int) -> OrganizationUsageResponse:
        """Get comprehensive usage report for organization."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        now = datetime.utcnow()
        period_start = org.usage_reset_at
        period_end = now

        # Get usage for current period
        usage_records = self.get_usage(org_id, start_date=period_start, end_date=period_end)

        metrics = {}
        for record in usage_records:
            if record.metric_name not in metrics:
                metrics[record.metric_name] = {"used": 0, "records": []}
            metrics[record.metric_name]["used"] += record.quantity
            metrics[record.metric_name]["records"].append({
                "quantity": record.quantity,
                "period_start": record.period_start.isoformat(),
                "period_end": record.period_end.isoformat(),
            })

        limits = {
            "members": org.max_members,
            "jobs": org.max_jobs_per_month,
            "research": org.max_research_per_month,
            "api_calls": org.max_api_calls_per_month,
        }

        utilization = {}
        for metric, data in metrics.items():
            limit = limits.get(metric, 1)
            utilization[metric] = min(1.0, data["used"] / limit) if limit > 0 else 0.0

        utilization["members"] = org.current_members / org.max_members if org.max_members > 0 else 0.0

        return OrganizationUsageResponse(
            organization_id=org.id,
            current_period_start=period_start,
            current_period_end=period_end,
            metrics=metrics,
            limits=limits,
            utilization=utilization,
        )

    def reset_monthly_usage(self, org_id: int) -> Organization:
        """Reset monthly usage counters."""
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        org.jobs_used_this_month = 0
        org.research_used_this_month = 0
        org.api_calls_used_this_month = 0
        org.usage_reset_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(org)
        return org

    # ============= Feature Flags =============

    def create_feature_flag(self, flag_data: FeatureFlagCreate, creator_id: int) -> FeatureFlag:
        """Create a feature flag."""
        # Check key uniqueness
        existing = self.db.query(FeatureFlag).filter(
            FeatureFlag.key == flag_data.key,
            FeatureFlag.organization_id == flag_data.organization_id
        ).first()
        if existing:
            raise ValueError("Feature flag key already exists")

        flag = FeatureFlag(
            **flag_data.dict(),
            created_by=creator_id,
        )
        self.db.add(flag)
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def update_feature_flag(self, flag_id: int, updates: FeatureFlagUpdate) -> Optional[FeatureFlag]:
        """Update a feature flag."""
        flag = self.db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
        if not flag:
            return None

        for field, value in updates.dict(exclude_unset=True).items():
            if field == "archived" and value:
                flag.archived_at = datetime.utcnow()
            else:
                setattr(flag, field, value)

        flag.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def evaluate_feature_flag(self, key: str, context: Dict[str, Any] = None) -> FeatureFlagEvaluation:
        """Evaluate a feature flag for a given context."""
        flag = self.db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
        if not flag or flag.archived_at:
            return FeatureFlagEvaluation(key=key, enabled=False, value=None, variant=None)

        # Check targeting
        enabled = flag.enabled
        variant = flag.variant
        value = flag.value

        if flag.target_type == "percentage" and flag.target_value:
            # Consistent hashing based on user_id
            user_id = context.get("user_id") if context else None
            if user_id:
                hash_val = hash(f"{key}:{user_id}") % 100
                if hash_val >= flag.target_value:
                    enabled = False

        elif flag.target_type == "organizations" and flag.target_organizations:
            org_id = context.get("organization_id") if context else None
            if org_id not in flag.target_organizations:
                enabled = False

        elif flag.target_type == "users" and flag.target_users:
            user_id = context.get("user_id") if context else None
            if user_id not in flag.target_users:
                enabled = False

        elif flag.target_type == "custom" and flag.custom_rules:
            # Custom rule evaluation would go here
            pass

        return FeatureFlagEvaluation(
            key=flag.key,
            enabled=enabled,
            value=value,
            variant=variant,
        )

    def get_feature_flags(self, org_id: Optional[int] = None) -> List[FeatureFlag]:
        """Get feature flags."""
        query = self.db.query(FeatureFlag).filter(FeatureFlag.archived_at.is_(None))
        if org_id is not None:
            query = query.filter(FeatureFlag.organization_id == org_id)
        return query.all()

    def delete_feature_flag(self, flag_id: int) -> bool:
        """Archive a feature flag."""
        flag = self.db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
        if not flag:
            return False
        flag.archived_at = datetime.utcnow()
        flag.enabled = False
        self.db.commit()
        return True

    # ============= Stripe Integration (Placeholder) =============

    def create_stripe_customer(self, org_id: int) -> str:
        """Create Stripe customer for organization."""
        # Placeholder for Stripe integration
        # In production, integrate with stripe.Customer.create()
        org = self.get_organization(org_id)
        if not org:
            raise ValueError("Organization not found")

        # Simulated Stripe customer ID
        customer_id = f"cus_{org.slug}_{org.id}"
        org.stripe_customer_id = customer_id
        self.db.commit()
        return customer_id

    def create_checkout_session(self, org_id: int, plan: OrganizationPlan,
                                billing_interval: BillingInterval,
                                success_url: str, cancel_url: str) -> CheckoutSession:
        """Create Stripe checkout session."""
        # Placeholder for Stripe integration
        session_id = f"cs_{org_id}_{plan.value}_{billing_interval.value}"
        return CheckoutSession(
            url=f"https://checkout.stripe.com/pay/{session_id}",
            session_id=session_id
        )

    def create_billing_portal_session(self, org_id: int, return_url: str) -> BillingPortalSession:
        """Create Stripe billing portal session."""
        # Placeholder for Stripe integration
        org = self.get_organization(org_id)
        if not org or not org.stripe_customer_id:
            raise ValueError("No Stripe customer found")
        return BillingPortalSession(url=f"https://billing.stripe.com/session/{org.stripe_customer_id}")

    def handle_stripe_webhook(self, payload: bytes, signature: str) -> bool:
        """Handle Stripe webhook events."""
        # Placeholder for Stripe webhook handling
        # In production, verify signature and process events
        logger.info("Stripe webhook received")
        return True

    def sync_usage_to_stripe(self, org_id: int) -> bool:
        """Sync usage records to Stripe for metered billing."""
        # Placeholder for Stripe usage reporting
        return True


class OrganizationService:
    """High-level organization service combining billing and member management."""

    def __init__(self, db: Session):
        self.db = db
        self.billing = BillingService(db)

    def get_user_organizations(self, user_id: int) -> List[Organization]:
        """Get all organizations a user is a member of."""
        member_orgs = self.db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True
        ).all()
        org_ids = [m.organization_id for m in member_orgs]
        return self.db.query(Organization).filter(
            Organization.id.in_(org_ids),
            Organization.status != OrganizationStatus.CANCELLED
        ).all()

    def get_user_role(self, user_id: int, org_id: int) -> Optional[str]:
        """Get user's role in organization."""
        member = self.db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True
        ).first()
        return member.role if member else None

    def check_permission(self, user_id: int, org_id: int, required_roles: List[str]) -> bool:
        """Check if user has required role in organization."""
        role = self.get_user_role(user_id, org_id)
        return role in required_roles if role else False

    def can_access_organization(self, user_id: int, org_id: int) -> bool:
        """Check if user can access organization."""
        return self.get_user_role(user_id, org_id) is not None

    def can_manage_organization(self, user_id: int, org_id: int) -> bool:
        """Check if user can manage organization (owner/admin)."""
        return self.check_permission(user_id, org_id, ["owner", "admin"])

    def can_manage_billing(self, user_id: int, org_id: int) -> bool:
        """Check if user can manage billing."""
        return self.check_permission(user_id, org_id, ["owner"])

    def can_manage_members(self, user_id: int, org_id: int) -> bool:
        """Check if user can manage members."""
        return self.check_permission(user_id, org_id, ["owner", "admin"])

    def can_manage_teams(self, user_id: int, org_id: int) -> bool:
        """Check if user can manage teams."""
        return self.check_permission(user_id, org_id, ["owner", "admin"])

    def can_manage_feature_flags(self, user_id: int, org_id: int) -> bool:
        """Check if user can manage feature flags."""
        return self.check_permission(user_id, org_id, ["owner", "admin"])