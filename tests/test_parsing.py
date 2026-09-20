"""Parsers are tested against every notation the four layouts actually print.

These run without a model. If extraction is wrong, this suite says whether the
cause was locating the field or reading it.
"""

from datetime import date
from decimal import Decimal

import pytest

from countersign.extraction.parsing import (
    ParseError,
    parse_amount,
    parse_currency,
    parse_date,
    parse_rate,
)


@pytest.mark.parametrize(
    "printed",
    [
        "BDT 1,234.56",
        "1,234.56 BDT",
        "Tk. 1,234.56",
        "Tk 1,234.56",
        "1,234.56",
        "1234.56",
        " 1,234.56 ",
        " 1,234.56",
    ],
)
def test_one_amount_written_eight_ways(printed):
    assert parse_amount(printed) == Decimal("1234.56")


def test_large_amounts_keep_every_group():
    assert parse_amount("BDT 1,328,821.78") == Decimal("1328821.78")


def test_negatives_in_both_accounting_notations():
    assert parse_amount("(1,200.00)") == Decimal("-1200.00")
    assert parse_amount("1,200.00-") == Decimal("-1200.00")
    assert parse_amount("-1,200.00") == Decimal("-1200.00")


def test_a_comma_that_is_not_a_thousands_separator_is_refused():
    # Some locales use a comma as the decimal mark. Silently dropping it would
    # turn 1,5 into 15 and overbill by a factor of ten.
    with pytest.raises(ParseError):
        parse_amount("1,5")


@pytest.mark.parametrize("junk", ["", "   ", "N/A", "-", "see attached", "12.34.56", "1.2.3"])
def test_unreadable_amounts_raise_rather_than_guess(junk):
    with pytest.raises(ParseError):
        parse_amount(junk)


def test_amount_never_accepts_a_float():
    with pytest.raises(ParseError):
        parse_amount(1234.56)


@pytest.mark.parametrize(
    "printed",
    ["2026-03-15", "15 Mar 2026", "15 March 2026", "Mar 15, 2026", "15/03/2026", "15-03-2026"],
)
def test_one_date_written_six_ways(printed):
    assert parse_date(printed) == date(2026, 3, 15)


def test_day_first_is_the_documented_reading():
    # Every layout in this corpus is day-first; ISO is unambiguous anyway.
    assert parse_date("03/04/2026") == date(2026, 4, 3)


@pytest.mark.parametrize("junk", ["", "31/02/2026", "not a date", "2026", "15/13/2026"])
def test_unreadable_dates_raise_rather_than_guess(junk):
    with pytest.raises(ParseError):
        parse_date(junk)


@pytest.mark.parametrize(
    ("printed", "expected"), [("15", "15"), ("15%", "15"), ("7.5 %", "7.5"), ("0", "0")]
)
def test_tax_rates_with_and_without_a_sign(printed, expected):
    assert parse_rate(printed) == Decimal(expected)


@pytest.mark.parametrize(
    ("printed", "expected"),
    [("BDT", "BDT"), ("bdt", "BDT"), ("Tk.", "BDT"), ("Taka", "BDT"), ("USD", "USD")],
)
def test_currency_aliases_that_appear_on_these_documents(printed, expected):
    assert parse_currency(printed) == expected


@pytest.mark.parametrize("junk", ["", "Rupees", "B", "BDTX"])
def test_unknown_currencies_raise_rather_than_defaulting(junk):
    # Defaulting to BDT would silently erase a currency mismatch, which is one of
    # the defects the checks exist to catch.
    with pytest.raises(ParseError):
        parse_currency(junk)
