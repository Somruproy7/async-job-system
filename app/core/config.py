from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
from functools import lru_cache
import re


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Async Job System"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production-use-strong-secret"
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = ["*"]

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://jobuser:jobpass@postgres:5432/jobsdb"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Job settings
    JOB_MAX_RETRIES: int = 3
    JOB_RETRY_BACKOFF_SECONDS: int = 60
    JOB_DEFAULT_TIMEOUT_SECONDS: int = 3600  # 1 hour
    JOB_HIGH_PRIORITY_QUEUE: str = "high"
    JOB_DEFAULT_QUEUE: str = "default"
    JOB_LOW_PRIORITY_QUEUE: str = "low"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_db_url(cls, v):
        """Normalize Railway's DATABASE_URL:
        - postgres:// or postgresql:// -> postgresql+asyncpg://
        - remove empty port (host:/db -> host/db)
        """
        if not v or not isinstance(v, str):
            return v
        # Fix empty port: postgresql://user:pass@host:/db -> remove the colon
        v = re.sub(r':(?=/)', '', v)
        # Fix scheme
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
