"""Item models"""

from pydantic import BaseModel, ConfigDict


class ItemCreate(BaseModel):
    """Item creation Schema"""

    name: str
    price: float


class ItemUpdate(BaseModel):
    """Item update Schema"""

    name: str | None = None
    price: float | None = None


class ItemRead(BaseModel):
    """Item read Schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
