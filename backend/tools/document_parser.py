import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_pdf(file_content: bytes) -> str:
    """Extract text from PDF file."""
    try:
        import pypdf
        pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise ValueError(f"Failed to parse PDF: {e}")


def parse_docx(file_content: bytes) -> str:
    """Extract text from DOCX file."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_content))
        text = ""
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        text += cell.text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX parsing failed: {e}")
        raise ValueError(f"Failed to parse DOCX: {e}")


def parse_text(file_content: bytes) -> str:
    """Extract text from plain text file."""
    try:
        return file_content.decode("utf-8").strip()
    except UnicodeDecodeError:
        try:
            return file_content.decode("latin-1").strip()
        except Exception as e:
            logger.error(f"Text parsing failed: {e}")
            raise ValueError(f"Failed to parse text file: {e}")


def parse_document(file_content: bytes, mime_type: str, filename: str) -> str:
    """Parse document based on mime type or file extension."""
    mime_type = mime_type.lower()
    filename = filename.lower()

    if mime_type == "application/pdf" or filename.endswith(".pdf"):
        return parse_pdf(file_content)
    elif mime_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ] or filename.endswith((".docx", ".doc")):
        return parse_docx(file_content)
    elif mime_type == "text/plain" or filename.endswith(".txt"):
        return parse_text(file_content)
    else:
        raise ValueError(f"Unsupported file type: {mime_type} ({filename})")


def extract_sections(text: str) -> dict:
    """Extract common resume sections from text."""
    import re

    sections = {
        "summary": "",
        "experience": "",
        "education": "",
        "skills": "",
        "projects": "",
        "certifications": "",
        "other": "",
    }

    section_patterns = {
        "summary": [
            r"(?:professional\s+)?summary",
            r"objective",
            r"profile",
            r"about\s+me",
        ],
        "experience": [
            r"experience",
            r"work\s+history",
            r"employment",
            r"professional\s+experience",
        ],
        "education": [
            r"education",
            r"academic\s+background",
            r"qualifications",
        ],
        "skills": [
            r"skills",
            r"technical\s+skills",
            r"competencies",
            r"technologies",
        ],
        "projects": [
            r"projects",
            r"personal\s+projects",
            r"key\s+projects",
        ],
        "certifications": [
            r"certifications",
            r"certificates",
            r"licenses",
        ],
    }

    lines = text.split("\n")
    current_section = "other"
    section_content = {k: [] for k in sections}

    for line in lines:
        line_lower = line.lower().strip()
        matched = False

        for section, patterns in section_patterns.items():
            for pattern in patterns:
                if re.match(rf"^{pattern}[:\s]*$", line_lower):
                    current_section = section
                    matched = True
                    break
            if matched:
                break

        if not matched and line.strip():
            section_content[current_section].append(line)

    for section, content in section_content.items():
        sections[section] = "\n".join(content).strip()

    return sections