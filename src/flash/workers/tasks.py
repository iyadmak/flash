import time

import structlog
from flash.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(  # type: ignore[untyped-decorator]
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=5,
)
def send_password_reset_email_celery(email: str, token: str) -> None:
    time.sleep(1)  # task time simulation
    logger.info(
        "password_reset_email_sent",
        email=email,
        reset_link=f"/reset-password?token={token}",
    )
