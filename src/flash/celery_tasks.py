import time
import structlog
from flash.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task  # type: ignore[untyped-decorator]
def send_password_reset_email_celery(email: str, token: str) -> None:
    time.sleep(1)  # task time simulation
    logger.info(
        "password_reset_email_sent",
        email=email,
        reset_link=f"/reset-password?token={token}",
    )
