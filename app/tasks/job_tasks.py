"""
Celery tasks for async job processing.
Each task updates job status/progress in PostgreSQL as it runs.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger
from sqlalchemy import select, update

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SyncSessionLocal
from app.models.job import Job, JobStatus, JobType, JobPriority

logger = get_task_logger(__name__)


# ─── Helper: Update job status synchronously ─────────────────────────────────

def _update_job_status_sync(
    job_id: str,
    status: JobStatus,
    progress: float = None,
    message: str = None,
    result: dict = None,
    error_detail: str = None,
    celery_task_id: str = None,
):
    """Persist job state changes to PostgreSQL (synchronous)."""
    with SyncSessionLocal() as db:
        try:
            values = {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
            if progress is not None:
                values["progress"] = progress
            if message is not None:
                values["status_message"] = message
            if result is not None:
                values["result"] = result
            if error_detail is not None:
                values["error_detail"] = error_detail
            if celery_task_id:
                values["celery_task_id"] = celery_task_id

            if status == JobStatus.RUNNING and "started_at" not in values:
                values["started_at"] = datetime.now(timezone.utc)
            if status in (JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED):
                values["completed_at"] = datetime.now(timezone.utc)
                values["progress"] = 100.0 if status == JobStatus.SUCCESS else values.get("progress", 0.0)

            db.execute(
                update(Job).where(Job.id == UUID(job_id)).values(**values)
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update job status: {e}")
            raise


# ─── Processor implementations ───────────────────────────────────────────────

import time

def _process_image(job_id: str, payload: dict, task_instance) -> dict:
    """Simulate image processing with progress updates."""
    steps = [
        (10, "Downloading image"),
        (30, "Validating format"),
        (50, "Applying transformations"),
        (80, "Optimising output"),
        (95, "Uploading result"),
    ]
    for progress, message in steps:
        _update_job_status_sync(job_id, JobStatus.RUNNING, progress=progress, message=message)
        time.sleep(1)  # Simulated work — replace with real logic

    output_url = f"https://cdn.example.com/processed/{job_id}.webp"
    return {"output_url": output_url, "format": "webp", "size_bytes": 204800}


def _generate_report(job_id: str, payload: dict, task_instance) -> dict:
    """Simulate report generation."""
    stages = [
        (15, "Fetching data sources"),
        (40, "Aggregating metrics"),
        (65, "Rendering charts"),
        (85, "Compiling PDF"),
        (95, "Storing report"),
    ]
    for progress, message in stages:
        _update_job_status_sync(job_id, JobStatus.RUNNING, progress=progress, message=message)
        time.sleep(1.5)

    report_url = f"https://reports.example.com/{job_id}.pdf"
    return {"report_url": report_url, "page_count": 12, "generated_at": datetime.now(timezone.utc).isoformat()}


def _send_emails(job_id: str, payload: dict, task_instance) -> dict:
    """Simulate bulk email sending with per-batch progress."""
    recipients = payload.get("recipients", [])
    total = max(len(recipients), 1)
    sent = 0
    failed_emails = []

    batch_size = 50
    for i in range(0, total, batch_size):
        batch = recipients[i : i + batch_size]
        # Simulate sending; real code calls SMTP/SES here
        time.sleep(0.5)
        sent += len(batch)
        progress = round((sent / total) * 90)
        _update_job_status_sync(
            job_id, JobStatus.RUNNING,
            progress=progress,
            message=f"Sent {sent}/{total} emails",
        )

    return {"total_sent": sent, "total_failed": len(failed_emails), "failed_emails": failed_emails}


def _export_data(job_id: str, payload: dict, task_instance) -> dict:
    """Simulate data export."""
    for progress, message in [(20, "Querying database"), (60, "Formatting CSV"), (90, "Compressing")]:
        _update_job_status_sync(job_id, JobStatus.RUNNING, progress=progress, message=message)
        time.sleep(1)
    return {"export_url": f"https://exports.example.com/{job_id}.csv.gz", "rows_exported": 50000}


PROCESSORS = {
    JobType.IMAGE_PROCESSING: _process_image,
    JobType.REPORT_GENERATION: _generate_report,
    JobType.EMAIL_SENDING: _send_emails,
    JobType.DATA_EXPORT: _export_data,
}


# ─── Main Celery task ────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.tasks.job_tasks.process_job",
    max_retries=settings.JOB_MAX_RETRIES,
    default_retry_delay=settings.JOB_RETRY_BACKOFF_SECONDS,
    soft_time_limit=settings.JOB_DEFAULT_TIMEOUT_SECONDS,
    acks_late=True,
    track_started=True,
)
def process_job(self, job_id: str, job_type: str, payload: dict[str, Any]):
    """
    Main entry point for all async jobs.
    Routes to the correct processor based on job_type.
    Handles retries and updates job status throughout.
    """
    logger.info(f"Starting job {job_id} (type={job_type}, attempt={self.request.retries + 1})")

    try:
        # Mark as running
        _update_job_status_sync(
            job_id, JobStatus.RUNNING,
            progress=0.0,
            message="Job started",
            celery_task_id=self.request.id,
        )

        # Dispatch to appropriate processor
        processor = PROCESSORS.get(JobType(job_type))
        if not processor:
            raise ValueError(f"Unknown job type: {job_type}")

        result = processor(job_id, payload, self)

        # Mark success
        _update_job_status_sync(
            job_id, JobStatus.SUCCESS,
            progress=100.0,
            message="Completed successfully",
            result=result,
        )

        logger.info(f"Job {job_id} completed successfully")
        return result

    except Exception as exc:
        logger.error(f"Job {job_id} failed (attempt {self.request.retries + 1}): {exc}")

        retry_count = self.request.retries + 1
        max_retries = self.max_retries

        if retry_count < max_retries:
            # Will retry — mark as retrying
            backoff = settings.JOB_RETRY_BACKOFF_SECONDS * (2 ** self.request.retries)
            _update_job_status_sync(
                job_id, JobStatus.RETRYING,
                message=f"Retry {retry_count}/{max_retries} in {backoff}s: {str(exc)[:200]}",
                error_detail=str(exc),
            )
            # Update retry counter in DB
            _increment_retry_count_sync(job_id)
            raise self.retry(exc=exc, countdown=backoff)
        else:
            # Exhausted retries — final failure
            _update_job_status_sync(
                job_id, JobStatus.FAILED,
                message="Max retries exceeded",
                error_detail=str(exc),
            )
            raise


def _increment_retry_count_sync(job_id: str):
    with SyncSessionLocal() as db:
        try:
            db.execute(
                update(Job)
                .where(Job.id == UUID(job_id))
                .values(retry_count=Job.retry_count + 1)
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to increment retry count: {e}")


# ─── Maintenance tasks ────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.job_tasks.cleanup_old_jobs")
def cleanup_old_jobs():
    """Remove completed/failed jobs older than 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    with SyncSessionLocal() as db:
        try:
            result = db.execute(
                select(Job).where(
                    Job.status.in_([JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED]),
                    Job.completed_at < cutoff,
                )
            )
            jobs = result.scalars().all()
            count = len(jobs)
            for job in jobs:
                db.delete(job)
            db.commit()
            logger.info(f"Cleaned up {count} old jobs")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup old jobs: {e}")


@celery_app.task(name="app.tasks.job_tasks.retry_stuck_jobs")
def retry_stuck_jobs():
    """Re-queue jobs stuck in RUNNING state for > 2 hours (worker crash recovery)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    with SyncSessionLocal() as db:
        try:
            result = db.execute(
                select(Job).where(
                    Job.status == JobStatus.RUNNING,
                    Job.started_at < cutoff,
                )
            )
            stuck_jobs = result.scalars().all()
            for job in stuck_jobs:
                logger.warning(f"Re-queuing stuck job {job.id}")
                job.status = JobStatus.PENDING
                job.status_message = "Re-queued after worker crash"
                job.started_at = None
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to retry stuck jobs: {e}")
