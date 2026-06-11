"""API v1 router"""

from fastapi import APIRouter
from flash.api.v1.routes import item

router = APIRouter(prefix="/v1")

router.include_router(item.router)
