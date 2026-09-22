"""Each check against small hand-built records, so every rule is pinned exactly."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from countersign.checks import duplicate, price_variance, tax, three_way
from countersign.checks.base import ABSTAINED, FAILED, PASSED, Ledger
from countersign.extraction.schema import ExtractedInvoice, ExtractedLine
from countersign.money import line_total, tax_of
from countersign.reference import Delivery, DeliveryLine, POLine, PurchaseOrder, Reference, Vendor

D = Decimal
VENDOR = Vendor("VEN-1", "Meghna Steel Ltd", "meghna steel", "111", 30, "BDT")
ORDER_DATE = date(2026, 6, 1)


def order(po_id="PO-1", price="100.00", qty="10", ordered_at=ORDER_DATE, vendor_id="VEN-1"):
    return PurchaseOrder(
        id=po_id,
        po_number=f"PO/{po_id}",
        vendor_id=vendor_id,
        ordered_at=ordered_at,
        currency="BDT",
        total=D("0"),
        lines=(
            POLine(po_id, 1, "STL-ROD-12", "MS deformed bar 12mm", "MT", D(qty), D(price), D("15")),
        ),
    )


def reference(*orders, delivered: dict[str, str] | None = None) -> Reference:
    deliveries = {}
    for po_id, qty in (delivered or {}).items():
        deliveries[po_id] = [
            Delivery(
                f"DN-{po_id}",
                f"DN/{po_id}",
                po_id,
                ORDER_DATE + timedelta(days=5),
                (DeliveryLine(1, D(qty)),),
            )
        ]
    return Reference(
        vendors={VENDOR.id: VENDOR},
        orders={o.id: o for o in orders},
        deliveries_by_po=deliveries,
    )


def invoice(
    qty="10",
    price="100.00",
    number="INV-1",
    currency="BDT",
    po="PO-1",
    issued=date(2026, 6, 20),
    tax_total=None,
    rate="15",
):
    lt = line_total(qty, price)
    line = ExtractedLine(
        line_no=1,
        sku="STL-ROD-12",
        description="MS deformed bar 12mm",
        uom="MT",
        quantity=D(qty),
        unit_price=D(price),
        line_total=lt,
        tax_rate=None if rate is None else D(rate),
    )
    tx = D(tax_total) if tax_total else tax_of(lt, "15")
    return ExtractedInvoice(
        invoice_number=number,
        vendor_name="Meghna Steel Ltd",
        vendor_tax_id="111",
        invoice_date=issued,
        due_date=None,
        purchase_order_ref=po,
        currency=currency,
        lines=[line],
        subtotal=lt,
        tax_total=tx,
        total=lt + tx,
    )


# --- three-way match -------------------------------------------------------


def test_a_clean_invoice_passes_the_three_way_match():
    ref = reference(order(), delivered={"PO-1": "10"})
    results = three_way.run(invoice(), VENDOR, ref.orders["PO-1"], ref, Ledger())
    assert [r.outcome for r in results] == [PASSED]


def test_price_over_tolerance_fails_with_the_numbers():
    ref = reference(order(), delivered={"PO-1": "10"})
    [result] = three_way.run(invoice(price="103.00"), VENDOR, ref.orders["PO-1"], ref, Ledger())
    assert (result.outcome, result.rule) == (FAILED, "price_above_order")
    assert (result.observed, result.expected) == (D("103.00"), D("100.00"))


def test_price_within_tolerance_passes():
    ref = reference(order(), delivered={"PO-1": "10"})
    results = three_way.run(invoice(price="101.50"), VENDOR, ref.orders["PO-1"], ref, Ledger())
    assert results[0].outcome == PASSED


def test_billing_more_than_was_received_fails():
    ref = reference(order(), delivered={"PO-1": "8"})
    [result] = three_way.run(invoice(qty="10"), VENDOR, ref.orders["PO-1"], ref, Ledger())
    assert result.rule == "quantity_over_received"
    assert (result.observed, result.expected) == (D("10"), D("8"))


def test_quantity_already_billed_is_not_available_twice():
    ref = reference(order(), delivered={"PO-1": "10"})
    ledger = Ledger()
    first = three_way.run(invoice(qty="6"), VENDOR, ref.orders["PO-1"], ref, ledger)
    second = three_way.run(
        invoice(qty="6", number="INV-2"), VENDOR, ref.orders["PO-1"], ref, ledger
    )
    assert first[0].outcome == PASSED
    assert second[0].rule == "quantity_over_received"


def test_an_order_never_delivered_fails():
    ref = reference(order())
    results = three_way.run(invoice(), VENDOR, ref.orders["PO-1"], ref, Ledger())
    assert "no_delivery" in {r.rule for r in results}


def test_a_currency_other_than_the_orders_fails():
    ref = reference(order(), delivered={"PO-1": "10"})
    results = three_way.run(invoice(currency="USD"), VENDOR, ref.orders["PO-1"], ref, Ledger())
    assert "currency" in {r.rule for r in results}


def test_an_order_belonging_to_another_vendor_fails():
    ref = reference(order(vendor_id="VEN-9"), delivered={"PO-1": "10"})
    [result] = three_way.run(invoice(), VENDOR, ref.orders["PO-1"], ref, Ledger())
    assert result.rule == "po_other_vendor"


# --- price variance --------------------------------------------------------


def history(prices):
    return [
        order(po_id=f"PO-H{i}", price=p, ordered_at=ORDER_DATE - timedelta(days=30 * (i + 1)))
        for i, p in enumerate(prices)
    ]


def test_thin_history_abstains_rather_than_guessing():
    ref = reference(order(), *history(["100.00", "101.00"]))
    [result] = price_variance.run(invoice(), VENDOR, ref.orders["PO-1"], ref)
    assert (result.outcome, result.rule) == (ABSTAINED, "insufficient_history")


def test_a_material_outlier_fails():
    ref = reference(
        order(price="150.00"), *history(["100.00", "101.00", "99.00", "100.50", "99.50", "100.20"])
    )
    [result] = price_variance.run(invoice(price="150.00"), VENDOR, ref.orders["PO-1"], ref)
    assert (result.outcome, result.rule) == (FAILED, "above_history")
    assert result.expected == D("100.10")


def test_a_statistically_unusual_but_immaterial_move_passes():
    # z is enormous on this tight history, but 3% is not money at risk.
    ref = reference(
        order(price="103.00"), *history(["100.00", "100.10", "99.90", "100.05", "99.95"])
    )
    [result] = price_variance.run(invoice(price="103.00"), VENDOR, ref.orders["PO-1"], ref)
    assert result.outcome == PASSED


def test_identical_past_prices_abstain():
    ref = reference(order(), *history(["100.00"] * 6))
    [result] = price_variance.run(invoice(), VENDOR, ref.orders["PO-1"], ref)
    assert result.rule == "zero_spread"


# --- duplicates ------------------------------------------------------------


def _dup(inv, ledger, ref, doc="D1", sha="a"):
    return duplicate.run(inv, VENDOR, ref.orders["PO-1"], ref, ledger, document_id=doc, sha256=sha)


def test_the_same_number_from_the_same_vendor_is_a_duplicate():
    ref = reference(order(), delivered={"PO-1": "10"})
    ledger = Ledger()
    assert _dup(invoice(), ledger, ref)[0].outcome == PASSED
    [again] = _dup(invoice(number="inv 1", issued=date(2026, 7, 1)), ledger, ref, "D2", "b")
    assert again.rule == "same_number"


def test_the_same_number_from_another_vendor_is_not():
    ref = reference(order(), delivered={"PO-1": "10"})
    ledger = Ledger()
    _dup(invoice(), ledger, ref)
    ledger.seen[0].vendor_id = "VEN-OTHER"
    assert _dup(invoice(), ledger, ref, "D2", "b")[0].outcome == PASSED


def test_identical_bytes_are_a_duplicate_whatever_they_say():
    ref = reference(order(), delivered={"PO-1": "10"})
    ledger = Ledger()
    _dup(invoice(), ledger, ref, sha="same")
    results = _dup(invoice(number="INV-9"), ledger, ref, "D2", sha="same")
    assert "same_bytes" in {r.rule for r in results}


def test_equal_invoices_beyond_the_delivery_count_are_near_duplicates():
    ref = reference(order(), delivered={"PO-1": "10"})
    ledger = Ledger()
    _dup(invoice(), ledger, ref)
    [near] = _dup(invoice(number="INV-2"), ledger, ref, "D2", "b")
    assert near.rule == "same_order_same_amount"


# --- tax -------------------------------------------------------------------


def test_tax_that_recomputes_exactly_passes():
    assert tax.run(invoice(), order())[0].outcome == PASSED


def test_one_cent_of_tax_is_a_failure():
    [result] = tax.run(invoice(tax_total="150.01"), order())
    assert (result.outcome, result.observed, result.expected) == (FAILED, D("150.01"), D("150.00"))


def test_a_missing_rate_comes_from_the_order():
    assert tax.run(invoice(rate=None), order())[0].outcome == PASSED


def test_no_rate_and_no_order_abstains():
    assert tax.run(invoice(rate=None), None)[0].outcome == ABSTAINED


# --- vendor identity -------------------------------------------------------


@pytest.fixture
def twins():
    a = Vendor("VEN-A", "Teesta Industries Ltd", "teesta industries", "823", 30, "BDT")
    b = Vendor("VEN-B", "Teesta Industries Corporation", "teesta industries", "476", 30, "BDT")
    return Reference(vendors={a.id: a, b.id: b}, orders={}, deliveries_by_po={})


def test_two_companies_sharing_a_normalised_name_are_told_apart_by_tax_id(twins):
    assert twins.identify_vendor("TEESTA INDUSTRIES LIMITED", "476")[0].id == "VEN-B"
    assert twins.identify_vendor("Teesta Industries Corp.", "823")[0].id == "VEN-A"


def test_without_a_tax_id_the_twins_are_ambiguous(twins):
    assert twins.identify_vendor("Teesta Industries", None) == (None, "vendor_ambiguous")


def test_a_tax_id_that_contradicts_the_name_is_not_resolved(twins):
    assert twins.identify_vendor("Teesta Industries Ltd", "999") == (None, "vendor_tax_id_mismatch")


def test_an_unread_document_on_the_same_order_holds_the_match():
    """Found by the evaluation: a near-duplicate cleared because the invoice it
    copied had failed extraction and was invisible to the ledger."""
    ref = reference(order(), delivered={"PO-1": "10"})
    results = three_way.run(invoice(), VENDOR, ref.orders["PO-1"], ref, Ledger(), ["INV-UNREAD"])
    held = [r for r in results if r.rule == "order_has_unread_document"]
    assert held and held[0].outcome == ABSTAINED
    assert held[0].evidence["documents"] == ["INV-UNREAD"]
