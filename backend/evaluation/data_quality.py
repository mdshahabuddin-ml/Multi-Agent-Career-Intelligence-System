from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class DataSourceType(Enum):
    """Types of data sources for reliability scoring."""
    OFFICIAL_API = "official_api"
    GOVERNMENT = "government"
    ACADEMIC = "academic"
    INDUSTRY_REPORT = "industry_report"
    COMPANY_WEBSITE = "company_website"
    JOB_BOARD = "job_board"
    USER_GENERATED = "user_generated"
    THIRD_PARTY_AGGREGATOR = "third_party_aggregator"
    UNKNOWN = "unknown"


class FreshnessTier(Enum):
    """Data freshness tiers."""
    REAL_TIME = "real_time"          # < 1 day
    RECENT = "recent"                # 1-7 days
    CURRENT = "current"              # 1-30 days
    STALE = "stale"                  # 30-90 days
    OUTDATED = "outdated"            # > 90 days


@dataclass
class QualityDimension:
    """A single quality dimension score."""
    name: str
    score: float
    max_score: float = 1.0
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def normalized_score(self) -> float:
        """Return score normalized to 0-1 range."""
        if self.max_score <= 0:
            return 0.0
        return min(self.score / self.max_score, 1.0)
    
    @property
    def weighted_score(self) -> float:
        """Return weighted score."""
        return self.normalized_score * self.weight
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "max_score": self.max_score,
            "weight": self.weight,
            "normalized_score": self.normalized_score,
            "weighted_score": self.weighted_score,
            "details": self.details
        }


@dataclass
class DataQualityResult:
    """Complete data quality assessment result."""
    data_identifier: str
    data_type: str
    dimensions: List[QualityDimension]
    overall_score: float
    confidence_level: str
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_identifier": self.data_identifier,
            "data_type": self.data_type,
            "overall_score": self.overall_score,
            "confidence_level": self.confidence_level,
            "assessed_at": self.assessed_at.isoformat(),
            "dimensions": [d.to_dict() for d in self.dimensions],
            "metadata": self.metadata
        }


class DataQualityScorer:
    """
    Data Quality Assessment System.
    
    Scoring Formula:
    ----------------
    overall_quality_score = (w1 * completeness_score + w2 * source_reliability_score + 
                            w3 * freshness_score + w4 * consistency_score) / (w1 + w2 + w3 + w4)
    
    Where weights are configurable (default: w1=0.3, w2=0.25, w3=0.25, w4=0.2)
    
    IMPORTANT: This score represents data quality/confidence signals, NOT factual truth.
    A high score indicates the data is complete, from reliable sources, fresh, and consistent.
    It does NOT guarantee the data is factually correct.
    """
    
    DEFAULT_WEIGHTS = {
        "completeness": 0.30,
        "source_reliability": 0.25,
        "freshness": 0.25,
        "consistency": 0.20
    }
    
    SOURCE_RELIABILITY_SCORES = {
        DataSourceType.OFFICIAL_API: 1.0,
        DataSourceType.GOVERNMENT: 0.95,
        DataSourceType.ACADEMIC: 0.9,
        DataSourceType.INDUSTRY_REPORT: 0.85,
        DataSourceType.COMPANY_WEBSITE: 0.8,
        DataSourceType.JOB_BOARD: 0.7,
        DataSourceType.USER_GENERATED: 0.5,
        DataSourceType.THIRD_PARTY_AGGREGATOR: 0.6,
        DataSourceType.UNKNOWN: 0.3
    }
    
    FRESHNESS_SCORES = {
        FreshnessTier.REAL_TIME: 1.0,
        FreshnessTier.RECENT: 0.9,
        FreshnessTier.CURRENT: 0.75,
        FreshnessTier.STALE: 0.5,
        FreshnessTier.OUTDATED: 0.2
    }
    
    CONFIDENCE_THRESHOLDS = {
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4,
        "very_low": 0.0
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()
    
    def _validate_weights(self):
        """Validate that weights sum to a positive value."""
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError("Weights must sum to a positive value")
        # Normalize weights
        self.weights = {k: v / total for k, v in self.weights.items()}
    
    def assess_completeness(
        self,
        data: Dict[str, Any],
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None
    ) -> QualityDimension:
        """
        Assess data completeness.
        
        Formula: (required_fields_present / total_required) * 0.7 + 
                 (optional_fields_present / total_optional) * 0.3
        """
        optional_fields = optional_fields or []
        
        required_present = sum(1 for f in required_fields if f in data and data[f] not in (None, "", []))
        required_total = len(required_fields)
        
        optional_present = sum(1 for f in optional_fields if f in data and data[f] not in (None, "", []))
        optional_total = len(optional_fields)
        
        required_score = required_present / required_total if required_total > 0 else 1.0
        optional_score = optional_present / optional_total if optional_total > 0 else 1.0
        
        score = (required_score * 0.7) + (optional_score * 0.3)
        
        return QualityDimension(
            name="completeness",
            score=score,
            max_score=1.0,
            weight=self.weights.get("completeness", 0.3),
            details={
                "required_fields_total": required_total,
                "required_fields_present": required_present,
                "optional_fields_total": optional_total,
                "optional_fields_present": optional_present,
                "required_score": required_score,
                "optional_score": optional_score
            }
        )
    
    def assess_source_reliability(
        self,
        source_type: DataSourceType,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> QualityDimension:
        """
        Assess source reliability based on source type and metadata.
        
        Base score from SOURCE_RELIABILITY_SCORES, adjusted by metadata factors.
        """
        base_score = self.SOURCE_RELIABILITY_SCORES.get(source_type, 0.3)
        
        adjustments = 0.0
        details = {"base_score": base_score, "source_type": source_type.value}
        
        if source_metadata:
            # Adjust for known reputable sources
            if source_metadata.get("is_verified", False):
                adjustments += 0.05
                details["verified_bonus"] = 0.05
            
            # Adjust for citation availability
            if source_metadata.get("has_citations", False):
                adjustments += 0.05
                details["citations_bonus"] = 0.05
            
            # Adjust for update frequency
            update_freq = source_metadata.get("update_frequency")
            if update_freq == "real_time":
                adjustments += 0.05
            elif update_freq == "daily":
                adjustments += 0.03
            elif update_freq == "weekly":
                adjustments += 0.02
            details["update_frequency"] = update_freq
            
            # Penalize for known issues
            if source_metadata.get("has_known_issues", False):
                adjustments -= 0.1
                details["issues_penalty"] = -0.1
        
        final_score = max(0.0, min(1.0, base_score + adjustments))
        
        return QualityDimension(
            name="source_reliability",
            score=final_score,
            max_score=1.0,
            weight=self.weights.get("source_reliability", 0.25),
            details=details
        )
    
    def assess_freshness(
        self,
        data_timestamp: datetime,
        reference_time: Optional[datetime] = None,
        tier_thresholds: Optional[Dict[FreshnessTier, int]] = None
    ) -> QualityDimension:
        """
        Assess data freshness based on age.
        
        Tiers (default):
        - REAL_TIME: < 1 day
        - RECENT: 1-7 days
        - CURRENT: 7-30 days
        - STALE: 30-90 days
        - OUTDATED: > 90 days
        """
        reference_time = reference_time or datetime.utcnow()
        
        default_thresholds = {
            FreshnessTier.REAL_TIME: 1,
            FreshnessTier.RECENT: 7,
            FreshnessTier.CURRENT: 30,
            FreshnessTier.STALE: 90,
            FreshnessTier.OUTDATED: float('inf')
        }
        thresholds = tier_thresholds or default_thresholds
        
        age_days = (reference_time - data_timestamp).days
        age_days = max(0, age_days)
        
        tier = FreshnessTier.OUTDATED
        for t, max_days in thresholds.items():
            if age_days <= max_days:
                tier = t
                break
        
        score = self.FRESHNESS_SCORES.get(tier, 0.2)
        
        return QualityDimension(
            name="freshness",
            score=score,
            max_score=1.0,
            weight=self.weights.get("freshness", 0.25),
            details={
                "age_days": age_days,
                "tier": tier.value,
                "data_timestamp": data_timestamp.isoformat(),
                "reference_time": reference_time.isoformat()
            }
        )
    
    def assess_consistency(
        self,
        data: Dict[str, Any],
        validation_rules: Optional[List[Dict[str, Any]]] = None,
        cross_field_checks: Optional[List[Dict[str, Any]]] = None
    ) -> QualityDimension:
        """
        Assess data consistency through validation rules and cross-field checks.
        
        Validation rules format:
        [
            {"field": "salary_min", "rule": "gte", "value": 0, "message": "Salary must be non-negative"},
            {"field": "experience_years", "rule": "lte", "value": 50, "message": "Experience seems unrealistic"}
        ]
        
        Cross-field checks format:
        [
            {"fields": ["salary_min", "salary_max"], "rule": "lte", "message": "Min salary must be <= max salary"}
        ]
        """
        validation_rules = validation_rules or []
        cross_field_checks = cross_field_checks or []
        
        passed_checks = 0
        total_checks = len(validation_rules) + len(cross_field_checks)
        failed_details = []
        
        # Field validation rules
        for rule in validation_rules:
            field = rule.get("field")
            rule_type = rule.get("rule")
            expected = rule.get("value")
            message = rule.get("message", "")
            
            actual = data.get(field)
            passed = False
            
            if actual is not None:
                if rule_type == "gte":
                    passed = actual >= expected
                elif rule_type == "lte":
                    passed = actual <= expected
                elif rule_type == "eq":
                    passed = actual == expected
                elif rule_type == "in":
                    passed = actual in expected
                elif rule_type == "not_in":
                    passed = actual not in expected
                elif rule_type == "regex":
                    import re
                    passed = bool(re.match(expected, str(actual)))
            
            if passed:
                passed_checks += 1
            else:
                failed_details.append({"field": field, "rule": rule_type, "message": message})
        
        # Cross-field checks
        for check in cross_field_checks:
            fields = check.get("fields", [])
            rule_type = check.get("rule")
            message = check.get("message", "")
            
            values = [data.get(f) for f in fields]
            if all(v is not None for v in values):
                passed = False
                if rule_type == "lte" and len(values) == 2:
                    passed = values[0] <= values[1]
                elif rule_type == "gte" and len(values) == 2:
                    passed = values[0] >= values[1]
                elif rule_type == "eq" and len(values) == 2:
                    passed = values[0] == values[1]
                
                if passed:
                    passed_checks += 1
                else:
                    failed_details.append({"fields": fields, "rule": rule_type, "message": message})
            else:
                # Missing fields count as failed consistency check
                failed_details.append({"fields": fields, "rule": rule_type, "message": f"{message} (missing fields)"})
        
        score = passed_checks / total_checks if total_checks > 0 else 1.0
        
        return QualityDimension(
            name="consistency",
            score=score,
            max_score=1.0,
            weight=self.weights.get("consistency", 0.2),
            details={
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": total_checks - passed_checks,
                "failed_details": failed_details
            }
        )
    
    def assess(
        self,
        data: Dict[str, Any],
        data_identifier: str,
        data_type: str,
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None,
        source_type: DataSourceType = DataSourceType.UNKNOWN,
        source_metadata: Optional[Dict[str, Any]] = None,
        data_timestamp: Optional[datetime] = None,
        validation_rules: Optional[List[Dict[str, Any]]] = None,
        cross_field_checks: Optional[List[Dict[str, Any]]] = None,
        reference_time: Optional[datetime] = None
    ) -> DataQualityResult:
        """
        Perform complete data quality assessment.
        
        Args:
            data: The data to assess
            data_identifier: Unique identifier for this data
            data_type: Type of data (e.g., "job_posting", "resume", "company_profile")
            required_fields: List of required field names
            optional_fields: List of optional field names
            source_type: Type of data source
            source_metadata: Additional metadata about the source
            data_timestamp: When the data was created/updated
            validation_rules: Field validation rules
            cross_field_checks: Cross-field consistency checks
            reference_time: Reference time for freshness (default: now)
        
        Returns:
            DataQualityResult with all dimension scores and overall score
        """
        dimensions = []
        
        # 1. Completeness
        completeness = self.assess_completeness(data, required_fields, optional_fields)
        dimensions.append(completeness)
        
        # 2. Source Reliability
        source_rel = self.assess_source_reliability(source_type, source_metadata)
        dimensions.append(source_rel)
        
        # 3. Freshness
        if data_timestamp:
            freshness = self.assess_freshness(data_timestamp, reference_time)
            dimensions.append(freshness)
        
        # 4. Consistency
        consistency = self.assess_consistency(data, validation_rules, cross_field_checks)
        dimensions.append(consistency)
        
        # Calculate overall weighted score
        total_weight = sum(d.weight for d in dimensions)
        weighted_sum = sum(d.weighted_score for d in dimensions)
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Determine confidence level
        confidence_level = "very_low"
        for level, threshold in sorted(self.CONFIDENCE_THRESHOLDS.items(), key=lambda x: -x[1]):
            if overall_score >= threshold:
                confidence_level = level
                break
        
        return DataQualityResult(
            data_identifier=data_identifier,
            data_type=data_type,
            dimensions=dimensions,
            overall_score=overall_score,
            confidence_level=confidence_level,
            metadata={
                "weights_used": self.weights,
                "formula": "weighted_average(completeness, source_reliability, freshness, consistency)",
                "disclaimer": "This score represents data quality/confidence signals, NOT factual truth."
            }
        )


def create_default_scorer() -> DataQualityScorer:
    """Create a scorer with default weights."""
    return DataQualityScorer()