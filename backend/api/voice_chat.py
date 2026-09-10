from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api import auth
from backend.database import get_db
from backend.models import VoiceCommand, VoiceCommandType, VoiceCommandStatus, ChatMessage, ChatSession, User
from backend.services.voice_chat_service import VoiceChatService

router = APIRouter(prefix="/voice-chat", tags=["Voice & Chat"])


# ==========================================
# Pydantic Schemas
# ==========================================

class VoiceCommandResponse(BaseModel):
    id: int
    transcript: str
    command_type: VoiceCommandType
    intent: Optional[str]
    entities: Optional[Dict[str, Any]]
    confidence: float
    status: VoiceCommandStatus
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    response_text: Optional[str]
    response_audio_url: Optional[str]
    processing_time_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class VoiceCommandCreate(BaseModel):
    transcript: str
    language: str = "en"


class VoiceCommandExecuteRequest(BaseModel):
    command_id: int


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    content_type: str
    context: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    audio_url: Optional[str]
    transcript: Optional[str]
    action_type: Optional[str]
    action_data: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: int
    session_id: str
    title: Optional[str]
    is_active: bool
    context: Optional[Dict[str, Any]]
    current_topic: Optional[str]
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatMessageCreate(BaseModel):
    content: str
    content_type: str = "text"
    context: Optional[Dict[str, Any]] = None


class ChatMessageSend(BaseModel):
    session_id: str
    content: str
    content_type: str = "text"
    context: Optional[Dict[str, Any]] = None


# ==========================================
# Helper
# ==========================================

def get_voice_chat_service(db: Session = Depends(get_db)) -> VoiceChatService:
    return VoiceChatService(db)


# ==========================================
# Voice Commands
# ==========================================

@router.post("/command", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandCreate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
    service: VoiceChatService = Depends(get_voice_chat_service),
):
    """Process a voice command from text transcript."""
    command = await service.process_command(
        user_id=current_user.id,
        transcript=request.transcript,
        language=request.language,
    )
    return VoiceCommandResponse.model_validate(command)


@router.post("/command/audio", response_model=VoiceCommandResponse)
async def process_voice_command_audio(
    file: UploadFile = File(...),
    language: str = Form("en"),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
    service: VoiceChatService = Depends(get_voice_chat_service),
):
    """Process a voice command from audio file (requires speech-to-text)."""
    # TODO: Integrate with speech-to-text service (Whisper, etc.)
    # For now, return placeholder
    raise HTTPException(
        status_code=501,
        detail="Audio processing not yet implemented. Use /command with transcript."
    )


@router.get("/commands", response_model=List[VoiceCommandResponse])
async def list_voice_commands(
    status: Optional[VoiceCommandStatus] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """List user's voice commands."""
    query = db.query(VoiceCommand).filter(VoiceCommand.user_id == current_user.id)
    
    if status:
        query = query.filter(VoiceCommand.status == status)
    
    commands = query.order_by(VoiceCommand.created_at.desc()).limit(limit).all()
    return [VoiceCommandResponse.model_validate(c) for c in commands]


@router.get("/commands/{command_id}", response_model=VoiceCommandResponse)
async def get_voice_command(
    command_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get voice command details."""
    command = db.query(VoiceCommand).filter(
        VoiceCommand.id == command_id,
        VoiceCommand.user_id == current_user.id,
    ).first()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    return VoiceCommandResponse.model_validate(command)


@router.post("/commands/{command_id}/retry", response_model=VoiceCommandResponse)
async def retry_voice_command(
    command_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
    service: VoiceChatService = Depends(get_voice_chat_service),
):
    """Retry a failed voice command."""
    command = db.query(VoiceCommand).filter(
        VoiceCommand.id == command_id,
        VoiceCommand.user_id == current_user.id,
    ).first()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    if command.status != VoiceCommandStatus.FAILED:
        raise HTTPException(status_code=400, detail="Can only retry failed commands")
    
    command = await service.retry_command(command)
    return VoiceCommandResponse.model_validate(command)


# ==========================================
# Chat Sessions
# ==========================================

@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    request: ChatSessionCreate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    import uuid
    session = ChatSession(
        user_id=current_user.id,
        session_id=str(uuid.uuid4()),
        title=request.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionResponse.model_validate(session)


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    active_only: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """List user's chat sessions."""
    query = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)
    
    if active_only:
        query = query.filter(ChatSession.is_active == True)
    
    sessions = query.order_by(ChatSession.updated_at.desc()).limit(limit).all()
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get chat session details."""
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return ChatSessionResponse.model_validate(session)


@router.delete("/chat/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: str,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()


# ==========================================
# Chat Messages
# ==========================================

@router.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    before_id: Optional[int] = Query(None),
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get messages for a chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    query = db.query(ChatMessage).filter(ChatMessage.session_id == session.id)
    
    if before_id:
        query = query.filter(ChatMessage.id < before_id)
    
    messages = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    return [ChatMessageResponse.model_validate(m) for m in reversed(messages)]


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    request: ChatMessageCreate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
    service: VoiceChatService = Depends(get_voice_chat_service),
):
    """Send a message in a chat session."""
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Save user message
    user_message = ChatMessage(
        user_id=current_user.id,
        session_id=session.id,
        role="user",
        content=request.content,
        content_type=request.content_type,
        context=request.context,
    )
    db.add(user_message)
    
    # Update session
    session.message_count += 1
    session.last_message_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user_message)
    
    # Process with AI agent
    assistant_message = await service.process_chat_message(
        session=session,
        user_message=user_message,
    )
    
    return ChatMessageResponse.model_validate(assistant_message)


# ==========================================
# Quick Actions (Voice/Chat shortcuts)
# ==========================================

@router.get("/quick-actions", response_model=List[Dict[str, Any]])
async def get_quick_actions():
    """Get available quick actions for voice/chat interface."""
    return [
        {
            "id": "search_jobs",
            "label": "Search Jobs",
            "description": "Find jobs matching your criteria",
            "examples": [
                "Find Python developer jobs in San Francisco",
                "Search for remote React positions",
                "Show me data science jobs with salary > 100k",
            ],
            "command_type": VoiceCommandType.SEARCH_JOBS,
        },
        {
            "id": "check_applications",
            "label": "Check Applications",
            "description": "View your application status",
            "examples": [
                "Show my pending applications",
                "What's the status of my Google application?",
                "How many interviews do I have this week?",
            ],
            "command_type": VoiceCommandType.CHECK_APPLICATIONS,
        },
        {
            "id": "create_content",
            "label": "Create Content",
            "description": "Create social media content",
            "examples": [
                "Create a LinkedIn post about my new certification",
                "Schedule an Instagram reel for tomorrow",
                "Draft a Twitter thread about career tips",
            ],
            "command_type": VoiceCommandType.CREATE_CONTENT,
        },
        {
            "id": "analyze_resume",
            "label": "Analyze Resume",
            "description": "Get ATS analysis and improvements",
            "examples": [
                "Analyze my resume for ATS",
                "How can I improve my resume for backend roles?",
                "Check if my resume has the right keywords",
            ],
            "command_type": VoiceCommandType.ANALYZE_RESUME,
        },
        {
            "id": "prepare_interview",
            "label": "Interview Prep",
            "description": "Generate interview preparation materials",
            "examples": [
                "Prepare for Amazon software engineer interview",
                "Give me behavioral questions for product manager",
                "What technical questions for data analyst role?",
            ],
            "command_type": VoiceCommandType.PREPARE_INTERVIEW,
        },
        {
            "id": "research_topic",
            "label": "Research Topic",
            "description": "Deep research on career topics",
            "examples": [
                "Research AI trends in 2024",
                "Find salary benchmarks for DevOps engineers",
                "Research company culture at Microsoft",
            ],
            "command_type": VoiceCommandType.RESEARCH_TOPIC,
        },
        {
            "id": "check_analytics",
            "label": "Check Analytics",
            "description": "View content performance analytics",
            "examples": [
                "Show my LinkedIn engagement this month",
                "Which platform has the best ROI?",
                "Top performing posts last week",
            ],
            "command_type": VoiceCommandType.CHECK_ANALYTICS,
        },
        {
            "id": "generate_cover_letter",
            "label": "Generate Cover Letter",
            "description": "Create tailored cover letters",
            "examples": [
                "Write a cover letter for Google SWE role",
                "Generate cover letter for remote position",
                "Create cover letter highlighting my Python experience",
            ],
            "command_type": VoiceCommandType.GENERATE_COVER_LETTER,
        },
    ]


@router.get("/command-types", response_model=List[Dict[str, str]])
async def get_command_types():
    """Get available voice command types."""
    return [
        {"value": ct.value, "label": ct.value.replace("_", " ").title()}
        for ct in VoiceCommandType
    ]