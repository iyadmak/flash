"""The application's error vocabulary.

Deliberately imports nothing: domain objects raise these directly (OrderModel
raises IllegalStatusTransition), so this module must not drag a web framework
into the domain. The FastAPI handlers that translate them live in
`error_handlers.py`.
"""


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


class IllegalStatusTransition(AppError):
    """Raised by OrderModel.change_status for a move the lifecycle disallows.

    409 rather than 422: the request is well-formed and the target status is a
    real status -- it is the order's current state that makes it impossible, and
    that is a conflict, not a validation failure.
    """

    status_code = 409
    error_code = "illegal_status_transition"
    detail = "That status change is not allowed."

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(f"An order cannot move from {current!r} to {requested!r}.")


class OrderNotMutable(AppError):
    """Raised by OrderModel.assert_editable once an order's contents are fixed."""

    status_code = 409
    error_code = "order_not_mutable"
    detail = "This order can no longer be changed."

    def __init__(self, current: str) -> None:
        super().__init__(f"An order with status {current!r} can no longer be changed.")


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
