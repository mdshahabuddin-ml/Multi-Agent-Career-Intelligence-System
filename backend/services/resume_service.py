import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from backend.agents.candidate import ProfileAgent
from backend.agents.application import ATSResumeAgent, ResumeReviewerAgent
from backend.config import settings
from backend.models import Resume, ResumeStatus, User

logger = logging.getLogger(__name__)

UPLOAD_DIR = "data/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


class ResumeService:
    """Service for resume management and processing."""

    def __init__(self, db: Session):
        self.db = db
        self.profile_agent = ProfileAgent()
        self.ats_agent = ATSResumeAgent()
        self.reviewer_agent = ResumeReviewerAgent()

    def _validate_file(self, file: UploadFile) -> tuple[str, str]:
        """Validate uploaded file and return extension and mime type."""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided",
            )

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        mime_type = file.content_type or "application/octet-stream"
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type {mime_type} not allowed",
            )

        return ext, mime_type

    def _generate_filepath(self, user_id: int, filename: str, ext: str) -> str:
        """Generate unique file path for storage."""
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:50]
        return os.path.join(UPLOAD_DIR, f"user_{user_id}_{timestamp}_{unique_id}_{safe_name}{ext}")

    async def upload_resume(
        self,
        user_id: int,
        file: UploadFile,
        is_primary: bool = False,
    ) -> Resume:
        """Upload and store resume file."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        ext, mime_type = self._validate_file(file)

        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
            )

        filepath = self._generate_filepath(user_id, file.filename, ext)

        with open(filepath, "wb") as f:
            f.write(content)

        if is_primary:
            self.db.query(Resume).filter(
                Resume.user_id == user_id,
                Resume.is_primary == True,
            ).update({Resume.is_primary: False})

        resume = Resume(
            user_id=user_id,
            filename=os.path.basename(filepath),
            original_filename=file.filename,
            file_path=filepath,
            file_size=len(content),
            mime_type=mime_type,
            status=ResumeStatus.UPLOADED,
            is_primary=is_primary,
        )

        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)

        logger.info(f"Resume uploaded: {resume.id} for user {user_id}")
        return resume

    async def parse_resume(self, resume_id: int) -> Resume:
        """Parse uploaded resume and extract structured data."""
        resume = self.db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found",
            )

        resume.status = ResumeStatus.PARSING
        self.db.commit()

        try:
            with open(resume.file_path, "rb") as f:
                file_content = f.read()

            profile_data = await self.profile_agent.process_resume_to_dict(
                file_content, resume.mime_type, resume.original_filename
            )

            resume.raw_text = profile_data["raw_text"]
            resume.parsed_data = profile_data
            resume.sections = profile_data["sections"]
            resume.extracted_skills = [s["name"] for s in profile_data["skills"]]
            resume.extracted_projects = profile_data["projects"]
            resume.extracted_experience = experience.get("entries", [])
            resume.extracted_education = []  # TODO: extract education
            resume.status = ResumeStatus.PARSED

            self.db.commit()
            self.db.refresh(resume)

            logger.info(f"Resume parsed successfully: {resume_id}")
            return resume

        except Exception as e:
            resume.status = ResumeStatus.FAILED
            self.db.commit()
            logger.error(f"Resume parsing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse resume: {str(e)}",
            )

    async def analyze_resume_ats(
        self,
        resume_id: int,
        target_role: Optional[str] = None,
        target_keywords: Optional[list[str]] = None,
    ) -> dict:
        """Analyze resume for ATS compatibility."""
        resume = self.db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found",
            )

        if resume.status != ResumeStatus.PARSED:
            await self.parse_resume(resume_id)
            self.db.refresh(resume)

        ats_result = await self.ats_agent.analyze_resume(
            resume.raw_text or "",
            resume.sections or {},
            target_role=target_role,
            target_keywords=target_keywords,
        )

        resume.ats_score = ats_result["overall_score"]
        resume.ats_feedback = ats_result
        self.db.commit()

        return ats_result

    async def review_resume(self, resume_id: int) -> dict:
        """Comprehensive resume review."""
        resume = self.db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found",
            )

        if resume.status != ResumeStatus.PARSED:
            await self.parse_resume(resume_id)
            self.db.refresh(resume)

        skills = [
            {"name": s, "category": "technical", "confidence": 0.8, "source": "resume"}
            for s in (resume.extracted_skills or [])
        ]

        review_result = await self.reviewer_agent.review_resume(
            resume.raw_text or "",
            resume.sections or {},
            skills,
            resume.extracted_projects or [],
            resume.parsed_data.get("experience", {}) if resume.parsed_data else {},
        )

        return review_result

    async def get_user_resumes(self, user_id: int) -> list[Resume]:
        """Get all resumes for a user."""
        return self.db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.created_at.desc()).all()

    async def get_resume(self, resume_id: int, user_id: int) -> Optional[Resume]:
        """Get specific resume for user."""
        return self.db.query(Resume).filter(
            Resume.id == resume_id,
            Resume.user_id == user_id,
        ).first()

    async def delete_resume(self, resume_id: int, user_id: int) -> bool:
        """Delete resume and file."""
        resume = await self.get_resume(resume_id, user_id)
        if not resume:
            return False

        try:
            if os.path.exists(resume.file_path):
                os.remove(resume.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")

        self.db.delete(resume)
        self.db.commit()
        return True

    async def set_primary_resume(self, resume_id: int, user_id: int) -> Resume:
        """Set resume as primary."""
        resume = await self.get_resume(resume_id, user_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found",
            )

        self.db.query(Resume).filter(
            Resume.user_id == user_id,
            Resume.is_primary == True,
        ).update({Resume.is_primary: False})

        resume.is_primary = True
        self.db.commit()
        self.db.refresh(resume)

        return resume