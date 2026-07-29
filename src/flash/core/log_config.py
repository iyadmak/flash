"""Logging Configuration"""

import logging

import structlog
from flash.core.config import get_settings


def configure_logging() -> None:
    """Configure structlog: pretty in dev, JSON in prod"""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,  # request-scoped context
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if get_settings().debug:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, get_settings().log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
