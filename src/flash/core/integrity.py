"""Translates raw SQLAlchemy/asyncpg integrity errors into flash's own
constraint-violation vocabulary, so repositories never branch on asyncpg
exception types directly.
"""

from typing import NoReturn
from asyncpg.exceptions import ForeignKeyViolationError as PGForeignKeyViolationError
from asyncpg.exceptions import UniqueViolationError as PGUniqueViolationError
from sqlalchemy.exc import IntegrityError
from flash.core.exceptions import ForeignKeyViolation, UniqueConstraintViolation


def _cause(e: IntegrityError) -> BaseException | None:
    assert e.orig is not None
    return e.orig.__cause__


def is_foreign_key_violation(e: IntegrityError) -> bool:
    return isinstance(_cause(e), PGForeignKeyViolationError)


def translate_integrity_error(e: IntegrityError) -> NoReturn:
    """Raise the constraint-name-carrying exception matching e's cause.

    Column-specific: which parent table an FK/unique violation maps to is
    something only the caller's context can resolve, so this raises a
    generic exception for a specific repository to catch and translate
    into a domain AppError.
    """
    cause = _cause(e)
    if isinstance(cause, PGForeignKeyViolationError):
        raise ForeignKeyViolation(cause.constraint_name) from e
    if isinstance(cause, PGUniqueViolationError):
        raise UniqueConstraintViolation(cause.constraint_name) from e
    raise e
