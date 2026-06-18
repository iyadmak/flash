from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from flash.core.db import Base
from datetime import datetime


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    total_price: Mapped[float]
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, server_default=func.now(), onupdate=func.now()
    )
