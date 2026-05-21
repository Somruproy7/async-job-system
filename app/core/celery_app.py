from celery import Celery
from kombu import Queue, Exchange
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "async_job_system",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.job_tasks"],
)

# Define exchanges
default_exchange = Exchange("jobs", type="direct")

# Configure queues with priorities
celery_app.conf.task_queues = (
    Queue(settings.JOB_HIGH_PRIORITY_QUEUE, default_exchange, routing_key="high", queue_arguments={"x-max-priority": 10}),
    Queue(settings.JOB_DEFAULT_QUEUE, default_exchange, routing_key="default", queue_arguments={"x-max-priority": 5}),
    Queue(settings.JOB_LOW_PRIORITY_QUEUE, default_exchange, routing_key="low", queue_arguments={"x-max-priority": 1}),
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Default queue
    task_default_queue=settings.JOB_DEFAULT_QUEUE,
    task_default_exchange="jobs",
    task_default_routing_key="default",

    # Results
    result_expires=86400,  # 24h
    task_track_started=True,
    task_send_sent_event=True,

    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # process one task at a time per worker

    # Retry policy
    task_max_retries=settings.JOB_MAX_RETRIES,

    # Monitoring (Flower)
    worker_send_task_events=True,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "app.tasks.job_tasks.cleanup_old_jobs",
            "schedule": 3600.0,  # hourly
        },
        "retry-stuck-jobs": {
            "task": "app.tasks.job_tasks.retry_stuck_jobs",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)

# Route tasks to queues based on job priority
celery_app.conf.task_routes = {
    "app.tasks.job_tasks.process_job": {
        "queue": settings.JOB_DEFAULT_QUEUE,
    },
}
