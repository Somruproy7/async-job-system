from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job, JobStatus, JobPriority
from app.models.user import User, UserRole
from app.core.config import settings
from app.schemas.schemas import JobCreateRequest, JobUpdateRequest


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: JobCreateRequest, owner: User) -> Job:
        job = Job(
            name=data.name,
            job_type=data.job_type,
            priority=data.priority,
            payload=data.payload,
            metadata_=data.metadata,
            max_retries=data.max_retries,
            owner_id=owner.id,
            status=JobStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID, owner: Optional[User] = None) -> Optional[Job]:
        stmt = select(Job).where(Job.id == job_id)
        # Non-admins can only see their own jobs
        if owner and owner.role != UserRole.ADMIN:
            stmt = stmt.where(Job.owner_id == owner.id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        owner: User,
        status: Optional[JobStatus] = None,
        job_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        stmt = select(Job)

        # Role-based filtering
        if owner.role != UserRole.ADMIN:
            stmt = stmt.where(Job.owner_id == owner.id)

        if status:
            stmt = stmt.where(Job.status == status)
        if job_type:
            stmt = stmt.where(Job.job_type == job_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        stmt = stmt.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        jobs = result.scalars().all()

        return jobs, total

    async def update(self, job: Job, data: JobUpdateRequest) -> Job:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(job, field, value)
        job.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def cancel(self, job: Job) -> Job:
        if job.status in (JobStatus.PENDING, JobStatus.QUEUED):
            job.status = JobStatus.CANCELLED
            job.status_message = "Cancelled by user"
            job.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
        return job

    async def mark_queued(self, job: Job, celery_task_id: str) -> Job:
        job.status = JobStatus.QUEUED
        job.celery_task_id = celery_task_id
        job.queued_at = datetime.now(timezone.utc)
        await self.db.flush()
        return job

    async def get_stats(self) -> dict:
        """Aggregate job statistics for admin dashboard."""
        status_counts = {}
        for status in JobStatus:
            count = (await self.db.execute(
                select(func.count(Job.id)).where(Job.status == status)
            )).scalar()
            status_counts[status.value] = count

        type_counts_result = await self.db.execute(
            select(Job.job_type, func.count(Job.id)).group_by(Job.job_type)
        )
        type_counts = {row[0].value: row[1] for row in type_counts_result}

        total = (await self.db.execute(select(func.count(Job.id)))).scalar()

        return {
            "total_jobs": total,
            "jobs_by_status": status_counts,
            "jobs_by_type": type_counts,
        }
