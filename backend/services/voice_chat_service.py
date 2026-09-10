import logging
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import VoiceCommand, VoiceCommandType, VoiceCommandStatus, ChatMessage, ChatSession, User
from backend.agents.career import CareerAgent
from backend.agents.job import JobSearchAgent
from backend.agents.application import ApplicationAgent

logger = logging.getLogger(__name__)


class VoiceChatService:
    """Service for processing voice commands and chat messages."""

    def __init__(self, db: Session):
        self.db = db
        self.career_agent = CareerAgent()
        self.job_search_agent = JobSearchAgent()
        self.application_agent = ApplicationAgent()

    # Command patterns for intent recognition
    COMMAND_PATTERNS = {
        VoiceCommandType.SEARCH_JOBS: [
            r"(find|search|look for|show me).*(job|position|role)",
            r"(job|position).*(search|find)",
        ],
        VoiceCommandType.CHECK_APPLICATIONS: [
            r"(check|show|view|status).*(application|applied)",
            r"(my|application).*(status|progress)",
            r"how many.*(interview|application)",
        ],
        VoiceCommandType.CREATE_CONTENT: [
            r"(create|make|write|draft).*(post|content|article|reel|story)",
            r"(schedule|post).*(instagram|linkedin|twitter|facebook|youtube|tiktok)",
        ],
        VoiceCommandType.SCHEDULE_CONTENT: [
            r"schedule.*(post|content|reel|story|video)",
            r"post.*(tomorrow|later|at|on)",
        ],
        VoiceCommandType.ANALYZE_RESUME: [
            r"(analyze|check|review|improve).*(resume|cv)",
            r"(ats|score).*(resume|cv)",
            r"resume.*(feedback|suggestions|keywords)",
        ],
        VoiceCommandType.GENERATE_COVER_LETTER: [
            r"(write|generate|create).*(cover letter|coverletter)",
            r"cover letter.*(for|job|position|role)",
        ],
        VoiceCommandType.PREPARE_INTERVIEW: [
            r"(prepare|prep|practice).*(interview)",
            r"interview.*(questions|prep|preparation)",
            r"(behavioral|technical).*(question|interview)",
        ],
        VoiceCommandType.RESEARCH_TOPIC: [
            r"(research|find out|look up).*(topic|trend|salary|company)",
            r"what.*(trend|salary|market).*",
        ],
        VoiceCommandType.CHECK_ANALYTICS: [
            r"(show|check|view).*(analytics|stats|metrics|performance)",
            r"(engagement|views|impressions).*(this|last).*month",
            r"top.*(post|content|performing)",
        ],
        VoiceCommandType.APPLY_JOB: [
            r"apply.*(to|for).*(job|position|role)",
            r"(submit|send).*(application|resume)",
        ],
        VoiceCommandType.NAVIGATE: [
            r"(go to|open|navigate|show).*(dashboard|profile|jobs|resume|calendar|analytics)",
        ],
        VoiceCommandType.SET_REMINDER: [
            r"(remind me|set reminder|alert me).*(to|about|for)",
        ],
        VoiceCommandType.GET_HELP: [
            r"(help|what can you do|commands|features)",
        ],
    }

    async def process_command(
        self,
        user_id: int,
        transcript: str,
        language: str = "en",
    ) -> VoiceCommand:
        """Process a voice command from transcript."""
        start_time = datetime.utcnow()

        # Create command record
        command = VoiceCommand(
            user_id=user_id,
            transcript=transcript,
            language=language,
            status=VoiceCommandStatus.PROCESSING,
        )
        self.db.add(command)
        self.db.commit()
        db.refresh(command)

        try:
            # Recognize intent
            command_type, intent, entities, confidence = self._recognize_intent(transcript)
            
            command.command_type = command_type
            command.intent = intent
            command.entities = entities
            command.confidence = confidence

            # Execute command
            result = await self._execute_command(command, user_id)
            
            command.status = VoiceCommandStatus.COMPLETED
            command.result = result.get("result")
            command.response_text = result.get("response_text")
            command.response_audio_url = result.get("response_audio_url")
            command.executed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Command processing failed: {e}")
            command.status = VoiceCommandStatus.FAILED
            command.error_message = str(e)

        finally:
            command.processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            command.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(command)

        return command

    def _recognize_intent(self, transcript: str) -> tuple:
        """Recognize command intent from transcript."""
        transcript_lower = transcript.lower()
        best_match = VoiceCommandType.UNKNOWN
        best_confidence = 0.0
        best_intent = None
        entities = {}

        for cmd_type, patterns in self.COMMAND_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, transcript_lower, re.IGNORECASE)
                if match:
                    confidence = 0.7 + (len(match.group(0)) / len(transcript)) * 0.3
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = cmd_type
                        best_intent = match.group(0)
                        
                        # Extract entities based on command type
                        entities = self._extract_entities(cmd_type, transcript)

        return best_match, best_intent, entities, best_confidence

    def _extract_entities(self, command_type: VoiceCommandType, transcript: str) -> Dict[str, Any]:
        """Extract entities from transcript based on command type."""
        entities = {}
        transcript_lower = transcript.lower()

        if command_type == VoiceCommandType.SEARCH_JOBS:
            # Extract role
            role_patterns = [
                r"(?:as|for|role|position)\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\s+in|\s+at|\s+with|\s*,|\.|$)",
                r"(?:find|search|show).*?(?:job|position|role).*?(?:in|for)\s+([a-zA-Z\s]+?)(?:\s+with|\s*,|\.|$)",
            ]
            for pattern in role_patterns:
                match = re.search(pattern, transcript_lower)
                if match:
                    entities["role"] = match.group(1).strip()
                    break

            # Extract location
            loc_patterns = [
                r"(?:in|at|location)\s+([a-zA-Z\s,]+?)(?:\s+with|\s*,|\s*\.|$)",
                r"(?:remote|onsite|hybrid)",
            ]
            for pattern in loc_patterns:
                match = re.search(pattern, transcript_lower)
                if match:
                    entities["location"] = match.group(1).strip()
                    break

            # Extract salary
            salary_match = re.search(r"(\$\d+(?:,\d{3})*(?:k)?|\d+k)", transcript_lower)
            if salary_match:
                entities["min_salary"] = salary_match.group(1)

        elif command_type == VoiceCommandType.CREATE_CONTENT:
            # Extract platform
            platforms = ["linkedin", "instagram", "twitter", "facebook", "youtube", "tiktok"]
            for platform in platforms:
                if platform in transcript_lower:
                    entities["platform"] = platform
                    break

            # Extract content type
            content_types = ["post", "reel", "story", "video", "short", "article", "thread"]
            for ct in content_types:
                if ct in transcript_lower:
                    entities["content_type"] = ct
                    break

            # Extract topic
            topic_match = re.search(r"(?:about|on|topic)\s+([a-zA-Z\s]+?)(?:\s+for|\s+tomorrow|\s+today|\.|$)", transcript_lower)
            if topic_match:
                entities["topic"] = topic_match.group(1).strip()

        elif command_type == VoiceCommandType.ANALYZE_RESUME:
            # Extract target role
            role_match = re.search(r"(?:for|target|role)\s+([a-zA-Z\s]+?)(?:\s*,|\.|$)", transcript_lower)
            if role_match:
                entities["target_role"] = role_match.group(1).strip()

        elif command_type == VoiceCommandType.PREPARE_INTERVIEW:
            role_match = re.search(r"(?:for|role|position)\s+([a-zA-Z\s]+?)(?:\s+at|\s+with|\s*,|\.|$)", transcript_lower)
            if role_match:
                entities["target_role"] = role_match.group(1).strip()
            
            company_match = re.search(r"(?:at|with|company)\s+([a-zA-Z\s]+?)(?:\s*,|\.|$)", transcript_lower)
            if company_match:
                entities["target_company"] = company_match.group(1).strip()

        elif command_type == VoiceCommandType.RESEARCH_TOPIC:
            topic_match = re.search(r"(?:research|topic|about|on)\s+([a-zA-Z\s]+?)(?:\s+for|\s*,|\.|$)", transcript_lower)
            if topic_match:
                entities["topic"] = topic_match.group(1).strip()

        return entities

    async def _execute_command(self, command: VoiceCommand, user_id: int) -> Dict[str, Any]:
        """Execute the recognized command."""
        cmd_type = command.command_type
        entities = command.entities or {}

        if cmd_type == VoiceCommandType.SEARCH_JOBS:
            return await self._handle_job_search(user_id, entities)
        elif cmd_type == VoiceCommandType.CHECK_APPLICATIONS:
            return await self._handle_check_applications(user_id)
        elif cmd_type == VoiceCommandType.CREATE_CONTENT:
            return await self._handle_create_content(user_id, entities)
        elif cmd_type == VoiceCommandType.SCHEDULE_CONTENT:
            return await self._handle_schedule_content(user_id, entities)
        elif cmd_type == VoiceCommandType.ANALYZE_RESUME:
            return await self._handle_analyze_resume(user_id, entities)
        elif cmd_type == VoiceCommandType.GENERATE_COVER_LETTER:
            return await self._handle_generate_cover_letter(user_id, entities)
        elif cmd_type == VoiceCommandType.PREPARE_INTERVIEW:
            return await self._handle_prepare_interview(user_id, entities)
        elif cmd_type == VoiceCommandType.RESEARCH_TOPIC:
            return await self._handle_research_topic(user_id, entities)
        elif cmd_type == VoiceCommandType.CHECK_ANALYTICS:
            return await self._handle_check_analytics(user_id)
        elif cmd_type == VoiceCommandType.APPLY_JOB:
            return await self._handle_apply_job(user_id, entities)
        elif cmd_type == VoiceCommandType.NAVIGATE:
            return await self._handle_navigate(entities)
        elif cmd_type == VoiceCommandType.GET_HELP:
            return self._handle_help()
        else:
            return {
                "response_text": "I'm not sure how to help with that. Try asking me to search for jobs, check your applications, create content, analyze your resume, or prepare for an interview.",
                "result": {"action": "help_shown"},
            }

    async def _handle_job_search(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle job search command."""
        role = entities.get("role", "")
        location = entities.get("location", "")
        
        if not role:
            return {
                "response_text": "What type of job are you looking for? For example: 'Find Python developer jobs in San Francisco'",
                "result": {"action": "ask_role"},
            }

        # Use job search agent
        try:
            results = await self.job_search_agent.search_jobs(
                query=role,
                location=location or "remote",
                limit=5,
            )
            
            job_list = "\n".join([
                f"• {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')} - {job.get('location', 'Remote')}"
                for job in results[:5]
            ])
            
            return {
                "response_text": f"I found {len(results)} {role} jobs{f' in {location}' if location else ''}:\n{job_list}\n\nWould you like me to help you apply to any of these?",
                "result": {"action": "jobs_found", "jobs": results[:5]},
            }
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return {
                "response_text": "I had trouble searching for jobs. Please try again or check the Jobs page directly.",
                "result": {"action": "error", "error": str(e)},
            }

    async def _handle_check_applications(self, user_id: int) -> Dict[str, Any]:
        """Handle check applications command."""
        from backend.services.application_service import ApplicationService
        app_service = ApplicationService(self.db)
        apps = app_service.get_user_applications(user_id)
        
        if not apps:
            return {
                "response_text": "You haven't applied to any jobs yet. Would you like me to help you find and apply to jobs?",
                "result": {"action": "no_applications"},
            }
        
        # Group by status
        by_status = {}
        for app in apps:
            status = app.status
            by_status[status] = by_status.get(status, 0) + 1
        
        status_summary = "\n".join([f"• {status.replace('_', ' ').title()}: {count}" for status, count in by_status.items()])
        
        return {
            "response_text": f"You have {len(apps)} total applications:\n{status_summary}\n\nWould you like details on a specific application?",
            "result": {"action": "applications_list", "applications": [{"id": a.id, "job_title": a.job.title if a.job else "Unknown", "status": a.status} for a in apps[:10]]},
        }

    async def _handle_create_content(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle create content command."""
        platform = entities.get("platform", "linkedin")
        content_type = entities.get("content_type", "post")
        topic = entities.get("topic", "")
        
        if not topic:
            return {
                "response_text": f"What would you like to create a {content_type} about on {platform.title()}?",
                "result": {"action": "ask_topic", "platform": platform, "content_type": content_type},
            }
        
        # Generate content using career agent
        try:
            result = await self.career_agent.generate_content(
                topic=topic,
                platform=platform,
                content_type=content_type,
            )
            
            return {
                "response_text": f"I've created a {content_type} for {platform.title()} about '{topic}':\n\n{result.get('content', 'Content generated')}\n\nWould you like me to schedule this or make changes?",
                "result": {"action": "content_created", "content": result, "platform": platform},
            }
        except Exception as e:
            logger.error(f"Content creation failed: {e}")
            return {
                "response_text": "I had trouble creating the content. Please try again.",
                "result": {"action": "error", "error": str(e)},
            }

    async def _handle_schedule_content(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle schedule content command."""
        return {
            "response_text": "Content scheduling is available in the Content Calendar. Would you like me to open it for you?",
            "result": {"action": "navigate_calendar"},
        }

    async def _handle_analyze_resume(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle analyze resume command."""
        return {
            "response_text": "I can analyze your resume for ATS compatibility and provide improvement suggestions. Please upload your resume on the Resume page, then I can run the analysis.",
            "result": {"action": "navigate_resume"},
        }

    async def _handle_generate_cover_letter(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle generate cover letter command."""
        role = entities.get("target_role", "")
        company = entities.get("target_company", "")
        
        if not role or not company:
            return {
                "response_text": "What role and company should I write the cover letter for? Example: 'Write a cover letter for Software Engineer at Google'",
                "result": {"action": "ask_role_company"},
            }
        
        try:
            from backend.services.application_service import ApplicationService
            app_service = ApplicationService(self.db)
            
            # Get user profile
            user = self.db.query(User).filter(User.id == user_id).first()
            candidate_profile = app_service._get_candidate_profile(user_id)
            
            result = app_service.generate_cover_letter(
                user_id=user_id,
                target_role=role,
                target_company=company,
                job_description=f"Position: {role} at {company}",
            )
            
            return {
                "response_text": f"Here's your cover letter for {role} at {company}:\n\n{result.content}\n\nWord count: {result.word_count}\nPersonalization score: {result.personalization_score:.0f}%",
                "result": {"action": "cover_letter_generated", "cover_letter": result.content},
            }
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return {
                "response_text": "I had trouble generating the cover letter. Please try again.",
                "result": {"action": "error", "error": str(e)},
            }

    async def _handle_prepare_interview(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle interview preparation command."""
        role = entities.get("target_role", "")
        company = entities.get("target_company", "")
        
        if not role:
            return {
                "response_text": "What role are you interviewing for? Example: 'Prepare for Software Engineer interview at Amazon'",
                "result": {"action": "ask_role"},
            }
        
        try:
            from backend.services.application_service import ApplicationService
            app_service = ApplicationService(self.db)
            
            result = app_service.prepare_for_interview(
                user_id=user_id,
                target_role=role,
                target_company=company or "the company",
            )
            
            questions = result.get("likely_questions", [])
            question_list = "\n".join([f"• {q.get('question', '')}" for q in questions[:5]])
            
            return {
                "response_text": f"Here's your interview prep for {role}{f' at {company}' if company else ''}:\n\n**Likely Questions:**\n{question_list}\n\n**STAR Stories:** {len(result.get('star_stories', []))} prepared\n**Questions to Ask:** {len(result.get('questions_to_ask', []))} ready",
                "result": {"action": "interview_prep", "prep": result},
            }
        except Exception as e:
            logger.error(f"Interview prep failed: {e}")
            return {
                "response_text": "I had trouble preparing interview materials. Please try again.",
                "result": {"action": "error", "error": str(e)},
            }

    async def _handle_research_topic(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle research topic command."""
        topic = entities.get("topic", "")
        
        if not topic:
            return {
                "response_text": "What topic would you like me to research? Example: 'Research AI trends in 2024' or 'Find salary benchmarks for DevOps engineers'",
                "result": {"action": "ask_topic"},
            }
        
        try:
            from backend.agents.research import ResearchAgent
            research_agent = ResearchAgent()
            
            result = await research_agent.research(
                query=topic,
                user_id=user_id,
            )
            
            return {
                "response_text": f"I've researched '{topic}'. Here's a summary:\n\n{result.get('summary', 'Research completed')[:500]}...\n\nFull report available in Research section.",
                "result": {"action": "research_completed", "research_id": result.get("research_id")},
            }
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return {
                "response_text": "I had trouble with the research. Please try again.",
                "result": {"action": "error", "error": str(e)},
            }

    async def _handle_check_analytics(self, user_id: int) -> Dict[str, Any]:
        """Handle check analytics command."""
        return {
            "response_text": "Your content analytics are available in the Analytics Dashboard. Would you like me to show you the key metrics?",
            "result": {"action": "navigate_analytics"},
        }

    async def _handle_apply_job(self, user_id: int, entities: Dict) -> Dict[str, Any]:
        """Handle apply job command."""
        return {
            "response_text": "To apply to a job, please go to the Jobs page, find the position, and click Apply. I can help you prepare the application materials (resume, cover letter, answers) once you've selected a job.",
            "result": {"action": "navigate_jobs"},
        }

    async def _handle_navigate(self, entities: Dict) -> Dict[str, Any]:
        """Handle navigation command."""
        # Extract page from transcript
        pages = {
            "dashboard": "/dashboard",
            "profile": "/profile",
            "jobs": "/jobs",
            "resume": "/resume",
            "calendar": "/content-calendar",
            "analytics": "/analytics",
            "applications": "/applications",
            "research": "/research",
            "career": "/career",
            "interview": "/interview",
        }
        
        return {
            "response_text": "I can help you navigate. Use the sidebar menu to go to different pages.",
            "result": {"action": "navigate_help", "pages": pages},
        }

    def _handle_help(self) -> Dict[str, Any]:
        """Handle help command."""
        return {
            "response_text": """I'm your CareerIntel AI assistant! Here's what I can help you with:

🎯 **Job Search**: "Find Python developer jobs in San Francisco"
📋 **Applications**: "Check my application status" or "Show pending applications"
📱 **Content**: "Create a LinkedIn post about my promotion" or "Schedule an Instagram reel for tomorrow"
📄 **Resume**: "Analyze my resume for ATS" or "Improve my resume for backend roles"
✍️ **Cover Letters**: "Write a cover letter for Software Engineer at Google"
🎤 **Interview Prep**: "Prepare for Amazon software engineer interview"
🔬 **Research**: "Research AI trends in 2024" or "Find salary benchmarks for DevOps"
📊 **Analytics**: "Show my LinkedIn engagement this month"

Just speak or type naturally - I'll understand!""",
            "result": {"action": "help_shown"},
        }

    async def process_chat_message(
        self,
        session: ChatSession,
        user_message: ChatMessage,
    ) -> ChatMessage:
        """Process a chat message and generate AI response."""
        # Get conversation context
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at).all()
        
        # Build context for AI
        context = {
            "session_topic": session.current_topic,
            "message_history": [
                {"role": m.role, "content": m.content}
                for m in messages[-10:]  # Last 10 messages
            ],
        }
        
        # Process as voice command if it looks like one
        transcript = user_message.content
        command_result = await self._execute_command(
            VoiceCommand(
                user_id=session.user_id,
                transcript=transcript,
                command_type=VoiceCommandType.UNKNOWN,
            ),
            session.user_id,
        )
        
        # Create assistant response
        assistant_message = ChatMessage(
            user_id=session.user_id,
            session_id=session.id,
            role="assistant",
            content=command_result.get("response_text", "I'm not sure how to help with that."),
            content_type="text",
            context=context,
            message_metadata={"command_type": command_result.get("result", {}).get("action")},
        )
        
        self.db.add(assistant_message)
        session.message_count += 1
        session.last_message_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(assistant_message)
        
        return assistant_message

    async def retry_command(self, command: VoiceCommand) -> VoiceCommand:
        """Retry a failed command."""
        command.status = VoiceCommandStatus.PROCESSING
        command.error_message = None
        self.db.commit()
        
        return await self.process_command(
            user_id=command.user_id,
            transcript=command.transcript,
            language=command.language,
        )