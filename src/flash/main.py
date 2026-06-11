"""Application Entry Point"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import structlog

from fastapi import FastAPI
from flash.api.routes import health
from flash.api.v1.router import router as v1_router
from flash.core.config import get_settings
from flash.core.log_config import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application Lifespan"""
    settings = get_settings()
    configure_logging()
    logger = structlog.get_logger()
    logger.info(
        "Starting up...",
        app_name=settings.app_name,
        debug=settings.debug,
        log_level=settings.log_level,
    )
    yield
    logger.info("Shutting down...")


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)

app.include_router(health.router)
app.include_router(v1_router, prefix="/api")
