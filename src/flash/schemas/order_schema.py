from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from flash.domain.money import Money
from flash.domain.order_status import OrderStatus
from flash.schemas.events import EventEnvelope


class OrderCreate(BaseModel):
    restaurant_id: int
    total_price: Money


class OrderStatusUpdate(BaseModel):
    """A status change is a named operation, not a field write.

    The enum rejects unknown values with a 422 before any service code runs.
    """

    status: OrderStatus


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    restaurant_id: int
    total_price: Money
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


# `status` and `total_price` stay primitives, unlike OrderRead: narrowing them would
# couple consumers to our enum and to Decimal's string serialization. Changing the
# wire format needs its own version bump.
#
# A comment, not a docstring: pydantic ships docstrings as the schema's `description`.
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
