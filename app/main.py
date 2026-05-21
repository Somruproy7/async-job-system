from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1 import auth, jobs, admin
from app.core.config import settings
from app.core.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables (with retry logic for Railway)
    import asyncio
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✅ Database connected and tables created")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Database connection attempt {attempt + 1} failed: {e}")
                print(f"   Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"❌ Failed to connect to database after {max_retries} attempts")
                raise
    
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
    
    health_status = {
        "status": "healthy",
        "service": "async-job-system",
        "environment": {
            "has_database_url": bool(os.getenv("DATABASE_URL")),
            "has_redis_url": bool(os.getenv("CELERY_BROKER_URL")),
            "port": os.getenv("PORT", "8000"),
        }
    }
    
    # Try to ping database
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)[:100]}"
        health_status["status"] = "degraded"
    
    return health_status
