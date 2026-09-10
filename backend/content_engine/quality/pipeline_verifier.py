"""Fact/quality gate for Career-to-Content drafts.

Layered, dependency-light verification (no live research pipeline required):
1. Structural checks — non-empty, minimum length, no placeholder leakage
   (e.g. leftover ``{token}`` template markers or classic stub echoes).
2. Grounding check — the draft should reuse at least one salient term from
   the intake brief (names, skills, highlight keywords), guarding against
   off-brief generation.
3. Entity grounding — named source entities (certifications, achievements,
   projects) must appear in the draft so invented credentials fail.
4. Numeric-claim support — numbers in the draft must appear in the brief,
   attached research, or the kind template (instruction numbers such as
   "60 seconds" are not user facts and never count against the draft).
5. Personal/sensitive data — emails, phone numbers, and secret-like tokens
   not present in the brief fail the draft.
6. Quality signals — shouting, excessive punctuation, duplicated sentences.
7. Source check — when research sources are attached, require at least one
   before a research-backed kind can pass at high confidence.

Returns ``{passed, score, issues}``; the orchestrator persists the score on
the pipeline run and blocks approval below threshold.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MIN_DRAFT_CHARS = 80
# Minimum share of an entity's significant tokens that must appear in the
# draft for entity-grounded kinds (achievements, certifications, projects).
ENTITY_OVERLAP_THRESHOLD = 0.5
# Drafts over a platform limit by more than this share lose too much to
# truncation and are flagged (soft issue, not an auto-fail).
PLATFORM_OVERFLOW_THRESHOLD = 0.5
PLACEHOLDER_PATTERNS = (
    r"\{[a-z_]+\}",          # unresolved {token} markers
    r"lorem ipsum",          # filler text
    r"Generated content for:",  # legacy stub echo
    r"Caption for .* on ",   # legacy stub echo
    r"Script for:",          # legacy stub echo
    r"TODO|FIXME|XXX",       # authoring leftovers
)

_STOPWORDS = frozenset(
    "a an the and or of to in on for with is are was were be by as at from "
    "it its this that you your we our they their he she his her i my me us "
    "so do does did not no yes if then than too very can will just about into "
    "over after before between out up down off own same such only own".split()
)


def _keywords(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]*", (text or "").lower())
    return {w for w in words if len(w) > 3 and w not in _STOPWORDS}


def _loose_terms(text: str) -> set:
    """Tokenize for entity grounding (keeps short tokens like AWS/IBM)."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]*", (text or "").lower())
    return {w for w in words if len(w) > 1 and w not in _STOPWORDS}


_NUMBER_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
_SECRET_RES = (
    re.compile(r"(api[_-]?key|secret|password|passwd|pwd|token)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\b"),
)


def _normalize_number(token: str) -> str:
    """Canonical form for comparing numeric claims ($, commas, %)."""
    return token.replace("$", "").replace(",", "").replace("%", "").strip()


def _unsupported_numbers(draft: str, supported_text: str) -> List[str]:
    """Numbers in the draft with no match in supported text."""
    supported = {_normalize_number(t) for t in _NUMBER_RE.findall(supported_text)}
    supported.discard("")
    return sorted({
        token for token in _NUMBER_RE.findall(draft)
        if _normalize_number(token) and _normalize_number(token) not in supported
    })


def _foreign_contacts(draft: str, brief_text: str) -> List[str]:
    """Emails/phones in the draft that do not appear in the brief."""
    found = _EMAIL_RE.findall(draft) + _PHONE_RE.findall(draft)
    return sorted({m.strip() for m in found if m.strip() and m.strip() not in brief_text})


def _leaked_secrets(draft: str, brief_text: str) -> List[str]:
    """Secret-like tokens in the draft that do not appear in the brief."""
    leaked = []
    for pattern in _SECRET_RES:
        for match in pattern.findall(draft):
            token = match if isinstance(match, str) else match[0]
            if token and token not in brief_text:
                leaked.append(token[:24] + ("..." if len(token) > 24 else ""))
    return sorted(set(leaked))


def validate_platform_fit(
    text: str, platforms: List[str], limits: Dict[str, int]
) -> Dict[str, Dict[str, Any]]:
    """Report per-platform fit (chars vs limit) without truncating."""
    cleaned = (text or "").strip()
    report = {}
    for platform in platforms or []:
        limit = limits.get(platform)
        if not limit:
            report[platform] = {"chars": len(cleaned), "limit": None, "fits": True, "over_by": 0}
            continue
        over = max(0, len(cleaned) - limit)
        report[platform] = {
            "chars": len(cleaned),
            "limit": limit,
            "fits": over == 0,
            "over_by": over,
        }
    return report


def _entity_overlap(entity: str, draft_text: str) -> float:
    """Share of the entity's significant tokens present in the draft."""
    wanted = _loose_terms(entity)
    if not wanted:
        return 1.0
    return len(wanted & _loose_terms(draft_text)) / len(wanted)


class PipelineVerifier:
    """Verify a draft before it may enter human review."""

    def __init__(self, pass_threshold: float = 0.6):
        self.pass_threshold = pass_threshold

    async def verify(
        self,
        text: str,
        brief: Optional[Dict] = None,
        sources: Optional[List[Dict]] = None,
        required_terms: Optional[List[str]] = None,
        kind_template: Optional[str] = None,
        platforms: Optional[List[str]] = None,
        platform_limits: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Verify a draft.

        ``required_terms`` names source entities (e.g. a certification or
        achievement title) that must be grounded in the draft. Missing
        entities fail the draft so invented achievements or credentials
        can never reach human review. Numbers are checked against the
        brief, research, and kind template; contacts/secrets against the
        brief. No single new check deducts enough to fail a draft alone.
        """
        issues: List[str] = []
        score = 1.0
        brief = brief or {}
        sources = sources or []

        cleaned = (text or "").strip()
        if len(cleaned) < MIN_DRAFT_CHARS:
            issues.append(f"draft too short ({len(cleaned)} chars, minimum {MIN_DRAFT_CHARS})")
            score -= 0.5

        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                issues.append(f"placeholder/stub leakage detected ({pattern})")
                score -= 0.4
                break

        brief_text = " ".join(
            str(brief.get(k, "")) if not isinstance(brief.get(k), list)
            else " ".join(str(v) for v in brief.get(k, []))
            for k in ("headline", "name", "target_role", "skills", "highlight")
        )
        brief_terms, draft_terms = _keywords(brief_text), _keywords(cleaned)
        if brief_terms and not (brief_terms & draft_terms):
            issues.append("draft shares no salient terms with the intake brief (possible off-brief generation)")
            score -= 0.3

        if brief.get("requires_sources") and not sources:
            issues.append("no research sources attached for a research-backed draft")
            score -= 0.2

        for entity in required_terms or []:
            if not entity or not str(entity).strip():
                continue
            lowered = cleaned.lower()
            if str(entity).strip().lower() in lowered:
                continue
            overlap = _entity_overlap(str(entity), cleaned)
            if overlap <= ENTITY_OVERLAP_THRESHOLD:
                issues.append(
                    f"draft does not mention required entity {str(entity).strip()!r} "
                    "(possible invented achievement or credential)"
                )
                score -= 0.5

        reference_text = " ".join([
            brief_text,
            " ".join(
                f"{s.get('title', '')} {s.get('snippet', '')}"
                for s in sources
            ),
            kind_template or "",
        ])
        unsupported = _unsupported_numbers(cleaned, reference_text)
        if unsupported:
            issues.append(
                f"numeric claims not supported by brief/research/template: "
                f"{', '.join(unsupported[:5])}"
            )
            score -= 0.15

        foreign = _foreign_contacts(cleaned, brief_text)
        if foreign:
            issues.append(
                f"personal contact not present in brief: {', '.join(foreign[:3])}"
            )
            score -= 0.3

        leaked = _leaked_secrets(cleaned, brief_text)
        if leaked:
            issues.append(f"possible secret/token leakage: {', '.join(leaked[:3])}")
            score -= 0.4

        words = re.findall(r"[A-Za-z']+", cleaned)
        alpha_words = [w for w in words if any(c.isalpha() for c in w)]
        if alpha_words:
            caps_ratio = sum(1 for w in alpha_words if w.isupper() and len(w) > 1) / len(alpha_words)
            if caps_ratio > 0.3 and len(cleaned) >= MIN_DRAFT_CHARS:
                issues.append("excessive ALL-CAPS shouting")
                score -= 0.1
        if cleaned.count("!") > 5:
            issues.append("excessive exclamation marks")
            score -= 0.1
        sentences = [s.strip().lower() for s in re.split(r"[.!?]+", cleaned) if len(s.strip()) > 20]
        if len(sentences) != len(set(sentences)):
            issues.append("duplicated sentences detected")
            score -= 0.1

        if platform_limits is None and platforms:
            from backend.content_engine.transformation.platform_formatter import PlatformFormatter
            platform_limits = dict(PlatformFormatter()._platform_limits)
        fit = validate_platform_fit(cleaned, platforms or [], platform_limits or {})
        for platform, report in fit.items():
            limit = report["limit"]
            if limit and report["over_by"] > limit * PLATFORM_OVERFLOW_THRESHOLD:
                issues.append(
                    f"draft exceeds {platform} limit by {report['over_by']} chars "
                    "(heavy truncation loss)"
                )
                score -= 0.2
                break

        score = max(0.0, round(score, 3))
        result = {"passed": score >= self.pass_threshold, "score": score, "issues": issues}
        logger.info("Pipeline verification: %s", result)
        return result
