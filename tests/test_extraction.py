"""Extraction end to end on real rendered documents, one per layout and format."""

import random
from decimal import Decimal

import pytest

from countersign.extraction.offline import from_text
from countersign.extraction.pipeline import extract_document
from countersign.extraction.schema import ExtractedInvoice, ExtractedLine
from countersign.extraction.validators import validate
from countersign.intake import ENCRYPTED, IMAGE_ONLY, UNREADABLE, read
from countersign.vendors import normalise_vendor_name
from data.render.layouts import LAYOUTS, layout_for_vendor
from data.render.mess import write_corrupt_pdf, write_encrypted_pdf, write_image_only_pdf
from data.render.pdf import render
from data.render.sheets import render_csv, render_xlsx


def _one_invoice_per_layout(corpus):
    chosen = {}
    for invoice in corpus["invoices"]:
        chosen.setdefault(layout_for_vendor(invoice.vendor_id).key, invoice)
    assert len(chosen) == len(LAYOUTS)
    return chosen


def _assert_matches(extracted: ExtractedInvoice, invoice, vendor):
    assert extracted.invoice_number == invoice.invoice_number
    assert normalise_vendor_name(extracted.vendor_name) == vendor.normalised_name
    assert extracted.invoice_date == invoice.issued_at
    assert extracted.due_date == invoice.due_at
    assert extracted.purchase_order_ref == invoice.po_id
    assert extracted.total == invoice.total
    assert [line.quantity for line in extracted.lines] == [line.quantity for line in invoice.lines]


def test_every_pdf_layout_extracts_completely(corpus, tmp_path):
    vendors = {vendor.id: vendor for vendor in corpus["vendors"]}
    for key, invoice in _one_invoice_per_layout(corpus).items():
        vendor = vendors[invoice.vendor_id]
        path = render(invoice, vendor, tmp_path / f"{key}.pdf")
        outcome = extract_document(path)
        assert outcome.ok, (key, outcome.failures)
        _assert_matches(outcome.invoice, invoice, vendor)


@pytest.mark.parametrize("renderer", [render_csv, render_xlsx])
def test_spreadsheet_formats_extract_completely(corpus, tmp_path, renderer):
    invoice = corpus["invoices"][3]
    vendor = next(v for v in corpus["vendors"] if v.id == invoice.vendor_id)
    suffix = ".csv" if renderer is render_csv else ".xlsx"
    outcome = extract_document(renderer(invoice, vendor, tmp_path / f"doc{suffix}"))
    assert outcome.ok, outcome.failures
    _assert_matches(outcome.invoice, invoice, vendor)


def test_a_price_run_into_the_unit_column_is_still_read():
    raw = from_text(
        "Meghna Steel Ltd\nBIN/TIN: 1\n"
        "3 RAW-CLK-BULK Imported clinker, bulk 32 MT10,187.84 BDT 15 326,010.88 BDT"
    )
    assert raw.lines[0].quantity == "32"
    assert raw.lines[0].unit_price.startswith("10,187.84")


@pytest.mark.parametrize(
    ("writer", "status"),
    [
        (write_corrupt_pdf, UNREADABLE),
        (write_image_only_pdf, IMAGE_ONLY),
        (lambda path: write_encrypted_pdf(path, "X"), ENCRYPTED),
    ],
)
def test_unreadable_documents_are_quarantined_not_raised(tmp_path, writer, status):
    path = writer(tmp_path / "bad.pdf")
    assert read(path).status == status
    outcome = extract_document(path)
    assert not outcome.ok
    assert outcome.review_reason == status


def _invoice(**changes) -> ExtractedInvoice:
    line = ExtractedLine(
        line_no=1,
        sku="X",
        description="x",
        uom="PCS",
        quantity=Decimal("3"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("30.00"),
        tax_rate=None,
    )
    fields = dict(
        invoice_number="1",
        vendor_name="v",
        invoice_date="2026-01-01",
        due_date=None,
        purchase_order_ref=None,
        currency="BDT",
        lines=[line],
        subtotal=Decimal("30.00"),
        tax_total=Decimal("4.50"),
        total=Decimal("34.50"),
    )
    fields.update(changes)
    return ExtractedInvoice(**fields)


def test_validators_pass_a_consistent_invoice():
    assert validate(_invoice()) == []


def test_a_dropped_line_is_caught_by_the_subtotal():
    # The case that motivated the validators: the reader returned fewer lines
    # than the document has, and every field it did return parsed cleanly.
    failures = validate(_invoice(subtotal=Decimal("45.00"), total=Decimal("49.50")))
    assert [failure.field for failure in failures] == ["subtotal"]


def test_a_misread_line_total_is_caught():
    bad = _invoice().lines[0].model_copy(update={"line_total": Decimal("300.00")})
    failures = validate(_invoice(lines=[bad]))
    assert failures[0].field == "lines[1].line_total"


def test_a_gap_in_line_numbers_is_caught():
    line = _invoice().lines[0].model_copy(update={"line_no": 2})
    assert any(failure.field == "lines" for failure in validate(_invoice(lines=[line])))


def test_offline_extraction_is_deterministic(corpus, tmp_path):
    invoice = random.Random(0).choice(corpus["invoices"])
    vendor = next(v for v in corpus["vendors"] if v.id == invoice.vendor_id)
    path = render(invoice, vendor, tmp_path / "same.pdf")
    assert extract_document(path).invoice == extract_document(path).invoice
