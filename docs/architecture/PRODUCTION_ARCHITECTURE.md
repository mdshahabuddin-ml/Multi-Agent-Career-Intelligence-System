# Multi-Agent Career Intelligence System - Production Architecture

## Architecture Overview

This document describes the production architecture that supports evolution from Final Year Project → MVP → Business Product → Scalable SaaS Platform.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PRODUCTION ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐  │
│  │   FRONTEND   │────│  API GATEWAY / LB    │────│     FASTAPI SERVICES     │  │
│  │  (React)     │    │   (nginx/Traefik)    │    │      (FastAPI)           │  │
│  └──────────────┘    └──────────────────────┘    └───────────┬──────────────┘  │
│                                                               │                 │
│                    ┌──────────────────────────────────────────┘                 │
│                    ▼                                                            │
│           ┌───────────────────────┐                                             │
│           │  AGENT ORCHESTRATION  │                                             │
│           │  (ResearchOrchestrator)                                            │
│           └───────────┬───────────┘                                             │
│                       │                                                         │
│        ┌──────────────┼──────────────┬──────────────┐                          │
│        ▼              ▼              ▼              ▼                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                  │
│  │  Research  │ │  Career    │ │  Job       │ │  Application               │  │
│  │  Agents    │ │  Agents    │ │  Agents    │ │  Agents                  │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘                  │
│                       │                                                         │
│                       ▼                                                         │
│           ┌───────────────────────┐                                             │
│           │      TASK QUEUE       │                                             │
│           │      (Celery/Redis)   │                                             │
│           └───────────┬───────────┘                                             │
│                       │                                                         │
│        ┌──────────────┼──────────────┐                          ┌────────────┐  │
│        ▼              ▼              ▼                          │  EXTERNAL  │  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │  PROVIDERS │  │
│  │ Research │ │Document  │ │Embedding │                        │            │  │
│  │ Worker   │ │Worker    │ │Worker    │                        │ • OpenAI   │  │
│  └──────────┘ └──────────┘ └──────────┘                        │ • Anthropic│  │
│        │              │              │                          │ • Google   │  │
│        │              │              │                          │ • Tavily   │  │
│        ▼              ▼              ▼                          │ • Serper   │  │
│ ┌────────────────────────────────────────────────────────────────────────────┐│
│ │                         DATA LAYER                                          ││
│ │  ┌────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────────────────┐ ││
│ │  │ PostgreSQL │ │ Vector DB   │ │ Object     │ │ Redis                  │ │
│ │  │ (Primary)  │ │ (pgvector/  │ │ Storage    │ │ (Cache/Queue/Session)  │ │
│ │  │            │ │  Weaviate)  │ │ (S3/MinIO) │ │                        │ │
│ │  └────────────┘ └─────────────┘ └────────────┘ └────────────────────────┘ ││
│ └────────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Status

| Layer | Component | Status | Details |
|-------|-----------|--------|---------|
| **Frontend** | React/Vite SPA | ✅ Complete | 20+ pages, context/state management, API services |
| **API Gateway** | nginx + docker-compose | ✅ Complete | Rate limiting, SSL termination, routing |
| **API Services** | FastAPI (20 routers) | ✅ Complete | Auth, Research, Jobs, Career, Resume, etc. |
| **Agent Orchestration** | ResearchOrchestrator | ✅ Complete | 11-phase pipeline, LLM-enhanced agents |
| **Task Queue** | Celery + Redis | ✅ Complete | 8 workers, priority queues, retry logic |
| **Workers** | 8 specialized workers | ✅ Complete | Research, Document, Embedding, Job, etc. |
| **PostgreSQL** | SQLAlchemy + Alembic | ✅ Complete | 20 models, migrations, relationships |
| **Vector DB** | pgvector/Weaviate ready | ✅ Ready | Vector store, embeddings, retrieval |
| **Object Storage** | S3/MinIO ready | ✅ Ready | Document parser, upload handling |
| **External Providers** | 13 providers | ✅ Complete | 8 LLM + 5 Search, with fallbacks |

## Evolution Path

### Phase 1: Final Year Project (Current)
- Single-server deployment
- SQLite/PostgreSQL local
- In-memory Redis
- Mock providers for testing
- Basic monitoring

### Phase 2: MVP (Next)
- Docker Compose production stack
- PostgreSQL + pgvector
- Redis Cluster
- Real provider APIs (OpenAI, Tavily)
- Basic logging/metrics (Prometheus/Grafana)
- CI/CD pipeline

### Phase 3: Business Product
- Kubernetes deployment
- Horizontal pod autoscaling
- Multi-region PostgreSQL
- Weaviate/Pinecone vector DB
- S3/MinIO object storage
- Advanced monitoring (Datadog/ELK)
- Rate limiting per tenant

### Phase 4: Scalable SaaS Platform
- Multi-tenant architecture
- API Gateway (Kong/Traefik)
- Service mesh (Istio/Linkerd)
- Event-driven architecture (Kafka)
- Multi-region active-active
- Advanced security (WAF, DDoS)
- Cost optimization (Spot instances, auto-scaling)

## Deployment Configurations

### Docker Compose (MVP)
```yaml
# docker-compose.yml
services:
  frontend:
    build: ./frontend
    ports: ["80:80"]
    
  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    deploy:
      replicas: 3
      
  celery_worker:
    build: ./backend
    command: celery -A backend.workers.celery_app worker -Q research,document,embedding
    deploy:
      replicas: 5
      
  postgres:
    image: pgvector/pgvector:pg16
    volumes: ["pgdata:/var/lib/postgresql/data"]
    
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
```

### Kubernetes (Business Product+)
```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: career-intel-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: career-intel-api
  template:
    spec:
      containers:
      - name: api
        image: career-intel/api:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: career-intel-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: career-intel-api
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Data Flow

```
User Request → API Gateway → FastAPI Router → Service Layer → Agent Orchestration
                                                                  ↓
                                                    Task Queue (Celery) → Workers
                                                                  ↓
                                                    Data Layer (PostgreSQL + Vector DB + Redis + S3)
                                                                  ↓
                                                    External Providers (LLM/Search)
                                                                  ↓
                                                    Response → Client
```

## Security Architecture

| Layer | Implementation |
|-------|----------------|
| **Network** | VPC, Security Groups, Private Subnets |
| **Transport** | TLS 1.3, mTLS (service mesh) |
| **Application** | JWT Auth, Rate Limiting, CSRF, CSP |
| **Data** | Encryption at rest (AES-256), in transit (TLS) |
| **Access** | RBAC, API Keys, Audit Logging |
| **Compliance** | GDPR, SOC2 ready |

## Monitoring & Observability

| Component | Tool |
|-----------|------|
| Metrics | Prometheus + Grafana |
| Logs | ELK Stack / Loki |
| Traces | Jaeger / Tempo |
| Alerts | Alertmanager + PagerDuty |
| Uptime | UptimeRobot / StatusPage |
| Cost | CloudWatch / Cloudability |

## Key Implementation Files

| Architecture Layer | Key Files |
|-------------------|-----------|
| **API Gateway** | `frontend/nginx.conf`, `docker-compose.yml` |
| **API Services** | `backend/main.py`, `backend/api/*.py` |
| **Agent Orchestration** | `backend/agents/research/orchestrator.py` |
| **Task Queue** | `backend/workers/celery_app.py` |
| **Workers** | `backend/workers/*_worker.py` |
| **Database** | `backend/models/*.py`, `backend/database.py` |
| **Vector DB** | `backend/rag/vector_store.py`, `backend/rag/embeddings.py` |
| **Object Storage** | `backend/tools/document_parser.py` |
| **LLM Providers** | `backend/providers/llm/*.py` |
| **Search Providers** | `backend/providers/search/*.py` |
| **Workers** | `backend/workers/*_worker.py` |

## Migration Checklist

### To MVP
- [ ] Production docker-compose with secrets management
- [ ] PostgreSQL with pgvector extension
- [ ] Redis Cluster setup
- [ ] Real provider API keys configured
- [ ] Prometheus + Grafana dashboards
- [ ] CI/CD pipeline (GitHub Actions/GitLab CI)
- [ ] Automated testing in pipeline
- [ ] Backup/restore procedures

### To Business Product
- [ ] Kubernetes manifests
- [ ] Helm charts for all services
- [ ] Weaviate/Pinecone vector database
- [ ] S3/MinIO object storage
- [ ] Service mesh (Istio)
- [ ] Advanced monitoring (Datadog/ELK)
- [ ] Multi-region deployment
- [ ] Disaster recovery plan

### To SaaS Platform
- [ ] Multi-tenant architecture
- [ ] API Gateway (Kong/Traefik)
- [ ] Event-driven architecture (Kafka)
- [ ] Advanced security (WAF, DDoS protection)
- [ ] Cost optimization automation
- [ ] Customer-facing status page
- [ ] SLA monitoring and reporting

---

**Last Updated:** 2026-08-31  
**Version:** 1.0.0  
**Status:** Ready for MVP deployment