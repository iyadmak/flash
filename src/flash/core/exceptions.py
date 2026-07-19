"""Application exceptions and centralized error handling."""

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class AppError(Exception):
    """Base class for known, expected application errors.

    Raised by services and repositories; they carry no HTTP knowledge beyond
    a status code that the handler uses to build the response.
    """

    status_code: int = 500
    error_code: str = "internal_error"
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class ItemNotFound(AppError):
    status_code = 404
    error_code = "item_not_found"
    detail = "The requested item does not exist."


class UserNotFound(AppError):
    status_code = 404
    error_code = "user_not_found"
    detail = "The requested user does not exist."


class RestaurantNotFound(AppError):
    status_code = 404
    error_code = "restaurant_not_found"
    detail = "The requested restaurant does not exist."


class OrderNotFound(AppError):
    status_code = 404
    error_code = "order_not_found"
    detail = "The requested order does not exist."


class EmailAlreadyRegistered(AppError):
    status_code = 409
    error_code = "email_already_registered"
    detail = "An account with this email already exists."


class InvalidCredentials(AppError):
    status_code = 401
    error_code = "invalid_credentials"
    detail = "Incorrect email or password"


class InvalidToken(AppError):
    status_code = 401
    error_code = "invalid_token"
    detail = "could not validate credentials."


class Forbidden(AppError):
    status_code = 403
    error_code = "forbidden"
    detail = "you don't have permission to perform this action."


class InvalidCursor(AppError):
    status_code = 400
    error_code = "invalid_cursor"
    detail = "The provided pagination cursor is invalid."


class RateLimitExceeded(AppError):
    status_code = 429
    error_code = "rate_limit_exceeded"
    detail = "Too many requests. Please try again later."


class DuplicateRequest(AppError):
    status_code = 409
    error_code = "duplicate_request"
    detail = "An identical request is already being processed."


class DeleteConflict(AppError):
    status_code = 409
    error_code = "delete_conflict"
    detail = "Cannot delete this resource because other records still depend on it."


class ForeignKeyViolation(Exception):
    """Raised by BaseRepository.create() when an insert references a row
    that doesn't exist. Deliberately not an AppError: the repository layer
    has no notion of "restaurants" or "users", only which constraint
    Postgres rejected -- the service layer catches this and translates the
    constraint name into the right domain-specific AppError. If a service
    ever forgets to catch it, it falls through to the generic 500 handler,
    which is the correct outcome for a missed translation.
    """

    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name
        super().__init__(f"Foreign key violation: {constraint_name}")


class UniqueConstraintViolation(Exception):
    """Raised by BaseRepository.create() when an insert collides with a
    unique constraint or index (e.g. a duplicate email). Same reasoning as
    ForeignKeyViolation: the repository layer only knows which constraint
    Postgres rejected, not what that means for a given model -- the service
    layer translates it into the right domain-specific AppError.
    """

    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name
        super().__init__(f"Unique constraint violation: {constraint_name}")


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
        return JSONResponse(
            status_code=422,
            content={"error": "validation_error", "detail": exc.errors()},
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
