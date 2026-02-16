"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from seal_agent.config import settings

celery_app = Celery(
    "seal_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "seal_agent.tasks.prospecting_tasks",
        "seal_agent.tasks.outreach_tasks",
        "seal_agent.tasks.pipeline_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    # Retry policy for transient failures
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Periodic beat schedule
celery_app.conf.beat_schedule = {
    "score-new-leads": {
        "task": "seal_agent.tasks.prospecting_tasks.score_new_leads",
        "schedule": crontab(minute="*/15"),
    },
    "execute-due-sequences": {
        "task": "seal_agent.tasks.outreach_tasks.execute_due_sequences",
        "schedule": crontab(minute="*/10"),
    },
    "pipeline-review": {
        "task": "seal_agent.tasks.pipeline_tasks.pipeline_review",
        "schedule": crontab(minute=0),  # Every hour
    },
    "identify-at-risk-deals": {
        "task": "seal_agent.tasks.pipeline_tasks.identify_at_risk_deals",
        "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM
    },
}
