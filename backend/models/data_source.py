"""Data source model - persisted configuration for data pipeline sources.

Canonical home of DataSource/SourceConfig/SourceType/SourceProviderType so
schema creation (Base.metadata.create_all) includes the data_sources table.
Re-exported from backend.data_pipeline.sources.source_registry for
backward compatibility.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SourceType(str, PyEnum):
    """Types of data sources."""
    OFFICIAL_API = "official_api"
    PUBLIC_FEED = "public_feed"
    LICENSED_DATASET = "licensed_dataset"
    PUBLIC_WEBPAGE = "public_webpage"
    USER_PROVIDED = "user_provided"
    INTERNAL_DATABASE = "internal_database"
    UNKNOWN = "unknown"


class SourceProviderType(str, PyEnum):
    """Types of source providers."""
    SEARCH_API = "search_api"
    NEWS_API = "news_api"
    ACADEMIC_API = "academic_api"
    COMPANY_API = "company_api"
    JOB_API = "job_api"
    RSS_FEED = "rss_feed"
    CUSTOM = "custom"


@dataclass
class SourceConfig:
    """Configuration for a data source (non-DB, for runtime use)."""
    source_id: str
    name: str
    source_type: SourceType
    provider_type: SourceProviderType
    domain: str
    enabled: bool = True
    priority: int = 1
    update_frequency: str = "daily"
    reliability_score: float = 0.5
    rate_limit: int = 60
    timeout_seconds: int = 30
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    terms_url: Optional[str] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "source_type": self.source_type.value,
            "provider_type": self.provider_type.value,
            "domain": self.domain,
            "enabled": self.enabled,
            "priority": self.priority,
            "update_frequency": self.update_frequency,
            "reliability_score": self.reliability_score,
            "rate_limit": self.rate_limit,
            "timeout_seconds": self.timeout_seconds,
            "api_key_env": self.api_key_env,
            "base_url": self.base_url,
            "custom_headers": self.custom_headers,
            "parameters": self.parameters,
            "terms_url": self.terms_url,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "consecutive_failures": self.consecutive_failures,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceConfig":
        return cls(
            source_id=data["source_id"],
            name=data["name"],
            source_type=SourceType(data["source_type"]),
            provider_type=SourceProviderType(data["provider_type"]),
            domain=data["domain"],
            enabled=data.get("enabled", True),
            priority=data.get("priority", 1),
            update_frequency=data.get("update_frequency", "daily"),
            reliability_score=data.get("reliability_score", 0.5),
            rate_limit=data.get("rate_limit", 60),
            timeout_seconds=data.get("timeout_seconds", 30),
            api_key_env=data.get("api_key_env"),
            base_url=data.get("base_url"),
            custom_headers=data.get("custom_headers", {}),
            parameters=data.get("parameters", {}),
            terms_url=data.get("terms_url"),
            last_success=datetime.fromisoformat(data["last_success"]) if data.get("last_success") else None,
            last_failure=datetime.fromisoformat(data["last_failure"]) if data.get("last_failure") else None,
            consecutive_failures=data.get("consecutive_failures", 0),
            metadata=data.get("metadata", {}),
        )


class DataSource(Base):
    """Database model for persisted source configuration."""
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(Enum(SourceType), nullable=False)
    provider_type: Mapped[str] = mapped_column(Enum(SourceProviderType), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    update_frequency: Mapped[str] = mapped_column(String(50), default="daily", nullable=False)
    reliability_score: Mapped[float] = mapped_column(default=0.5, nullable=False)
    rate_limit: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    api_key_env: Mapped[str | None] = mapped_column(String(100), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    custom_headers: Mapped[Dict[str, str] | None] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    terms_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_success: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_failure: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_metadata: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_config(self) -> SourceConfig:
        """Convert to SourceConfig dataclass."""
        return SourceConfig(
            source_id=self.source_id,
            name=self.name,
            source_type=self.source_type,
            provider_type=self.provider_type,
            domain=self.domain,
            enabled=self.enabled,
            priority=self.priority,
            update_frequency=self.update_frequency,
            reliability_score=self.reliability_score,
            rate_limit=self.rate_limit,
            timeout_seconds=self.timeout_seconds,
            api_key_env=self.api_key_env,
            base_url=self.base_url,
            custom_headers=self.custom_headers or {},
            parameters=self.parameters or {},
            terms_url=self.terms_url,
            last_success=self.last_success,
            last_failure=self.last_failure,
            consecutive_failures=self.consecutive_failures,
            metadata=self.source_metadata or {},
        )

    @classmethod
    def from_config(cls, config: SourceConfig) -> "DataSource":
        """Create DataSource from SourceConfig."""
        return cls(
            source_id=config.source_id,
            name=config.name,
            source_type=config.source_type,
            provider_type=config.provider_type,
            domain=config.domain,
            enabled=config.enabled,
            priority=config.priority,
            update_frequency=config.update_frequency,
            reliability_score=config.reliability_score,
            rate_limit=config.rate_limit,
            timeout_seconds=config.timeout_seconds,
            api_key_env=config.api_key_env,
            base_url=config.base_url,
            custom_headers=config.custom_headers,
            parameters=config.parameters,
            terms_url=config.terms_url,
            last_success=config.last_success,
            last_failure=config.last_failure,
            consecutive_failures=config.consecutive_failures,
            source_metadata=config.metadata,
        )
