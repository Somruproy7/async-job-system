import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, Text,
    Enum as SAEnum, ForeignKey, Float
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    IMAGE_PROCESSING = "image_processing"
    REPORT_GENERATION = "report_generation"
    EMAIL_SENDING = "email_sending"
    DATA_EXPORT = "data_export"
    CUSTOM = "custom"


class JobPriority(str, Enum):
    HIGH = "high"
    DEFAULT = "default"
    LOW = "low"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    celery_task_id = Column(String(255), unique=True, nullable=True, index=True)

    # Identity
    name = Column(String(255), nullable=False)
    job_type = Column(SAEnum(JobType), nullable=False, index=True)
    priority = Column(SAEnum(JobPriority), default=JobPriority.DEFAULT, nullable=False, index=True)

    # Status tracking
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    status_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    error_detail = Column(Text, nullable=True)

    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Payload
    payload = Column(JSON, nullable=False, default=dict)
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)

    # Timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    queued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner = relationship("User", back_populates="jobs")

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def queue_wait_seconds(self) -> float | None:
        if self.queued_at and self.started_at:
            return (self.started_at - self.queued_at).total_seconds()
        return None

    def __repr__(self):
        return f"<Job {self.name} [{self.status}]>"
