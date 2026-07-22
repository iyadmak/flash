from flash.core.adapters.cache import CacheProtocol
from flash.schemas.analytics_schema import RestaurantMetrics
from flash.services.restaurant_service import RestaurantService


def _order_count_key(restaurant_id: int) -> str:
    return f"metrics:restaurant:{restaurant_id}:order_count"


def _revenue_cents_key(restaurant_id: int) -> str:
    return f"metrics:restaurant:{restaurant_id}:revenue_cents"


class AnalyticsService:
    def __init__(
        self, cache: CacheProtocol, restaurant_service: RestaurantService
    ) -> None:
        self._cache = cache
        self._restaurant_service = restaurant_service

    async def get_restaurant_metrics(self, restaurant_id: int) -> RestaurantMetrics:
        await self._restaurant_service.get(restaurant_id)

        order_count = await self._cache.get(_order_count_key(restaurant_id))
        revenue_cents = await self._cache.get(_revenue_cents_key(restaurant_id))

        return RestaurantMetrics(
            restaurant_id=restaurant_id,
            order_count=int(order_count or 0),
            total_revenue=int(revenue_cents or 0) / 100,
        )
