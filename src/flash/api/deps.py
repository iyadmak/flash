"""API Dependencies"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from flash.core.config import Settings, get_settings
from flash.services.item_service import ItemService
from flash.core.db import get_async_session


SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def get_item_service() -> ItemService:
    """Get Item Service"""
    return ItemService()


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
