"""Tests for the Money type.

The first class states the property the whole change exists for; the rest cover
what the validator refuses. Without these, "we switched to Decimal" is an
assertion in a commit message rather than something the suite would notice
regressing.
"""

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from flash.domain.money import Money, zero

money = TypeAdapter(Money)


class TestWhyDecimal:
    def test_float_addition_does_not_hold_for_money(self) -> None:
        """The reason total == sum(items) could not be trusted on floats."""
        assert 0.1 + 0.2 != 0.3

    def test_decimal_addition_does(self) -> None:
        assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")

    def test_summing_a_realistic_basket_is_exact(self) -> None:
        """A 0.10 side, a 0.20 drink and a 9.99 main is 10.29. Summed as floats it
        is 10.290000000000001, so an order total compared against its own line
        items would disagree with itself for no reason a user could be told.

        Note the failure is not reliable, which is what makes it nasty: ten 0.10s
        happen to sum to exactly 1.0 because the errors cancel. Whether a given
        basket is wrong depends on the prices in it.
        """
        basket = ["0.10", "0.20", "9.99"]
        assert sum((Decimal(p) for p in basket), zero()) == Decimal("10.29")
        assert sum(float(p) for p in basket) != 10.29

    def test_zero_carries_the_scale(self) -> None:
        assert zero() == Decimal("0.00")
        assert sum([Decimal("1.50")], zero()) == Decimal("1.50")


class TestAccepts:
    @pytest.mark.parametrize("raw", ["0", "0.00", "12", "12.5", "12.50", "99999999.99"])
    def test_valid_amounts(self, raw: str) -> None:
        assert money.validate_python(Decimal(raw)) == Decimal(raw)

    def test_a_json_string(self) -> None:
        """The format our own API emits has to be one it can read back."""
        assert money.validate_json('"42.50"') == Decimal("42.50")

    def test_a_json_number(self) -> None:
        assert money.validate_json("42.50") == Decimal("42.50")


class TestRefuses:
    def test_a_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            money.validate_python(Decimal("-0.01"))

    def test_more_precision_than_the_column_stores(self) -> None:
        """The important one. NUMERIC(10, 2) would round 12.567 to 12.57 on write
        with no error, so the amount the client sent and the amount stored would
        differ silently. Rejecting is the only honest answer."""
        with pytest.raises(ValidationError):
            money.validate_python(Decimal("12.567"))

    def test_more_digits_than_the_column_holds(self) -> None:
        with pytest.raises(ValidationError):
            money.validate_python(Decimal("123456789.00"))
