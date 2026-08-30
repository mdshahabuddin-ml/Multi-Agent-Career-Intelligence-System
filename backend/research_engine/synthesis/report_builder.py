from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum as PyEnum
import logging

from backend.research_engine.synthesis.research_synthesizer import SynthesisResult, SynthesizedSection

logger = logging.getLogger(__name__)


class ReportFormat(str, PyEnum):
    """Report output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    PLAIN_TEXT = "plain_text"


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    format: ReportFormat = ReportFormat.MARKDOWN
    include_toc: bool = True
    include_citations: bool = True
    include_methodology: bool = True
    include_limitations: bool = True
    include_evidence_details: bool = False
    max_findings: int = 10
    max_recommendations: int = 10
    custom_css: Optional[str] = None
    template: Optional[str] = None


@dataclass
class GeneratedReport:
    """Generated report with content."""
    research_id: int
    format: ReportFormat
    content: str
    metadata: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    file_size_bytes: int = 0


class ReportBuilder:
    """Build research reports in multiple formats."""

    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()

    def build_report(
        self,
        synthesis: SynthesisResult,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
    ) -> GeneratedReport:
        """Build a report from synthesis results."""
        logger.info(f"Building {self.config.format.value} report for research #{synthesis.research_id if hasattr(synthesis, 'research_id') else 'unknown'}")

        if self.config.format == ReportFormat.MARKDOWN:
            content = self._build_markdown(synthesis, sources, verification_results)
        elif self.config.format == ReportFormat.HTML:
            content = self._build_html(synthesis, sources, verification_results)
        elif self.config.format == ReportFormat.JSON:
            content = self._build_json(synthesis, sources, verification_results)
        elif self.config.format == ReportFormat.PLAIN_TEXT:
            content = self._build_plain_text(synthesis, sources, verification_results)
        else:
            # Default to markdown
            content = self._build_markdown(synthesis, sources, verification_results)

        return GeneratedReport(
            research_id=synthesis.research_id if hasattr(synthesis, 'research_id') else 0,
            format=self.config.format,
            content=content,
            metadata={
                "query": synthesis.query,
                "research_type": synthesis.research_type,
                "confidence": synthesis.confidence,
                "word_count": synthesis.word_count,
                "section_count": len(synthesis.sections),
                "source_count": len(sources),
            },
            file_size_bytes=len(content.encode('utf-8')),
        )

    def _build_markdown(
        self,
        synthesis: SynthesisResult,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
    ) -> str:
        """Build Markdown report."""
        md = []

        # Title
        md.append(f"# {self._generate_title(synthesis)}")
        md.append("")

        # Metadata
        md.append("## Metadata")
        md.append(f"- **Research ID**: {synthesis.research_id if hasattr(synthesis, 'research_id') else 'N/A'}")
        md.append(f"- **Query**: {synthesis.query}")
        md.append(f"- **Research Type**: {synthesis.research_type.replace('_', ' ').title()}")
        md.append(f"- **Generated**: {synthesis.created_at.strftime('%Y-%m-%d %H:%M') if synthesis.created_at else 'N/A'}")
        md.append(f"- **Confidence**: {synthesis.confidence * 100:.0f}%")
        md.append(f"- **Word Count**: ~{synthesis.word_count}")
        md.append("")

        # Table of Contents
        if self.config.include_toc:
            md.append("## Table of Contents")
            md.append("1. [Executive Summary](#executive-summary)")
            md.append("2. [Key Findings](#key-findings)")
            for i, section in enumerate(synthesis.sections, 3):
                anchor = section.title.lower().replace(" ", "-")
                md.append(f"{i}. [{section.title}](#{anchor})")
            md.append(f"{len(synthesis.sections) + 3}. [Recommendations](#recommendations)")
            if self.config.include_methodology:
                md.append(f"{len(synthesis.sections) + 4}. [Methodology](#methodology)")
            if self.config.include_limitations:
                md.append(f"{len(synthesis.sections) + 5}. [Limitations](#limitations)")
            if self.config.include_citations:
                md.append(f"{len(synthesis.sections) + 6}. [Sources & Citations](#sources--citations)")
            md.append("")

        # Executive Summary
        md.append("## Executive Summary")
        md.append(synthesis.executive_summary)
        md.append("")

        # Key Findings
        md.append("## Key Findings")
        for i, finding in enumerate(synthesis.key_findings[:self.config.max_findings], 1):
            md.append(f"{i}. {finding}")
        md.append("")

        # Sections
        for section in synthesis.sections:
            md.append(f"## {section.title}")
            md.append(section.content)
            md.append("")

        # Recommendations
        md.append("## Recommendations")
        for i, rec in enumerate(synthesis.recommendations[:self.config.max_recommendations], 1):
            md.append(f"{i}. {rec}")
        md.append("")

        # Methodology
        if self.config.include_methodology:
            md.append("## Methodology")
            md.append(synthesis.methodology)
            md.append("")

        # Limitations
        if self.config.include_limitations:
            md.append("## Limitations")
            for lim in synthesis.limitations:
                md.append(f"- {lim}")
            md.append("")

        # Sources & Citations
        if self.config.include_citations:
            md.append("## Sources & Citations")
            for i, source in enumerate(sources, 1):
                md.append(f"[{i}] {self._format_citation(source)}")
            md.append("")

        return "\n".join(md)

    def _build_html(
        self,
        synthesis: SynthesisResult,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
    ) -> str:
        """Build HTML report."""
        markdown = self._build_markdown(synthesis, sources, verification_results)

        # Simple markdown to HTML conversion
        html = markdown.replace("\n# ", "\n<h1>").replace("\n## ", "\n<h2>").replace("\n### ", "\n<h3>")
        html = html.replace("\n- ", "\n<li>").replace("\n", "<br>")
        html = html.replace("[", "<sup>[").replace("]", "]</sup>")

        # Wrap in HTML structure
        css = self.config.custom_css or """
        body {font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px 20px; line-height: 1.6;}
        h1 {color: #1a1a2e; border-bottom: 2px solid #4f46e5; padding-bottom: 10px;}
        h2 {color: #2563eb; margin-top: 30px;}
        h3 {color: #4b5563;}
        code {background: #f3f4f6; padding: 2px 6px; border-radius: 4px;}
        pre {background: #1f2937; color: #e5e7eb; padding: 15px; border-radius: 8px; overflow-x: auto;}
        blockquote {border-left: 4px solid #4f46e5; padding-left: 15px; color: #6b7280; margin: 20px 0;}
        table {width: 100%; border-collapse: collapse; margin: 20px 0;}
        th, td {border: 1px solid #e5e7eb; padding: 10px; text-align: left;}
        th {background: #f3f4f6;}
        a {color: #4f46e5;}
        """

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._generate_title(synthesis)}</title>
    <style>{css}</style>
</head>
<body>
{html}
</body>
</html>"""

    def _build_json(
        self,
        synthesis: SynthesisResult,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
    ) -> str:
        """Build JSON report."""
        import json

        report = {
            "metadata": {
                "research_id": synthesis.research_id if hasattr(synthesis, 'research_id') else None,
                "query": synthesis.query,
                "research_type": synthesis.research_type,
                "generated_at": synthesis.created_at.isoformat() if synthesis.created_at else None,
                "confidence": synthesis.confidence,
                "word_count": synthesis.word_count,
            },
            "executive_summary": synthesis.executive_summary,
            "key_findings": synthesis.key_findings,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "confidence": s.confidence,
                    "supporting_claims": s.supporting_claims,
                }
                for s in synthesis.sections
            ],
            "recommendations": synthesis.recommendations,
            "methodology": synthesis.methodology if self.config.include_methodology else None,
            "limitations": synthesis.limitations if self.config.include_limitations else None,
            "sources": sources if self.config.include_citations else None,
            "verification_summary": {
                "total_claims": len(verification_results),
                "verified": sum(1 for v in verification_results if v.get("status") == "verified"),
                "likely": sum(1 for v in verification_results if v.get("status") == "likely"),
                "conflicting": sum(1 for v in verification_results if v.get("status") == "conflicting"),
                "uncertain": sum(1 for v in verification_results if v.get("status") == "uncertain"),
                "rejected": sum(1 for v in verification_results if v.get("status") == "rejected"),
            },
        }

        return json.dumps(report, indent=2, default=str)

    def _build_plain_text(
        self,
        synthesis: SynthesisResult,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
    ) -> str:
        """Build plain text report."""
        lines = []

        lines.append("=" * 80)
        lines.append(self._generate_title(synthesis))
        lines.append("=" * 80)
        lines.append("")

        lines.append(f"Query: {synthesis.query}")
        lines.append(f"Research Type: {synthesis.research_type.replace('_', ' ').title()}")
        lines.append(f"Generated: {synthesis.created_at.strftime('%Y-%m-%d %H:%M') if synthesis.created_at else 'N/A'}")
        lines.append(f"Confidence: {synthesis.confidence * 100:.0f}%")
        lines.append(f"Word Count: ~{synthesis.word_count}")
        lines.append("")

        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        lines.append(synthesis.executive_summary)
        lines.append("")

        lines.append("KEY FINDINGS")
        lines.append("-" * 40)
        for i, finding in enumerate(synthesis.key_findings[:self.config.max_findings], 1):
            lines.append(f"  {i}. {finding}")
        lines.append("")

        for section in synthesis.sections:
            lines.append(section.title.upper())
            lines.append("-" * 40)
            lines.append(section.content)
            lines.append("")

        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)
        for i, rec in enumerate(synthesis.recommendations[:self.config.max_recommendations], 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

        if self.config.include_methodology:
            lines.append("METHODOLOGY")
            lines.append("-" * 40)
            lines.append(synthesis.methodology)
            lines.append("")

        if self.config.include_limitations:
            lines.append("LIMITATIONS")
            lines.append("-" * 40)
            for lim in synthesis.limitations:
                lines.append(f"  - {lim}")
            lines.append("")

        if self.config.include_citations:
            lines.append("SOURCES & CITATIONS")
            lines.append("-" * 40)
            for i, source in enumerate(sources, 1):
                lines.append(f"  [{i}] {self._format_citation(source)}")
            lines.append("")

        return "\n".join(lines)

    def _generate_title(self, synthesis: SynthesisResult) -> str:
        """Generate report title."""
        type_titles = {
            "job_market": "Job Market Analysis Report",
            "company": "Company Intelligence Report",
            "technology": "Technology Trends Report",
            "career_path": "Career Path Analysis Report",
            "skill_analysis": "Skill Gap Analysis Report",
            "salary": "Salary Benchmark Report",
            "interview_prep": "Interview Preparation Report",
            "general": "Research Report",
        }
        base = type_titles.get(synthesis.research_type, "Research Report")
        return f"{base}: {synthesis.query[:80]}"

    def _format_citation(self, source: Dict[str, Any]) -> str:
        """Format source as citation."""
        parts = []

        if source.get("author"):
            parts.append(source["author"])
        elif source.get("domain"):
            parts.append(source["domain"])

        if source.get("title"):
            parts.append(f'"{source["title"]}"')

        if source.get("published_date"):
            try:
                dt = datetime.fromisoformat(source["published_date"].replace("Z", "+00:00"))
                parts.append(dt.strftime("%B %Y"))
            except Exception:
                pass

        parts.append(f"URL: {source.get('url', '')}")

        return ". ".join(parts) + "."

    def build_multi_format(
        self,
        synthesis: SynthesisResult,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
        formats: List[ReportFormat],
    ) -> Dict[ReportFormat, GeneratedReport]:
        """Build report in multiple formats."""
        reports = {}
        original_format = self.config.format

        for fmt in formats:
            self.config.format = fmt
            reports[fmt] = self.build_report(synthesis, sources, verification_results)

        self.config.format = original_format
        return reports