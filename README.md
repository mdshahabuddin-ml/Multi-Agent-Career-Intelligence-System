# Multi-Agent Career Intelligence System (CareerIntel AI)

An AI-powered career intelligence platform built with a modular multi-agent architecture. The system provides end-to-end career guidance including resume analysis, job matching, market research, interview preparation, and application tracking.

## 🎯 Vision

Build a production-oriented AI-powered career intelligence platform that:

1. **Understands the candidate** - Parse resumes, extract skills, projects, experience
2. **Understands the job market** - Research companies, technologies, industry trends
3. **Matches intelligently** - Search, normalize, and rank job opportunities
4. **Identifies gaps** - Skill gap analysis and career path recommendations
5. **Generates materials** - ATS-optimized resumes, cover letters, application answers
6. **Prepares for interviews** - Mock interviews with evaluation and feedback
7. **Conducts research** - Multi-agent research with evidence verification and citations
8. **Tracks everything** - Application tracking and career analytics

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│                    React + Vite Frontend                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        API GATEWAY                           │
│                     FastAPI Backend                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SUPERVISOR AGENT                          │
│         (Orchestrates all specialized agents)               │
└─────────────────────────┬───────────────────────────────────┘
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Candidate │    │   Jobs   │    │ Research │
    │ Agents   │    │ Agents   │    │ Agents   │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                  ┌────────────┐
                  │ Workflows  │
                  └─────┬──────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
      ┌────────┐  ┌──────────┐  ┌──────────┐
      │ Tools  │  │   RAG    │  │Database  │
      └────────┘  └──────────┘  └──────────┘
                        │
                        ▼
                 ┌────────────┐
                 │ Evidence   │
                 │  Layer     │
                 └─────┬──────┘
                       │
                       ▼
                 ┌────────────┐
                 │Verification│
                 │  Layer     │
                 └─────┬──────┘
                       │
                       ▼
                 ┌────────────┐
                 │ Analysis   │
                 │  Layer     │
                 └─────┬──────┘
                       │
                       ▼
                 ┌────────────┐
                 │ Synthesis  │
                 │  Layer     │
                 └────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.12+ (for local backend development)

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd careerintel-ai

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec backend python backend/database_init.py

# Access services
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Database: postgresql://careerintel:careerintel@localhost:5432/careerintel
```

### Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r ../requirements.txt

# Set environment variables
cp ../.env.example ../.env
# Edit .env with your API keys

# Start PostgreSQL (via Docker)
docker run -d \
  --name careerintel-postgres \
  -e POSTGRES_USER=careerintel \
  -e POSTGRES_PASSWORD=careerintel \
  -e POSTGRES_DB=careerintel \
  -p 5432:5432 \
  postgres:16-alpine

# Initialize database
python database_init.py

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 📁 Project Structure

```
careerintel-ai/
│
├── README.md
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── dashboard/
│   │   │   ├── profile/
│   │   │   ├── resume/
│   │   │   ├── jobs/
│   │   │   ├── research/
│   │   │   ├── career/
│   │   │   ├── interview/
│   │   │   ├── applications/
│   │   │   └── analytics/
│   │   │
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── utils/
│   │   ├── routes/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── nginx.conf
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── database_init.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── profile.py
│   │   ├── jobs.py
│   │   ├── research.py
│   │   ├── news.py
│   │   ├── resume.py
│   │   ├── career.py
│   │   ├── interview.py
│   │   ├── applications.py
│   │   ├── dashboard.py
│   │   └── health.py
│   │
│   ├── agents/
│   │   ├── supervisor/
│   │   ├── candidate/
│   │   ├── research/
│   │   ├── jobs/
│   │   ├── career/
│   │   ├── application/
│   │   └── interview/
│   │
│   ├── workflows/
│   ├── research_engine/
│   ├── rag/
│   ├── tools/
│   ├── models/
│   ├── services/
│   ├── evaluation/
│   ├── workers/
│   └── utils/
│
├── data/
├── generated/
├── tests/
└── docs/
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | Multi-Agent Career Intelligence System |
| `APP_ENV` | Environment (development/production) | development |
| `DEBUG` | Debug mode | true |
| `BACKEND_HOST` | Backend host | 0.0.0.0 |
| `BACKEND_PORT` | Backend port | 8000 |
| `DATABASE_URL` | PostgreSQL connection string | postgresql://careerintel:careerintel@localhost:5432/careerintel |
| `SECRET_KEY` | JWT secret key | (required) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry | 60 |
| `OPENAI_API_KEY` | OpenAI API key | (required for AI features) |
| `FRONTEND_URL` | Frontend URL for CORS | http://localhost:5173 |
| `QDRANT_URL` | Qdrant vector database URL | http://localhost:6333 |
| `REDIS_URL` | Redis URL for task queue | redis://localhost:6379/0 |

## 📚 API Documentation

Once the backend is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | Login and get JWT token |
| `/auth/me` | GET | Get current user info |
| `/profile` | GET/PUT | Get/update user profile |
| `/resume/upload` | POST | Upload and parse resume |
| `/jobs/search` | POST | Search jobs |
| `/jobs/match` | POST | Match jobs to profile |
| `/research/start` | POST | Start research task |
| `/career/analyze` | POST | Career analysis |
| `/interview/mock` | POST | Start mock interview |

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm run test

# Run with coverage
pytest --cov=backend --cov-report=html
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Database only
docker-compose up -d postgres

# Run backend tests in container
docker-compose exec backend pytest -v
```

## 📦 Production Deployment

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Or build production images
docker build -t careerintel-backend:latest .
docker build -t careerintel-frontend:latest ./frontend
```

### Production Checklist

- [ ] Set strong `SECRET_KEY` in `.env`
- [ ] Configure `OPENAI_API_KEY` and other API keys
- [ ] Use managed PostgreSQL (RDS, Cloud SQL)
- [ ] Use managed Redis (ElastiCache, Cloud Memorystore)
- [ ] Use managed Qdrant or vector database
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy for database
- [ ] Set up CI/CD pipeline

## 🧩 Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ | Development Environment Setup |
| 2 | 🔄 | Database Foundation |
| 3 | ⏳ | Authentication |
| 4 | ⏳ | Candidate Intelligence |
| 5 | ⏳ | Resume Intelligence |
| 6 | ⏳ | Job Intelligence |
| 7 | ⏳ | Multi-Agent Research System |
| 8 | ⏳ | Research Engine |
| 9 | ⏳ | RAG System |
| 10 | ⏳ | Career Intelligence |
| 11 | ⏳ | Application Intelligence |
| 12 | ⏳ | Interview Intelligence |
| 13 | ⏳ | Frontend Integration |
| 14 | ⏳ | Dashboard |
| 15 | ⏳ | Workers |
| 16 | ⏳ | Evaluation |
| 17 | ⏳ | Testing |
| 18 | ⏳ | Security |
| 19 | ⏳ | Observability |
| 20 | ⏳ | Production Docker |
| 21 | ⏳ | Documentation |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- LangChain & LangGraph for agent orchestration
- Qdrant for vector search
- React & Vite for the frontend
- All open-source contributors

---

**Built with ❤️ for career intelligence**