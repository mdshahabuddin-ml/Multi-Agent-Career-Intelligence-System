from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import hashlib
import json


class CollectorHealth(str, Enum):
    """Health status of a collector."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class RawDataRecord:
    """
    Raw data record preserving source information for traceability.
    
    Every record from external sources should be wrapped in this
    to maintain provenance through the pipeline.
    """
    source_id: str
    source_name: str
    source_type: str
    external_id: str
    source_url: Optional[str]
    collected_at: datetime
    raw_payload: Dict[str, Any]
    checksum: str
    content_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        source_id: str,
        source_name: str,
        source_type: str,
        external_id: str,
        source_url: Optional[str],
        raw_payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> "RawDataRecord":
        """Create a RawDataRecord with computed hashes."""
        collected_at = datetime.utcnow()
        
        # Stable serialization for hashing
        payload_str = json.dumps(raw_payload, sort_keys=True, default=str)
        checksum = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
        content_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:32]
        
        return cls(
            source_id=source_id,
            source_name=source_name,
            source_type=source_type,
            external_id=external_id,
            source_url=source_url,
            collected_at=collected_at,
            raw_payload=raw_payload,
            checksum=checksum,
            content_hash=content_hash,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "external_id": self.external_id,
            "source_url": self.source_url,
            "collected_at": self.collected_at.isoformat(),
            "raw_payload": self.raw_payload,
            "checksum": self.checksum,
            "content_hash": self.content_hash,
            "metadata": self.metadata
        }


class BaseCollector(ABC):
    """
    Abstract base class for all data collectors.
    
    Responsibilities:
    - Fetch data from external source
    - Parse into structured raw records
    - Return structured raw records with provenance
    - Provide health check capability
    
    Every collector must implement:
    - source_name: Unique identifier
    - source_type: Type of source (api, feed, webpage, etc.)
    - fetch(): Retrieve raw data
    - parse(): Transform to RawDataRecord list
    - health_check(): Verify source accessibility
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._source_name = self.config.get("source_name", self.__class__.__name__)
        self._source_type = self.config.get("source_type", "unknown")
        self._rate_limit = self.config.get("rate_limit", 60)
        self._timeout = self.config.get("timeout_seconds", 30)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type
    
    @property
    def rate_limit(self) -> int:
        return self._rate_limit
    
    @property
    def timeout(self) -> int:
        return self._timeout
    
    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch raw data from the external source.
        
        Returns:
            List of raw payload dictionaries from the source.
        """
        pass
    
    @abstractmethod
    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """
        Parse raw data into structured RawDataRecord objects.
        
        Args:
            raw_data: List of raw payloads from fetch()
            
        Returns:
            List of RawDataRecord with provenance metadata.
        """
        pass
    
    async def collect(self, **kwargs) -> List[RawDataRecord]:
        """
        Full collection cycle: fetch + parse.
        
        This is the main entry point for the ingestion pipeline.
        """
        raw_data = await self.fetch(**kwargs)
        return await self.parse(raw_data)
    
    @abstractmethod
    async def health_check(self) -> CollectorHealth:
        """
        Check if the source is accessible and healthy.
        
        Returns:
            CollectorHealth status.
        """
        pass
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get collector metadata for registry."""
        return {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "rate_limit": self.rate_limit,
            "timeout_seconds": self.timeout,
            "config": {k: v for k, v in self.config.items() if k not in ("api_key", "secret")}
        }