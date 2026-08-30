"""
Deduplication modules for detecting duplicate records.
"""

from backend.data_pipeline.deduplication.duplicate_detector import DuplicateDetector, DuplicateMatch

__all__ = ["DuplicateDetector", "DuplicateMatch"]