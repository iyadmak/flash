from typing import Any

from flash.consumers.analytics import handle
from flash.schemas.order_schema import OrderCreatedData, OrderCreatedEvent


class FakeUpdateResult:
    def __init__(self, upserted_id: str | None) -> None:
        self.upserted_id = upserted_id


class FakeReportsCollection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}

    async def replace_one(
        self, filter: dict[str, Any], replacement: dict[str, Any], upsert: bool = False
    ) -> FakeUpdateResult:
        doc_id = filter["_id"]
        is_new = doc_id not in self.documents
        self.documents[doc_id] = replacement
        return FakeUpdateResult(upserted_id=doc_id if is_new else None)


class FakeDailyReportsCollection:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}

    async def update_one(
        self, filter: dict[str, Any], update: dict[str, Any], upsert: bool = False
    ) -> None:
        doc_id = filter["_id"]
        doc = self.documents.setdefault(doc_id, {})
        for field, amount in update.get("$inc", {}).items():
            doc[field] = doc.get(field, 0) + amount
        for field, value in update.get("$setOnInsert", {}).items():
            doc.setdefault(field, value)


def make_event(
    restaurant_id: int, total_price: float, created_at: str = "2026-01-01T00:00:00Z"
) -> OrderCreatedEvent:
    return OrderCreatedEvent(
        data=OrderCreatedData(
            id=1,
            user_id=1,
            restaurant_id=restaurant_id,
            total_price=total_price,
            status="pending",
            created_at=created_at,
            updated_at=created_at,
        )
    )


async def test_report_document_is_stored_with_event_id_as_mongo_id() -> None:
    reports = FakeReportsCollection()
    daily_reports = FakeDailyReportsCollection()
    event = make_event(restaurant_id=5, total_price=10.00)

    await handle(reports, daily_reports, event)

    stored = reports.documents[str(event.event_id)]
    assert stored["data"]["restaurant_id"] == 5
    assert stored["data"]["total_price"] == 10.00


async def test_replaying_same_event_id_does_not_duplicate_report() -> None:
    reports = FakeReportsCollection()
    daily_reports = FakeDailyReportsCollection()
    event = make_event(restaurant_id=5, total_price=10.00)

    await handle(reports, daily_reports, event)
    await handle(
        reports, daily_reports, event
    )  # simulates redelivery of the same event

    assert len(reports.documents) == 1
    assert reports.documents[str(event.event_id)]["data"]["restaurant_id"] == 5


async def test_daily_report_increments_order_count_and_revenue_cents() -> None:
    reports = FakeReportsCollection()
    daily_reports = FakeDailyReportsCollection()
    event = make_event(
        restaurant_id=5, total_price=12.50, created_at="2026-07-20T10:00:00Z"
    )

    await handle(reports, daily_reports, event)

    doc = daily_reports.documents["5:2026-07-20"]
    assert doc["order_count"] == 1
    assert doc["revenue_cents"] == 1250
    assert doc["restaurant_id"] == 5
    assert doc["report_date"] == "2026-07-20"


async def test_daily_report_accumulates_across_multiple_orders_same_day() -> None:
    reports = FakeReportsCollection()
    daily_reports = FakeDailyReportsCollection()

    await handle(
        reports,
        daily_reports,
        make_event(
            restaurant_id=5, total_price=10.00, created_at="2026-07-20T10:00:00Z"
        ),
    )
    await handle(
        reports,
        daily_reports,
        make_event(
            restaurant_id=5, total_price=5.00, created_at="2026-07-20T18:00:00Z"
        ),
    )

    doc = daily_reports.documents["5:2026-07-20"]
    assert doc["order_count"] == 2
    assert doc["revenue_cents"] == 1500


async def test_daily_report_different_restaurants_tracked_separately_same_day() -> None:
    reports = FakeReportsCollection()
    daily_reports = FakeDailyReportsCollection()

    await handle(
        reports,
        daily_reports,
        make_event(
            restaurant_id=5, total_price=10.00, created_at="2026-07-20T10:00:00Z"
        ),
    )
    await handle(
        reports,
        daily_reports,
        make_event(
            restaurant_id=6, total_price=20.00, created_at="2026-07-20T10:00:00Z"
        ),
    )

    assert daily_reports.documents["5:2026-07-20"]["order_count"] == 1
    assert daily_reports.documents["6:2026-07-20"]["order_count"] == 1


async def test_daily_report_buckets_by_restaurant_and_date() -> None:
    reports = FakeReportsCollection()
    daily_reports = FakeDailyReportsCollection()

    await handle(
        reports,
        daily_reports,
        make_event(
            restaurant_id=5, total_price=10.00, created_at="2026-07-20T10:00:00Z"
        ),
    )
    await handle(
        reports,
        daily_reports,
        make_event(
            restaurant_id=5, total_price=20.00, created_at="2026-07-21T10:00:00Z"
        ),
    )

    assert daily_reports.documents["5:2026-07-20"]["order_count"] == 1
    assert daily_reports.documents["5:2026-07-21"]["order_count"] == 1
    assert len(daily_reports.documents) == 2


async def test_replaying_same_event_does_not_double_count_daily_report() -> None:
    reports = FakeReportsCollection()
    daily_reports = FakeDailyReportsCollection()
    event = make_event(
        restaurant_id=5, total_price=10.00, created_at="2026-07-20T10:00:00Z"
    )

    await handle(reports, daily_reports, event)
    await handle(reports, daily_reports, event)  # simulates redelivery

    doc = daily_reports.documents["5:2026-07-20"]
    assert doc["order_count"] == 1
    assert doc["revenue_cents"] == 1000
