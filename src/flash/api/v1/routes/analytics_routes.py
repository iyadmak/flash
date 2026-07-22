from fastapi import APIRouter, Depends
from flash.api.deps import AnalyticsServiceDep, get_current_user
from flash.schemas.analytics_schema import RestaurantMetrics

router = APIRouter(
    prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)]
)


@router.get("/restaurants/{restaurant_id}")
async def get_restaurant_metrics(
    analytics_service: AnalyticsServiceDep, restaurant_id: int
) -> RestaurantMetrics:
    return await analytics_service.get_restaurant_metrics(restaurant_id)
