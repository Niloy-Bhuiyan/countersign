"""Plant known defects into the corpus and record the truth about them.

Each affected invoice carries exactly one planted defect. The record of what was
planted is written to ``data/ground_truth/exceptions.json`` and is the only thing
the evaluation harness scores against.

Two rules keep the ground truth meaningful:

* **A planted defect never makes an invoice internally inconsistent by accident.**
  Raising a quantity recomputes the line total, the subtotal and the tax, so the
  invoice still adds up and only the comparison against the delivery fails.
  Otherwise every defect would also look like a tax defect.
* **A defect may legitimately trip more than one check.** ``expected_check`` names
  the check that should catch it first; the evaluation reports both per-check
  attribution and whether the invoice was flagged at all. Contorting the corpus so
  exactly one check fires would be tuning the data to the answer.

``PRICE_ABOVE_HISTORY`` is the reason both a three-way match and a price-variance
check exist. It raises the purchase order price as well as the invoice price, so
the invoice agrees with its own paperwork perfectly and only the vendor's own
price history gives it away.
"""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from countersign.money import line_total as compute_line_total
from countersign.money import money
from data.invoices import Invoice, number_for, totals_for
from data.records import Delivery, PurchaseOrder, Vendor

#: Defect code -> the check expected to catch it first.
EXPECTED_CHECK = {
    "QTY_OVER_DELIVERY": "THREE_WAY_MATCH",
    "PRICE_ABOVE_PO": "THREE_WAY_MATCH",
    "PRICE_ABOVE_HISTORY": "PRICE_VARIANCE",
    "DUPLICATE_EXACT": "DUPLICATE_INVOICE",
    "DUPLICATE_NEAR": "DUPLICATE_INVOICE",
    "TAX_MISMATCH": "TAX_ARITHMETIC",
    "NO_DELIVERY": "THREE_WAY_MATCH",
    "CURRENCY_MISMATCH": "THREE_WAY_MATCH",
}

#: Share of the finished corpus that carries a defect.
DEFECT_RATE = 0.18

PO_PRICE_DEFECTS = ("PRICE_ABOVE_HISTORY",)
APPENDING = ("DUPLICATE_EXACT", "DUPLICATE_NEAR", "NO_DELIVERY")


def _retotal(invoice: Invoice) -> None:
    invoice.subtotal, invoice.tax_total, invoice.total = totals_for(invoice.lines)


def _qty_over_delivery(rng: random.Random, invoice: Invoice) -> str:
    line = rng.choice(invoice.lines)
    original = line.quantity
    line.quantity = money(original * Decimal(str(round(rng.uniform(1.08, 1.35), 3))))
    line.line_total = compute_line_total(line.quantity, line.unit_price)
    _retotal(invoice)
    return f"line {line.line_no} billed {line.quantity} against {original} delivered"


def _price_above_po(rng: random.Random, invoice: Invoice) -> str:
    line = rng.choice(invoice.lines)
    original = line.unit_price
    line.unit_price = money(original * Decimal(str(round(rng.uniform(1.05, 1.18), 4))))
    line.line_total = compute_line_total(line.quantity, line.unit_price)
    _retotal(invoice)
    return f"line {line.line_no} priced {line.unit_price} against {original} ordered"


def _tax_mismatch(rng: random.Random, invoice: Invoice) -> str:
    original = invoice.tax_total
    # A transposition or a dropped line, not a random number: this is what the
    # arithmetic error actually looks like on a real invoice.
    invoice.tax_total = money(original * Decimal(str(round(rng.uniform(0.62, 0.88), 3))))
    invoice.total = money(invoice.subtotal + invoice.tax_total)
    return f"tax stated {invoice.tax_total} against {original} computed from the lines"


def _currency_mismatch(invoice: Invoice) -> str:
    original = invoice.currency
    invoice.currency = "USD"
    return f"billed in {invoice.currency} against {original} on the order"


def _price_above_history(rng: random.Random, invoice: Invoice, order: PurchaseOrder) -> str:
    """Raise the order price and the invoice price together.

    The invoice then matches its own purchase order exactly. Only the vendor's
    price history for that item shows the problem.
    """
    line = rng.choice(invoice.lines)
    po_line = next(pol for pol in order.lines if pol.sku == line.sku)
    factor = Decimal(str(round(rng.uniform(1.35, 1.9), 4)))
    original = po_line.unit_price

    po_line.unit_price = money(original * factor)
    po_line.line_total = compute_line_total(po_line.quantity, po_line.unit_price)
    order.subtotal, order.tax_total, order.total = totals_for(order.lines)

    line.unit_price = po_line.unit_price
    line.line_total = compute_line_total(line.quantity, line.unit_price)
    _retotal(invoice)
    return (
        f"{line.sku} ordered and billed at {line.unit_price}, "
        f"against {original} on the vendor's prior orders"
    )


def _clone(invoice: Invoice, new_id: str) -> Invoice:
    return replace(
        invoice,
        id=new_id,
        lines=[replace(line) for line in invoice.lines],
        defect=None,
        defect_detail=None,
    )


def plant(
    rng: random.Random,
    vendors: list[Vendor],
    orders: list[PurchaseOrder],
    deliveries: list[Delivery],
    invoices: list[Invoice],
) -> list[dict]:
    """Mutate the corpus in place and return the ground truth records."""
    by_vendor = {vendor.id: vendor for vendor in vendors}
    by_po = {order.id: order for order in orders}
    delivered_po_ids = {delivery.po_id for delivery in deliveries}
    undelivered = [order for order in orders if order.id not in delivered_po_ids]

    # Only three of the eight codes add an invoice; the rest alter one in place.
    # So the corpus grows by a fraction of the defects planted, and the target has
    # to solve for the rate against the *final* size rather than the starting one.
    appending_share = len(APPENDING) / len(EXPECTED_CHECK)
    target = round(len(invoices) * DEFECT_RATE / (1 - DEFECT_RATE * appending_share))
    codes = [code for code in EXPECTED_CHECK]
    plan = [codes[i % len(codes)] for i in range(target)]
    rng.shuffle(plan)

    clean_pool = [inv for inv in invoices if inv.defect is None]
    rng.shuffle(clean_pool)
    truth: list[dict] = []

    for code in plan:
        if code in APPENDING:
            if code == "NO_DELIVERY":
                if not undelivered:
                    continue
                order = undelivered.pop()
                vendor = by_vendor[order.vendor_id]
                issued_at = order.ordered_at + timedelta(days=rng.randrange(5, 30))
                lines = [replace(line) for line in order.lines]
                subtotal, tax_total, total = totals_for(lines)
                new = Invoice(
                    id=f"INV-{len(invoices) + 1:04d}",
                    invoice_number=number_for(vendor, 9000 + len(truth), issued_at),
                    vendor_id=vendor.id,
                    po_id=order.id,
                    delivery_id=None,
                    issued_at=issued_at,
                    due_at=issued_at + timedelta(days=vendor.payment_terms_days),
                    currency=order.currency,
                    subtotal=subtotal,
                    tax_total=tax_total,
                    total=total,
                    lines=lines,
                )
                detail = f"billed against {order.po_number} with no delivery recorded"
            else:
                if not clean_pool:
                    continue
                source = clean_pool.pop()
                new = _clone(source, f"INV-{len(invoices) + 1:04d}")
                new.issued_at = source.issued_at + timedelta(days=rng.randrange(4, 40))
                new.due_at = new.issued_at + timedelta(
                    days=by_vendor[new.vendor_id].payment_terms_days
                )
                if code == "DUPLICATE_EXACT":
                    detail = (
                        f"resubmits {source.invoice_number} "
                        f"from {source.issued_at.isoformat()} unchanged"
                    )
                else:
                    new.invoice_number = number_for(
                        by_vendor[new.vendor_id], 9500 + len(truth), new.issued_at
                    )
                    detail = (
                        f"same order and total as {source.invoice_number} under a different number"
                    )

            new.defect = code
            new.defect_detail = detail
            invoices.append(new)
            target_invoice = new

        else:
            if not clean_pool:
                continue
            target_invoice = clean_pool.pop()
            if code in PO_PRICE_DEFECTS:
                detail = _price_above_history(rng, target_invoice, by_po[target_invoice.po_id])
            elif code == "QTY_OVER_DELIVERY":
                detail = _qty_over_delivery(rng, target_invoice)
            elif code == "PRICE_ABOVE_PO":
                detail = _price_above_po(rng, target_invoice)
            elif code == "TAX_MISMATCH":
                detail = _tax_mismatch(rng, target_invoice)
            else:
                detail = _currency_mismatch(target_invoice)
            target_invoice.defect = code
            target_invoice.defect_detail = detail

        truth.append(
            {
                "invoice_id": target_invoice.id,
                "invoice_number": target_invoice.invoice_number,
                "vendor_id": target_invoice.vendor_id,
                "po_id": target_invoice.po_id,
                "defect_code": code,
                "expected_check": EXPECTED_CHECK[code],
                "detail": detail,
            }
        )

    return truth
