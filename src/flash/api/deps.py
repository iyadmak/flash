"""API Dependencies"""

from typing import Annotated
from fastapi import Depends

from flash.core.config import Settings, get_settings
from flash.services.item_service import ItemService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_item_service() -> ItemService:
    """Get Item Service"""
    return ItemService()


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
