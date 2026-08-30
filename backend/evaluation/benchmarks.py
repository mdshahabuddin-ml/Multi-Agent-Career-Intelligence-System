from typing import Dict, List, Any
from backend.evaluation.base import TestCase, EvaluationLevel


RESEARCH_BENCHMARKS = [
    TestCase(
        test_case_id="research_001",
        name="Company Research - Tech Company",
        description="Research a technology company for interview preparation",
        level=EvaluationLevel.END_TO_END,
        input_data={
            "query": "Research Microsoft's culture, recent projects, and interview process for software engineering roles",
            "research_type": "company",
            "target_company": "Microsoft",
            "target_role": "Software Engineer",
            "max_sources": 10,
        },
        expected_output={
            "ground_truth_facts": [
                {"text": "Microsoft was founded in 1975"},
                {"text": "Microsoft headquarters is in Redmond, Washington"},
                {"text": "Azure is Microsoft's cloud platform"},
            ],
            "expected_claims": [
                "Microsoft has a strong engineering culture",
                "Microsoft offers competitive compensation",
                "Microsoft invests heavily in AI research",
            ],
            "relevant_documents": [
                "https://careers.microsoft.com",
                "https://www.microsoft.com/en-us/research",
                "https://news.microsoft.com",
            ],
        },
        evaluation_criteria=[
            {"metric": "source_count", "threshold": 0.7},
            {"metric": "citation_quality", "threshold": 0.6},
            {"metric": "verification_rate", "threshold": 0.7},
            {"metric": "confidence_score", "threshold": 0.7},
            {"metric": "completeness", "threshold": 0.7},
        ],
        tags=["company_research", "tech", "interview_prep"],
    ),
    TestCase(
        test_case_id="research_002",
        name="Market Research - AI Job Market",
        description="Research current AI/ML job market trends",
        level=EvaluationLevel.END_TO_END,
        input_data={
            "query": "What are the current trends in AI/ML job market for 2024? Salary ranges, in-demand skills, top hiring companies",
            "research_type": "market",
            "target_role": "Machine Learning Engineer",
            "max_sources": 15,
        },
        expected_output={
            "ground_truth_facts": [
                {"text": "Machine learning engineer salaries range from $120k to $200k+"},
                {"text": "Python, PyTorch, TensorFlow are top required skills"},
                {"text": "Generative AI skills are in high demand"},
            ],
            "expected_claims": [
                "AI job market is growing rapidly",
                "Remote work options are common",
                "Advanced degrees are often preferred",
            ],
            "relevant_documents": [
                "https://www.linkedin.com/jobs/machine-learning-engineer-jobs",
                "https://www.indeed.com/career/machine-learning-engineer/salaries",
                "https://aiindex.stanford.edu",
            ],
        },
        evaluation_criteria=[
            {"metric": "source_count", "threshold": 0.7},
            {"metric": "citation_quality", "threshold": 0.6},
            {"metric": "verification_rate", "threshold": 0.7},
            {"metric": "confidence_score", "threshold": 0.7},
            {"metric": "source_diversity", "threshold": 0.5},
        ],
        tags=["market_research", "ai_ml", "salary"],
    ),
    TestCase(
        test_case_id="research_003",
        name="Skill Gap Analysis",
        description="Analyze skill gaps for career transition",
        level=EvaluationLevel.END_TO_END,
        input_data={
            "query": "What skills do I need to transition from frontend developer to full-stack developer?",
            "research_type": "skill_gap",
            "target_role": "Full Stack Developer",
        },
        expected_output={
            "ground_truth_facts": [
                {"text": "Backend languages include Node.js, Python, Go, Java"},
                {"text": "Database knowledge (SQL, NoSQL) is required"},
                {"text": "API design and REST/GraphQL are essential"},
            ],
            "expected_claims": [
                "Full-stack developers need both frontend and backend skills",
                "Cloud platform experience is valuable",
                "DevOps basics are increasingly expected",
            ],
        },
        evaluation_criteria=[
            {"metric": "completeness", "threshold": 0.7},
            {"metric": "coherence", "threshold": 0.6},
            {"metric": "verification_rate", "threshold": 0.6},
        ],
        tags=["skill_gap", "career_transition", "fullstack"],
    ),
]


RAG_BENCHMARKS = [
    TestCase(
        test_case_id="rag_001",
        name="Technical Question Answering",
        description="Answer a technical question using retrieved documents",
        level=EvaluationLevel.COMPONENT,
        input_data={
            "query": "How does React's useEffect hook work and when should you use it?",
            "retrieved_documents": [
                {
                    "id": "doc1",
                    "content": "useEffect is a React hook that lets you perform side effects in function components. It runs after every render by default.",
                    "url": "https://react.dev/reference/react/useEffect"
                },
                {
                    "id": "doc2",
                    "content": "useEffect takes a callback function and optional dependency array. Empty array means run once on mount.",
                    "url": "https://react.dev/learn/synchronizing-with-effects"
                },
            ]
        },
        expected_output={
            "answer": "React's useEffect hook lets you perform side effects in function components. It runs after renders, with an optional dependency array to control when it executes. Use it for data fetching, subscriptions, or DOM manipulation.",
            "relevant_documents": ["doc1", "doc2"],
        },
        evaluation_criteria=[
            {"metric": "relevance", "threshold": 0.7},
            {"metric": "faithfulness", "threshold": 0.8},
            {"metric": "hallucination_rate", "threshold": 0.9},
            {"metric": "citation_accuracy", "threshold": 0.7},
        ],
        tags=["technical_qa", "react", "hooks"],
    ),
    TestCase(
        test_case_id="rag_002",
        name="Career Advice Generation",
        description="Generate career advice based on retrieved resume and job data",
        level=EvaluationLevel.COMPONENT,
        input_data={
            "query": "Based on my React and Node.js experience, what roles should I target?",
            "retrieved_documents": [
                {
                    "id": "doc1",
                    "content": "Full Stack Developer roles require React, Node.js, databases, and API design skills.",
                    "url": "internal://job_desc/1"
                },
                {
                    "id": "doc2",
                    "content": "Frontend Architect roles focus on React ecosystem, performance, and team leadership.",
                    "url": "internal://job_desc/2"
                },
            ]
        },
        expected_output={
            "answer": "Based on your React and Node.js experience, you should target Full Stack Developer roles which require both frontend and backend skills. You could also consider Frontend Architect roles if you want to specialize.",
            "relevant_documents": ["doc1", "doc2"],
        },
        evaluation_criteria=[
            {"metric": "relevance", "threshold": 0.7},
            {"metric": "faithfulness", "threshold": 0.8},
            {"metric": "completeness", "threshold": 0.6},
        ],
        tags=["career_advice", "job_matching"],
    ),
    TestCase(
        test_case_id="rag_003",
        name="Interview Question Answering",
        description="Answer behavioral interview question using STAR method",
        level=EvaluationLevel.COMPONENT,
        input_data={
            "query": "Tell me about a time you solved a difficult technical problem",
            "retrieved_documents": [
                {
                    "id": "doc1",
                    "content": "STAR method: Situation, Task, Action, Result. Structure behavioral answers with these four components.",
                    "url": "internal://interview_guide/star"
                },
                {
                    "id": "doc2",
                    "content": "Example: Reduced API latency by 50% by implementing caching and query optimization. Situation: high latency. Task: improve performance. Action: added Redis cache, optimized SQL. Result: 50% improvement.",
                    "url": "internal://interview_examples/backend_perf"
                },
            ]
        },
        expected_output={
            "answer": "Using the STAR method: Situation - our API had high latency affecting users. Task - needed to reduce response times. Action - implemented Redis caching and optimized database queries. Result - achieved 50% latency reduction.",
            "relevant_documents": ["doc1", "doc2"],
        },
        evaluation_criteria=[
            {"metric": "relevance", "threshold": 0.7},
            {"metric": "faithfulness", "threshold": 0.8},
            {"metric": "coherence", "threshold": 0.7},
        ],
        tags=["interview_prep", "behavioral", "star_method"],
    ),
]


JOB_MATCHING_BENCHMARKS = [
    TestCase(
        test_case_id="job_match_001",
        name="Software Engineer Job Matching",
        description="Match jobs for a Python/React developer",
        level=EvaluationLevel.END_TO_END,
        input_data={
            "query": "Python React developer jobs",
            "user_profile": {
                "skills": ["Python", "React", "JavaScript", "PostgreSQL", "Docker", "AWS"],
                "experience_years": 3,
                "preferred_location": "San Francisco",
                "prefers_remote": True,
                "min_salary": 130000,
            }
        },
        expected_output={
            "relevant_jobs": [
                "job_001", "job_002", "job_003", "job_004", "job_005"
            ],
        },
        evaluation_criteria=[
            {"metric": "precision@5", "threshold": 0.5},
            {"metric": "recall@5", "threshold": 0.5},
            {"metric": "mrr", "threshold": 0.5},
            {"metric": "skill_match_quality", "threshold": 0.6},
            {"metric": "location_match", "threshold": 0.7},
            {"metric": "salary_match", "threshold": 0.5},
        ],
        tags=["job_matching", "fullstack", "python", "react"],
    ),
    TestCase(
        test_case_id="job_match_002",
        name="Senior ML Engineer Matching",
        description="Match senior ML engineer roles",
        level=EvaluationLevel.END_TO_END,
        input_data={
            "query": "Senior machine learning engineer positions",
            "user_profile": {
                "skills": ["Python", "PyTorch", "TensorFlow", "MLOps", "Kubernetes", "GCP"],
                "experience_years": 6,
                "preferred_location": "Remote",
                "prefers_remote": True,
                "min_salary": 180000,
            }
        },
        expected_output={
            "relevant_jobs": [
                "job_ml_001", "job_ml_002", "job_ml_003"
            ],
        },
        evaluation_criteria=[
            {"metric": "precision@3", "threshold": 0.5},
            {"metric": "recall@3", "threshold": 0.5},
            {"metric": "mrr", "threshold": 0.5},
            {"metric": "skill_match_quality", "threshold": 0.7},
            {"metric": "location_match", "threshold": 0.8},
        ],
        tags=["job_matching", "ml", "senior", "remote"],
    ),
]


RESUME_BENCHMARKS = [
    TestCase(
        test_case_id="resume_001",
        name="Senior Developer Resume Parsing",
        description="Parse a senior software engineer resume",
        level=EvaluationLevel.COMPONENT,
        input_data={
            "resume_text": """
            JOHN DOE
            Senior Software Engineer | San Francisco, CA | john.doe@email.com | (555) 123-4567
            LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

            EXPERIENCE
            Senior Software Engineer | TechCorp Inc. | 2021-Present
            - Led team of 5 engineers building scalable microservices
            - Architected migration from monolith to microservices using Go and Kubernetes
            - Reduced deployment time by 80% through CI/CD pipeline improvements
            - Technologies: Go, Kubernetes, PostgreSQL, Redis, gRPC, AWS

            Software Engineer | StartupXYZ | 2018-2021
            - Built full-stack web applications using React, Node.js, and MongoDB
            - Implemented real-time features using WebSockets
            - Designed RESTful APIs serving 100k+ daily requests
            - Technologies: React, Node.js, MongoDB, Express, Docker

            EDUCATION
            BS Computer Science | Stanford University | 2018
            - GPA: 3.8/4.0
            - Relevant coursework: Distributed Systems, Algorithms, Databases

            SKILLS
            Languages: Go, Python, JavaScript, TypeScript, SQL
            Frameworks: React, Node.js, Express, Gin, gRPC
            Infrastructure: Kubernetes, Docker, AWS, Terraform, CI/CD
            Databases: PostgreSQL, MongoDB, Redis
            """,
        },
        expected_output={
            "skills": ["Go", "Python", "JavaScript", "TypeScript", "SQL", "React", "Node.js", "Express", "Gin", "gRPC", "Kubernetes", "Docker", "AWS", "Terraform", "PostgreSQL", "MongoDB", "Redis"],
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "TechCorp Inc.",
                    "location": "San Francisco, CA",
                    "description": "Led team of 5 engineers building scalable microservices. Architected migration from monolith to microservices using Go and Kubernetes. Reduced deployment time by 80% through CI/CD pipeline improvements.",
                },
                {
                    "title": "Software Engineer",
                    "company": "StartupXYZ",
                    "location": "San Francisco, CA",
                    "description": "Built full-stack web applications using React, Node.js, and MongoDB. Implemented real-time features using WebSockets. Designed RESTful APIs serving 100k+ daily requests.",
                },
            ],
            "education": [
                {
                    "degree": "BS Computer Science",
                    "institution": "Stanford University",
                    "field_of_study": "Computer Science",
                    "graduation_year": "2018",
                },
            ],
            "contact_info": {
                "email": "john.doe@email.com",
                "phone": "(555) 123-4567",
                "linkedin": "linkedin.com/in/johndoe",
                "github": "github.com/johndoe",
            },
            "sections": {
                "experience": True,
                "education": True,
                "skills": True,
                "contact": True,
            },
        },
        evaluation_criteria=[
            {"metric": "skill_extraction_accuracy", "threshold": 0.7},
            {"metric": "experience_extraction_accuracy", "threshold": 0.6},
            {"metric": "education_extraction_accuracy", "threshold": 0.7},
            {"metric": "contact_info_accuracy", "threshold": 0.8},
            {"metric": "section_detection_completeness", "threshold": 0.7},
        ],
        tags=["resume_parsing", "senior", "fullstack"],
    ),
    TestCase(
        test_case_id="resume_002",
        name="Entry Level Resume Parsing",
        description="Parse an entry-level developer resume",
        level=EvaluationLevel.COMPONENT,
        input_data={
            "resume_text": """
            JANE SMITH
            Junior Software Developer | New York, NY | jane.smith@email.com
            LinkedIn: linkedin.com/in/janesmith

            EDUCATION
            BS Computer Science | NYU | 2023
            - GPA: 3.6/4.0
            - Projects: Built a task management app with React/Node.js
            - Hackathon winner: 1st place at NYU Hackathon 2022

            EXPERIENCE
            Software Engineering Intern | BigTech Co. | Summer 2022
            - Developed internal tools using Python and Django
            - Wrote unit tests achieving 90% code coverage
            - Collaborated with senior engineers on code reviews

            PROJECTS
            Task Manager App | React, Node.js, PostgreSQL
            - Full-stack application for task management
            - Implemented authentication, CRUD operations, real-time updates

            SKILLS
            Languages: Python, JavaScript, TypeScript, SQL
            Frameworks: React, Django, Express
            Tools: Git, Docker, VS Code
            """,
        },
        expected_output={
            "skills": ["Python", "JavaScript", "TypeScript", "SQL", "React", "Django", "Express", "Git", "Docker"],
            "experience": [
                {
                    "title": "Software Engineering Intern",
                    "company": "BigTech Co.",
                    "description": "Developed internal tools using Python and Django. Wrote unit tests achieving 90% code coverage. Collaborated with senior engineers on code reviews.",
                },
            ],
            "education": [
                {
                    "degree": "BS Computer Science",
                    "institution": "NYU",
                    "field_of_study": "Computer Science",
                    "graduation_year": "2023",
                },
            ],
            "contact_info": {
                "email": "jane.smith@email.com",
                "linkedin": "linkedin.com/in/janesmith",
            },
            "sections": {
                "experience": True,
                "education": True,
                "skills": True,
                "projects": True,
                "contact": True,
            },
        },
        evaluation_criteria=[
            {"metric": "skill_extraction_accuracy", "threshold": 0.7},
            {"metric": "experience_extraction_accuracy", "threshold": 0.6},
            {"metric": "education_extraction_accuracy", "threshold": 0.7},
            {"metric": "contact_info_accuracy", "threshold": 0.8},
        ],
        tags=["resume_parsing", "entry_level", "intern"],
    ),
]


ALL_BENCHMARKS = {
    "research": RESEARCH_BENCHMARKS,
    "rag": RAG_BENCHMARKS,
    "job_matching": JOB_MATCHING_BENCHMARKS,
    "resume": RESUME_BENCHMARKS,
}


def get_benchmarks(category: str = None) -> List[TestCase]:
    """Get benchmark test cases for a category or all."""
    if category:
        return ALL_BENCHMARKS.get(category, [])
    all_cases = []
    for cases in ALL_BENCHMARKS.values():
        all_cases.extend(cases)
    return all_cases