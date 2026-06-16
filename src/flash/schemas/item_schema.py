from pydantic import BaseModel, ConfigDict


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
