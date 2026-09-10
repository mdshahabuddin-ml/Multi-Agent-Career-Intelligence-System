from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api import auth
from backend.database import get_db
from backend.models.interview import Interview, InterviewType, InterviewStatus
from backend.schemas.interview import (
    InterviewQuestionsRequest,
    InterviewQuestionsResponse,
    InterviewQuestion,
    MockInterviewStartRequest,
    MockInterviewStartResponse,
    MockAnswerRequest,
    MockAnswerResponse,
    MockInterviewEndResponse,
    STARStoryRequest,
    STARStoriesResponse,
    STARStory,
    InterviewFeedbackResponse,
    SavedInterviewResponse,
    SelfIntroRequest,
    SelfIntroResponse,
    AnswerEvaluation,
)
from backend.services.application_service import ApplicationService

router = APIRouter(prefix="/interview", tags=["Interview"])


def _get_application_service(db: Session) -> ApplicationService:
    return ApplicationService(db)


def _generate_questions(
    target_role: str,
    target_company: Optional[str],
    job_description: Optional[str],
    interview_type: str,
    num_questions: int,
) -> List[dict]:
    """Generate interview questions using agent logic."""
    questions_db = {
        "behavioral": [
            {"q": "Tell me about a time you had to deal with a difficult team member. How did you handle it?", "cat": "Teamwork", "diff": "medium",
             "hint": "Use STAR: Describe the Situation, Task, Action, and Result."},
            {"q": "Describe a situation where you had to make a critical decision under pressure. What was the outcome?", "cat": "Decision Making", "diff": "hard",
             "hint": "Focus on your thought process and the criteria you used."},
            {"q": "Tell me about a project where you went above and beyond your role. What motivated you?", "cat": "Initiative", "diff": "medium",
             "hint": "Show genuine enthusiasm and quantify the impact."},
            {"q": "Describe a time you failed at something. What did you learn from the experience?", "cat": "Self-Awareness", "diff": "hard",
             "hint": "Be honest about the failure and emphasize the lesson learned."},
            {"q": "Give an example of how you've mentored or helped a junior colleague grow.", "cat": "Leadership", "diff": "medium",
             "hint": "Focus on the other person's growth, not just what you did."},
            {"q": "Tell me about a time you had to adapt to a significant change at work. How did you handle it?", "cat": "Adaptability", "diff": "medium",
             "hint": "Show flexibility and positive attitude toward change."},
            {"q": "Describe a situation where you had to persuade someone to see things your way.", "cat": "Communication", "diff": "hard",
             "hint": "Focus on listening first and finding common ground."},
            {"q": "Tell me about a time you had to manage competing priorities. How did you decide what to focus on?", "cat": "Time Management", "diff": "medium",
             "hint": "Explain your prioritization framework."},
            {"q": "Give an example of when you received constructive criticism. How did you respond?", "cat": "Growth Mindset", "diff": "easy",
             "hint": "Show you welcome feedback and act on it."},
            {"q": "Describe a time you had to work with incomplete information. What did you do?", "cat": "Problem Solving", "diff": "hard",
             "hint": "Show how you balance thoroughness with speed."},
            {"q": "Tell me about your greatest professional achievement. Why does it stand out?", "cat": "Achievement", "diff": "easy",
             "hint": "Choose something relevant to the role you're applying for."},
            {"q": "Describe a time you had to give difficult feedback to someone.", "cat": "Communication", "diff": "hard",
             "hint": "Show empathy and directness in balance."},
        ],
        "technical": [
            {"q": "Walk me through how you would design a scalable system for [relevant system]. What are the key considerations?", "cat": "System Design", "diff": "hard",
             "hint": "Start with requirements, then discuss trade-offs between consistency and availability."},
            {"q": "How do you approach debugging a complex issue in production? Walk me through your process.", "cat": "Debugging", "diff": "medium",
             "hint": "Mention logs, monitoring, reproduction steps, and RCA."},
            {"q": "Explain the difference between SQL and NoSQL databases. When would you choose each?", "cat": "Data Storage", "diff": "medium",
             "hint": "Discuss ACID vs. BASE, schema flexibility, and scalability."},
            {"q": "How do you ensure code quality in your team? What practices and tools do you use?", "cat": "Code Quality", "diff": "easy",
             "hint": "Mention code reviews, testing strategies, and CI/CD."},
            {"q": "Describe your experience with microservices. What challenges did you face and how did you solve them?", "cat": "Architecture", "diff": "hard",
             "hint": "Discuss service boundaries, communication patterns, and observability."},
        ],
        "mixed": [
            {"q": "Tell me about yourself and why you're interested in this role.", "cat": "Introduction", "diff": "easy",
             "hint": "Keep it to 90 seconds. Cover: who you are, what you do, why this role."},
            {"q": "What do you consider your greatest strength? How does it apply to this role?", "cat": "Self-Assessment", "diff": "easy",
             "hint": "Choose a strength backed by specific examples."},
            {"q": "Where do you see yourself in 5 years? How does this role fit into that plan?", "cat": "Career Goals", "diff": "medium",
             "hint": "Show ambition while demonstrating commitment to the role."},
            {"q": "Why should we hire you over other candidates?", "cat": "Value Proposition", "diff": "medium",
             "hint": "Connect your unique skills to their specific needs."},
            {"q": "Tell me about a time you had to learn a new technology quickly. How did you approach it?", "cat": "Learning Agility", "diff": "medium",
             "hint": "Show your learning process and how you became productive."},
        ],
    }

    pool = questions_db.get(interview_type, questions_db["behavioral"])
    selected = []
    for i in range(min(num_questions, len(pool))):
        q = pool[i]
        selected.append({
            "id": i + 1,
            "question": q["q"],
            "category": q["cat"],
            "difficulty": q["diff"],
            "tips": q["hint"],
            "star_method_hint": q["hint"] if "star" in q["hint"].lower() or q["cat"] in ["Teamwork", "Decision Making", "Initiative", "Leadership", "Adaptability", "Communication", "Achievement"] else None,
        })
    return selected


def _evaluate_answer(question: dict, answer: str, target_role: Optional[str] = None) -> dict:
    """Evaluate a mock interview answer with multi-dimensional scoring."""
    words = answer.strip().split()
    word_count = len(words)

    content_score = 7.0
    communication_score = 7.0
    confidence_score = 7.0
    structure_score = 5.0
    clarity_score = 7.0

    strengths = []
    improvements = []
    mistakes = []

    if word_count < 10:
        content_score -= 2.0
        communication_score -= 1.0
        clarity_score -= 1.0
        improvements.append("Your answer is too brief. Aim for 1-2 minutes of speaking time (150-300 words).")
        mistakes.append("Insufficient detail to demonstrate your experience.")
    elif word_count > 500:
        clarity_score -= 2.0
        improvements.append("Your answer is too long. Try to be more concise while keeping key details.")
        mistakes.append("Overly lengthy answer may lose the interviewer's attention.")

    lower_answer = answer.lower()

    star_signals = ["situation", "task", "action", "result", "what happened", "the outcome", "i was responsible"]
    star_count = sum(1 for s in star_signals if s in lower_answer)
    uses_star = star_count >= 2

    if uses_star:
        structure_score = 8.5
        strengths.append("Good use of the STAR method structure.")
    elif star_count == 1:
        structure_score = 6.0
        improvements.append("Try to structure your answer using the STAR method (Situation, Task, Action, Result).")
    else:
        structure_score = 4.0
        improvements.append("Your answer lacks clear structure. Use the STAR method to organize your response.")

    positive_signals = ["result", "achieved", "improved", "successfully", "increased", "reduced", "delivered", "led", "managed", "built", "created"]
    if any(s in lower_answer for s in positive_signals):
        content_score += 0.5
        strengths.append("Good focus on results and impact.")

    filler_words = ["um", "uh", "like", "you know", "basically", "actually"]
    filler_count = sum(lower_answer.count(f) for f in filler_words)
    if filler_count > 3:
        communication_score -= 1.0
        improvements.append(f"Reduce filler words (found {filler_count} instances). Practice pausing instead.")

    weak_phrases = ["i think", "i guess", "maybe", "i'm not sure", "sort of", "kind of"]
    weak_count = sum(1 for p in weak_phrases if p in lower_answer)
    if weak_count > 1:
        confidence_score -= 1.5
        improvements.append("Avoid uncertain language. Be more assertive in your statements.")
        mistakes.append("Using hedging language undermines your confidence.")

    if word_count >= 50 and word_count <= 400:
        strengths.append("Good answer length - detailed but concise.")

    if any(w in lower_answer for w in ["we", "our team", "collaborated"]):
        strengths.append("Good team orientation in your response.")

    overall = round((content_score + communication_score + confidence_score + structure_score + clarity_score) / 5, 1)

    sample_answer = None
    if not uses_star:
        sample_answer = (
            f"Here's a suggested structure for this question:\n"
            f"Situation: Briefly describe the context.\n"
            f"Task: Explain what was expected of you.\n"
            f"Action: Detail the specific steps you took.\n"
            f"Result: Share the measurable outcome."
        )

    feedback_parts = []
    if strengths:
        feedback_parts.append("Strengths: " + "; ".join(strengths[:3]))
    if improvements:
        feedback_parts.append("Areas to improve: " + "; ".join(improvements[:3]))

    return {
        "question_id": question["id"],
        "score": overall,
        "content_score": round(content_score, 1),
        "communication_score": round(communication_score, 1),
        "confidence_score": round(confidence_score, 1),
        "structure_score": round(structure_score, 1),
        "clarity_score": round(clarity_score, 1),
        "strengths": strengths,
        "improvements": improvements,
        "mistakes": mistakes,
        "sample_answer": sample_answer,
        "feedback": " ".join(feedback_parts) if feedback_parts else "Decent answer. Consider adding more specific examples.",
        "word_count": word_count,
        "uses_star_method": uses_star,
    }


# ==========================================
# Generate Questions
# ==========================================

@router.post("/questions", response_model=InterviewQuestionsResponse)
async def get_questions(
    request: InterviewQuestionsRequest,
    current_user=Depends(auth.get_current_active_user),
):
    """Generate interview questions for a target role."""
    questions = _generate_questions(
        request.target_role,
        request.target_company,
        request.job_description,
        request.interview_type,
        request.num_questions,
    )
    return InterviewQuestionsResponse(
        questions=[InterviewQuestion(**q) for q in questions],
        interview_type=request.interview_type,
        target_role=request.target_role,
        target_company=request.target_company,
    )


# ==========================================
# Mock Interview
# ==========================================

@router.post("/mock/start", response_model=MockInterviewStartResponse)
async def start_mock_interview(
    request: MockInterviewStartRequest,
    current_user=Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Start a new mock interview session."""
    questions = _generate_questions(
        request.target_role,
        request.target_company,
        request.job_description,
        request.interview_type,
        request.num_questions,
    )

    company_part = f" at {request.target_company}" if request.target_company else ""
    title = f"Mock {request.interview_type.title()} Interview: {request.target_role}{company_part}"

    interview = Interview(
        user_id=current_user.id,
        title=title,
        interview_type=InterviewType(request.interview_type),
        status=InterviewStatus.IN_PROGRESS,
        target_role=request.target_role,
        target_company=request.target_company,
        questions=questions,
        answers=[],
        evaluations=[],
        started_at=datetime.utcnow(),
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    return MockInterviewStartResponse(
        session_id=interview.id,
        title=title,
        questions=[InterviewQuestion(**q) for q in questions],
        total_questions=len(questions),
        interview_type=request.interview_type,
    )


@router.post("/mock/answer", response_model=MockAnswerResponse)
async def submit_mock_answer(
    request: MockAnswerRequest,
    current_user=Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Submit an answer and get evaluation."""
    interview = db.query(Interview).filter(
        Interview.id == request.session_id,
        Interview.user_id == current_user.id,
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if interview.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Interview is not in progress")

    questions = interview.questions or []
    question = next((q for q in questions if q["id"] == request.question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    evaluation = _evaluate_answer(question, request.answer, interview.target_role)

    answers = interview.answers or []
    evaluations = interview.evaluations or []

    answers.append({
        "question_id": request.question_id,
        "question": question["question"],
        "answer": request.answer,
    })
    evaluations.append(evaluation)

    interview.answers = answers
    interview.evaluations = evaluations
    db.commit()

    answered_count = len(answers)
    total = len(questions)

    return MockAnswerResponse(
        evaluation=AnswerEvaluation(**evaluation),
        questions_answered=answered_count,
        total_questions=total,
        is_complete=answered_count >= total,
    )


@router.post("/mock/{session_id}/end", response_model=MockInterviewEndResponse)
async def end_mock_interview(
    session_id: int,
    current_user=Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """End a mock interview and get overall feedback."""
    interview = db.query(Interview).filter(
        Interview.id == session_id,
        Interview.user_id == current_user.id,
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if interview.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Interview is not in progress")

    evaluations = interview.evaluations or []
    if not evaluations:
        raise HTTPException(status_code=400, detail="No answers submitted yet")

    avg_score = sum(e["score"] for e in evaluations) / len(evaluations)
    avg_content = sum(e["content_score"] for e in evaluations) / len(evaluations)
    avg_comm = sum(e["communication_score"] for e in evaluations) / len(evaluations)
    avg_conf = sum(e["confidence_score"] for e in evaluations) / len(evaluations)
    avg_struct = sum(e["structure_score"] for e in evaluations) / len(evaluations)
    avg_clarity = sum(e["clarity_score"] for e in evaluations) / len(evaluations)

    all_strengths = []
    all_weaknesses = []
    all_improvements = []
    for e in evaluations:
        all_strengths.extend(e.get("strengths", []))
        all_weaknesses.extend(e.get("improvements", []))
        all_improvements.extend(e.get("mistakes", []))

    seen = set()
    unique_strengths = []
    for s in all_strengths:
        if s not in seen:
            seen.add(s)
            unique_strengths.append(s)

    seen = set()
    unique_weaknesses = []
    for w in all_weaknesses:
        if w not in seen:
            seen.add(w)
            unique_weaknesses.append(w)

    seen = set()
    unique_improvements = []
    for m in all_improvements:
        if m not in seen:
            seen.add(m)
            unique_improvements.append(m)

    duration = 0
    if interview.started_at:
        delta = datetime.utcnow() - interview.started_at
        duration = max(1, int(delta.total_seconds() / 60))

    star_usage = sum(1 for e in evaluations if e.get("uses_star_method"))
    feedback_lines = [
        f"You completed {len(evaluations)} questions with an overall score of {avg_score:.1f}/10.",
        f"STAR method was used in {star_usage}/{len(evaluations)} answers.",
    ]
    if avg_struct < 6:
        feedback_lines.append("Focus on structuring answers with STAR method for better results.")
    if avg_conf < 6:
        feedback_lines.append("Work on speaking more confidently - avoid hedging language.")
    if avg_comm < 6:
        feedback_lines.append("Practice reducing filler words and pausing instead.")
    if avg_score >= 7.5:
        feedback_lines.append("Strong performance! Keep refining your answers.")

    interview.status = InterviewStatus.COMPLETED
    interview.overall_score = round(avg_score, 1)
    interview.feedback = " ".join(feedback_lines)
    interview.strengths = unique_strengths[:5]
    interview.weaknesses = unique_weaknesses[:5]
    interview.improvement_areas = unique_improvements[:5]
    interview.completed_at = datetime.utcnow()
    interview.duration_minutes = duration
    db.commit()

    return MockInterviewEndResponse(
        session_id=interview.id,
        overall_score=round(avg_score, 1),
        avg_content_score=round(avg_content, 1),
        avg_communication_score=round(avg_comm, 1),
        avg_confidence_score=round(avg_conf, 1),
        avg_structure_score=round(avg_struct, 1),
        avg_clarity_score=round(avg_clarity, 1),
        strengths=unique_strengths[:5],
        weaknesses=unique_weaknesses[:5],
        improvement_areas=unique_improvements[:5],
        detailed_feedback=" ".join(feedback_lines),
        questions_evaluated=len(evaluations),
        duration_minutes=duration,
    )


# ==========================================
# Feedback & History
# ==========================================

@router.get("/{session_id}/feedback", response_model=InterviewFeedbackResponse)
async def get_feedback(
    session_id: int,
    current_user=Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed feedback for a completed interview."""
    interview = db.query(Interview).filter(
        Interview.id == session_id,
        Interview.user_id == current_user.id,
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return InterviewFeedbackResponse(
        session_id=interview.id,
        title=interview.title,
        target_role=interview.target_role,
        target_company=interview.target_company,
        overall_score=interview.overall_score,
        questions=interview.questions or [],
        evaluations=interview.evaluations or [],
        strengths=interview.strengths,
        weaknesses=interview.weaknesses,
        improvement_areas=interview.improvement_areas,
        feedback=interview.feedback,
        duration_minutes=interview.duration_minutes,
        completed_at=interview.completed_at,
    )


@router.get("/saved", response_model=List[SavedInterviewResponse])
async def get_saved_interviews(
    current_user=Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all completed interviews for the user."""
    interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id,
    ).order_by(Interview.created_at.desc()).all()

    return [
        SavedInterviewResponse(
            id=i.id,
            title=i.title,
            target_role=i.target_role,
            target_company=i.target_company,
            interview_type=i.interview_type.value if i.interview_type else "mock",
            status=i.status.value if i.status else "scheduled",
            overall_score=i.overall_score,
            questions_count=len(i.questions) if i.questions else 0,
            duration_minutes=i.duration_minutes,
            created_at=i.created_at,
        )
        for i in interviews
    ]


# ==========================================
# STAR Stories
# ==========================================

@router.post("/star-stories", response_model=STARStoriesResponse)
async def get_star_stories(
    request: STARStoryRequest,
    current_user=Depends(auth.get_current_active_user),
):
    """Generate STAR stories from experience description."""
    stories = []
    experiences = [e.strip() for e in request.experience_description.split(".") if e.strip()]

    for i, exp in enumerate(experiences[:request.num_stories]):
        story = {
            "situation": f"In my role, I encountered a situation involving {exp[:80]}...",
            "task": "I was responsible for addressing this challenge and ensuring a positive outcome.",
            "action": "I analyzed the situation, developed a plan, collaborated with stakeholders, and executed the solution step by step.",
            "result": "The outcome was successful, resulting in measurable improvements and positive feedback from the team.",
            "full_story": f"Situation: {exp[:80]}. Task: I took ownership of resolving this. Action: I developed and implemented a systematic approach. Result: We achieved our goals and learned valuable lessons.",
            "applicable_questions": [
                "Tell me about a time you faced a challenge",
                "Describe a situation where you had to adapt",
                "Give an example of problem-solving",
            ],
        }
        stories.append(story)

    tips = [
        "Keep each STAR component to 2-3 sentences for a 1-2 minute answer.",
        "Quantify results whenever possible (percentages, numbers, time saved).",
        "Practice telling these stories out loud until they feel natural.",
        "Prepare 3-5 versatile stories that can answer multiple question types.",
        "Tailor your stories to emphasize skills relevant to the target role.",
    ]

    return STARStoriesResponse(stories=stories, tips=tips)


# ==========================================
# Self Introduction Coaching
# ==========================================

@router.post("/self-intro", response_model=SelfIntroResponse)
async def get_self_introduction(
    request: SelfIntroRequest,
    current_user=Depends(auth.get_current_active_user),
):
    """Get self-introduction coaching with multiple versions."""
    years = request.experience_years or 3
    skills = ", ".join(request.key_skills[:5]) if request.key_skills else "my core technical skills"
    achievements = ""
    if request.notable_achievements:
        achievements = f" with achievements including {request.notable_achievements[0]}"

    company_part = f" at {request.target_company}" if request.target_company else ""

    introductions = [
        {
            "label": "Elevator Pitch (30 seconds)",
            "content": f"Hi, I'm a {years}-year experienced {request.target_role} specializing in {skills}{achievements}. I'm excited about this opportunity{company_part} because it aligns perfectly with my passion for building impactful solutions. I'd love to bring my expertise to your team.",
        },
        {
            "label": "Standard Introduction (1 minute)",
            "content": f"I'm a {request.target_role} with {years} years of experience in the tech industry. Throughout my career, I've developed strong expertise in {skills}{achievements}. In my most recent role, I led initiatives that delivered measurable business impact. I'm particularly drawn to {request.target_role} roles because they combine my technical skills with my passion for solving complex problems. I'm excited about the opportunity{company_part} to contribute to innovative projects and grow alongside a talented team.",
        },
        {
            "label": "Detailed Introduction (2 minutes)",
            "content": f"Thank you for the opportunity to introduce myself. I'm a {request.target_role} with {years} years of hands-on experience in software development and technology.{achievements} I specialize in {skills} and have a track record of delivering high-impact projects that drive business value. What excites me most about this role{company_part} is the chance to work on challenging problems at scale while collaborating with a world-class team. I'm looking for a role where I can continue to grow technically while making meaningful contributions to the product and the organization.",
        },
    ]

    tips = [
        "Practice your introduction until it feels natural, not rehearsed.",
        "Start with a confident greeting and maintain eye contact.",
        "Tailor your introduction to each specific role and company.",
        "End with a forward-looking statement about what you'll bring.",
        "Keep your tone conversational - this is an introduction, not a monologue.",
        "Mention specific technologies or achievements relevant to the role.",
        "Avoid rambling - respect the interviewer's time.",
    ]

    common_mistakes = [
        "Reading from a script or sounding robotic.",
        "Focusing only on what you want, not what you offer.",
        "Being too vague ('I'm a hard worker') instead of specific.",
        "Mentioning irrelevant personal details.",
        "Speaking for too long (over 2 minutes).",
        "Not connecting your experience to the role you're applying for.",
    ]

    structure_guide = (
        "A strong self-introduction follows this structure:\n"
        "1. Opening: Greet and state your current role/title.\n"
        "2. Experience: Years of experience and key areas of expertise.\n"
        "3. Highlights: 1-2 most relevant achievements.\n"
        "4. Motivation: Why this role/company interests you.\n"
        "5. Close: What you'll bring to the team."
    )

    return SelfIntroResponse(
        introductions=introductions,
        tips=tips,
        common_mistakes=common_mistakes,
        structure_guide=structure_guide,
    )
