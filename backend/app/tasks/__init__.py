"""Background task package for Celery workers."""

from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
