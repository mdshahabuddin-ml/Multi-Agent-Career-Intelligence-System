import logging
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass
from difflib import SequenceMatcher

from backend.data_pipeline.normalization.job_normalizer import NormalizedJob

logger = logging.getLogger(__name__)


@dataclass
class DuplicateMatch:
    """Represents a duplicate match between two jobs."""
    job1_index: int
    job2_index: int
    similarity_score: float
    match_reasons: List[str]
    is_duplicate: bool


class DuplicateDetector:
    """Detect duplicate job postings across sources."""

    def __init__(
        self,
        title_threshold: float = 0.85,
        company_threshold: float = 0.9,
        location_threshold: float = 0.8,
        overall_threshold: float = 0.85,
    ):
        self.name = "duplicate_detector"
        self.title_threshold = title_threshold
        self.company_threshold = company_threshold
        self.location_threshold = location_threshold
        self.overall_threshold = overall_threshold

    def _similarity(self, a: str, b: str) -> float:
        """Calculate string similarity using SequenceMatcher."""
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity with special handling for common variations."""
        clean1 = self._clean_title(title1)
        clean2 = self._clean_title(title2)
        return self._similarity(clean1, clean2)

    def _clean_title(self, title: str) -> str:
        """Clean job title for comparison."""
        import re
        title = re.sub(r"\b(senior|junior|lead|principal|staff|entry|mid)\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\b(remote|onsite|hybrid|on-site)\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"[^\w\s]", " ", title)
        title = re.sub(r"\s+", " ", title).strip()
        return title

    def _company_similarity(self, company1: str, company2: str) -> float:
        """Calculate company name similarity."""
        clean1 = self._clean_company(company1)
        clean2 = self._clean_company(company2)
        return self._similarity(clean1, clean2)

    def _clean_company(self, company: str) -> str:
        """Clean company name for comparison."""
        import re
        suffixes = ["inc", "inc.", "llc", "llc.", "corp", "corp.", "ltd", "ltd.", "co", "co.", "company"]
        for suffix in suffixes:
            company = re.sub(rf"\b{suffix}\b", "", company, flags=re.IGNORECASE)
        company = re.sub(r"[^\w\s]", " ", company)
        company = re.sub(r"\s+", " ", company).strip()
        return company

    def _location_similarity(self, loc1: str, loc2: str) -> float:
        """Calculate location similarity."""
        if not loc1 or not loc2:
            return 0.0
        loc1 = loc1.lower()
        loc2 = loc2.lower()

        if loc1 == loc2:
            return 1.0

        if "remote" in loc1 and "remote" in loc2:
            return 0.95

        import re
        city1 = re.split(r"[,;]", loc1)[0].strip()
        city2 = re.split(r"[,;]", loc2)[0].strip()
        if city1 and city2 and self._similarity(city1, city2) > 0.8:
            return 0.85

        return self._similarity(loc1, loc2)

    def _content_hash(self, job: NormalizedJob) -> str:
        """Generate content hash for exact duplicate detection."""
        content = f"{job.title}|{job.company_name}|{job.description[:500]}"
        return hashlib.md5(content.encode()).hexdigest()

    def find_duplicates(self, jobs: List[NormalizedJob]) -> List[DuplicateMatch]:
        """Find duplicate jobs in a list."""
        logger.info(f"Checking {len(jobs)} jobs for duplicates")
        matches = []

        hash_map: Dict[str, int] = {}
        for i, job in enumerate(jobs):
            h = self._content_hash(job)
            if h in hash_map:
                matches.append(DuplicateMatch(
                    job1_index=hash_map[h],
                    job2_index=i,
                    similarity_score=1.0,
                    match_reasons=["Exact content hash match"],
                    is_duplicate=True,
                ))
            else:
                hash_map[h] = i

        for i in range(len(jobs)):
            if any(m.job1_index == i or m.job2_index == i for m in matches if m.is_duplicate):
                continue

            for j in range(i + 1, len(jobs)):
                if any(m.job1_index == j or m.job2_index == j for m in matches if m.is_duplicate):
                    continue

                match = self._compare_jobs(jobs[i], jobs[j])
                if match.is_duplicate:
                    matches.append(match)

        logger.info(f"Found {len(matches)} duplicate pairs")
        return matches

    def _compare_jobs(self, job1: NormalizedJob, job2: NormalizedJob) -> DuplicateMatch:
        """Compare two jobs for duplication."""
        reasons = []

        title_sim = self._title_similarity(job1.title, job2.title)
        company_sim = self._company_similarity(job1.company_name, job2.company_name)
        location_sim = self._location_similarity(job1.location, job2.location)

        overall_sim = (
            title_sim * 0.4 +
            company_sim * 0.3 +
            location_sim * 0.2 +
            (1.0 if job1.source_job_id == job2.source_job_id else 0.0) * 0.1
        )

        if title_sim >= self.title_threshold:
            reasons.append(f"Title match ({title_sim:.0%})")
        if company_sim >= self.company_threshold:
            reasons.append(f"Company match ({company_sim:.0%})")
        if location_sim >= self.location_threshold:
            reasons.append(f"Location match ({location_sim:.0%})")

        is_dup = overall_sim >= self.overall_threshold and len(reasons) >= 2

        return DuplicateMatch(
            job1_index=-1,
            job2_index=-1,
            similarity_score=overall_sim,
            match_reasons=reasons,
            is_duplicate=is_dup,
        )

    def deduplicate(self, jobs: List[NormalizedJob]) -> List[NormalizedJob]:
        """Remove duplicates from job list, keeping highest quality."""
        matches = self.find_duplicates(jobs)

        duplicate_groups: Dict[int, List[int]] = {}
        for match in matches:
            if match.is_duplicate:
                if match.job1_index not in duplicate_groups:
                    duplicate_groups[match.job1_index] = [match.job1_index]
                duplicate_groups[match.job1_index].append(match.job2_index)

        to_remove = set()
        for group in duplicate_groups.values():
            sorted_group = sorted(group, key=lambda i: jobs[i].quality_score, reverse=True)
            to_remove.update(sorted_group[1:])

        deduplicated = [job for i, job in enumerate(jobs) if i not in to_remove]
        logger.info(f"Deduplicated: {len(jobs)} -> {len(deduplicated)} jobs")
        return deduplicated