# CareerIntel AI - Docker Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        External Users                               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy (Port 80/443)               │
│  • Rate Limiting  • SSL Termination  • Load Balancing              │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│   Frontend (Nginx)  │ │  Backend API    │ │  Monitoring      │
│   (Static Assets)   │ │  (FastAPI)      │ │  (Prometheus/    │
└─────────────────────┘ └────────┬────────┘ │   Grafana/Loki)  │
                                 │        └──────────────────┘
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌─────────────┐ ┌──────────┐ ┌───────────┐
            │ PostgreSQL  │ │  Redis   │ │  Qdrant   │
            │ (Primary DB)│ │ (Cache/  │ │ (Vector   │
            │             │ │  Queue)  │ │  Search)  │
            └─────────────┘ └──────────┘ └───────────┘
                    │
                    ▼
            ┌─────────────────────┐
            │  Celery Workers     │
            │  • Research         │
            │  • Jobs             │
            │  • Documents        │
            │  • Embeddings       │
            │  • Notifications    │
            └─────────────────────┘
```

## Quick Start (Development)

```bash
# Clone and navigate
cd Multi-Agent-Career-Intelligence-System

# Copy environment template
cp .env.production.template .env
# Edit .env with your values

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run database migrations
docker-compose exec backend alembic upgrade head

# Access services:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Flower: http://localhost:5555
```

## Production Deployment

### Prerequisites

- Docker 24+ and Docker Compose 2+
- Domain name with DNS configured
- SSL certificates (Let's Encrypt recommended)
- Minimum 8GB RAM, 4 CPU cores (16GB+ recommended)

### Setup

```bash
# 1. Copy production environment template
cp .env.production.template .env.production

# 2. Edit with production values
vim .env.production

# 3. Place SSL certificates in ./ssl/
mkdir -p ssl
# Add yourdomain.crt and yourdomain.key

# 4. Deploy
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 5. Run migrations
docker-compose -f docker-compose.prod.yml --env-file .env.production \
  exec backend alembic upgrade head

# 6. Verify health
docker-compose -f docker-compose.prod.yml --env-file .env.production ps
```

### SSL Certificate Setup (Let's Encrypt)

```bash
# Using certbot
sudo certbot certonly --standalone -d careerintel.ai -d www.careerintel.ai

# Copy certificates
sudo cp /etc/letsencrypt/live/careerintel.ai/fullchain.pem ./ssl/careerintel.crt
sudo cp /etc/letsencrypt/live/careerintel.ai/privkey.pem ./ssl/careerintel.key
sudo chown $USER:$USER ./ssl/*

# Set up auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'docker-compose -f /path/to/docker-compose.prod.yml restart nginx'" | sudo crontab -
```

## Service Details

### Core Services

| Service | Port | Description |
|---------|------|-------------|
| Nginx (Reverse Proxy) | 80/443 | SSL termination, rate limiting, load balancing |
| Frontend | 80 (internal) | Static asset serving, SPA routing |
| Backend API | 8000 (internal) | FastAPI application |
| PostgreSQL | 5432 (internal) | Primary database |
| Redis | 6379 (internal) | Cache, Celery broker, sessions |
| Qdrant | 6333/6334 (internal) | Vector database for embeddings |

### Worker Queues

| Worker | Queue | Concurrency | Purpose |
|--------|-------|-------------|---------|
| celery-worker-research | research | 4 | Multi-agent research pipeline |
| celery-worker-jobs | jobs | 4 | Job search, matching, ranking |
| celery-worker-documents | documents | 4 | Resume parsing, document processing |
| celery-worker-embeddings | embeddings | 2 | Vector embedding generation |
| celery-worker-notifications | notifications | 8 | Email, push, in-app notifications |

### Monitoring Stack

| Service | Port | Description |
|---------|------|-------------|
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Dashboards & alerting |
| Loki | 3100 | Log aggregation |
| Promtail | 9080 | Log shipping |
| Flower | 5555 | Celery task monitoring |

## Scaling Guidelines

### Horizontal Scaling

```bash
# Scale backend
docker-compose -f docker-compose.prod.yml up -d --scale backend=4

# Scale workers based on queue backlog
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker-research=4

# Scale frontend
docker-compose -f docker-compose.prod.yml up -d --scale frontend=3
```

### Resource Limits (Production)

```yaml
# Example resource constraints in docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

### Queue Monitoring

```bash
# Check queue lengths
docker-compose exec backend python -c "
from backend.workers.celery_app import app
i = app.control.inspect()
print('Active:', i.active())
print('Reserved:', i.reserved())
print('Scheduled:', i.scheduled())
print('Stats:', i.stats())
"

# Or use Flower UI at http://localhost:5555
```

## Health Checks

```bash
# All services
docker-compose -f docker-compose.prod.yml ps

# Individual service health
curl http://localhost:8000/health
curl http://localhost:6333/health
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health

# Database
docker-compose exec postgres pg_isready -U careerintel

# Redis
docker-compose exec redis redis-cli ping
```

## Backup & Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U careerintel careerintel > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker-compose exec postgres pg_dump -U careerintel careerintel | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
gunzip -c backup_20240115_120000.sql.gz | docker-compose exec -T postgres psql -U careerintel careerintel
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v careerintel_postgres_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/postgres_$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v careerintel_redis_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/redis_$(date +%Y%m%d).tar.gz -C /data .
docker run --rm -v careerintel_qdrant_data:/data -v $(pwd)/backups:/backup alpine tar czf /backup/qdrant_$(date +%Y%m%d).tar.gz -C /data .
```

## Troubleshooting

### Common Issues

**1. Backend fails to start**
```bash
# Check logs
docker-compose logs backend

# Common causes:
# - Database not ready (wait for healthcheck)
# - Missing environment variables
# - Migration needed
```

**2. Celery workers not processing tasks**
```bash
# Check worker status
docker-compose logs celery-worker-research

# Check Redis connection
docker-compose exec redis redis-cli ping

# Check queue
docker-compose exec backend python -c "
from backend.workers.celery_app import app
print(app.control.inspect().active())
"
```

**3. Frontend shows blank page**
```bash
# Check nginx config
docker-compose exec frontend nginx -t

# Check build output
docker-compose logs frontend

# Verify API connectivity
curl http://backend:8000/health
```

**4. High memory usage**
```bash
# Check container stats
docker stats

# Adjust worker concurrency
# Reduce --concurrency in docker-compose.prod.yml
```

**5. Database connection pool exhausted**
```bash
# Check pool settings in backend/config.py
# Increase pool size or reduce worker concurrency
```

### Debug Commands

```bash
# Enter container shell
docker-compose exec backend bash
docker-compose exec postgres psql -U careerintel -d careerintel
docker-compose exec redis redis-cli

# View specific service logs
docker-compose logs -f --tail=100 backend
docker-compose logs -f celery-worker-research

# Check resource usage
docker stats --no-stream

# Network connectivity
docker-compose exec backend ping postgres
docker-compose exec backend ping redis
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/username/careerintel:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/careerintel
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## Security Checklist

- [ ] Change all default passwords in `.env.production`
- [ ] Use strong `SECRET_KEY` (64+ random chars)
- [ ] Configure SSL/TLS certificates
- [ ] Restrict monitoring endpoints to internal IPs
- [ ] Enable firewall (only 80/443/22 open)
- [ ] Set up automated security updates
- [ ] Configure log rotation
- [ ] Enable database SSL connections
- [ ] Set up intrusion detection (fail2ban)
- [ ] Regular vulnerability scanning

## Maintenance

### Routine Tasks

```bash
# Weekly
docker system prune -f
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Monthly
# Rotate logs
# Update base images
# Review resource usage
# Test backup restoration

# Quarterly
# Rotate secrets/keys
# Review security advisories
# Update dependencies
```

## Support

For issues:
1. Check logs: `docker-compose logs -f <service>`
2. Check health endpoints
3. Review this guide
4. Check GitHub issues