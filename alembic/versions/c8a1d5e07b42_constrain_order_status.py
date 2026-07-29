"""constrain order status to the lifecycle

Revision ID: c8a1d5e07b42
Revises: ff806cd5ce32
Create Date: 2026-07-29 18:20:00.000000

`status` was an unconstrained VARCHAR holding whatever string a client posted,
because OrderCreate took it straight from the request body. It becomes a
VARCHAR(32) with a CHECK constraint listing the known states -- matching the
SQLAlchemy Enum(native_enum=False) on OrderModel.

A CHECK constraint rather than a Postgres ENUM type on purpose: adding a state
to an ENUM needs ALTER TYPE, which cannot run inside a transaction alongside
other DDL in older Postgres and is awkward to reverse. Rewriting a CHECK is a
plain drop-and-create.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8a1d5e07b42"
down_revision: Union[str, Sequence[str], None] = "ff806cd5ce32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUSES = (
    "pending",
    "confirmed",
    "preparing",
    "out_for_delivery",
    "delivered",
    "cancelled",
)
_KNOWN = ", ".join(f"'{status}'" for status in STATUSES)


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows carry arbitrary client-supplied strings, so fold anything
    # unrecognised into 'pending' before the constraint goes on -- otherwise this
    # migration fails on any real data.
    op.execute(f"UPDATE orders SET status = 'pending' WHERE status NOT IN ({_KNOWN})")
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_check_constraint("order_status", "orders", f"status IN ({_KNOWN})")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_orders_order_status", "orders", type_="check")
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(),
        existing_nullable=False,
    )
