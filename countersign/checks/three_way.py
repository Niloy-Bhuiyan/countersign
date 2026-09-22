"""Three-way match: the invoice against the order and against what was received.

Rules, in the order they are applied:

1. The purchase order exists and belongs to the invoicing vendor.
2. The invoice is in the order's currency.
3. Every invoice line matches an order line (see ``matching``).
4. Unit price is within ``price_tolerance_pct`` of the ordered price.
5. Quantity billed does not exceed quantity received by the invoice date, less
   quantity already accepted on earlier invoices. Quantity has no tolerance.

A purchase order with no delivery at all fails rule 5 outright: billing for goods
that were never received is exactly the case this check exists for.
"""

from __future__ import annotations

from decimal import Decimal

from countersign.checks.base import (
    FAILED,
    THREE_WAY_MATCH,
    CheckResult,
    Ledger,
    passed,
)
from countersign.checks.matching import match_line
from countersign.extraction.schema import ExtractedInvoice
from countersign.money import pct_deviation
from countersign.reference import PurchaseOrder, Reference, Vendor
from countersign.settings import settings


def _fail(rule: str, explanation: str, **kwargs) -> CheckResult:
    return CheckResult(THREE_WAY_MATCH, FAILED, explanation, rule=rule, **kwargs)


def run(
    invoice: ExtractedInvoice,
    vendor: Vendor,
    order: PurchaseOrder | None,
    reference: Reference,
    ledger: Ledger,
) -> list[CheckResult]:
    if order is None:
        return [
            _fail(
                "po_not_found",
                f"The invoice cites order {invoice.purchase_order_ref or '(none)'}, "
                "which is not on the order book.",
            )
        ]
    if order.vendor_id != vendor.id:
        return [
            _fail(
                "po_other_vendor",
                f"Order {order.po_number} was raised with a different vendor.",
                evidence={"purchase_orders": [order.id]},
            )
        ]

    results: list[CheckResult] = []
    evidence_po = {"purchase_orders": [order.id]}

    if invoice.currency != order.currency:
        results.append(
            _fail(
                "currency",
                f"Billed in {invoice.currency}; order {order.po_number} is in {order.currency}.",
                evidence=evidence_po,
            )
        )

    deliveries = [
        d for d in reference.deliveries(order.id) if d.delivered_at <= invoice.invoice_date
    ]
    delivery_ids = [d.id for d in deliveries]
    if not reference.deliveries(order.id):
        results.append(
            _fail(
                "no_delivery",
                f"No delivery has been recorded against order {order.po_number}.",
                evidence=evidence_po,
            )
        )

    accepted: list[tuple[int, Decimal]] = []
    for line in invoice.lines:
        po_line, how = match_line(line, order)
        if po_line is None:
            results.append(
                _fail(
                    "line_unmatched",
                    f"Line {line.line_no} ({line.description}) matches nothing on order "
                    f"{order.po_number}.",
                    line_no=line.line_no,
                    evidence=evidence_po,
                )
            )
            continue

        deviation = pct_deviation(line.unit_price, po_line.unit_price)
        if deviation > settings.price_tolerance_pct:
            results.append(
                _fail(
                    "price_above_order",
                    f"Line {line.line_no} is priced {line.unit_price} against "
                    f"{po_line.unit_price} ordered, {deviation}% over a "
                    f"{settings.price_tolerance_pct}% tolerance.",
                    line_no=line.line_no,
                    observed=line.unit_price,
                    expected=po_line.unit_price,
                    tolerance=settings.price_tolerance_pct,
                    evidence=evidence_po,
                )
            )

        if not reference.deliveries(order.id):
            continue
        received = sum(
            (
                dl.quantity_received
                for d in deliveries
                for dl in d.lines
                if dl.po_line_no == po_line.line_no
            ),
            Decimal(0),
        )
        available = received - ledger.billed_on(order.id, po_line.line_no)
        if line.quantity > available:
            results.append(
                _fail(
                    "quantity_over_received",
                    f"Line {line.line_no} bills {line.quantity} {po_line.uom}; "
                    f"{received} received by {invoice.invoice_date.isoformat()} and "
                    f"{ledger.billed_on(order.id, po_line.line_no)} already billed leaves "
                    f"{available}.",
                    line_no=line.line_no,
                    observed=line.quantity,
                    expected=available,
                    tolerance=Decimal(0),
                    evidence={**evidence_po, "deliveries": delivery_ids},
                )
            )
        else:
            accepted.append((po_line.line_no, line.quantity))

    if not any(r.rule == "quantity_over_received" for r in results):
        for line_no, quantity in accepted:
            ledger.bill(order.id, line_no, quantity)

    if results:
        return results
    return [
        passed(
            THREE_WAY_MATCH,
            f"All {len(invoice.lines)} lines agree with order {order.po_number} on price and "
            f"with {len(deliveries)} delivery note(s) on quantity.",
            purchase_orders=[order.id],
            deliveries=delivery_ids,
        )
    ]
