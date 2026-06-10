"""Logging Configuration"""

import logging

import structlog
from flash.core.config import settings


def configure_logging() -> None:
    """Configure structlog: pretty in dev, JSON in prod"""
    # shared processors for all loggers
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,  # pulls in request-scoped context
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),  # adds stack trace to the log record
        structlog.processors.format_exc_info,  # adds exception info to the log record
    ]

    # the dev/prod split:
    if settings.debug:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(
                logging, settings.log_level.upper(), logging.INFO
            )  # filters log based on the level set
        ),
        logger_factory=structlog.PrintLoggerFactory(),  # prints to stdout
        cache_logger_on_first_use=True,
    )
