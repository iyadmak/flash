from datetime import datetime
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from flash.core.db import Base
from flash.core.exceptions import IllegalStatusTransition, OrderNotMutable
from flash.domain.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from flash.domain.order_status import (
    ALLOWED_TRANSITIONS,
    EDITABLE_STATUSES,
    OrderStatus,
)


class OrderModel(Base):
    __tablename__ = "orders"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    # NUMERIC, not DOUBLE PRECISION: exact for money, and asyncpg returns a Decimal.
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_MAX_DIGITS, MONEY_DECIMAL_PLACES)
    )
    # native_enum=False: a VARCHAR + CHECK, so adding a state needs no ALTER TYPE.
    # values_callable persists "pending" rather than SQLAlchemy's default "PENDING".
    # Typed as OrderStatus, not str: Enum.__hash__ comes from the member name, so a
    # plain "pending" compares equal to the member but misses every dict lookup.
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="order_status",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=OrderStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, server_default=func.now(), onupdate=func.now()
    )

    def change_status(self, new_status: OrderStatus) -> None:
        """The only place `status` is assigned. No-op moves are rejected too."""
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise IllegalStatusTransition(self.status, new_status)
        self.status = new_status

    def assert_editable(self) -> None:
        """Guard for anything that changes what the order contains."""
        if self.status not in EDITABLE_STATUSES:
            raise OrderNotMutable(self.status)
