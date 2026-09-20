"""Invariants the corpus has to hold, or the evaluation measures nothing.

The evaluation scores the checks against the generator's ground truth. That is
only meaningful if a clean invoice is genuinely clean and a defective one is
defective for exactly the recorded reason. These tests are what make the numbers
in the README worth reading.
"""

from collections import Counter

import pytest

from countersign.money import line_total
from countersign.settings import settings
from data.defects import DEFECT_RATE, EXPECTED_CHECK
from data.generate import build
from data.invoices import totals_for


def test_counts_match_the_manifest(corpus):
    assert len(corpus["vendors"]) == 40
    assert len(corpus["orders"]) == 460
    assert len(corpus["invoices"]) == 500


def test_ground_truth_covers_exactly_the_defective_invoices(corpus):
    flagged = {inv.id for inv in corpus["invoices"] if inv.defect}
    recorded = {row["invoice_id"] for row in corpus["truth"]}
    assert flagged == recorded


def test_each_defective_invoice_carries_exactly_one_defect(corpus):
    recorded = [row["invoice_id"] for row in corpus["truth"]]
    assert len(recorded) == len(set(recorded))


def test_defect_rate_is_close_to_the_target(corpus):
    rate = len(corpus["truth"]) / len(corpus["invoices"])
    assert abs(rate - DEFECT_RATE) < 0.01


def test_every_defect_code_is_represented(corpus):
    seen = Counter(row["defect_code"] for row in corpus["truth"])
    assert set(seen) == set(EXPECTED_CHECK)
    assert min(seen.values()) >= 5


def test_clean_invoices_are_arithmetically_exact(corpus):
    """A check that fires on one of these is a false positive, unambiguously."""
    for invoice in corpus["invoices"]:
        if invoice.defect:
            continue
        subtotal, tax_total, total = totals_for(invoice.lines)
        assert (subtotal, tax_total, total) == (
            invoice.subtotal,
            invoice.tax_total,
            invoice.total,
        ), invoice.id
        for line in invoice.lines:
            assert line_total(line.quantity, line.unit_price) == line.line_total


def test_only_the_tax_defect_breaks_the_arithmetic(corpus):
    """Otherwise every planted defect would also look like a tax defect."""
    for invoice in corpus["invoices"]:
        if not invoice.defect or invoice.defect == "TAX_MISMATCH":
            continue
        subtotal, tax_total, total = totals_for(invoice.lines)
        assert (subtotal, tax_total, total) == (
            invoice.subtotal,
            invoice.tax_total,
            invoice.total,
        ), f"{invoice.id} ({invoice.defect})"


def test_price_history_defects_agree_with_their_purchase_order(corpus):
    """The point of this defect is that the paperwork is internally perfect.

    The order was raised at the inflated price too, so a three-way match passes
    and only the vendor's own price history gives it away. If this test fails, the
    price-variance check is being credited for catches the match check made.
    """
    by_po = {order.id: order for order in corpus["orders"]}
    subjects = [inv for inv in corpus["invoices"] if inv.defect == "PRICE_ABOVE_HISTORY"]
    assert subjects

    for invoice in subjects:
        po_lines = {line.sku: line for line in by_po[invoice.po_id].lines}
        for line in invoice.lines:
            assert line.unit_price == po_lines[line.sku].unit_price, invoice.id


def test_clean_invoices_bill_what_was_delivered(corpus):
    by_delivery = {d.id: d for d in corpus["deliveries"]}
    for invoice in corpus["invoices"]:
        if invoice.defect or invoice.delivery_id is None:
            continue
        delivery = by_delivery[invoice.delivery_id]
        billed = sum(line.quantity for line in invoice.lines)
        delivered = sum(line.quantity_received for line in delivery.lines)
        assert billed == delivered, invoice.id


def test_price_history_is_deep_enough_to_test_the_variance_check(corpus):
    """Most vendor-item pairs must clear the minimum, and some must not.

    A corpus where every pair clears it would never exercise the abstention path;
    one where none do would make the check meaningless.
    """
    counts = Counter(
        (order.vendor_id, line.sku) for order in corpus["orders"] for line in order.lines
    )
    deep = [n for n in counts.values() if n >= settings.price_history_min_points]
    assert len(deep) / len(counts) > 0.6
    assert len(deep) < len(counts)


@pytest.mark.parametrize("seed", [settings.corpus_seed])
def test_the_same_seed_gives_the_same_corpus(seed):
    first, second = build(seed), build(seed)
    assert [i.id for i in first["invoices"]] == [i.id for i in second["invoices"]]
    assert [i.invoice_number for i in first["invoices"]] == [
        i.invoice_number for i in second["invoices"]
    ]
    assert first["truth"] == second["truth"]
