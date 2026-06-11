"""Item Endpoints"""

from fastapi import APIRouter
from flash.schemas.item import Item
from flash.api.deps import ItemServiceDep

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
def list_items(service: ItemServiceDep) -> list[Item]:
    """Get all items"""
    return service.get_items()
