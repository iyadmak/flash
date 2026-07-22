from typing import Any, Protocol
from collections.abc import Awaitable
from flash.schemas.analytics_schema import RestaurantMetrics


class DailyReportsCollectionProtocol(Protocol):
    def aggregate(self, pipeline: list[dict[str, Any]]) -> Awaitable[Any]: ...


class RestaurantExistenceCheckProtocol(Protocol):
    async def get(self, restaurant_id: int) -> Any: ...


class AnalyticsService:
    def __init__(
        self,
        daily_reports: DailyReportsCollectionProtocol,
        restaurant_service: RestaurantExistenceCheckProtocol,
    ) -> None:
        self._daily_reports = daily_reports
        self._restaurant_service = restaurant_service

    async def get_restaurant_metrics(self, restaurant_id: int) -> RestaurantMetrics:
        await self._restaurant_service.get(restaurant_id)
        cursor = await self._daily_reports.aggregate(
            [
                {"$match": {"restaurant_id": restaurant_id}},
                {
                    "$group": {
                        "_id": None,
                        "order_count": {"$sum": "$order_count"},
                        "revenue_cents": {"$sum": "$revenue_cents"},
                    }
                },
            ]
        )
        totals = await cursor.to_list()
        order_count = totals[0]["order_count"] if totals else 0
        revenue_cents = totals[0]["revenue_cents"] if totals else 0

        return RestaurantMetrics(
            restaurant_id=restaurant_id,
            order_count=order_count,
            total_revenue=revenue_cents / 100,
        )
