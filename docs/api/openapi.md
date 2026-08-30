# CareerIntel AI - API Documentation

## Overview

This document provides comprehensive API documentation for the CareerIntel AI backend. The API is built with FastAPI and provides automatic OpenAPI/Swagger documentation.

## Base URL

```
Development: http://localhost:8000
Production:  https://api.careerintel.ai
```

## Authentication

All protected endpoints require JWT Bearer token authentication:

```
Authorization: Bearer <access_token>
```

### Token Acquisition

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Response
{
  "user": {...},
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## API Endpoints

### Authentication (`/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login and get JWT token | No |
| GET | `/auth/me` | Get current user info | Yes |

#### Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

#### Get Current User
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

### Resume Management (`/resume`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/resume/upload` | Upload resume file | Yes |
| POST | `/resume/{id}/parse` | Parse resume content | Yes |
| POST | `/resume/{id}/ats` | ATS compatibility analysis | Yes |
| POST | `/resume/{id}/review` | Comprehensive resume review | Yes |
| GET | `/resume/` | List user resumes | Yes |
| GET | `/resume/{id}` | Get resume details | Yes |
| DELETE | `/resume/{id}` | Delete resume | Yes |
| POST | `/resume/{id}/primary` | Set as primary resume | Yes |

#### Upload Resume
```bash
curl -X POST http://localhost:8000/resume/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@resume.pdf" \
  -F "is_primary=true"
```

#### Parse Resume
```bash
curl -X POST http://localhost:8000/resume/1/parse \
  -H "Authorization: Bearer <token>"
```

#### ATS Analysis
```bash
curl -X POST http://localhost:8000/resume/1/ats \
  -H "Authorization: Bearer <token>" \
  -F "target_role=software engineer" \
  -F "target_keywords=python,react,aws"
```

#### Resume Review
```bash
curl -X POST http://localhost:8000/resume/1/review \
  -H "Authorization: Bearer <token>"
```

### Job Search (`/jobs`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/jobs/search` | Search jobs from external sources | No |
| GET | `/jobs/search` | Search saved jobs with filters | No |
| GET | `/jobs/recommendations` | Personalized job recommendations | Yes |
| GET | `/jobs/stats` | Job market statistics | No |
| GET | `/jobs/` | List jobs with pagination | No |
| GET | `/jobs/{id}` | Get job details | No |
| POST | `/jobs/{id}/save` | Save job for later | Yes |
| GET | `/jobs/saved` | Get user's saved jobs | Yes |

#### Search Jobs
```bash
curl -X POST http://localhost:8000/jobs/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python developer",
    "location": "San Francisco",
    "remote": true,
    "limit": 20
  }'
```

#### Get Recommendations
```bash
curl -X GET http://localhost:8000/jobs/recommendations \
  -H "Authorization: Bearer <token>" \
  -G --data-urlencode "limit=10"
```

### Research (`/research`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/research/start` | Start new research task | Yes |
| GET | `/research/{id}/status` | Get research status | Yes |
| GET | `/research/{id}` | Get completed report | Yes |
| GET | `/research/` | List user research | Yes |
| POST | `/research/{id}/cancel` | Cancel running research | Yes |
| GET | `/research/{id}/sources` | Get research sources | Yes |
| GET | `/research/{id}/citations` | Get research citations | Yes |

#### Start Research
```bash
curl -X POST http://localhost:8000/research/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI job market trends 2024",
    "research_type": "job_market",
    "target_role": "Machine Learning Engineer",
    "target_location": "San Francisco",
    "max_sources": 10,
    "timeout_seconds": 300
  }'
```

#### Check Status
```bash
curl -X GET http://localhost:8000/research/1/status \
  -H "Authorization: Bearer <token>"
```

### Career Intelligence (`/career`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/career/assess` | Comprehensive career assessment | Yes |
| POST | `/career/goals` | Create career goal | Yes |
| GET | `/career/goals` | List career goals | Yes |
| POST | `/career/goals/{id}/progress` | Update goal progress | Yes |
| GET | `/career/job-search-strategy` | Get job search strategy | Yes |
| GET | `/career/skill-recommendations` | Get skill recommendations | Yes |
| GET | `/career/path-options` | Get career path options | Yes |
| GET | `/career/learning-resources` | Get learning resources | Yes |
| POST | `/career/learning-plan` | Create learning plan | Yes |
| GET | `/career/insights` | Get career insights | Yes |

#### Career Assessment
```bash
curl -X POST http://localhost:8000/career/assess \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_role": "Software Engineer",
    "years_experience": 5,
    "skills": [
      {"name": "Python", "proficiency": "advanced"},
      {"name": "React", "proficiency": "advanced"}
    ],
    "target_role": "Senior Software Engineer",
    "weekly_learning_hours": 10
  }'
```

### Applications (`/applications`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/applications/prepare` | Prepare complete application | Yes |
| POST | `/applications/ats/analyze` | ATS analysis | Yes |
| POST | `/applications/resume/review` | Resume review | Yes |
| POST | `/applications/resume/optimize` | Resume optimization | Yes |
| POST | `/applications/cover-letter` | Generate cover letter | Yes |
| POST | `/applications/cover-letter/optimize` | Cover letter optimization | Yes |
| POST | `/applications/answers` | Generate application answers | Yes |
| POST | `/applications/interview-prep` | Interview preparation | Yes |
| POST | `/applications/` | Submit application | Yes |
| GET | `/applications/` | List applications | Yes |
| GET | `/applications/{id}` | Get application details | Yes |
| PATCH | `/applications/{id}` | Update application status | Yes |
| DELETE | `/applications/{id}` | Withdraw application | Yes |
| GET | `/applications/stats` | Application statistics | Yes |
| GET | `/applications/stats/insights` | Application insights | Yes |

#### Prepare Application
```bash
curl -X POST http://localhost:8000/applications/prepare \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "resume_text": "John Doe\nSenior Software Engineer...",
    "candidate_profile": {
      "name": "John Doe",
      "email": "john@example.com",
      "years_experience": 8,
      "key_skills": ["Python", "React", "AWS"]
    },
    "job_description": "We need a Senior Software Engineer...",
    "cover_letter_tone": "professional"
  }'
```

#### Generate Cover Letter
```bash
curl -X POST http://localhost:8000/applications/cover-letter \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "target_role": "Senior Software Engineer",
    "target_company": "Google",
    "job_description": "We need...",
    "hiring_manager": "Jane Smith",
    "tone": "professional",
    "length": "medium"
  }'
```

#### Generate Application Answers
```bash
curl -X POST http://localhost:8000/applications/answers \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "questions": [
      "Tell me about a challenging project",
      "Why do you want to work here?"
    ],
    "target_role": "Senior Software Engineer",
    "target_company": "Google"
  }'
```

### Evaluation (`/evaluation`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/evaluation/benchmarks` | List benchmarks | Yes |
| GET | `/evaluation/benchmarks/categories` | List categories | Yes |
| GET | `/evaluation/evaluators` | List evaluators | Yes |
| POST | `/evaluation/run` | Run evaluation | Yes |
| POST | `/evaluation/run/async` | Run async evaluation | Yes |
| GET | `/evaluation/tasks/{id}` | Get task status | Yes |
| GET | `/evaluation/results/{id}` | Get results | Yes |
| POST | `/evaluation/custom` | Run custom evaluation | Yes |
| GET | `/evaluation/history` | Evaluation history | Yes |

#### Run Evaluation
```bash
curl -X POST http://localhost:8000/evaluation/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "research",
    "mock_outputs": true
  }'
```

### Security (`/security`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/security/scopes` | List API key scopes | Yes |
| POST | `/security/api-keys` | Create API key | Yes |
| GET | `/security/api-keys` | List API keys | Yes |
| GET | `/security/api-keys/{id}` | Get API key | Yes |
| PATCH | `/security/api-keys/{id}` | Update API key | Yes |
| DELETE | `/security/api-keys/{id}` | Revoke API key | Yes |
| POST | `/security/api-keys/{id}/rotate` | Rotate API key | Yes |
| GET | `/security/status` | Security status (admin) | Yes |
| GET | `/security/csrf-token` | Get CSRF token | Yes |

#### Create API Key
```bash
curl -X POST http://localhost:8000/security/api-keys \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "scopes": ["read", "research", "jobs"],
    "expires_in_days": 90
  }'
```

### Health Check (`/health`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/health/` | Basic health check | No |
| GET | `/health/db` | Database connectivity | No |

```bash
curl -X GET http://localhost:8000/health/
curl -X GET http://localhost:8000/health/db
```

## Rate Limiting

API requests are rate limited:
- **Default**: 100 requests per minute per IP
- **Burst**: 20 requests per 10 seconds
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Error Responses

Standard error format:
```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `202` - Accepted (async)
- `204` - No Content
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

## API Key Authentication

For server-to-server communication, use API keys:

```bash
curl -X GET http://localhost:8000/jobs/search \
  -H "X-API-Key: ci_<your_api_key>"
```

Or with Bearer token:
```bash
curl -X GET http://localhost:8000/jobs/search \
  -H "Authorization: Bearer ci_<your_api_key>"
```

## Webhooks (Coming Soon)

Future support for webhook notifications:
- Job application status changes
- Research completion
- New job matches
- Interview scheduling

## SDKs

Official SDKs available:
- **Python**: `pip install careerintel-sdk`
- **JavaScript/TypeScript**: `npm install @careerintel/sdk`

## Support

- **Documentation**: https://docs.careerintel.ai
- **API Status**: https://status.careerintel.ai
- **Support**: support@careerintel.ai
- **GitHub**: https://github.com/careerintel/careerintel-ai