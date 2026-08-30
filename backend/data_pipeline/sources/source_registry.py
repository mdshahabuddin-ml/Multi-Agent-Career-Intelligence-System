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


class SourceRegistry:
    """Registry for managing data source configurations with DB persistence."""

    def __init__(self, db_session=None):
        self._db = db_session
        self._cache: Dict[str, SourceConfig] = {}
        self._loaded = False

    def _load_from_db(self):
        """Load all enabled sources from database."""
        if not self._db:
            return
        try:
            sources = self._db.query(DataSource).filter(DataSource.enabled == True).all()
            for source in sources:
                self._cache[source.source_id] = source.to_config()
            self._loaded = True
        except Exception as e:
            # Table may not exist yet
            self._loaded = True

    def register(self, config: SourceConfig, persist: bool = True) -> SourceConfig:
        """Register a new source configuration."""
        if self._db and persist:
            existing = self._db.query(DataSource).filter(DataSource.source_id == config.source_id).first()
            if existing:
                # Update existing
                for key, value in config.to_dict().items():
                    if hasattr(existing, key) and key not in ("id", "created_at"):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                source = DataSource.from_config(config)
                self._db.add(source)
            self._db.commit()
        self._cache[config.source_id] = config
        return config

    def unregister(self, source_id: str, persist: bool = True) -> bool:
        """Unregister a source."""
        if self._db and persist:
            source = self._db.query(DataSource).filter(DataSource.source_id == source_id).first()
            if source:
                self._db.delete(source)
                self._db.commit()
        return self._cache.pop(source_id, None) is not None

    def get(self, source_id: str) -> Optional[SourceConfig]:
        """Get a source configuration by ID."""
        if not self._loaded:
            self._load_from_db()
        return self._cache.get(source_id)

    def get_by_domain(self, domain: str) -> Optional[SourceConfig]:
        """Get a source configuration by domain."""
        if not self._loaded:
            self._load_from_db()
        for config in self._cache.values():
            if config.domain == domain:
                return config
        return None

    def list_enabled(self, source_type: Optional[SourceType] = None) -> List[SourceConfig]:
        """List all enabled sources, optionally filtered by type."""
        if not self._loaded:
            self._load_from_db()
        sources = [c for c in self._cache.values() if c.enabled]
        if source_type:
            sources = [c for c in sources if c.source_type == source_type]
        return sorted(sources, key=lambda c: -c.priority)

    def list_all(self) -> List[SourceConfig]:
        """List all sources including disabled."""
        if not self._loaded:
            self._load_from_db()
        return list(self._cache.values())

    def update_status(self, source_id: str, success: bool, error: Optional[str] = None):
        """Update source status after a collection attempt."""
        config = self.get(source_id)
        if not config:
            return
        
        now = datetime.utcnow()
        if success:
            config.last_success = now
            config.consecutive_failures = 0
        else:
            config.last_failure = now
            config.consecutive_failures += 1
            if config.consecutive_failures >= 5:
                config.enabled = False
        
        if self._db:
            source = self._db.query(DataSource).filter(DataSource.source_id == source_id).first()
            if source:
                source.last_success = config.last_success
                source.last_failure = config.last_failure
                source.consecutive_failures = config.consecutive_failures
                source.enabled = config.enabled
                source.updated_at = now
                self._db.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        if not self._loaded:
            self._load_from_db()
        total = len(self._cache)
        enabled = sum(1 for c in self._cache.values() if c.enabled)
        by_type = {}
        for c in self._cache.values():
            by_type[c.source_type.value] = by_type.get(c.source_type.value, 0) + 1
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "by_type": by_type,
        }

    def create_default_sources(self):
        """Create default source configurations."""
        defaults = [
            SourceConfig(
                source_id="mock_jobs",
                name="Mock Job Provider",
                source_type=SourceType.INTERNAL_DATABASE,
                provider_type=SourceProviderType.CUSTOM,
                domain="internal.mock",
                enabled=True,
                priority=0,
                update_frequency="manual",
                reliability_score=0.3,
                rate_limit=100,
                timeout_seconds=10,
                parameters={"description": "Development/testing mock data"},
            ),
        ]
        for config in defaults:
            if config.source_id not in self._cache:
                self.register(config, persist=True)


# Global registry instance
default_registry = SourceRegistry()