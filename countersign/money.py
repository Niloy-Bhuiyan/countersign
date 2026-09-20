"""Exact decimal arithmetic for the money path.

Every amount in Countersign is a ``Decimal``. Binary floats are rejected at the
boundary rather than tolerated, because a float that is wrong in the seventh
decimal place produces a tax check that fails on correct invoices and passes on
incorrect ones.

Rounding policy: two decimal places, ROUND_HALF_UP, applied at every step. Half-up
is what the invoices themselves use; banker's rounding would disagree with the
supplier's own arithmetic on exact halves.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from countersign.settings import settings

CENTS = Decimal(1).scaleb(-settings.money_places)


class MoneyError(ValueError):
    """Raised when a value cannot be used as an exact amount."""


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Coerce to Decimal, refusing float.

    A float is refused rather than converted: ``Decimal(0.1)`` is not ``0.1``, and
    silently accepting one puts an inexact value into the money path where nothing
    downstream can tell it apart from an exact one.
    """
    if isinstance(value, float):
        raise MoneyError(f"float {value!r} is not an exact amount; pass a str, int or Decimal")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise MoneyError(f"cannot read {value!r} as an amount") from exc


def money(value: Decimal | int | str) -> Decimal:
    """Round a value to the money scale using the documented policy."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def line_total(quantity: Decimal | int | str, unit_price: Decimal | int | str) -> Decimal:
    """Quantity times unit price, rounded once at the end."""
    return money(to_decimal(quantity) * to_decimal(unit_price))


def tax_of(base: Decimal | int | str, rate_pct: Decimal | int | str) -> Decimal:
    """Tax on a base amount at a percentage rate."""
    return money(to_decimal(base) * to_decimal(rate_pct) / Decimal(100))


def pct_deviation(observed: Decimal | int | str, expected: Decimal | int | str) -> Decimal:
    """Signed percentage deviation of ``observed`` from ``expected``.

    Returns four decimal places rather than the money scale: this is a ratio used
    for comparison against a tolerance, not an amount anyone is paid.
    """
    expected_d = to_decimal(expected)
    if expected_d == 0:
        raise MoneyError("cannot express a deviation from zero as a percentage")
    ratio = (to_decimal(observed) - expected_d) / expected_d * Decimal(100)
    return ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
