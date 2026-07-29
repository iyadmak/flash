"""The application's error vocabulary.

Imports nothing: domain objects raise these directly, so it must not drag a web
framework into the domain. The handlers live in `error_handlers.py`.
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

    409, not 422: the request is well-formed; the order's current state is what
    makes it impossible, which is a conflict rather than a validation failure.
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
    """An insert referenced a row that does not exist.

    Deliberately not an AppError: the repository knows only which constraint
    Postgres rejected, so a repository translates the name into a domain error. A
    missed translation falls through to a 500, which is the right outcome.
    """

    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name
        super().__init__(f"Foreign key violation: {constraint_name}")


class UniqueConstraintViolation(Exception):
    """An insert collided with a unique constraint, e.g. a duplicate email.

    Same reasoning as ForeignKeyViolation: translated by a repository.
    """

    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name
        super().__init__(f"Unique constraint violation: {constraint_name}")
