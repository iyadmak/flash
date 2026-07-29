from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from flash.domain.order_status import OrderStatus
from flash.schemas.events import EventEnvelope


class OrderCreate(BaseModel):
    restaurant_id: int
    total_price: float


class OrderStatusUpdate(BaseModel):
    """The whole of what a client may change about a placed order.

    Replaces OrderUpdate, which let a caller assign status and total_price as
    bare fields -- so an order could be walked from `delivered` back to
    `pending`. A status change is a named operation now, not a field write, and
    `status: OrderStatus` rejects unknown values at the edge with a 422 before
    any service code runs.
    """

    status: OrderStatus


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    restaurant_id: int
    total_price: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


# Event payload. `status` stays a plain `str` here, unlike OrderRead: the event is
# a contract with other services, and they should not need a redeploy every time a
# state is added to our internal lifecycle. Narrowing it to the enum would also
# change the published JSON schema for no consumer's benefit.
#
# Deliberately a comment and not a docstring -- pydantic emits docstrings as the
# schema's `description`, so an internal design note would ship as part of the
# published contract. The snapshot test caught exactly that.
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
