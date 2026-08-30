# Final comprehensive test
from backend.agents.career import (
    SkillGapAgent, CareerPathAgent, LearningAgent, CareerAdvisor,
    SkillCategory, ProficiencyLevel, CandidateSkill, CareerStage
)
from backend.agents.application import (
    ATSResumeAgent, ResumeReviewerAgent, CoverLetterAgent,
    ApplicationAnswerAgent, ApplicationQuestion, QuestionType
)
from backend.agents.candidate import SkillCategory, ProficiencyLevel, CandidateSkill
import asyncio

print('=== COMPREHENSIVE SYSTEM TEST ===')
print()

# Test all career agents
print('1. Testing Career Agents...')
agent = SkillGapAgent()
skills = [
    CandidateSkill('Python', SkillCategory.TECHNICAL, ProficiencyLevel.ADVANCED),
    CandidateSkill('JavaScript', SkillCategory.TECHNICAL, ProficiencyLevel.INTERMEDIATE),
]
result = agent.analyze_skill_gaps(skills, 'software engineer')
print('  SkillGapAgent: OK (match=' + str(result.overall_match_score) + ', gaps=' + str(len(result.gaps)) + ')')

path_agent = CareerPathAgent()
trajectory = path_agent.generate_trajectory(
    current_role='Software Engineer',
    current_skills=['Python', 'JavaScript', 'React'],
    years_experience=3,
)
rp = trajectory.recommended_path
rec = rp.target_role if rp else 'None'
print('  CareerPathAgent: OK (recommended=' + rec + ')')

learning = LearningAgent()
plan = learning.generate_learning_plan(
    user_id=1, target_role='Senior Software Engineer',
    target_skills=['System Design', 'Kubernetes'],
    current_skills=['Python', 'JavaScript'],
    skill_gaps=['System Design', 'Kubernetes'],
    weekly_hours=10,
)
print('  LearningAgent: OK (phases=' + str(len(plan.phases)) + ', weeks=' + str(plan.total_estimated_weeks) + ')')

advisor = CareerAdvisor()
assessment = advisor.assess_career(
    user_id=1, current_role='Software Engineer', years_experience=3,
    skills=[{'name': 'Python', 'category': 'technical', 'proficiency': 'advanced'},
            {'name': 'JavaScript', 'category': 'technical', 'proficiency': 'intermediate'}],
    target_role='Senior Software Engineer',
)
print('  CareerAdvisor: OK (score=' + str(assessment.overall_score) + ', advice=' + str(len(assessment.advice)) + ')')

print()
print('2. Testing Application Agents...')
from backend.agents.application import (
    ATSResumeAgent, ResumeReviewerAgent, CoverLetterAgent,
    ApplicationAnswerAgent, ApplicationQuestion, QuestionType
)
from backend.agents.candidate import SkillCategory, ProficiencyLevel, CandidateSkill

text = '''John Doe
Software Engineer
john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe | github.com/johndoe
SUMMARY
Experienced software engineer with 5 years of experience building scalable web applications.
Led team of 5 developers to deliver e-commerce platform serving 100K+ users.
EXPERIENCE
Senior Developer at TechCorp (2020-2023)
- Built microservices with Python and FastAPI, improving API response time by 40%
- Led migration from monolith to microservices, reducing deployment time by 60%
- Mentored 3 junior developers and established code review processes
SKILLS
Python, JavaScript, TypeScript, React, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git, CI/CD
PROJECTS
E-commerce Platform - Built with React and Django, deployed on AWS'''

ats_agent = ATSResumeAgent()
result = ats_agent.analyze(text, target_role='Senior Software Engineer')
print('  ATSResumeAgent: OK (score=' + str(result.overall_score) + ')')

reviewer = ResumeReviewerAgent()
review = reviewer.review(text, target_role='Senior Software Engineer')
print('  ResumeReviewerAgent: OK (score=' + str(review.overall_score) + ', grade=' + review.grade + ')')

cover_letter_agent = CoverLetterAgent()
from backend.agents.application import CoverLetterContext, CoverLetterTone, CoverLetterLength
cl_context = CoverLetterContext(
    candidate_name='John Doe', candidate_email='john.doe@email.com',
    candidate_phone='(555) 123-4567', candidate_location='San Francisco, CA',
    target_role='Senior Software Engineer', target_company='TechCorp',
    hiring_manager='Jane Smith', key_skills=['Python', 'FastAPI', 'React', 'AWS', 'Kubernetes'],
    key_achievements=['Led team of 5 developers', 'Improved API response time by 40%'],
    years_experience=5, current_role='Senior Developer',
    tone=CoverLetterTone.PROFESSIONAL, length=CoverLetterLength.MEDIUM,
)
cl_result = cover_letter_agent.generate(cl_context)
print('  CoverLetterAgent: OK (words=' + str(cl_result.word_count) + ', personalization=' + str(cl_result.personalization_score) + ')')

answer_agent = ApplicationAnswerAgent()
questions = [
    ApplicationQuestion(question='Tell me about a time you led a challenging project.', question_type=QuestionType.BEHAVIORAL, required=True),
    ApplicationQuestion(question='Why do you want to work at TechCorp?', question_type=QuestionType.MOTIVATION, required=True),
]
profile = {
    'years_experience': 5,
    'skills': [{'name': 'Python', 'category': 'technical', 'proficiency': 'expert'}],
    'achievements': [{'situation': '...', 'task': '...', 'action': '...', 'result': '...'}],
    'target_role': 'Senior Software Engineer',
}
answers = answer_agent.generate_answers(
    [ApplicationQuestion(question='Tell me about a time you led a challenging project.', question_type=QuestionType.BEHAVIORAL, required=True)],
    candidate_profile={'years_experience': 5, 'skills': [{'name': 'Python', 'category': 'technical', 'proficiency': 'expert'}], 'achievements': [{'situation': '...', 'task': '...', 'action': '...', 'result': '...'}], 'target_role': 'Senior Software Engineer'},
    target_role='Senior Software Engineer', target_company='TechCorp'
)
print('  ApplicationAnswerAgent: OK (confidence=' + str(answers.overall_confidence) + ')')

print()
print('=== ALL TESTS PASSED ===')