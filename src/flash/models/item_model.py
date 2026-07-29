from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from flash.core.db import Base
from flash.domain.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class ItemModel(Base):
    __tablename__ = "items"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    name: Mapped[str]
    price: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_MAX_DIGITS, MONEY_DECIMAL_PLACES)
    )
