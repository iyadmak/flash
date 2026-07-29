from pydantic import BaseModel, ConfigDict

from flash.domain.money import Money


class ItemCreate(BaseModel):
    name: str
    price: Money


class ItemUpdate(BaseModel):
    name: str | None = None
    price: Money | None = None


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Money
    order_id: int


class ItemPage(BaseModel):
    items: list[ItemRead]
    next_cursor: str | None
