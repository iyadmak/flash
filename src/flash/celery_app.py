from celery import Celery
from flash.core.config import get_settings

celery_app = Celery(
    "flash", broker=get_settings().rabbitmq_url, include=["flash.celery_tasks"]
)
