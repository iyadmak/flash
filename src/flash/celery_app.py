from celery import Celery
from flash.core.config import get_settings

celery_app = Celery(
    "flash", broker=get_settings().rabbitmq_url, include=["flash.celery_tasks"]
)
# At-least-once delivery as the app-wide default: only ack a task after it
# finishes (success or retries exhausted), so a worker crash mid-task gets
# the message redelivered instead of silently lost. Requires tasks to be
# safe to run more than once -- override per-task where that's not true.
celery_app.conf.task_acks_late = True
