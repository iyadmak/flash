"""Items Model"""
from sqlalchemy.orm import Mapped, mapped_column
from flash.core.db import Base

class Item(Base):
    """Item Model"""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    price: Mapped[float]
