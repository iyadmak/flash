"""Translates asyncpg integrity errors into flash's own constraint vocabulary,
so repositories never branch on asyncpg exception types directly."""

from typing import NoReturn
from asyncpg.exceptions import ForeignKeyViolationError as PGForeignKeyViolationError
from asyncpg.exceptions import UniqueViolationError as PGUniqueViolationError
from sqlalchemy.exc import IntegrityError
from flash.core.exceptions import ForeignKeyViolation, UniqueConstraintViolation


def _cause(error: IntegrityError) -> BaseException | None:
    assert error.orig is not None
    return error.orig.__cause__


def is_foreign_key_violation(error: IntegrityError) -> bool:
    return isinstance(_cause(error), PGForeignKeyViolationError)


def translate_integrity_error(error: IntegrityError) -> NoReturn:
    """Raise the constraint-name-carrying exception matching the error's cause.

    Which parent table a violation maps to is only resolvable in the caller's
    context, so the repository translates this into a domain AppError.
    """
    cause = _cause(error)
    if isinstance(cause, PGForeignKeyViolationError):
        raise ForeignKeyViolation(cause.constraint_name) from error
    if isinstance(cause, PGUniqueViolationError):
        raise UniqueConstraintViolation(cause.constraint_name) from error
    raise error
