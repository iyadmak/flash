from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from flash.core.db import Base


class UserModel(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    is_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
