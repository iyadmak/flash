from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from flash.core.db import Base


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    name: Mapped[str]
    price: Mapped[float]
