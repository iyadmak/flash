"""How money is represented.

`float` cannot hold 0.10 exactly, so summing line items drifts and an order total
would disagree with its own items. Decimal is exact for base-10 amounts.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import Field

# Shared with the NUMERIC(10, 2) columns so validation and storage cannot drift.
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

`decimal_places` is load-bearing: without it the column would round 12.567 on
write and the stored amount would differ from the one sent, silently.
"""


def zero() -> Decimal:
    """Zero at the right scale to seed a sum of line items."""
    return Decimal("0.00")
