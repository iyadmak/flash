"""Item Endpoints"""

from fastapi import APIRouter
from flash.schemas.item import Item
from flash.services.item_service import get_items

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
def list_items() -> list[Item]:
    """Get all items"""
    return get_items()
