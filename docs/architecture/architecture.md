# CareerIntel AI - Architecture Documentation

## System Overview

CareerIntel AI is a modular multi-agent career intelligence platform built with a clean, scalable architecture. The system follows a layered architecture pattern with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│                    React + Vite Frontend                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                               │
│                     FastAPI Backend                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │  Auth   │ │ Resume  │ │  Jobs   │ │Research │ │ Career   │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬─────┘  │
└───────┼────────────┼───────────┼──────────┼─────────┼─────────┘
        │            │           │          │         │
        ▼            ▼           ▼          ▼         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SUPERVISOR LAYER                              │
│         (ResearchSupervisor - Orchestrates Agents)              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Candidate    │    │    Jobs       │    │  Research     │
│  Agents       │    │  Agents       │    │  Agents       │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                   ┌─────────────────┐
                   │   Workflows     │
                   └────────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Tools     │     │     RAG      │     │  Database  │
└─────────────┘     └──────────────┘     └────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   Evidence   │
                   │   Layer      │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Verification │
                   │   Layer      │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  Analysis    │
                   │   Layer      │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  Synthesis   │
                   │   Layer      │
                   └──────────────┘
```

## Component Architecture

### 1. API Gateway Layer (FastAPI)

**Location**: `backend/main.py`, `backend/api/`

**Responsibilities**:
- HTTP request/response handling
- Authentication & authorization
- Request validation & serialization
- Rate limiting & security middleware
- CORS configuration
- OpenAPI documentation generation

**Key Components**:
- `main.py` - Application factory, middleware setup
- `api/auth.py` - JWT authentication endpoints
- `api/resume.py` - Resume CRUD & processing
- `api/jobs.py` - Job search & recommendations
- `api/research.py` - Research workflow management
- `api/career.py` - Career intelligence endpoints
- `api/applications.py` - Application workflow
- `api/evaluation.py` - Evaluation framework
- `api/security.py` - API keys, audit, CSRF

### 2. Service Layer

**Location**: `backend/services/`

**Responsibilities**:
- Business logic orchestration
- Database transaction management
- External API integration
- Agent coordination

**Services**:
- `ResumeService` - Resume upload, parsing, ATS analysis, review
- `JobService` - Job search, normalization, matching, recommendations
- `ResearchService` - Research workflow orchestration
- `CareerService` - Career assessment, goals, learning plans
- `ApplicationService` - Application workflow, cover letters, answers

### 3. Agent Layer

**Location**: `backend/agents/`

**Design Pattern**: Each agent follows a consistent interface with:
- Async execution methods
- Structured input/output dataclasses
- Comprehensive logging
- Error handling with graceful degradation

#### Agent Categories:

**Candidate Agents** (`agents/candidate/`):
- `ProfileAgent` - Orchestrates full candidate pipeline
- `ResumeParserAgent` - Document parsing (PDF, DOCX, TXT)
- `SkillExtractionAgent` - Technical/soft skill extraction
- `ProjectAnalyzerAgent` - Project extraction & analysis
- `ExperienceAnalyzerAgent` - Work history analysis

**Job Agents** (`agents/jobs/`):
- `JobSearchAgent` - Multi-provider job search
- `JobNormalizer` - Standardize job data formats
- `DuplicateDetector` - Identify duplicate postings
- `RequirementExtractor` - Parse job requirements
- `JobMatchingAgent` - Candidate-job matching
- `OpportunityRanker` - Rank & prioritize opportunities

**Research Agents** (`agents/research/`):
- `ResearchSupervisor` - Orchestrates research workflow
- `ResearchPlanner` - Creates research plans
- `WebResearcher` - Web search agent
- `NewsResearcher` - News search agent
- `JobMarketResearcher` - Job market data
- `CompanyResearcher` - Company analysis
- `AcademicResearcher` - Academic paper search
- `EvidenceAgent` - Collect supporting evidence
- `VerificationAgent` - Fact-check claims
- `AnalysisAgent` - Analyze findings
- `SynthesisAgent` - Synthesize insights
- `ReportAgent` - Generate formatted reports

**Career Agents** (`agents/career/`):
- `SkillGapAgent` - Skill gap analysis
- `CareerPathAgent` - Career trajectory planning
- `LearningAgent` - Learning plan generation
- `CareerAdvisor` - Comprehensive career guidance

**Application Agents** (`agents/application/`):
- `ATSResumeAgent` - ATS compatibility analysis
- `ResumeReviewerAgent` - Content quality review
- `CoverLetterAgent` - Personalized cover letters
- `ApplicationAnswerAgent` - Application Q&A generation
- `ApplicationAgent` - Full workflow orchestration

### 4. RAG System (Retrieval-Augmented Generation)

**Location**: `backend/rag/`

**Components**:
- `ingestion/` - Document loaders (Resume, Job, News, Company, Research)
- `embeddings/` - Multi-provider embeddings (OpenAI, HuggingFace, Cohere, Mock)
- `retriever/` - Hybrid retrieval (Vector + BM25)
- `reranker/` - Cross-encoder, LLM, hybrid reranking
- `vector_store/` - Qdrant & in-memory vector stores
- `metadata_filter/` - Advanced filtering (date, source, credibility)
- `citation_manager/` - Inline citation formatting
- `prompts/` - Prompt templates & context building

### 5. Data Layer

**Database**: PostgreSQL with SQLAlchemy ORM

**Models** (`backend/models/`):
- Core: `User`, `Profile`, `Skill`, `Project`, `Experience`
- Resume: `Resume`, `ResumeStatus`
- Jobs: `Job`, `Company`
- Applications: `Application`
- Research: `Research`, `ResearchSource`, `ResearchClaim`, `ResearchEvidence`
- Interview: `Interview`
- Learning: `LearningPlan`
- Notifications: `Notification`

**Migrations**: Alembic (`backend/alembic/`)

### 6. Background Workers

**Location**: `backend/workers/`

**Queue System**: Celery + Redis

**Workers**:
- `research_worker.py` - Research task execution
- `job_worker.py` - Job sync, recommendations, cleanup
- `document_worker.py` - Document processing
- `embedding_worker.py` - Embedding generation
- `notification_worker.py` - Email, push, in-app notifications
- `maintenance.py` - Cleanup, optimization, backups

**Beat Schedule**:
- Job sync: Every 4 hours
- Embedding generation: Every 30 minutes
- Notifications: Every 5 minutes
- Cleanup: Hourly/Daily
- Recommendations update: Hourly

### 7. Security Layer

**Location**: `backend/security/`

**Components**:
- `middleware.py` - Rate limiting, security headers, request validation, CSRF
- `api_keys.py` - API key management (generation, validation, rotation)
- `audit.py` - Structured audit logging
- `config.py` - Security configuration

**Features**:
- JWT authentication (HS256)
- Password hashing (bcrypt)
- Rate limiting (sliding window)
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Input validation (size, depth, array limits)
- API key authentication with scopes
- Comprehensive audit logging

### 8. Evaluation Framework

**Location**: `backend/evaluation/`

**Components**:
- `base.py` - Core evaluation types (MetricType, EvaluationLevel, TestCase, EvaluationSuite)
- `retrieval.py` - Retrieval metrics (Precision@K, Recall@K, MRR, NDCG)
- `research.py` - Research quality & accuracy evaluators
- `generation.py` - RAG generation evaluators (relevance, faithfulness, hallucination)
- `job_matching.py` - Job matching evaluators
- `resume.py` - Resume parsing & scoring evaluators
- `benchmarks.py` - Standardized test cases
- `runner.py` - CLI evaluation runner

## Data Flow

### Resume Processing Flow
```
Upload → Parse → Extract Sections → Extract Skills → 
Analyze Projects → Analyze Experience → ATS Analysis → 
Content Review → Store Results
```

### Job Search Flow
```
Query → Multi-provider Search → Normalize → Deduplicate → 
Extract Requirements → Match to Candidate → Rank → Store/Return
```

### Research Flow
```
Query → Plan (ResearchPlanner) → Execute (Supervisor + Agents) → 
Collect Evidence → Verify Claims → Analyze → Synthesize → 
Generate Report → Store Results
```

### Application Flow
```
Job + Resume + Profile → ATS Analysis → Resume Review → 
Cover Letter → Application Answers → Interview Prep → 
Checklist → Submit Application
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| **API Framework** | FastAPI |
| **Database** | PostgreSQL + SQLAlchemy |
| **Migrations** | Alembic |
| **Task Queue** | Celery + Redis |
| **Vector DB** | Qdrant |
| **Authentication** | JWT (HS256) + bcrypt |
| **Document Parsing** | pypdf, python-docx |
| **Embeddings** | OpenAI, HuggingFace, Cohere |
| **LLM** | OpenAI (GPT-4o-mini) |
| **Frontend** | React + Vite |
| **Testing** | pytest, pytest-asyncio, pytest-cov |
| **Monitoring** | Structured logging, audit trails |

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Load Balancer                           │
│                        (nginx)                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Frontend     │ │  Backend      │ │  Backend      │
│  (React)      │ │  (FastAPI)    │ │  (FastAPI)    │
│               │ │  Instance 1   │ │  Instance 2   │
└───────────────┘ └───────┬───────┘ └───────┬───────┘
                          │                 │
              ┌───────────┴─────────────────┴───────────┐
              ▼                                         ▼
       ┌──────────────┐                        ┌──────────────┐
       │  PostgreSQL  │                        │    Redis     │
       │  (Primary)   │                        │  (Celery +   │
       │              │                        │   Cache)     │
       └──────────────┘                        └──────────────┘
              │
              ▼
       ┌──────────────┐
       │   Qdrant     │
       │ (Vector DB)  │
       └──────────────┘
```

## Scalability Considerations

### Horizontal Scaling
- Stateless FastAPI instances behind load balancer
- Celery workers scale independently per queue
- Read replicas for database queries

### Queue Optimization
- Dedicated queues per workload type
- Priority-based task execution
- Worker prefetch tuning

### Caching Strategy
- Redis for session/cache
- Qdrant for vector similarity
- In-memory for hot data

### Database Optimization
- Connection pooling (SQLAlchemy)
- Indexed queries for common patterns
- Partitioning for large tables (research, applications)

## Security Architecture

### Defense in Depth
1. **Network**: VPC, security groups, WAF
2. **Transport**: TLS 1.3 everywhere
3. **Application**: Rate limiting, input validation, CSP
4. **Data**: Encryption at rest, field-level encryption for PII
5. **Identity**: JWT + API keys, role-based access

### Compliance
- GDPR-ready (data export, deletion)
- SOC 2 aligned logging
- Audit trails for all mutations

## Monitoring & Observability

### Logging
- Structured JSON logging
- Correlation IDs for request tracing
- Audit log for all state changes

### Metrics (Planned)
- Request latency (p50, p95, p99)
- Queue depth & processing time
- Error rates by endpoint
- Agent execution metrics

### Health Checks
- `/health/` - Basic liveness
- `/health/db` - Database connectivity
- Worker status via Celery inspect

## Future Architecture Evolution

### Planned Enhancements
1. **Event-Driven Architecture**: Kafka for async event processing
2. **Multi-Tenancy**: Organization-level isolation
3. **Plugin System**: Custom agent/provider extensions
4. **GraphQL Gateway**: Flexible data querying
5. **Real-time**: WebSocket for live updates
6. **ML Pipeline**: Automated model training/evaluation