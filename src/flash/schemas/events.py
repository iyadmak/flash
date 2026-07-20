import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EventEnvelope[DataT: BaseModel](BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    event_version: int = 1
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: DataT
