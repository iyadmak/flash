"""Centralized HTTP error handling.

Split from `exceptions.py` so that the exception hierarchy itself stays free of
any web-framework import. Domain objects raise AppErrors -- OrderModel raises
IllegalStatusTransition -- and nothing in the domain should transitively import
FastAPI to do it.
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from flash.core.exceptions import AppError

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the app. Called once from main."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Known errors are expected control flow — log at warning, no traceback."""
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Log the validation errors (the fields), never the raw payload."""
        logger.warning(
            "validation_failed",
            path=request.url.path,
            errors=exc.errors(),
        )
        # jsonable_encoder, not the raw list: pydantic puts the failed constraint in
        # each error's `ctx`, and a constraint can be a value json.dumps refuses --
        # `ge=Decimal("0")` on Money is exactly that. Without this, a negative price
        # made the handler itself blow up and the request 500'd instead of 422'd.
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                {"error": "validation_error", "detail": exc.errors()}
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, _exc: Exception) -> JSONResponse:
        """Genuine bugs: full traceback to logs, opaque 500 to the client."""
        logger.exception("unhandled_exception", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": "An unexpected error occurred.",
            },
        )
