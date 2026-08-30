import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import weasyprint for PDF generation
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("weasyprint not available - PDF export will return HTML bytes")


@dataclass
class ResearchReport:
    """Final research report."""
    research_id: int
    query: str
    research_type: str
    title: str
    executive_summary: str
    key_findings: List[str]
    detailed_findings: List[Dict[str, Any]]
    recommendations: List[str]
    methodology: str
    limitations: List[str]
    sources: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    confidence: float
    generated_at: datetime = field(default_factory=datetime.utcnow)
    word_count: int = 0
    page_count: int = 0


class ReportAgent:
    """Generate final research reports in multiple formats."""

    def __init__(self):
        self.name = "report_agent"

    async def generate_report(
        self,
        research_id: int,
        query: str,
        research_type: str,
        synthesis_result: Dict[str, Any],
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
    ) -> ResearchReport:
        """Generate comprehensive research report."""
        logger.info(f"Generating report for research #{research_id}")

        report = ResearchReport(
            research_id=research_id,
            query=query,
            research_type=research_type,
            title=self._generate_title(query, research_type),
            executive_summary=synthesis_result.get("executive_summary", ""),
            key_findings=synthesis_result.get("key_findings", []),
            detailed_findings=synthesis_result.get("detailed_findings", []),
            recommendations=synthesis_result.get("recommendations", []),
            methodology=synthesis_result.get("methodology", ""),
            limitations=synthesis_result.get("limitations", []),
            sources=self._format_sources(sources),
            citations=self._generate_citations(sources, verification_results),
            confidence=synthesis_result.get("confidence", 0.5),
        )

        # Calculate word count
        report.word_count = self._calculate_word_count(report)
        report.page_count = max(1, report.word_count // 350)

        return report

    def _generate_title(self, query: str, research_type: str) -> str:
        """Generate report title."""
        type_titles = {
            "job_market": "Job Market Analysis",
            "company": "Company Intelligence Report",
            "technology": "Technology Trends Report",
            "career_path": "Career Path Analysis",
            "skill_analysis": "Skill Gap Analysis",
            "salary": "Salary Benchmark Report",
            "interview_prep": "Interview Preparation Research",
            "general": "Research Report",
        }
        base = type_titles.get(research_type, "Research Report")
        return f"{base}: {query[:80]}"

    def _format_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources for report."""
        formatted = []
        for i, source in enumerate(sources):
            formatted.append({
                "index": i + 1,
                "title": source.get("title", "Untitled"),
                "url": source.get("url", ""),
                "source_type": source.get("source_type", "web"),
                "domain": source.get("domain", ""),
                "author": source.get("author", ""),
                "published_date": source.get("published_date", ""),
                "credibility": source.get("credibility", 0),
                "relevance": source.get("relevance", 0),
                "snippet": source.get("snippet", "")[:200],
            })
        return formatted

    def _generate_citations(
        self,
        sources: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate citations linking claims to sources."""
        citations = []

        for i, source in enumerate(sources):
            # Find claims supported by this source
            supporting_claims = []
            for v in verification_results:
                if v.get("status") in ["verified", "likely"]:
                    claim_evidence = v.get("evidence", [])
                    for e in claim_evidence:
                        if e.get("source_url") == source.get("url"):
                            supporting_claims.append(v.get("claim_text", "")[:100])

            citations.append({
                "source_index": i + 1,
                "source_title": source.get("title", "Untitled"),
                "source_url": source.get("url", ""),
                "source_type": source.get("source_type", "web"),
                "supporting_claims": supporting_claims[:3],
                "citation_format": self._format_citation(source, i + 1),
            })

        return citations

    def _format_citation(self, source: Dict[str, Any], index: int) -> str:
        """Format citation in standard format."""
        parts = []

        if source.get("author"):
            parts.append(source["author"])
        elif source.get("domain"):
            parts.append(source["domain"])

        if source.get("title"):
            parts.append(f'"{source["title"]}"')

        if source.get("published_date"):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(source["published_date"].replace("Z", "+00:00"))
                parts.append(dt.strftime("%B %Y"))
            except Exception:
                pass

        parts.append(f"URL: {source.get('url', '')}")

        return f"[{index}] " + ". ".join(parts) + "."

    def _calculate_word_count(self, report: ResearchReport) -> int:
        """Calculate approximate word count."""
        count = len(report.executive_summary.split())
        count += sum(len(f.split()) for f in report.key_findings)
        count += sum(len(str(f).split()) for f in report.detailed_findings)
        count += sum(len(r.split()) for r in report.recommendations)
        count += len(report.methodology.split())
        count += sum(len(l.split()) for l in report.limitations)
        return count

    async def export_markdown(self, report: ResearchReport) -> str:
        """Export report as Markdown."""
        md = [
            f"# {report.title}",
            f"\n**Research ID:** {report.research_id}  ",
            f"**Query:** {report.query}  ",
            f"**Type:** {report.research_type.replace('_', ' ').title()}  ",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M')}  ",
            f"**Confidence:** {report.confidence * 100:.0f}%  ",
            f"**Word Count:** ~{report.word_count}  ",
            "\n---\n",
            "## Executive Summary",
            report.executive_summary,
            "\n## Key Findings",
        ]

        for i, finding in enumerate(report.key_findings, 1):
            md.append(f"{i}. {finding}")

        md.append("\n## Detailed Findings")
        for finding in report.detailed_findings:
            md.append(f"\n### {finding.get('claim', 'Finding')}")
            md.append(f"**Status:** {finding.get('status', 'N/A').title()}  ")
            md.append(f"**Confidence:** {finding.get('confidence', 0) * 100:.0f}%  ")
            md.append(f"**Supporting Sources:** {finding.get('supporting_sources', 0)}  ")
            if finding.get("key_evidence"):
                md.append("\n**Key Evidence:**")
                for ev in finding["key_evidence"]:
                    md.append(f"- {ev.get('source_title', 'Source')}: {ev.get('snippet', '')[:150]}...")

        md.append("\n## Recommendations")
        for i, rec in enumerate(report.recommendations, 1):
            md.append(f"{i}. {rec}")

        md.append("\n## Methodology")
        md.append(report.methodology)

        md.append("\n## Limitations")
        for lim in report.limitations:
            md.append(f"- {lim}")

        md.append("\n## Sources & Citations")
        for citation in report.citations:
            md.append(f"\n{citation['citation_format']}")

        return "\n".join(md)

    async def export_html(self, report: ResearchReport) -> str:
        """Export report as HTML."""
        markdown = await self.export_markdown(report)
        # Simple markdown to HTML conversion (in production, use a proper library)
        html = markdown.replace("\n## ", "\n<h2>").replace("\n### ", "\n<h3>")
        html = html.replace("\n", "<br>")
        html = f"<html><head><title>{report.title}</title><style>body {{font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;}}</style></head><body>{html}</body></html>"
        return html

    async def export_pdf(self, report: ResearchReport) -> bytes:
        """Export report as PDF using weasyprint."""
        html = await self.export_html(report)
        
        if WEASYPRINT_AVAILABLE:
            # Generate PDF using weasyprint
            html_doc = HTML(string=html)
            css = CSS(string="""
                @page {
                    margin: 2cm;
                    @top-center { content: element(title); }
                    @bottom-center { content: counter(page); }
                }
                body { font-family: 'DejaVu Sans', Arial, sans-serif; line-height: 1.6; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 30px; }
                h3 { color: #7f8c8d; }
                .metadata { color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px; }
                .key-findings li { margin-bottom: 8px; }
                .detailed-finding { margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
                .recommendations li { margin-bottom: 10px; }
                .limitations li { color: #e74c3c; }
                .citation { font-size: 0.85em; color: #555; margin-bottom: 10px; }
            """)
            pdf_bytes = html_doc.write_pdf(stylesheets=[css])
            return pdf_bytes
        else:
            # Fallback - return HTML bytes with note
            logger.warning("weasyprint not available - returning HTML as PDF fallback")
            return html.encode('utf-8')