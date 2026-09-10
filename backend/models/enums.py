from enum import Enum as PyEnum


class SubscriptionTier(str, PyEnum):
    FREE = "free"
    PRO = "pro"
    CREATOR = "creator"
    PROFESSIONAL = "professional"
    BUSINESS = "business"


class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"


class BillingInterval(str, PyEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class UserType(str, PyEnum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    CREATOR = "creator"
    AGENCY = "agency"


class CompanyRole(str, PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    MEMBER = "member"