from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1 import auth, jobs, admin
from app.core.config import settings
from app.core.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: single fast attempt to create tables.
    # Do NOT retry with backoff here — each uvicorn worker runs this before it can
    # serve requests, so a long retry loop blocks all workers and causes Railway's
    # healthcheck to time out before any worker becomes ready.
    # DB connectivity is reported on every /health request instead.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database connected and tables created")
    except Exception as e:
        # Don't raise — boot in degraded mode so /health is reachable immediately
        print(f"⚠️ Starting in degraded mode — DB unavailable: {e}")

    yield

    # Shutdown: dispose engine
    await engine.dispose()


app = FastAPI(
    title="Async Job Processing System",
    description="Distributed job scheduling with Celery, Redis, and PostgreSQL",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint with database connectivity test"""
    import os
    import asyncio

    health_status = {
        "status": "healthy",
        "service": "async-job-system",
        "environment": {
            "has_database_url": bool(os.getenv("DATABASE_URL")),
            "has_redis_url": bool(os.getenv("CELERY_BROKER_URL")),
            "port": os.getenv("PORT", "8000"),
        }
    }

    # Try to ping database with a hard timeout so this endpoint never hangs
    async def _ping_db():
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(_ping_db(), timeout=3.0)
        health_status["database"] = "connected"
    except asyncio.TimeoutError:
        health_status["database"] = "error: connection timed out"
        health_status["status"] = "degraded"
    except Exception as e:
        health_status["database"] = f"error: {str(e)[:100]}"
        health_status["status"] = "degraded"

    return health_status
