"""Celery application configuration."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

_broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
_result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "queueless",
    broker=_broker_url,
    backend=_result_backend,
    include=[
        "app.tasks.orders",
        "app.tasks.notifications",
        "app.tasks.payments",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_annotations={"*": {"max_retries": 3}},
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)
