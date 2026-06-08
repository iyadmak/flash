"""Item models"""

from pydantic import BaseModel


class Item(BaseModel):
    """Item Schema"""

    id: int
    name: str
    price: float
