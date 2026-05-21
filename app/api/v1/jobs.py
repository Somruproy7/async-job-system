import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.job import JobStatus, JobType, JobPriority
from app.models.user import User
from app.schemas.schemas import (
    JobCreateRequest, JobListResponse, JobResponse, JobStatusResponse,
)
from app.services.job_service import JobService
from app.tasks.job_tasks import process_job

router = APIRouter()

# Priority → Celery queue mapping
PRIORITY_QUEUE_MAP = {
    JobPriority.HIGH: settings.JOB_HIGH_PRIORITY_QUEUE,
    JobPriority.DEFAULT: settings.JOB_DEFAULT_QUEUE,
    JobPriority.LOW: settings.JOB_LOW_PRIORITY_QUEUE,
}


@router.post("/", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    data: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new async job. Returns immediately with job details; processing is asynchronous."""
    svc = JobService(db)
    job = await svc.create(data, owner=current_user)

    # Dispatch to Celery — route to the correct priority queue
    queue = PRIORITY_QUEUE_MAP[data.priority]
    celery_result = process_job.apply_async(
        kwargs={
            "job_id": str(job.id),
            "job_type": data.job_type.value,
            "payload": data.payload,
        },
        queue=queue,
        priority={"high": 9, "default": 5, "low": 1}[queue],
    )

    # Record the Celery task ID and mark queued
    job = await svc.mark_queued(job, celery_task_id=celery_result.id)

    return job


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = Query(None),
    job_type: Optional[JobType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List jobs. Admins see all; regular users see only their own."""
    svc = JobService(db)
    jobs, total = await svc.list_jobs(
        owner=current_user,
        status=status,
        job_type=job_type.value if job_type else None,
        page=page,
        page_size=page_size,
    )
    return JobListResponse(
        items=jobs,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full job details."""
    svc = JobService(db)
    job = await svc.get_by_id(job_id, owner=current_user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lightweight status endpoint — poll this for real-time progress.
    Returns only status, progress %, and message.
    """
    svc = JobService(db)
    job = await svc.get_by_id(job_id, owner=current_user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending or queued job."""
    svc = JobService(db)
    job = await svc.get_by_id(job_id, owner=current_user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.PENDING, JobStatus.QUEUED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in '{job.status}' state",
        )

    # Revoke the Celery task if it exists
    if job.celery_task_id:
        from app.core.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=False)

    job = await svc.cancel(job)
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually re-queue a failed job."""
    svc = JobService(db)
    job = await svc.get_by_id(job_id, owner=current_user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")

    # Re-queue
    queue = PRIORITY_QUEUE_MAP[job.priority]
    celery_result = process_job.apply_async(
        kwargs={
            "job_id": str(job.id),
            "job_type": job.job_type.value,
            "payload": job.payload,
        },
        queue=queue,
    )
    job = await svc.mark_queued(job, celery_task_id=celery_result.id)
    return job
