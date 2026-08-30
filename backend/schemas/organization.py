from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from enum import Enum


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    CANCELLED = "cancelled"


class OrganizationPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"
    UNPAID = "unpaid"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class TeamRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    website: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    billing_name: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None
    tax_id: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    billing_name: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None
    tax_id: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    features: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    sso_enabled: Optional[bool] = None
    sso_provider: Optional[str] = None
    sso_config: Optional[Dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    logo_url: Optional[str]
    website: Optional[str]
    status: OrganizationStatus
    plan: OrganizationPlan
    billing_email: Optional[str]
    billing_name: Optional[str]
    billing_address: Optional[Dict[str, Any]]
    tax_id: Optional[str]
    settings: Optional[Dict[str, Any]]
    features: Optional[List[str]]
    allowed_domains: Optional[List[str]]
    sso_enabled: bool
    sso_provider: Optional[str]
    max_members: int
    max_jobs_per_month: int
    max_research_per_month: int
    max_api_calls_per_month: int
    current_members: int
    jobs_used_this_month: int
    research_used_this_month: int
    api_calls_used_this_month: int
    usage_reset_at: datetime
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    trial_ends_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrganizationMemberCreate(BaseModel):
    user_id: int
    role: str = "member"
    title: Optional[str] = None
    department: Optional[str] = None


class OrganizationMemberUpdate(BaseModel):
    role: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationMemberResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int
    role: str
    title: Optional[str]
    department: Optional[str]
    joined_at: datetime
    invited_by: Optional[int]
    invitation_id: Optional[int]
    is_active: bool
    last_active_at: Optional[datetime]
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    is_private: bool = False


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_private: Optional[bool] = None


class TeamResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    description: Optional[str]
    slug: str
    is_default: bool
    is_private: bool
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


class TeamMemberCreate(BaseModel):
    user_id: int
    role: TeamRole = TeamRole.MEMBER


class TeamMemberUpdate(BaseModel):
    role: Optional[TeamRole] = None


class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    role: TeamRole
    joined_at: datetime
    added_by: Optional[int]
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "member"
    team_id: Optional[int] = None
    team_role: Optional[TeamRole] = None
    expires_in_days: int = 7


class InvitationResponse(BaseModel):
    id: int
    organization_id: int
    team_id: Optional[int]
    email: str
    role: str
    team_role: Optional[TeamRole]
    invited_by: int
    status: InvitationStatus
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
    inviter_name: Optional[str] = None
    inviter_email: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    plan: OrganizationPlan
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    quantity: int = 1


class SubscriptionUpdate(BaseModel):
    quantity: Optional[int] = None
    cancel_at_period_end: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    id: int
    organization_id: int
    plan: OrganizationPlan
    billing_interval: BillingInterval
    quantity: int
    unit_amount: int
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str]
    stripe_price_id: Optional[str]
    stripe_current_period_start: Optional[datetime]
    stripe_current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    canceled_at: Optional[datetime]
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    organization_id: int
    subscription_id: Optional[int]
    invoice_number: str
    status: InvoiceStatus
    subtotal: int
    tax: int
    total: int
    amount_paid: int
    amount_due: int
    currency: str
    issue_date: datetime
    due_date: Optional[datetime]
    paid_at: Optional[datetime]
    voided_at: Optional[datetime]
    stripe_invoice_id: Optional[str]
    hosted_invoice_url: Optional[str]
    invoice_pdf_url: Optional[str]
    line_items: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageRecordCreate(BaseModel):
    metric_name: str
    quantity: int
    unit_price: int = 0
    period_start: datetime
    period_end: datetime


class UsageRecordResponse(BaseModel):
    id: int
    organization_id: int
    subscription_id: Optional[int]
    metric_name: str
    quantity: int
    unit_price: int
    period_start: datetime
    period_end: datetime
    stripe_usage_record_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FeatureFlagCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9_.-]+$")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: bool = False
    value: Optional[Dict[str, Any]] = None
    target_type: str = "all"
    target_value: Optional[float] = None
    target_organizations: Optional[List[int]] = None
    target_users: Optional[List[int]] = None
    custom_rules: Optional[Dict[str, Any]] = None
    is_experiment: bool = False
    experiment_id: Optional[str] = None
    variant: Optional[str] = None
    tags: Optional[List[str]] = None


class FeatureFlagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    value: Optional[Dict[str, Any]] = None
    target_type: Optional[str] = None
    target_value: Optional[float] = None
    target_organizations: Optional[List[int]] = None
    target_users: Optional[List[int]] = None
    custom_rules: Optional[Dict[str, Any]] = None
    archived: Optional[bool] = None


class FeatureFlagResponse(BaseModel):
    id: int
    organization_id: Optional[int]
    key: str
    name: str
    description: Optional[str]
    enabled: bool
    value: Optional[Dict[str, Any]]
    target_type: str
    target_value: Optional[float]
    target_organizations: Optional[List[int]]
    target_users: Optional[List[int]]
    custom_rules: Optional[Dict[str, Any]]
    is_experiment: bool
    experiment_id: Optional[str]
    variant: Optional[str]
    tags: Optional[List[str]]
    created_by: int
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class FeatureFlagEvaluation(BaseModel):
    key: str
    enabled: bool
    value: Optional[Dict[str, Any]]
    variant: Optional[str]


class OrganizationUsageResponse(BaseModel):
    organization_id: int
    current_period_start: datetime
    current_period_end: datetime
    metrics: Dict[str, Dict[str, Any]]
    limits: Dict[str, int]
    utilization: Dict[str, float]


class BillingPortalSession(BaseModel):
    url: str


class CheckoutSession(BaseModel):
    url: str
    session_id: str