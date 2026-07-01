from pydantic import BaseModel
from pydantic import ConfigDict


class RestaurantCreate(BaseModel):
    owner_id: int
    name: str
    address: str
    phone: str | None = None
    email: str | None = None


class RestaurantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    phone: str | None = None
    email: str | None = None


class RestaurantUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
