from datetime import datetime

from sqlalchemy import Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from flash.core.db import Base
from flash.core.exceptions import IllegalStatusTransition, OrderNotMutable
from flash.domain.order_status import (
    ALLOWED_TRANSITIONS,
    EDITABLE_STATUSES,
    OrderStatus,
)


class OrderModel(Base):
    __tablename__ = "orders"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    total_price: Mapped[float]
    # native_enum=False keeps this a VARCHAR with a CHECK constraint rather than a
    # Postgres ENUM type, which cannot be altered without a migration dance every
    # time a state is added. values_callable persists the lowercase *values*
    # ("pending") instead of SQLAlchemy's default of member *names* ("PENDING"),
    # which is what existing rows and the event payload already contain.
    #
    # Typing the column as OrderStatus rather than str matters more than it looks:
    # Enum.__hash__ is derived from the member name, so a plain "pending" loaded
    # from the database would compare equal to OrderStatus.PENDING while hashing
    # differently -- and every ALLOWED_TRANSITIONS lookup would silently miss.
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
        """Advance the order. The only place `status` is ever assigned.

        Rejects same-status "changes" too, since PENDING is not in its own
        transition set -- a no-op PUT used to succeed silently and report a change
        that never happened.
        """
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise IllegalStatusTransition(self.status, new_status)
        self.status = new_status

    def assert_editable(self) -> None:
        """Guard for anything that changes what the order contains.

        Called by the aggregate's write paths rather than by each caller, so a
        method added later cannot forget it: there is no way to reach the items
        of an order except through code that has already asked this question.
        """
        if self.status not in EDITABLE_STATUSES:
            raise OrderNotMutable(self.status)
