# Async Job Processing System

A production-grade distributed job scheduler built with **FastAPI**, **Celery**, **Redis**, and **PostgreSQL**. Designed for real-world workloads including image processing, report generation, and bulk email sending — with full async execution, real-time status tracking, and JWT-secured APIs.

---

## Architecture

```
Client
  │
  ▼
FastAPI (REST API)  ──── JWT Auth ────▶ PostgreSQL
  │                                        ▲
  │ apply_async()                          │ status updates
  ▼                                        │
Redis (Broker)                             │
  │                                        │
  ├──▶ [high queue]  ──▶ Worker ──────────┘
  ├──▶ [default queue] ▶ Worker
  └──▶ [low queue]   ──▶ Worker-Low

Celery Beat ──▶ Maintenance Tasks (cleanup, stuck-job retry)
Flower ──▶ Real-time worker/task monitoring dashboard
```

---

## Features

- **Async REST API** — Submit jobs and get a `202 Accepted` immediately. Poll `/jobs/{id}/status` for real-time progress.
- **Priority queues** — Three queues (`high`, `default`, `low`) with per-job routing.
- **Automatic retries** — Configurable max retries with exponential backoff.
- **Crash recovery** — Beat task re-queues jobs stuck in `RUNNING` after 2 hours (worker crash recovery).
- **Role-based access** — Admins see all jobs; regular users see only their own.
- **JWT authentication** — Short-lived access tokens + long-lived refresh tokens.
- **Flower dashboard** — Real-time Celery worker and task monitoring at `/flower`.
- **Docker Compose** — Single command to run the full stack locally.
- **GitHub Actions CI/CD** — Tests → Docker build → zero-downtime EC2 deploy on every push to `main`.

---

## Quick Start

### Local Development

```bash
# 1. Clone and configure
git clone https://github.com/YOUR_USERNAME/async-job-system
cd async-job-system
cp .env.example .env          # edit secrets

# 2. Start everything
docker compose up -d

# 3. Check it's running
curl http://localhost:8000/health

# 4. View Dashboard
open http://localhost:3001

# 5. View API docs
open http://localhost:8000/api/docs
```

### ☁️ Cloud Deployment (Recommended)

**Deploy in 10 minutes to Railway + Vercel (Free tier available!)**

See **[QUICK_DEPLOY.md](QUICK_DEPLOY.md)** for step-by-step guide.

- **Backend (Railway)**: API + Workers + Database + Redis
- **Frontend (Vercel)**: Dashboard UI

**Or use traditional deployment:**
- **Docker Compose**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **AWS EC2**: Use `scripts/ec2-setup.sh`

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Current user info |

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jobs/` | Submit a job (202 Accepted) |
| GET | `/api/v1/jobs/` | List jobs (paginated) |
| GET | `/api/v1/jobs/{id}` | Full job details |
| GET | `/api/v1/jobs/{id}/status` | Lightweight status + progress |
| POST | `/api/v1/jobs/{id}/cancel` | Cancel pending/queued job |
| POST | `/api/v1/jobs/{id}/retry` | Re-queue a failed job |

### Submit a Job

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r .access_token)

# Submit an image processing job
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Resize product images",
    "job_type": "image_processing",
    "priority": "high",
    "payload": {
      "image_url": "https://example.com/product.jpg",
      "width": 800,
      "format": "webp"
    }
  }'

# Poll for status
JOB_ID=<id from above response>
curl http://localhost:8000/api/v1/jobs/$JOB_ID/status \
  -H "Authorization: Bearer $TOKEN"
```

### Job Types

| Type | Payload fields | Description |
|------|---------------|-------------|
| `image_processing` | `image_url`, `width`, `format` | Resize, convert, optimise images |
| `report_generation` | `report_type`, `date_range`, `filters` | Generate PDF/Excel reports |
| `email_sending` | `recipients[]`, `template_id`, `subject` | Bulk email with tracking |
| `data_export` | `query`, `format`, `destination` | Export DB data to CSV/JSON |

---

## Configuration

Key `.env` variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | JWT signing key (change this!) |
| `DATABASE_URL` | postgres... | Async PostgreSQL URL |
| `CELERY_BROKER_URL` | redis://... | Celery message broker |
| `JOB_MAX_RETRIES` | 3 | Max retry attempts per job |
| `JOB_RETRY_BACKOFF_SECONDS` | 60 | Base backoff (doubles each retry) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime |

---

## Development

```bash
# Run tests
pytest tests/ -v --cov=app

# Database migrations
docker compose run --rm api alembic revision --autogenerate -m "description"
docker compose run --rm api alembic upgrade head

# Scale workers
docker compose up -d --scale worker=4

# Watch Celery logs
docker compose logs -f worker

# Connect to DB
docker compose exec postgres psql -U jobuser jobsdb
```

---

## Production Deployment (AWS EC2)

```bash
# 1. Provision EC2 instance (Ubuntu 24.04, t3.medium minimum)
# 2. Run setup script
scp scripts/ec2-setup.sh ubuntu@<EC2_IP>:/tmp/
ssh ubuntu@<EC2_IP> "sudo bash /tmp/ec2-setup.sh"

# 3. Add GitHub secrets:
#    EC2_HOST, EC2_USER, EC2_SSH_KEY (private key)

# 4. Push to main → CI/CD deploys automatically
git push origin main
```

---

## Project Structure

```
async-job-system/
├── app/
│   ├── api/v1/          # FastAPI routers (auth, jobs, admin)
│   ├── core/            # Config, DB, security, Celery
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic (JobService, UserService)
│   ├── tasks/           # Celery task definitions
│   └── main.py          # FastAPI app + lifespan
├── tests/               # pytest test suite
├── docker/              # Dockerfiles + postgres init
├── scripts/             # EC2 setup script
├── .github/workflows/   # GitHub Actions CI/CD
├── docker-compose.yml
├── requirements.txt
└── alembic.ini
```
