import asyncio
from typing import Any

import structlog

logger = structlog.get_logger()


async def send_password_reset_email(
    ctx: dict[str, Any], email: str, token: str
) -> None:
    await asyncio.sleep(1)  # simulate latency to a real email provider
    logger.info(
        "password_reset_email_sent",
        email=email,
        reset_link=f"/reset-password?token={token}",
    )
