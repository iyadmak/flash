"""API v1 router"""

from fastapi import APIRouter
from flash.api.v1.routes import (
    item_routes,
    user_routes,
    restaurant_routes,
    order_routes,
    auth_routes,
)

router = APIRouter(prefix="/v1")

router.include_router(auth_routes.router)
router.include_router(item_routes.router)
router.include_router(user_routes.router)
router.include_router(restaurant_routes.router)
router.include_router(order_routes.router)
