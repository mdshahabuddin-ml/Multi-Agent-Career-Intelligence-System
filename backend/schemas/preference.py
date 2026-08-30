from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class NotificationChannel(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationFrequency(str, Enum):
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


class JobAlertFrequency(str, Enum):
    REAL_TIME = "real_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


class ThemeMode(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ContentDensity(str, Enum):
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"


class JobPreferencesBase(BaseModel):
    preferred_job_types: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    preferred_remote_types: Optional[List[str]] = None
    min_salary: Optional[int] = None
    preferred_industries: Optional[List[str]] = None
    excluded_companies: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    salary_currency: str = "USD"
    job_alert_frequency: JobAlertFrequency = JobAlertFrequency.DAILY
    job_alert_enabled: bool = True


class NotificationPreferencesBase(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    in_app_notifications: bool = True
    notification_channels: Optional[List[str]] = None
    notification_frequency: NotificationFrequency = NotificationFrequency.DAILY
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: str = "UTC"


class ContentUIPreferencesBase(BaseModel):
    theme_mode: ThemeMode = ThemeMode.SYSTEM
    content_density: ContentDensity = ContentDensity.COMFORTABLE
    language: str = "en"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24h"
    show_salary_estimates: bool = True
    auto_save_drafts: bool = True
    compact_mode: bool = False


class PrivacyPreferencesBase(BaseModel):
    profile_visibility: str = "private"
    data_sharing_consent: bool = False
    analytics_opt_out: bool = False
    marketing_emails: bool = False
    third_party_integrations: bool = False


class LearningPreferencesBase(BaseModel):
    learning_style: str = "mixed"
    skill_gap_priority: str = "market_demand"
    preferred_learning_platforms: Optional[List[str]] = None
    weekly_learning_hours: Optional[int] = None


class RecommendationWeightsBase(BaseModel):
    rec_weight_skills_match: float = 0.35
    rec_weight_salary: float = 0.25
    rec_weight_location: float = 0.20
    rec_weight_company_culture: float = 0.10
    rec_weight_growth_potential: float = 0.10

    @field_validator('*', mode='before')
    @classmethod
    def validate_weights(cls, v, info):
        if info.field_name.startswith('rec_weight_') and (v < 0 or v > 1):
            raise ValueError(f'{info.field_name} must be between 0 and 1')
        return v


class UserPreferenceCreate(BaseModel):
    job_preferences: Optional[JobPreferencesBase] = None
    notification_preferences: Optional[NotificationPreferencesBase] = None
    content_ui_preferences: Optional[ContentUIPreferencesBase] = None
    privacy_preferences: Optional[PrivacyPreferencesBase] = None
    learning_preferences: Optional[LearningPreferencesBase] = None
    recommendation_weights: Optional[RecommendationWeightsBase] = None


class UserPreferenceUpdate(BaseModel):
    job_preferences: Optional[JobPreferencesBase] = None
    notification_preferences: Optional[NotificationPreferencesBase] = None
    content_ui_preferences: Optional[ContentUIPreferencesBase] = None
    privacy_preferences: Optional[PrivacyPreferencesBase] = None
    learning_preferences: Optional[LearningPreferencesBase] = None
    recommendation_weights: Optional[RecommendationWeightsBase] = None


class UserPreferenceResponse(BaseModel):
    id: int
    user_id: int
    job_preferences: JobPreferencesBase
    notification_preferences: NotificationPreferencesBase
    content_ui_preferences: ContentUIPreferencesBase
    privacy_preferences: PrivacyPreferencesBase
    learning_preferences: LearningPreferencesBase
    recommendation_weights: RecommendationWeightsBase
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBehaviorLogCreate(BaseModel):
    event_type: str
    event_category: str
    event_action: str
    event_label: Optional[str] = None
    event_value: Optional[float] = None
    page_url: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    country: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    session_id: str


class UserBehaviorLogResponse(BaseModel):
    id: int
    user_id: int
    session_id: str
    event_type: str
    event_category: str
    event_action: str
    event_label: Optional[str]
    event_value: Optional[float]
    page_url: Optional[str]
    referrer: Optional[str]
    device_type: Optional[str]
    browser: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[int]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class UserInteractionCreate(BaseModel):
    interaction_type: str
    entity_type: str
    entity_id: int
    duration_seconds: Optional[int] = None
    scroll_depth: Optional[float] = None
    click_position: Optional[str] = None
    rating: Optional[int] = None
    feedback_text: Optional[str] = None
    is_positive: Optional[bool] = None
    source: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class UserInteractionResponse(BaseModel):
    id: int
    user_id: int
    interaction_type: str
    entity_type: str
    entity_id: int
    duration_seconds: Optional[int]
    scroll_depth: Optional[float]
    click_position: Optional[str]
    rating: Optional[int]
    feedback_text: Optional[str]
    is_positive: Optional[bool]
    source: Optional[str]
    context: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PersonalizationProfileResponse(BaseModel):
    id: int
    user_id: int
    inferred_skills: Optional[List[str]]
    inferred_interests: Optional[List[str]]
    inferred_seniority: Optional[str]
    inferred_job_functions: Optional[List[str]]
    inferred_industries: Optional[List[str]]
    inferred_work_style: Optional[str]
    job_search_engagement: float
    learning_engagement: float
    research_engagement: float
    community_engagement: float
    last_updated: datetime
    model_version: str
    confidence_score: float
    is_active: bool
    manual_override: bool

    class Config:
        from_attributes = True


class PreferenceImportExport(BaseModel):
    preferences: UserPreferenceResponse
    exported_at: datetime
    version: str = "1.0"