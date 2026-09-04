from celery import Celery

from app.config import settings

celery_app = Celery(
    "mlops",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_always_eager=settings.eager_tasks,
)


@celery_app.task(name="deployments.process")
def process_deployment_task(deployment_id: str) -> str:
    from app.config import settings
    from app.db import SessionLocal
    from app.services.registry import process_deployment

    db = SessionLocal()
    try:
        process_deployment(db, deployment_id, delay_seconds=settings.deploy_step_delay_seconds)
        return deployment_id
    finally:
        db.close()


def enqueue_deployment(deployment_id: str) -> None:
    process_deployment_task.delay(deployment_id)
