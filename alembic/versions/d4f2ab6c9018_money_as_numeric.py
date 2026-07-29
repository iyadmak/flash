"""store money as numeric rather than double precision

Revision ID: d4f2ab6c9018
Revises: c8a1d5e07b42
Create Date: 2026-07-29 19:05:00.000000

orders.total_price and items.price were DOUBLE PRECISION, which cannot represent
0.10 exactly. That is tolerable while a total is just a number the client posts,
and not tolerable once the total is the sum of the line items: the invariant
total == sum(items) has to be an assertion that holds, not one that usually holds.

NUMERIC(10, 2) is exact for the base-10 quantities money is, and asyncpg hands it
back as a Decimal with the scale preserved. Postgres has an assignment cast from
double precision, so existing values convert in place -- rounded to two decimal
places, which is the only sane reading of a price that was stored as
9.989999999999999.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4f2ab6c9018"
down_revision: Union[str, Sequence[str], None] = "c8a1d5e07b42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MONEY = sa.Numeric(10, 2)


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "orders",
        "total_price",
        existing_type=sa.Float(),
        type_=MONEY,
        existing_nullable=False,
    )
    op.alter_column(
        "items",
        "price",
        existing_type=sa.Float(),
        type_=MONEY,
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema.

    Lossy in principle: anything that needed more than a double can hold is
    already rounded. In practice nothing here exceeds that range.
    """
    op.alter_column(
        "items",
        "price",
        existing_type=MONEY,
        type_=sa.Float(),
        existing_nullable=False,
    )
    op.alter_column(
        "orders",
        "total_price",
        existing_type=MONEY,
        type_=sa.Float(),
        existing_nullable=False,
    )
