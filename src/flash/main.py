"""Application Entry Point"""

import structlog
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI
from aiokafka import AIOKafkaProducer

from flash.api.routes.health import router as health_router
from flash.api.v1.router import router as v1_router
from flash.core.config import get_settings
from flash.core.log_config import configure_logging
from flash.core.exceptions import register_exception_handlers
from flash.core.middleware import RequestLoggingMiddleware


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
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await producer.start()
    _app.state.kafka_producer = producer
    yield
    await producer.stop()
    logger.info("Shutting down...")


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(v1_router, prefix="/api")
