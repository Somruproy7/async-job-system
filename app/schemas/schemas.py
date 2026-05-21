from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.job import JobStatus, JobType, JobPriority
from app.models.user import UserRole


# ─── Auth Schemas ────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Job Schemas ─────────────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    job_type: JobType
    priority: JobPriority = JobPriority.DEFAULT
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0, le=10)

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: dict) -> dict:
        import json
        if len(json.dumps(v)) > 1_000_000:  # 1MB limit
            raise ValueError("Payload too large (max 1MB)")
        return v


class JobUpdateRequest(BaseModel):
    status: Optional[JobStatus] = None
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    status_message: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error_detail: Optional[str] = None


class JobResponse(BaseModel):
    id: UUID
    celery_task_id: Optional[str]
    name: str
    job_type: JobType
    priority: JobPriority
    status: JobStatus
    progress: float
    status_message: Optional[str]
    result: Optional[dict[str, Any]]
    error_detail: Optional[str]
    retry_count: int
    max_retries: int
    payload: dict[str, Any]
    duration_seconds: Optional[float]
    queue_wait_seconds: Optional[float]
    created_at: datetime
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    owner_id: UUID

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    pages: int


class JobStatusResponse(BaseModel):
    id: UUID
    status: JobStatus
    progress: float
    status_message: Optional[str]
    celery_task_id: Optional[str]

    model_config = {"from_attributes": True}


# ─── Admin Schemas ────────────────────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    total_jobs: int
    jobs_by_status: dict[str, int]
    jobs_by_type: dict[str, int]
    total_users: int
    active_workers: int
    queue_depths: dict[str, int]
