import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def parse_date_range(text: str) -> tuple[Optional[str], Optional[str]]:
    """Parse date ranges like 'Jan 2020 - Dec 2021' or '2020-2022'."""
    patterns = [
        r"(\w+\s+\d{4})\s*[--]\s*(\w+\s+\d{4}|present|current)",
        r"(\d{4})\s*[--]\s*(\d{4}|present|current)",
        r"(\d{1,2}/\d{4})\s*[--]\s*(\d{1,2}/\d{4}|present|current)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = match.group(1).strip()
            end = match.group(2).strip()
            if end.lower() in ["present", "current"]:
                end = None
            return start, end
    return None, None


def extract_experience_entries(text: str) -> list[dict]:
    """Extract structured experience entries from text."""
    entries = []

    lines = text.split("\n")
    current_entry = None

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        has_date = bool(re.search(r'\b\d{4}\s*[--]\s*(?:\d{4}|present|current)\b', line_stripped, re.IGNORECASE))
        has_role_company = bool(re.search(r'(?:^|\s)(?:at|@|,)\s+', line_stripped, re.IGNORECASE))
        is_bullet = line_stripped.startswith(('-', '*', '*', '.'))

        if has_date or has_role_company:
            if current_entry and (current_entry.get("company") or current_entry.get("role")):
                entries.append(current_entry)

            start_date, end_date = parse_date_range(line_stripped)

            role = ""
            company = ""

            if has_role_company:
                parts = re.split(r'\s+(?:at|@|,)\s+', line_stripped, 1)
                if len(parts) == 2:
                    role = parts[0].strip()
                    company = parts[1].strip()
                else:
                    role = line_stripped
            else:
                role = line_stripped

            current_entry = {
                "company": company,
                "role": role,
                "description": "",
                "start_date": start_date,
                "end_date": end_date,
            }
        elif current_entry and is_bullet:
            current_entry["description"] += " " + line_stripped.lstrip('-**. ').strip()
        elif current_entry and line_stripped:
            current_entry["description"] += " " + line_stripped

    if current_entry and (current_entry.get("company") or current_entry.get("role")):
        entries.append(current_entry)

    return entries


def calculate_years_of_experience(entries: list[dict]) -> int:
    """Calculate total years of experience from entries."""
    total_months = 0
    for entry in entries:
        start = entry.get("start_date")
        end = entry.get("end_date") or datetime.now().strftime("%Y-%m")

        try:
            if start:
                if len(start) == 4:
                    start_dt = datetime.strptime(start, "%Y")
                elif len(start) == 7:
                    start_dt = datetime.strptime(start, "%m/%Y")
                else:
                    start_dt = datetime.strptime(start[:4], "%Y")
            else:
                continue

            if end:
                if len(end) == 4:
                    end_dt = datetime.strptime(end, "%Y")
                elif len(end) == 7:
                    end_dt = datetime.strptime(end, "%m/%Y")
                else:
                    end_dt = datetime.strptime(end[:4], "%Y")
            else:
                end_dt = datetime.now()

            months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
            total_months += max(0, months)
        except Exception:
            continue

    return max(0, total_months // 12)


class ExperienceAnalyzerAgent:
    """Agent responsible for analyzing work experience from resume."""

    def __init__(self):
        self.name = "experience_analyzer_agent"

    async def analyze_experience(self, raw_text: str, sections: dict) -> dict:
        """Extract and analyze work experience from resume."""
        logger.info("Analyzing experience from resume")

        experience_text = sections.get("experience", "")
        all_text = raw_text or " ".join(sections.values())

        entries = extract_experience_entries(experience_text or all_text)
        years = calculate_years_of_experience(entries)

        companies = list(set(e.get("company", "") for e in entries if e.get("company")))
        roles = list(set(e.get("role", "") for e in entries if e.get("role")))

        return {
            "entries": entries,
            "years_of_experience": years,
            "companies": companies,
            "roles": roles,
            "entry_count": len(entries),
        }