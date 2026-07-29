"""An order's lifecycle, as data.

Outside `models/` so schemas can share it without importing `core.db`, which
builds an engine at import time -- the analytics consumer needs no DATABASE_URL.
"""

import enum


class OrderStatus(enum.StrEnum):
    """StrEnum so the column and the JSON on the wire stay lowercase strings."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# A table, not branches scattered through services. Terminal states map to an empty
# set, so no code path can escape them -- not just the paths someone guarded.
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.CONFIRMED, OrderStatus.CANCELLED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.PREPARING, OrderStatus.CANCELLED}),
    OrderStatus.PREPARING: frozenset(
        {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED}
    ),
    OrderStatus.OUT_FOR_DELIVERY: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

# Contents may change only before the restaurant accepts the order.
EDITABLE_STATUSES = frozenset({OrderStatus.PENDING})
