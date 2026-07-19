from datetime import datetime
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from flash.core.db import Base


class ProcessedEventModel(Base):
    __tablename__ = "processed_events"
    __table_args__ = (UniqueConstraint("consumer_name", "event_id"),)

    consumer_name: Mapped[str] = mapped_column(nullable=False)
    event_id: Mapped[str] = mapped_column(nullable=False)
    processed_at: Mapped[datetime] = mapped_column(server_default=func.now())
