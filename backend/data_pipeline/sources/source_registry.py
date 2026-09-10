from datetime import datetime
from typing import Optional, Dict, Any, List

# Canonical model lives in backend.models so schema creation includes it.
# Re-exported here for backward compatibility - do not rename/remove.
from backend.models.data_source import (
    DataSource,
    SourceConfig,
    SourceProviderType,
    SourceType,
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