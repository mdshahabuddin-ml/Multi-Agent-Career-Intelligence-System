from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime
import asyncio
import logging
import os

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def parse_document_task(self, document_id: int, file_path: str = None):
    """Parse a document and extract text/content."""
    try:
        logger.info(f"Parsing document: {document_id}")
        
        from backend.services.resume_service import ResumeService
        from backend.database import get_db
        from backend.models import Resume
        
        db = next(get_db())
        resume = db.query(Resume).filter(Resume.id == document_id).first()
        
        if not resume:
            raise ValueError(f"Document {document_id} not found")
        
        file_path = file_path or resume.file_path
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        resume_service = ResumeService(db)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            profile_data = loop.run_until_complete(
                resume_service.parse_resume(resume.id)
            )
            
            logger.info(f"Parsed document {document_id}")
            return {"status": "completed", "document_id": document_id}
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Document parsing failed for {document_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def extract_entities_task(self, document_id: int):
    """Extract entities (skills, companies, etc.) from document."""
    try:
        logger.info(f"Extracting entities from document: {document_id}")
        
        from backend.agents.candidate.skill_extraction_agent import SkillExtractionAgent
        from backend.agents.candidate.project_analyzer import ProjectAnalyzerAgent
        from backend.agents.candidate.experience_analyzer import ExperienceAnalyzerAgent
        from backend.database import get_db
        from backend.models import Resume
        
        db = next(get_db())
        resume = db.query(Resume).filter(Resume.id == document_id).first()
        
        if not resume or not resume.raw_text:
            raise ValueError("Document has no text content")
        
        skill_agent = SkillExtractionAgent()
        project_agent = ProjectAnalyzerAgent()
        exp_agent = ExperienceAnalyzerAgent()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            skills = loop.run_until_complete(
                skill_agent.extract_skills(resume.raw_text, {})
            )
            projects = loop.run_until_complete(
                project_agent.analyze_projects(resume.raw_text, {})
            )
            experience = loop.run_until_complete(
                exp_agent.analyze_experience(resume.raw_text, {})
            )
            
            # Update resume with extracted entities
            resume.extracted_skills = [s["name"] for s in skills]
            resume.extracted_projects = projects
            resume.extracted_experience = experience
            from backend.database import get_db
            db = next(get_db())
            db.commit()
            
            logger.info(f"Extracted entities for document {document_id}")
            return {
                "status": "completed",
                "skills_count": len(skills),
                "projects_count": len(projects),
                "experience_count": len(experience.get("entries", []))
            }
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Entity extraction failed for document {document_id}: {exc}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def extract_resume_sections_task(self, document_id: int):
    """Extract structured sections from resume."""
    try:
        logger.info(f"Extracting sections from resume: {document_id}")
        
        from backend.tools.document_parser import extract_sections
        from backend.database import get_db
        from backend.models import Resume
        
        db = next(get_db())
        resume = db.query(Resume).filter(Resume.id == document_id).first()
        
        if not resume or not resume.raw_text:
            raise ValueError("Document has no text content")
        
        sections = extract_sections(resume.raw_text)
        resume.sections = sections
        db.commit()
        
        logger.info(f"Extracted sections for document {document_id}")
        return {"status": "completed", "sections": list(sections.keys())}
        
    except Exception as exc:
        logger.error(f"Section extraction failed for document {document_id}: {exc}")
        raise


@shared_task
def cleanup_old_documents():
    """Clean up old temporary document files."""
    logger.info("Cleaning up old document files")
    
    from backend.database import get_db
    from backend.models import Resume
    from datetime import datetime, timedelta
    import os
    
    db = next(get_db())
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    # Find old temporary files
    old_resumes = db.query(Resume).filter(
        Resume.status == "failed",
        Resume.created_at < datetime.utcnow() - timedelta(days=7)
    ).all()
    
    cleaned = 0
    for resume in old_resumes:
        try:
            if resume.file_path and os.path.exists(resume.file_path):
                os.remove(resume.file_path)
                cleaned += 1
        except Exception as e:
            logger.error(f"Failed to remove file for resume {resume.id}: {e}")
    
    db.commit()
    
    logger.info(f"Cleaned up {cleaned} old document files")
    return {"status": "completed", "cleaned_count": cleaned}