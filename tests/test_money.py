"""The money path must be exact. These tests pin the cases a float gets wrong."""

from decimal import Decimal

import pytest

from countersign.money import MoneyError, line_total, money, pct_deviation, tax_of


def test_float_is_refused_at_the_boundary():
    with pytest.raises(MoneyError):
        money(1234.56)


def test_strings_and_integers_are_accepted():
    assert money("1234.56") == Decimal("1234.56")
    assert money(1200) == Decimal("1200.00")


def test_half_up_rounding_where_float_rounds_down():
    # round(2.675, 2) is 2.67 in Python, because the nearest double to 2.675 is
    # 2.67499999999999982236431605997495353221893310546875. An invoice that shows
    # 2.68 would fail a tax check computed in float.
    assert round(2.675, 2) == 2.67
    assert money("2.675") == Decimal("2.68")


def test_repeated_addition_does_not_drift():
    # A 7-line invoice of 0.10 each. In float the total is 0.7000000000000001,
    # which is enough for an equality check against the printed subtotal to fail.
    # Not every line count drifts, which is what makes the bug hard to notice.
    assert sum([0.1] * 7) == 0.7000000000000001

    decimal_total = sum((money("0.10") for _ in range(7)), Decimal(0))
    assert decimal_total == Decimal("0.70")


def test_line_total_rounds_once_at_the_end():
    # 3 x 19.995 is 59.985, which rounds to 59.99. Rounding each factor first
    # would give 3 x 20.00 = 60.00 and overstate the line by a cent.
    assert line_total("3", "19.995") == Decimal("59.99")


def test_tax_of_applies_the_money_scale():
    assert tax_of("1000.00", "7.5") == Decimal("75.00")
    assert tax_of("333.33", "15") == Decimal("50.00")


def test_pct_deviation_is_signed():
    assert pct_deviation("110", "100") == Decimal("10.0000")
    assert pct_deviation("90", "100") == Decimal("-10.0000")


def test_pct_deviation_refuses_a_zero_baseline():
    with pytest.raises(MoneyError):
        pct_deviation("10", "0")
