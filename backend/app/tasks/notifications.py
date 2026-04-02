"""Background tasks related to notifications."""

from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_order_notification_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_order_notification_task(self, *, order_id: int, event: str) -> dict[str, str | int]:  # noqa: ARG001
    """Stub notification sender for order events."""
    return {"status": "queued_stub", "order_id": order_id, "event": event}


def queue_order_notification(order_id: int, event: str) -> None:
    """Enqueue non-blocking order notification task."""
    send_order_notification_task.delay(order_id=order_id, event=event)
