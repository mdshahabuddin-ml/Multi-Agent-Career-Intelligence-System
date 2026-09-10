from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum

from backend.models.subscription import (
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    UserType,
    CompanyRole,
)


class SubscriptionTierEnum(str, Enum):
    FREE = "free"
    PRO = "pro"
    CREATOR = "creator"
    PROFESSIONAL = "professional"
    BUSINESS = "business"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"


class BillingIntervalEnum(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class UserTypeEnum(str, Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    CREATOR = "creator"
    AGENCY = "agency"


class CompanyRoleEnum(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    MEMBER = "member"


# ============= Subscription Limits =============

TIER_LIMITS = {
    SubscriptionTierEnum.FREE: {
        "research_monthly": 5,
        "content_monthly": 3,
        "api_calls_monthly": 0,
        "job_posts_monthly": 0,
        "candidate_searches_monthly": 0,
        "team_members": 1,
        "career_paths": 2,
        "content_scheduling": False,
        "brand_voice": False,
        "analytics": "basic",
        "priority_support": False,
    },
    SubscriptionTierEnum.PRO: {
        "research_monthly": -1,
        "content_monthly": 20,
        "api_calls_monthly": 1000,
        "job_posts_monthly": 0,
        "candidate_searches_monthly": 0,
        "team_members": 1,
        "career_paths": -1,
        "content_scheduling": True,
        "brand_voice": False,
        "analytics": "advanced",
        "priority_support": False,
    },
    SubscriptionTierEnum.CREATOR: {
        "research_monthly": -1,
        "content_monthly": -1,
        "api_calls_monthly": 10000,
        "job_posts_monthly": 0,
        "candidate_searches_monthly": 0,
        "team_members": 3,
        "career_paths": -1,
        "content_scheduling": True,
        "brand_voice": True,
        "analytics": "advanced",
        "priority_support": True,
    },
    SubscriptionTierEnum.PROFESSIONAL: {
        "research_monthly": -1,
        "content_monthly": -1,
        "api_calls_monthly": 50000,
        "job_posts_monthly": 5,
        "candidate_searches_monthly": 50,
        "team_members": 5,
        "career_paths": -1,
        "content_scheduling": True,
        "brand_voice": True,
        "analytics": "advanced",
        "priority_support": True,
    },
    SubscriptionTierEnum.BUSINESS: {
        "research_monthly": -1,
        "content_monthly": -1,
        "api_calls_monthly": -1,
        "job_posts_monthly": -1,
        "candidate_searches_monthly": -1,
        "team_members": -1,
        "career_paths": -1,
        "content_scheduling": True,
        "brand_voice": True,
        "analytics": "enterprise",
        "priority_support": True,
    },
}

TIER_PRICES = {
    SubscriptionTierEnum.PRO: {"monthly": 2900, "yearly": 29000},
    SubscriptionTierEnum.CREATOR: {"monthly": 4900, "yearly": 49000},
    SubscriptionTierEnum.PROFESSIONAL: {"monthly": 9900, "yearly": 99000},
    SubscriptionTierEnum.BUSINESS: {"monthly": 29900, "yearly": 299000},
}

TIER_STRIPE_PRICE_IDS = {
    SubscriptionTierEnum.PRO: {"monthly": "price_pro_monthly", "yearly": "price_pro_yearly"},
    SubscriptionTierEnum.CREATOR: {"monthly": "price_creator_monthly", "yearly": "price_creator_yearly"},
    SubscriptionTierEnum.PROFESSIONAL: {"monthly": "price_professional_monthly", "yearly": "price_professional_yearly"},
    SubscriptionTierEnum.BUSINESS: {"monthly": "price_business_monthly", "yearly": "price_business_yearly"},
}


def get_tier_limit(tier: SubscriptionTierEnum, feature: str) -> int:
    """Get limit for a feature at a given tier. -1 means unlimited."""
    return TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTierEnum.FREE]).get(feature, 0)


def get_tier_price(tier: SubscriptionTierEnum, interval: BillingIntervalEnum) -> int:
    """Get price in cents for a tier and interval."""
    return TIER_PRICES.get(tier, {}).get(interval.value, 0)


def get_stripe_price_id(tier: SubscriptionTierEnum, interval: BillingIntervalEnum) -> Optional[str]:
    """Get Stripe price ID for a tier and interval."""
    return TIER_STRIPE_PRICE_IDS.get(tier, {}).get(interval.value)


# ============= Schemas =============

class SubscriptionCreate(BaseModel):
    tier: SubscriptionTierEnum
    interval: BillingIntervalEnum = BillingIntervalEnum.MONTHLY
    payment_method_id: Optional[str] = None
    promotion_code: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    tier: Optional[SubscriptionTierEnum] = None
    interval: Optional[BillingIntervalEnum] = None
    cancel_at_period_end: Optional[bool] = None
    promotion_code: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: int
    tier: SubscriptionTierEnum
    status: SubscriptionStatusEnum
    interval: BillingIntervalEnum
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    canceled_at: Optional[datetime]
    trial_end: Optional[datetime]
    
    # Usage
    research_used: int
    content_used: int
    api_calls_used: int
    job_posts_used: int
    candidate_searches_used: int
    
    # Limits
    limits: Dict[str, int]
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionStatusResponse(BaseModel):
    subscription: Optional[SubscriptionResponse]
    tier: SubscriptionTierEnum
    is_active: bool
    is_trial: bool
    days_remaining: Optional[int]
    limits: Dict[str, int]
    usage: Dict[str, int]
    usage_percentage: Dict[str, float]


class CheckoutSessionCreate(BaseModel):
    tier: SubscriptionTierEnum
    interval: BillingIntervalEnum = BillingIntervalEnum.MONTHLY
    success_url: str
    cancel_url: str
    promotion_code: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class BillingPortalSessionResponse(BaseModel):
    portal_url: str


class UsageResponse(BaseModel):
    feature: str
    used: int
    limit: int
    percentage: float
    is_unlimited: bool


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    branding: Optional[Dict[str, Any]] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    slug: str
    domain: Optional[str]
    logo_url: Optional[str]
    description: Optional[str]
    size: Optional[str]
    industry: Optional[str]
    location: Optional[str]
    website: Optional[str]
    linkedin_url: Optional[str]
    subscription_tier: SubscriptionTierEnum
    is_active: bool
    is_verified: bool
    owner_id: int
    member_count: int
    job_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyMemberCreate(BaseModel):
    email: EmailStr
    role: CompanyRoleEnum = CompanyRoleEnum.MEMBER
    permissions: Optional[Dict[str, bool]] = None


class CompanyMemberUpdate(BaseModel):
    role: Optional[CompanyRoleEnum] = None
    permissions: Optional[Dict[str, bool]] = None
    status: Optional[str] = None


class CompanyMemberResponse(BaseModel):
    id: int
    company_id: int
    user_id: int
    user_email: str
    user_full_name: Optional[str]
    user_avatar_url: Optional[str]
    role: CompanyRoleEnum
    permissions: Dict[str, bool]
    status: str
    invited_at: datetime
    joined_at: Optional[datetime]

    class Config:
        from_attributes = True


class CompanyInviteResponse(BaseModel):
    invite_id: int
    email: str
    role: CompanyRoleEnum
    company_name: str
    invite_url: str


class UserProfileCreate(BaseModel):
    user_type: UserTypeEnum = UserTypeEnum.INDIVIDUAL
    headline: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    years_experience: Optional[int] = None
    skills: Optional[List[str]] = None
    target_role: Optional[str] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    industry: Optional[str] = None
    content_niches: Optional[List[str]] = None
    social_accounts: Optional[Dict[str, str]] = None


class UserProfileUpdate(BaseModel):
    user_type: Optional[UserTypeEnum] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    years_experience: Optional[int] = None
    skills: Optional[List[str]] = None
    target_role: Optional[str] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    industry: Optional[str] = None
    content_niches: Optional[List[str]] = None
    social_accounts: Optional[Dict[str, str]] = None
    brand_voice: Optional[Dict[str, Any]] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    weekly_digest: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    profile_visibility: Optional[str] = None
    show_salary: Optional[bool] = None
    open_to_work: Optional[bool] = None
    open_to_hire: Optional[bool] = None


class UserProfileResponse(BaseModel):
    user_id: int
    user_type: UserTypeEnum
    headline: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    location: Optional[str]
    timezone: str
    current_role: Optional[str]
    current_company: Optional[str]
    years_experience: Optional[int]
    skills: List[str]
    target_role: Optional[str]
    desired_salary_min: Optional[int]
    desired_salary_max: Optional[int]
    industry: Optional[str]
    brand_voice: Optional[Dict[str, Any]]
    content_niches: List[str]
    social_accounts: Optional[Dict[str, str]]
    email_notifications: bool
    push_notifications: bool
    weekly_digest: bool
    marketing_emails: bool
    profile_visibility: str
    show_salary: bool
    open_to_work: bool
    open_to_hire: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeatureLimitResponse(BaseModel):
    feature: str
    limit: int
    used: int
    remaining: int
    is_unlimited: bool
    percentage_used: float
    tier_required: Optional[SubscriptionTierEnum] = None


class TierComparisonResponse(BaseModel):
    tiers: Dict[SubscriptionTierEnum, Dict[str, Any]]
    current_tier: SubscriptionTierEnum
    recommended_tier: Optional[SubscriptionTierEnum] = None