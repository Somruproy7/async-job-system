from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.core.celery_app import celery_app
from app.models.user import User
from app.schemas.schemas import AdminStatsResponse
from app.services.job_service import JobService
from app.services.user_service import UserService

router = APIRouter()


@router.get("/stats", response_model=AdminStatsResponse)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """System-wide stats: job counts, queue depths, active workers."""
    job_svc = JobService(db)
    user_svc = UserService(db)

    job_stats = await job_svc.get_stats()
    total_users = await user_svc.get_total_count()

    # Inspect Celery workers + queues
    inspect = celery_app.control.inspect(timeout=2.0)
    active = inspect.active() or {}
    active_workers = len(active)

    # Queue depth per queue via Redis
    queue_depths = {}
    try:
        with celery_app.connection() as conn:
            for queue_name in ["high", "default", "low"]:
                bound = celery_app.amqp.queues[queue_name](conn.channel())
                queue_depths[queue_name] = bound.queue_declare(passive=True).message_count
    except Exception:
        queue_depths = {"high": -1, "default": -1, "low": -1}

    return AdminStatsResponse(
        total_jobs=job_stats["total_jobs"],
        jobs_by_status=job_stats["jobs_by_status"],
        jobs_by_type=job_stats["jobs_by_type"],
        total_users=total_users,
        active_workers=active_workers,
        queue_depths=queue_depths,
    )


@router.get("/workers")
async def list_workers(_admin: User = Depends(require_admin)):
    """Live Celery worker info."""
    inspect = celery_app.control.inspect(timeout=2.0)
    return {
        "active": inspect.active() or {},
        "reserved": inspect.reserved() or {},
        "stats": inspect.stats() or {},
    }
