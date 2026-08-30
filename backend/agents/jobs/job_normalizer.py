"""
Backward compatibility imports for JobNormalizer and NormalizedJob.
These have moved to backend.data_pipeline.normalization.job_normalizer
"""

from backend.data_pipeline.normalization.job_normalizer import (
    JobNormalizer,
    NormalizedJob,
    normalize_salary,
    normalize_experience_level,
    normalize_employment_type,
    normalize_remote_type,
    normalize_location,
    extract_skills_from_text,
    extract_company_domain,
)

__all__ = [
    "JobNormalizer",
    "NormalizedJob",
    "normalize_salary",
    "normalize_experience_level",
    "normalize_employment_type",
    "normalize_remote_type",
    "normalize_location",
    "extract_skills_from_text",
    "extract_company_domain",
]