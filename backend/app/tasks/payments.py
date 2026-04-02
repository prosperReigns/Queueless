"""Background tasks related to payments."""

from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.payments.verify_payment_backup_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def verify_payment_backup_task(self, payment_reference: str) -> str:  # noqa: ARG001
    """Backup payment verification task stub."""
    return f"verification_scheduled:{payment_reference}"
