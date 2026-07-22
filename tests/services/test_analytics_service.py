"""Unit tests for AnalyticsService — no DB, no Mongo, just the service
against fakes for the daily-reports collection and the restaurant
existence check."""

from typing import Any

import pytest

from flash.core.exceptions import RestaurantNotFound
from flash.services.analytics_service import AnalyticsService


class FakeAggregateCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    async def to_list(self) -> list[dict[str, Any]]:
        return self._docs


class FakeDailyReportsCollection:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents

    async def aggregate(self, pipeline: list[dict[str, Any]]) -> FakeAggregateCursor:
        restaurant_id = pipeline[0]["$match"]["restaurant_id"]
        matching = [d for d in self._documents if d["restaurant_id"] == restaurant_id]
        if not matching:
            return FakeAggregateCursor([])
        return FakeAggregateCursor(
            [
                {
                    "order_count": sum(d["order_count"] for d in matching),
                    "revenue_cents": sum(d["revenue_cents"] for d in matching),
                }
            ]
        )


class FakeRestaurantService:
    def __init__(self, existing_ids: set[int]) -> None:
        self._existing_ids = existing_ids

    async def get(self, restaurant_id: int) -> None:
        if restaurant_id not in self._existing_ids:
            raise RestaurantNotFound()


async def test_get_restaurant_metrics_sums_across_daily_reports() -> None:
    daily_reports = FakeDailyReportsCollection(
        [
            {"restaurant_id": 5, "order_count": 2, "revenue_cents": 1500},
            {"restaurant_id": 5, "order_count": 1, "revenue_cents": 1000},
            {"restaurant_id": 6, "order_count": 10, "revenue_cents": 99999},
        ]
    )
    restaurant_service = FakeRestaurantService(existing_ids={5, 6})
    service = AnalyticsService(daily_reports, restaurant_service)

    metrics = await service.get_restaurant_metrics(5)

    assert metrics.restaurant_id == 5
    assert metrics.order_count == 3
    assert metrics.total_revenue == 25.00


async def test_get_restaurant_metrics_returns_zeros_for_restaurant_with_no_orders() -> (
    None
):
    daily_reports = FakeDailyReportsCollection([])
    restaurant_service = FakeRestaurantService(existing_ids={5})
    service = AnalyticsService(daily_reports, restaurant_service)

    metrics = await service.get_restaurant_metrics(5)

    assert metrics.order_count == 0
    assert metrics.total_revenue == 0.0


async def test_get_restaurant_metrics_raises_for_nonexistent_restaurant() -> None:
    daily_reports = FakeDailyReportsCollection([])
    restaurant_service = FakeRestaurantService(existing_ids=set())
    service = AnalyticsService(daily_reports, restaurant_service)

    with pytest.raises(RestaurantNotFound):
        await service.get_restaurant_metrics(999)
