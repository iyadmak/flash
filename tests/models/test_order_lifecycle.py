"""Tests for the rules OrderModel owns.

No service, no repository, no database -- these exercise the aggregate's own
behaviour directly, which is the point of moving the rules onto the model. If
these pass, every caller that goes through change_status/assert_editable
inherits the guarantee.
"""

import pytest

from flash.core.exceptions import IllegalStatusTransition, OrderNotMutable
from flash.domain.order_status import (
    ALLOWED_TRANSITIONS,
    EDITABLE_STATUSES,
    OrderStatus,
)
from flash.models.order_model import OrderModel

TERMINAL_STATUSES = frozenset(
    status for status, onward in ALLOWED_TRANSITIONS.items() if not onward
)


def an_order(status: OrderStatus = OrderStatus.PENDING) -> OrderModel:
    return OrderModel(user_id=1, restaurant_id=2, total_price=42.50, status=status)


class TestTransitionTable:
    def test_every_status_has_an_entry(self) -> None:
        """A status missing from the table would raise KeyError on any attempt to
        move it, rather than a clean domain error."""
        assert set(ALLOWED_TRANSITIONS) == set(OrderStatus)

    def test_no_transition_targets_an_unknown_status(self) -> None:
        for onward in ALLOWED_TRANSITIONS.values():
            assert onward <= set(OrderStatus)

    def test_no_status_transitions_to_itself(self) -> None:
        for status, onward in ALLOWED_TRANSITIONS.items():
            assert status not in onward

    def test_delivered_and_cancelled_are_the_terminal_states(self) -> None:
        assert TERMINAL_STATUSES == {OrderStatus.DELIVERED, OrderStatus.CANCELLED}

    def test_every_status_is_reachable_from_pending(self) -> None:
        """Guards against adding a state and forgetting to wire an edge into it,
        which would leave dead vocabulary that no order can ever hold."""
        reached = {OrderStatus.PENDING}
        frontier = [OrderStatus.PENDING]
        while frontier:
            for onward in ALLOWED_TRANSITIONS[frontier.pop()]:
                if onward not in reached:
                    reached.add(onward)
                    frontier.append(onward)
        assert reached == set(OrderStatus)


class TestChangeStatus:
    @pytest.mark.parametrize(
        ("start", "target"),
        [
            (start, target)
            for start, onward in ALLOWED_TRANSITIONS.items()
            for target in onward
        ],
    )
    def test_allows_every_edge_in_the_table(
        self, start: OrderStatus, target: OrderStatus
    ) -> None:
        order = an_order(status=start)
        order.change_status(target)
        assert order.status is target

    @pytest.mark.parametrize(
        ("start", "target"),
        [
            (start, target)
            for start, onward in ALLOWED_TRANSITIONS.items()
            for target in set(OrderStatus) - onward
        ],
    )
    def test_refuses_every_edge_absent_from_the_table(
        self, start: OrderStatus, target: OrderStatus
    ) -> None:
        order = an_order(status=start)
        with pytest.raises(IllegalStatusTransition):
            order.change_status(target)
        assert order.status is start

    def test_the_error_names_both_states(self) -> None:
        order = an_order(status=OrderStatus.DELIVERED)
        with pytest.raises(IllegalStatusTransition) as excinfo:
            order.change_status(OrderStatus.PENDING)
        assert "delivered" in str(excinfo.value)
        assert "pending" in str(excinfo.value)


class TestAssertEditable:
    def test_pending_orders_are_editable(self) -> None:
        an_order(status=OrderStatus.PENDING).assert_editable()

    @pytest.mark.parametrize("status", sorted(set(OrderStatus) - EDITABLE_STATUSES))
    def test_everything_past_pending_is_frozen(self, status: OrderStatus) -> None:
        """Once the restaurant has accepted an order, its line items are part of a
        commercial record -- including while it is still in flight, not only once
        it is delivered."""
        with pytest.raises(OrderNotMutable):
            an_order(status=status).assert_editable()
