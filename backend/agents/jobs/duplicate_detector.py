"""
Backward compatibility imports for DuplicateDetector and DuplicateMatch.
These have moved to backend.data_pipeline.deduplication.duplicate_detector
"""

from backend.data_pipeline.deduplication.duplicate_detector import (
    DuplicateDetector,
    DuplicateMatch,
)

__all__ = [
    "DuplicateDetector",
    "DuplicateMatch",
]