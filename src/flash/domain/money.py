"""How money is represented.

`float` cannot hold 0.10 exactly, so summing line items drifts -- which matters
immediately, because the order total is about to become the sum of its items and
`total == sum(items)` has to be an assertion that holds rather than one that
usually holds. Decimal is exact for the base-10 quantities money actually is.

Imports pydantic but nothing infrastructural. The rule this package follows is
"no SQLAlchemy engine, no web framework" -- see order_status.py -- and pydantic is
already loaded in every process here, consumers included.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

# NUMERIC(10, 2): up to 99,999,999.99. Kept as constants so the column definition
# and the request validation cannot drift apart -- if pydantic accepted 3 decimal
# places while the column stored 2, Postgres would round on write and no error
# would ever be raised.
MONEY_MAX_DIGITS = 10
MONEY_DECIMAL_PLACES = 2

Money = Annotated[
    Decimal,
    Field(
        ge=0,
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
    ),
]
"""A non-negative amount with at most two decimal places.

`decimal_places` is a real guard, not decoration: without it 12.567 would be
accepted and silently rounded by the column, so the value the client sent and the
value that got stored would differ with nothing to say so.
"""


def zero() -> Decimal:
    """The additive identity, at the right scale for summing line items."""
    return Decimal("0.00")
