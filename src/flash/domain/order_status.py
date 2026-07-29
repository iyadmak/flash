"""An order's lifecycle, as data.

Lives outside `models/` on purpose. Both the ORM model and the API schemas need
this vocabulary, and if it lived on the model then importing OrderRead would
transitively import `core.db` -- which builds a SQLAlchemy engine at import time
and would force the analytics consumer, which touches no relational database, to
carry a DATABASE_URL.

This module imports nothing. That is the point: it is the one place the rules
about what an order *is* can be read without wading through persistence or
transport.
"""

import enum


class OrderStatus(enum.StrEnum):
    """StrEnum so the persisted column and the JSON on the wire stay plain
    lowercase strings. Consumers of `order.created` keep reading a string and are
    unaffected when a state is added here."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# The lifecycle as a table rather than as branches scattered through services.
# Terminal states map to an empty set, so "where can this go next" and "is this
# finished" are the same question -- and a state with no outgoing edges cannot be
# escaped by any code path, not merely by the paths someone remembered to guard.
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

# What an order *contains* may only change while the restaurant has not yet
# accepted it. Once confirmed, the line items are part of a commercial record.
EDITABLE_STATUSES = frozenset({OrderStatus.PENDING})
