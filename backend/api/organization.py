from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.api import auth
from backend.services.billing_service import BillingService, OrganizationService
from backend.models import (
    User, Team, TeamMember, FeatureFlag,
    OrganizationPlan, BillingInterval,
)
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

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def get_billing_service(db: Session = Depends(get_db)) -> BillingService:
    return BillingService(db)


def get_org_service(db: Session = Depends(get_db)) -> OrganizationService:
    return OrganizationService(db)


# ============= Organization CRUD =============

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user = Depends(auth.get_current_active_user),
    billing: BillingService = Depends(get_billing_service),
):
    """Create a new organization."""
    try:
        org = billing.create_organization(current_user.id, org_data)
        return org
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """List organizations for current user."""
    return org_service.get_user_organizations(current_user.id)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Get organization by ID."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    org = org_service.billing.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    updates: OrganizationUpdate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Update organization settings."""
    if not org_service.can_manage_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    org = org_service.billing.update_organization(org_id, updates)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Delete (cancel) organization."""
    if not org_service.can_manage_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    success = org_service.billing.delete_organization(org_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")


# ============= Member Management =============

@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
async def list_members(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """List organization members."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    members = org_service.billing.get_members(org_id)
    
    # Enrich with user info
    result = []
    for member in members:
        user = org_service.billing.db.query(User).filter(User.id == member.user_id).first()
        result.append(OrganizationMemberResponse(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role,
            title=member.title,
            department=member.department,
            joined_at=member.joined_at,
            invited_by=member.invited_by,
            invitation_id=member.invitation_id,
            is_active=member.is_active,
            last_active_at=member.last_active_at,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
        ))
    return result


@router.post("/{org_id}/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: int,
    member_data: OrganizationMemberCreate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Add a member to organization."""
    if not org_service.can_manage_members(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        member = org_service.billing.add_member(org_id, member_data, current_user.id)
        user = org_service.billing.db.query(User).filter(User.id == member.user_id).first()
        return OrganizationMemberResponse(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role,
            title=member.title,
            department=member.department,
            joined_at=member.joined_at,
            invited_by=member.invited_by,
            invitation_id=member.invitation_id,
            is_active=member.is_active,
            last_active_at=member.last_active_at,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{org_id}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_member(
    org_id: int,
    user_id: int,
    updates: OrganizationMemberUpdate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Update member details."""
    if not org_service.can_manage_members(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    member = org_service.billing.update_member(org_id, user_id, updates)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    user = org_service.billing.db.query(User).filter(User.id == member.user_id).first()
    return OrganizationMemberResponse(
        id=member.id,
        organization_id=member.organization_id,
        user_id=member.user_id,
        role=member.role,
        title=member.title,
        department=member.department,
        joined_at=member.joined_at,
        invited_by=member.invited_by,
        invitation_id=member.invitation_id,
        is_active=member.is_active,
        last_active_at=member.last_active_at,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
    )


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: int,
    user_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Remove a member from organization."""
    if not org_service.can_manage_members(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        success = org_service.billing.remove_member(org_id, user_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============= Team Management =============

@router.post("/{org_id}/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    org_id: int,
    team_data: TeamCreate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Create a new team."""
    if not org_service.can_manage_teams(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        team = org_service.billing.create_team(org_id, team_data, current_user.id)
        return TeamResponse(
            id=team.id,
            organization_id=team.organization_id,
            name=team.name,
            description=team.description,
            slug=team.slug,
            is_default=team.is_default,
            is_private=team.is_private,
            created_at=team.created_at,
            updated_at=team.updated_at,
            member_count=1,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{org_id}/teams", response_model=List[TeamResponse])
async def list_teams(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """List teams in organization."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    teams = org_service.billing.get_teams(org_id)
    result = []
    for team in teams:
        member_count = org_service.billing.db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
        result.append(TeamResponse(
            id=team.id,
            organization_id=team.organization_id,
            name=team.name,
            description=team.description,
            slug=team.slug,
            is_default=team.is_default,
            is_private=team.is_private,
            created_at=team.created_at,
            updated_at=team.updated_at,
            member_count=member_count,
        ))
    return result


@router.patch("/{org_id}/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    org_id: int,
    team_id: int,
    updates: TeamUpdate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Update team settings."""
    if not org_service.can_manage_teams(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    team = org_service.billing.update_team(org_id, team_id, updates)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    member_count = org_service.billing.db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        slug=team.slug,
        is_default=team.is_default,
        is_private=team.is_private,
        created_at=team.created_at,
        updated_at=team.updated_at,
        member_count=member_count,
    )


@router.delete("/{org_id}/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    org_id: int,
    team_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Delete a team."""
    if not org_service.can_manage_teams(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    team = org_service.billing.db.query(Team).filter(
        Team.id == team_id,
        Team.organization_id == org_id
    ).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if team.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default team")
    org_service.billing.db.delete(team)
    org_service.billing.db.commit()


@router.post("/{org_id}/teams/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    org_id: int,
    team_id: int,
    member_data: TeamMemberCreate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Add member to team."""
    if not org_service.can_manage_teams(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        member = org_service.billing.add_team_member(team_id, member_data.user_id, member_data.role, current_user.id)
        user = org_service.billing.db.query(User).filter(User.id == member.user_id).first()
        return TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            added_by=member.added_by,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{org_id}/teams/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    org_id: int,
    team_id: int,
    user_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Remove member from team."""
    if not org_service.can_manage_teams(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        success = org_service.billing.remove_team_member(team_id, user_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============= Invitations =============

@router.post("/{org_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    org_id: int,
    invitation_data: InvitationCreate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Create an invitation."""
    if not org_service.can_manage_members(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        invitation = org_service.billing.create_invitation(org_id, invitation_data, current_user.id)
        inviter = org_service.billing.db.query(User).filter(User.id == invitation.invited_by).first()
        return InvitationResponse(
            id=invitation.id,
            organization_id=invitation.organization_id,
            team_id=invitation.team_id,
            email=invitation.email,
            role=invitation.role,
            team_role=invitation.team_role,
            invited_by=invitation.invited_by,
            status=invitation.status,
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            created_at=invitation.created_at,
            inviter_name=inviter.full_name if inviter else None,
            inviter_email=inviter.email if inviter else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{org_id}/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """List all invitations for organization."""
    if not org_service.can_manage_members(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    invitations = org_service.billing.get_invitations(org_id)
    result = []
    for inv in invitations:
        inviter = org_service.billing.db.query(User).filter(User.id == inv.invited_by).first()
        result.append(InvitationResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            team_id=inv.team_id,
            email=inv.email,
            role=inv.role,
            team_role=inv.team_role,
            invited_by=inv.invited_by,
            status=inv.status,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            created_at=inv.created_at,
            inviter_name=inviter.full_name if inviter else None,
            inviter_email=inviter.email if inviter else None,
        ))
    return result


@router.delete("/{org_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    org_id: int,
    invitation_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Revoke an invitation."""
    if not org_service.can_manage_members(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    success = org_service.billing.revoke_invitation(invitation_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")


# ============= Subscriptions =============

@router.post("/{org_id}/subscription", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    org_id: int,
    sub_data: SubscriptionCreate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Create or update subscription."""
    if not org_service.can_manage_billing(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        subscription = org_service.billing.create_subscription(org_id, sub_data)
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{org_id}/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Get current subscription."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    subscription = org_service.billing.get_subscription(org_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found")
    return subscription


@router.patch("/{org_id}/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    org_id: int,
    updates: SubscriptionUpdate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Update subscription."""
    if not org_service.can_manage_billing(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    subscription = org_service.billing.get_subscription(org_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(subscription, field, value)
    subscription.updated_at = datetime.utcnow()
    org_service.billing.db.commit()
    org_service.billing.db.refresh(subscription)
    return subscription


@router.delete("/{org_id}/subscription", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_subscription(
    org_id: int,
    cancel_at_period_end: bool = Query(True),
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Cancel subscription."""
    if not org_service.can_manage_billing(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    subscription = org_service.billing.cancel_subscription(org_id, cancel_at_period_end)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found")


# ============= Invoices =============

@router.get("/{org_id}/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """List invoices for organization."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return org_service.billing.get_invoices(org_id)


@router.get("/{org_id}/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    org_id: int,
    invoice_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Get specific invoice."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    invoices = org_service.billing.get_invoices(org_id)
    invoice = next((inv for inv in invoices if inv.id == invoice_id), None)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


# ============= Usage =============

@router.get("/{org_id}/usage", response_model=OrganizationUsageResponse)
async def get_usage(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Get organization usage report."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return org_service.billing.get_organization_usage(org_id)


@router.post("/{org_id}/usage/reset", response_model=OrganizationResponse)
async def reset_monthly_usage(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Reset monthly usage counters (admin only)."""
    if not org_service.can_manage_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return org_service.billing.reset_monthly_usage(org_id)


# ============= Feature Flags =============

@router.post("/{org_id}/feature-flags", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    org_id: int,
    flag_data: FeatureFlagCreate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Create a feature flag."""
    if not org_service.can_manage_feature_flags(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        flag_data.organization_id = org_id
        flag = org_service.billing.create_feature_flag(flag_data, current_user.id)
        creator = org_service.billing.db.query(User).filter(User.id == flag.created_by).first()
        return FeatureFlagResponse(
            id=flag.id,
            organization_id=flag.organization_id,
            key=flag.key,
            name=flag.name,
            description=flag.description,
            enabled=flag.enabled,
            value=flag.value,
            target_type=flag.target_type,
            target_value=flag.target_value,
            target_organizations=flag.target_organizations,
            target_users=flag.target_users,
            custom_rules=flag.custom_rules,
            is_experiment=flag.is_experiment,
            experiment_id=flag.experiment_id,
            variant=flag.variant,
            tags=flag.tags,
            created_by=flag.created_by,
            created_at=flag.created_at,
            updated_at=flag.updated_at,
            archived_at=flag.archived_at,
            creator_name=creator.full_name if creator else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{org_id}/feature-flags", response_model=List[FeatureFlagResponse])
async def list_feature_flags(
    org_id: int,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """List feature flags for organization."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    flags = org_service.billing.get_feature_flags(org_id)
    result = []
    for flag in flags:
        creator = org_service.billing.db.query(User).filter(User.id == flag.created_by).first()
        result.append(FeatureFlagResponse(
            id=flag.id,
            organization_id=flag.organization_id,
            key=flag.key,
            name=flag.name,
            description=flag.description,
            enabled=flag.enabled,
            value=flag.value,
            target_type=flag.target_type,
            target_value=flag.target_value,
            target_organizations=flag.target_organizations,
            target_users=flag.target_users,
            custom_rules=flag.custom_rules,
            is_experiment=flag.is_experiment,
            experiment_id=flag.experiment_id,
            variant=flag.variant,
            tags=flag.tags,
            created_by=flag.created_by,
            created_at=flag.created_at,
            updated_at=flag.updated_at,
            archived_at=flag.archived_at,
            creator_name=creator.full_name if creator else None,
        ))
    return result


@router.get("/{org_id}/feature-flags/{flag_key}/evaluate", response_model=FeatureFlagEvaluation)
async def evaluate_feature_flag(
    org_id: int,
    flag_key: str,
    user_id: Optional[int] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Evaluate a feature flag for a context."""
    if not org_service.can_access_organization(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    context = {"user_id": user_id or current_user.id, "organization_id": org_id}
    return org_service.billing.evaluate_feature_flag(flag_key, context)


@router.patch("/{org_id}/feature-flags/{flag_key}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    org_id: int,
    flag_key: str,
    updates: FeatureFlagUpdate,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Update a feature flag."""
    if not org_service.can_manage_feature_flags(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    flag = org_service.billing.db.query(FeatureFlag).filter(
        FeatureFlag.key == flag_key,
        FeatureFlag.organization_id == org_id
    ).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    flag = org_service.billing.update_feature_flag(flag.id, updates)
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    creator = org_service.billing.db.query(User).filter(User.id == flag.created_by).first()
    return FeatureFlagResponse(
        id=flag.id,
        organization_id=flag.organization_id,
        key=flag.key,
        name=flag.name,
        description=flag.description,
        enabled=flag.enabled,
        value=flag.value,
        target_type=flag.target_type,
        target_value=flag.target_value,
        target_organizations=flag.target_organizations,
        target_users=flag.target_users,
        custom_rules=flag.custom_rules,
        is_experiment=flag.is_experiment,
        experiment_id=flag.experiment_id,
        variant=flag.variant,
        tags=flag.tags,
        created_by=flag.created_by,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
        archived_at=flag.archived_at,
        creator_name=creator.full_name if creator else None,
    )


@router.delete("/{org_id}/feature-flags/{flag_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(
    org_id: int,
    flag_key: str,
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Archive a feature flag."""
    if not org_service.can_manage_feature_flags(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    flag = org_service.billing.db.query(FeatureFlag).filter(
        FeatureFlag.key == flag_key,
        FeatureFlag.organization_id == org_id
    ).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    org_service.billing.delete_feature_flag(flag.id)


# ============= Stripe Integration =============

@router.post("/{org_id}/billing/checkout", response_model=CheckoutSession)
async def create_checkout_session(
    org_id: int,
    plan: str = Query(...),
    billing_interval: str = Query("monthly"),
    success_url: str = Query(...),
    cancel_url: str = Query(...),
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Create Stripe checkout session."""
    if not org_service.can_manage_billing(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        session = org_service.billing.create_checkout_session(
            org_id,
            OrganizationPlan(plan),
            BillingInterval(billing_interval),
            success_url,
            cancel_url,
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{org_id}/billing/portal", response_model=BillingPortalSession)
async def create_billing_portal_session(
    org_id: int,
    return_url: str = Query(...),
    current_user = Depends(auth.get_current_active_user),
    org_service: OrganizationService = Depends(get_org_service),
):
    """Create Stripe billing portal session."""
    if not org_service.can_manage_billing(current_user.id, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    try:
        session = org_service.billing.create_billing_portal_session(org_id, return_url)
        return session
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))