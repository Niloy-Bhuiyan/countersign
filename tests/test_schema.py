"""The extraction contract, and what it refuses to accept."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from countersign.extraction.schema import RawInvoice, RawLine, parse_raw


def a_raw_invoice(**overrides) -> RawInvoice:
    defaults = dict(
        invoice_number="INV-2026-00001",
        vendor_name="Meghna Steel Ltd",
        invoice_date="15 Mar 2026",
        due_date="14 Apr 2026",
        purchase_order_ref="PO-0006",
        currency="BDT",
        lines=[
            RawLine(
                line_no=1,
                sku="STL-ROD-12",
                description="MS deformed bar 12mm",
                uom="MT",
                quantity="14",
                unit_price="BDT 89,000.00",
                line_total="BDT 1,246,000.00",
                tax_rate="15",
            )
        ],
        subtotal="BDT 1,246,000.00",
        tax_total="BDT 186,900.00",
        total="BDT 1,432,900.00",
    )
    return RawInvoice(**{**defaults, **overrides})


def test_a_clean_extraction_types_completely():
    outcome = parse_raw(a_raw_invoice())

    assert outcome.ok
    invoice = outcome.invoice
    assert invoice.invoice_date == date(2026, 3, 15)
    assert invoice.currency == "BDT"
    assert invoice.total == Decimal("1432900.00")
    assert invoice.lines[0].unit_price == Decimal("89000.00")
    assert invoice.lines[0].tax_rate == Decimal("15")


def test_every_failure_is_reported_not_just_the_first():
    """Three bad fields should be one review item listing three problems."""
    outcome = parse_raw(
        a_raw_invoice(invoice_date="not a date", currency="Rupees", total="see attached")
    )

    assert not outcome.ok
    assert {failure.field for failure in outcome.failures} == {
        "invoice_date",
        "currency",
        "total",
    }
    assert all(failure.printed for failure in outcome.failures)


def test_a_missing_invoice_number_is_a_failure_not_an_empty_string():
    outcome = parse_raw(a_raw_invoice(invoice_number="   "))
    assert not outcome.ok
    assert outcome.failures[0].field == "invoice_number"


def test_an_invoice_with_no_lines_is_a_failure():
    outcome = parse_raw(a_raw_invoice(lines=[]))
    assert not outcome.ok
    assert any(failure.field == "lines" for failure in outcome.failures)


def test_a_failed_line_is_reported_by_its_line_number():
    outcome = parse_raw(
        a_raw_invoice(
            lines=[
                RawLine(
                    line_no=1, description="ok", quantity="10", unit_price="5", line_total="50"
                ),
                RawLine(
                    line_no=2, description="bad", quantity="ten", unit_price="5", line_total="50"
                ),
            ]
        )
    )
    assert not outcome.ok
    assert outcome.failures[0].field == "lines[2].quantity"


def test_the_model_cannot_return_a_field_that_is_not_in_the_schema():
    """A document instructing the model to set an approval flag has nothing to set."""
    with pytest.raises(ValidationError):
        RawInvoice(invoice_number="X", approved=True)

    with pytest.raises(ValidationError):
        RawLine(line_no=1, priority="urgent")


def test_no_field_in_the_schema_expresses_a_decision():
    decision_words = {"approve", "approved", "verified", "status", "action", "priority", "pay"}
    for field in list(RawInvoice.model_fields) + list(RawLine.model_fields):
        assert not decision_words & set(field.lower().split("_"))
