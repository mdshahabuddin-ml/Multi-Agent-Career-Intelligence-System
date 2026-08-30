from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum as PyEnum
from abc import ABC, abstractmethod
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FilterOperator(str, PyEnum):
    """Filter operators."""
    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    IN = "in"  # In list
    NIN = "nin"  # Not in list
    CONTAINS = "contains"  # String contains
    STARTS_WITH = "starts_with"  # String starts with
    ENDS_WITH = "ends_with"  # String ends with
    REGEX = "regex"  # Regex match
    EXISTS = "exists"  # Field exists
    RANGE = "range"  # Range query


class FilterLogic(str, PyEnum):
    """Logical operators for combining filters."""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class FilterCondition:
    """A single filter condition."""
    field: str
    operator: FilterOperator
    value: Any
    case_sensitive: bool = False

    def evaluate(self, record: Dict[str, Any]) -> bool:
        """Evaluate condition against a record."""
        field_value = self._get_nested_value(record, self.field)

        if self.operator == FilterOperator.EXISTS:
            return field_value is not None

        if field_value is None:
            return False

        # String operations
        if isinstance(field_value, str):
            return self._eval_string(field_value, self.value)

        # Numeric operations
        if isinstance(field_value, (int, float)):
            return self._eval_numeric(field_value, self.value)

        # List operations
        if isinstance(field_value, list):
            return self._eval_list(field_value, self.value)

        # Datetime operations
        if isinstance(field_value, datetime):
            return self._eval_datetime(field_value, self.value)

        # Boolean
        if isinstance(field_value, bool):
            return self._eval_bool(field_value, self.value)

        # Default: exact match
        return field_value == self.value

    def _get_nested_value(self, record: Dict[str, Any], field: str) -> Any:
        """Get nested field value using dot notation."""
        parts = field.split(".")
        value = record
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            if value is None:
                return None
        return value

    def _eval_string(self, field_val: str, filter_val: Any) -> bool:
        fv = field_val if self.case_sensitive else field_val.lower()
        fv_filter = str(filter_val) if self.case_sensitive else str(filter_val).lower()

        if self.operator == FilterOperator.EQ:
            return fv == fv_filter
        elif self.operator == FilterOperator.NE:
            return fv != fv_filter
        elif self.operator == FilterOperator.CONTAINS:
            return fv_filter in fv
        elif self.operator == FilterOperator.STARTS_WITH:
            return fv.startswith(fv_filter)
        elif self.operator == FilterOperator.ENDS_WITH:
            return fv.endswith(fv_filter)
        elif self.operator == FilterOperator.REGEX:
            import re
            return bool(re.search(fv_filter, fv))
        elif self.operator == FilterOperator.IN:
            return fv in [v.lower() if not self.case_sensitive else v for v in filter_val]
        elif self.operator == FilterOperator.NIN:
            return fv not in [v.lower() if not self.case_sensitive else v for v in filter_val]
        return False

    def _eval_numeric(self, field_val: Union[int, float], filter_val: Any) -> bool:
        try:
            fv = float(filter_val) if not isinstance(filter_val, (int, float)) else filter_val
        except (ValueError, TypeError):
            return False

        if self.operator == FilterOperator.EQ:
            return field_val == fv
        elif self.operator == FilterOperator.NE:
            return field_val != fv
        elif self.operator == FilterOperator.GT:
            return field_val > fv
        elif self.operator == FilterOperator.GTE:
            return field_val >= fv
        elif self.operator == FilterOperator.LT:
            return field_val < fv
        elif self.operator == FilterOperator.LTE:
            return field_val <= fv
        elif self.operator == FilterOperator.RANGE:
            if isinstance(filter_val, dict):
                min_val = filter_val.get("min")
                max_val = filter_val.get("max")
                if min_val is not None and field_val < min_val:
                    return False
                if max_val is not None and field_val > max_val:
                    return False
                return True
        return False

    def _eval_list(self, field_val: List[Any], filter_val: Any) -> bool:
        if self.operator == FilterOperator.IN:
            return any(v in field_val for v in (filter_val if isinstance(filter_val, list) else [filter_val]))
        elif self.operator == FilterOperator.NIN:
            return not any(v in field_val for v in (filter_val if isinstance(filter_val, list) else [filter_val]))
        elif self.operator == FilterOperator.CONTAINS:
            return filter_val in field_val
        return False

    def _eval_datetime(self, field_val: datetime, filter_val: Any) -> bool:
        if isinstance(filter_val, str):
            try:
                filter_val = datetime.fromisoformat(filter_val.replace("Z", "+00:00"))
            except ValueError:
                return False
        elif isinstance(filter_val, (int, float)):
            filter_val = datetime.fromtimestamp(filter_val)

        if not isinstance(filter_val, datetime):
            return False

        if self.operator == FilterOperator.EQ:
            return field_val == filter_val
        elif self.operator == FilterOperator.NE:
            return field_val != filter_val
        elif self.operator == FilterOperator.GT:
            return field_val > filter_val
        elif self.operator == FilterOperator.GTE:
            return field_val >= filter_val
        elif self.operator == FilterOperator.LT:
            return field_val < filter_val
        elif self.operator == FilterOperator.LTE:
            return field_val <= filter_val
        elif self.operator == FilterOperator.RANGE:
            if isinstance(filter_val, dict):
                min_val = filter_val.get("min")
                max_val = filter_val.get("max")
                if min_val and field_val < min_val:
                    return False
                if max_val and field_val > max_val:
                    return False
                return True
        return False

    def _eval_bool(self, field_val: bool, filter_val: Any) -> bool:
        if isinstance(filter_val, str):
            filter_val = filter_val.lower() in ("true", "1", "yes")
        elif isinstance(filter_val, (int, float)):
            filter_val = bool(filter_val)
        elif not isinstance(filter_val, bool):
            return False

        if self.operator == FilterOperator.EQ:
            return field_val == filter_val
        elif self.operator == FilterOperator.NE:
            return field_val != filter_val
        return False


@dataclass
class FilterGroup:
    """A group of filter conditions combined with logic."""
    conditions: List[FilterCondition] = field(default_factory=list)
    logic: FilterLogic = FilterLogic.AND
    groups: List["FilterGroup"] = field(default_factory=list)

    def evaluate(self, record: Dict[str, Any]) -> bool:
        """Evaluate filter group against a record."""
        results = []

        # Evaluate conditions
        for condition in self.conditions:
            results.append(condition.evaluate(record))

        # Evaluate nested groups
        for group in self.groups:
            results.append(group.evaluate(record))

        if not results:
            return True

        if self.logic == FilterLogic.AND:
            return all(results)
        elif self.logic == FilterLogic.OR:
            return any(results)
        elif self.logic == FilterLogic.NOT:
            return not all(results)
        return True

    def add_condition(self, field: str, operator: FilterOperator, value: Any, **kwargs) -> "FilterGroup":
        """Add a condition to the group."""
        self.conditions.append(FilterCondition(field=field, operator=operator, value=value, **kwargs))
        return self

    def add_group(self, group: "FilterGroup") -> "FilterGroup":
        """Add a nested group."""
        self.groups.append(group)
        return self


class MetadataFilter:
    """Main metadata filtering class."""

    def __init__(self):
        self._groups: List[FilterGroup] = []
        self._default_logic = FilterLogic.AND

    def add_group(self, group: FilterGroup) -> "MetadataFilter":
        """Add a filter group."""
        self._groups.append(group)
        return self

    def add_condition(
        self,
        field: str,
        operator: Union[FilterOperator, str],
        value: Any,
        **kwargs
    ) -> "MetadataFilter":
        """Add a simple condition (convenience method)."""
        if isinstance(operator, str):
            operator = FilterOperator(operator)

        if not self._groups:
            self._groups.append(FilterGroup(logic=self._default_logic))

        self._groups[0].add_condition(field, operator, value, **kwargs)
        return self

    def set_logic(self, logic: Union[FilterLogic, str]) -> "MetadataFilter":
        """Set default logic for top-level group."""
        if isinstance(logic, str):
            logic = FilterLogic(logic)
        self._default_logic = logic
        if self._groups:
            self._groups[0].logic = logic
        return self

    def evaluate(self, record: Dict[str, Any]) -> bool:
        """Evaluate all filter groups against a record."""
        if not self._groups:
            return True

        results = [group.evaluate(record) for group in self._groups]
        return all(results)

    def filter_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter a list of records."""
        return [r for r in records if self.evaluate(r)]

    def clear(self) -> "MetadataFilter":
        """Clear all filters."""
        self._groups.clear()
        return self

    def is_empty(self) -> bool:
        """Check if filter is empty."""
        return len(self._groups) == 0


# Convenience functions for common filters
class CommonFilters:
    """Common filter builders."""

    @staticmethod
    def by_source_type(source_types: List[str]) -> MetadataFilter:
        """Filter by source type."""
        f = MetadataFilter()
        f.add_condition("source_type", FilterOperator.IN, source_types)
        return f

    @staticmethod
    def by_domain(domains: List[str]) -> MetadataFilter:
        """Filter by source domain."""
        f = MetadataFilter()
        f.add_condition("source_domain", FilterOperator.IN, domains)
        return f

    @staticmethod
    def by_date_range(start: Optional[datetime] = None, end: Optional[datetime] = None) -> MetadataFilter:
        """Filter by publication date range."""
        f = MetadataFilter()
        if start:
            f.add_condition("published_date", FilterOperator.GTE, start)
        if end:
            f.add_condition("published_date", FilterOperator.LTE, end)
        return f

    @staticmethod
    def by_credibility(min_score: float = 0.0, max_score: float = 1.0) -> MetadataFilter:
        """Filter by credibility score range."""
        f = MetadataFilter()
        if min_score > 0:
            f.add_condition("credibility_score", FilterOperator.GTE, min_score)
        if max_score < 1.0:
            f.add_condition("credibility_score", FilterOperator.LTE, max_score)
        return f

    @staticmethod
    def by_relevance(min_score: float = 0.0) -> MetadataFilter:
        """Filter by minimum relevance score."""
        f = MetadataFilter()
        if min_score > 0:
            f.add_condition("relevance_score", FilterOperator.GTE, min_score)
        return f

    @staticmethod
    def by_skill(skills: List[str]) -> MetadataFilter:
        """Filter by skills (for resume/job chunks)."""
        f = MetadataFilter()
        f.add_condition("skills", FilterOperator.CONTAINS, skills[0] if skills else "")
        # For multiple skills, would need OR logic
        return f

    @staticmethod
    def by_company(companies: List[str]) -> MetadataFilter:
        """Filter by company name."""
        f = MetadataFilter()
        f.add_condition("company_name", FilterOperator.IN, companies)
        return f

    @staticmethod
    def by_location(locations: List[str]) -> MetadataFilter:
        """Filter by location."""
        f = MetadataFilter()
        f.add_condition("location", FilterOperator.IN, locations)
        return f

    @staticmethod
    def by_remote(is_remote: Optional[bool] = None) -> MetadataFilter:
        """Filter by remote status."""
        f = MetadataFilter()
        if is_remote is not None:
            f.add_condition("is_remote", FilterOperator.EQ, is_remote)
        return f

    @staticmethod
    def by_experience_level(levels: List[str]) -> MetadataFilter:
        """Filter by experience level."""
        f = MetadataFilter()
        f.add_condition("experience_level", FilterOperator.IN, levels)
        return f

    @staticmethod
    def by_employment_type(types: List[str]) -> MetadataFilter:
        """Filter by employment type."""
        f = MetadataFilter()
        f.add_condition("employment_type", FilterOperator.IN, types)
        return f

    @staticmethod
    def custom_filter(
        field: str,
        operator: Union[FilterOperator, str],
        value: Any,
        logic: FilterLogic = FilterLogic.AND,
    ) -> MetadataFilter:
        """Create custom filter."""
        f = MetadataFilter()
        f.set_logic(logic)
        f.add_condition(field, operator, value)
        return f


# Pre-built filter presets
class FilterPresets:
    """Pre-built filter combinations."""

    @staticmethod
    def high_quality_recent() -> MetadataFilter:
        """High credibility, recent sources."""
        f = MetadataFilter()
        f.set_logic(FilterLogic.AND)
        f.add_condition("credibility_score", FilterOperator.GTE, 0.7)
        f.add_condition("relevance_score", FilterOperator.GTE, 0.5)
        return f

    @staticmethod
    def academic_sources() -> MetadataFilter:
        """Academic and government sources only."""
        f = MetadataFilter()
        f.add_condition("source_type", FilterOperator.IN, ["academic", "government"])
        return f

    @staticmethod
    def job_market_sources() -> MetadataFilter:
        """Job market and company sources."""
        f = MetadataFilter()
        f.add_condition("source_type", FilterOperator.IN, ["job_board", "company"])
        return f

    @staticmethod
    def remote_jobs() -> MetadataFilter:
        """Remote job postings."""
        f = MetadataFilter()
        f.add_condition("is_remote", FilterOperator.EQ, True)
        f.add_condition("source_type", FilterOperator.EQ, "job_board")
        return f

    @staticmethod
    def senior_roles() -> MetadataFilter:
        """Senior level positions."""
        f = MetadataFilter()
        f.add_condition("experience_level", FilterOperator.IN, ["senior", "lead", "principal", "staff", "director"])
        return f