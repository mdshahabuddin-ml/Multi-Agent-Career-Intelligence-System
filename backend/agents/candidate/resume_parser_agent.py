import logging
from typing import Optional

from backend.tools.document_parser import parse_document, extract_sections

logger = logging.getLogger(__name__)


class ResumeParserAgent:
    """Agent responsible for parsing resume documents and extracting structured text."""

    def __init__(self):
        self.name = "resume_parser_agent"

    async def parse_resume(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str,
    ) -> dict:
        """
        Parse a resume document and return structured data.

        Returns:
            dict with keys: raw_text, sections, filename, mime_type, file_size
        """
        logger.info(f"Parsing resume: {filename} ({mime_type})")

        try:
            raw_text = parse_document(file_content, mime_type, filename)
            sections = extract_sections(raw_text)

            return {
                "raw_text": raw_text,
                "sections": sections,
                "filename": filename,
                "mime_type": mime_type,
                "file_size": len(file_content),
                "success": True,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Resume parsing failed: {e}")
            return {
                "raw_text": "",
                "sections": {},
                "filename": filename,
                "mime_type": mime_type,
                "file_size": len(file_content),
                "success": False,
                "error": str(e),
            }

    async def parse_multiple_resumes(
        self,
        files: list[dict],
    ) -> list[dict]:
        """Parse multiple resume files."""
        results = []
        for file_info in files:
            result = await self.parse_resume(
                file_info["content"],
                file_info["mime_type"],
                file_info["filename"],
            )
            results.append(result)
        return results