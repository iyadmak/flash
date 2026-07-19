"""add naming convention for constraints

Revision ID: 7943475e81a3
Revises: 37a79aff5860
Create Date: 2026-07-19 16:50:51.743290

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7943475e81a3"
down_revision: Union[str, Sequence[str], None] = "37a79aff5860"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, old_name, new_name) for every constraint whose Postgres-assigned
# default name doesn't match the naming_convention now set on Base.metadata.
# Index names are untouched: SQLAlchemy's built-in default for auto-named
# indexes (ix_<table>_<column>) already matches our convention.
PRIMARY_KEYS = [
    ("items", "items_pkey", "pk_items"),
    ("orders", "orders_pkey", "pk_orders"),
    ("restaurants", "restaurants_pkey", "pk_restaurants"),
    ("users", "users_pkey", "pk_users"),
    ("password_reset_tokens", "password_reset_tokens_pkey", "pk_password_reset_tokens"),
]

FOREIGN_KEYS = [
    ("items", "items_order_id_fkey", "fk_items_order_id_orders"),
    ("orders", "orders_restaurant_id_fkey", "fk_orders_restaurant_id_restaurants"),
    ("orders", "orders_user_id_fkey", "fk_orders_user_id_users"),
    ("restaurants", "restaurants_owner_id_fkey", "fk_restaurants_owner_id_users"),
    (
        "password_reset_tokens",
        "password_reset_tokens_user_id_fkey",
        "fk_password_reset_tokens_user_id_users",
    ),
]


def _rename_constraint(table: str, old_name: str, new_name: str) -> None:
    # Skip if old_name is absent: on a database that ran the full migration
    # chain under today's code, earlier migrations already created the
    # constraint under new_name directly, via the naming_convention now
    # wired into env.py's target_metadata.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{old_name}' AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT "{old_name}" TO "{new_name}";
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    """Upgrade schema."""
    for table, old_name, new_name in [*PRIMARY_KEYS, *FOREIGN_KEYS]:
        _rename_constraint(table, old_name, new_name)


def downgrade() -> None:
    """Downgrade schema."""
    for table, old_name, new_name in [*PRIMARY_KEYS, *FOREIGN_KEYS]:
        _rename_constraint(table, new_name, old_name)
