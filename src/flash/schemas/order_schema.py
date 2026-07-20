from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from flash.schemas.events import EventEnvelope


class OrderCreate(BaseModel):
    user_id: int
    restaurant_id: int
    total_price: float
    status: str


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    restaurant_id: int
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime


class OrderUpdate(BaseModel):
    total_price: float
    status: str


class OrderCreatedData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    restaurant_id: int
    total_price: float
    status: str
    created_at: datetime
    updated_at: datetime


class OrderCreatedEvent(EventEnvelope[OrderCreatedData]):
    event_type: Literal["order.created"] = "order.created"
