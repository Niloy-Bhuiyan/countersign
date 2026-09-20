"""Derive clean invoices from purchase orders and deliveries.

A clean invoice bills exactly what was delivered, at exactly the price the
purchase order agreed, with arithmetic that ties to the cent. Every check must
pass on one. Defects are applied afterwards in ``data.defects``.

Invoice numbering is per vendor and deliberately inconsistent across vendors:
suppliers number their own invoices however they like, and an extraction that
assumes one format is an extraction that breaks on the second vendor.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from countersign.money import line_total as compute_line_total
from countersign.money import money, tax_of
from data.records import Delivery, Line, PurchaseOrder, Vendor

#: One format per vendor, assigned by position so the corpus is reproducible.
NUMBER_FORMATS = (
    "INV-{year}-{seq:05d}",
    "{year}/INV/{seq:04d}",
    "SI{seq:06d}",
    "{prefix}-{yy}{mm}-{seq:04d}",
    "BILL {seq:05d}/{yy}",
)


@dataclass
class Invoice:
    id: str
    invoice_number: str
    vendor_id: str
    po_id: str | None
    delivery_id: str | None
    issued_at: date
    due_at: date
    currency: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    lines: list[Line] = field(default_factory=list)
    #: Defect code, or None for a clean invoice. Written to the ground truth file,
    #: never to the documents themselves.
    defect: str | None = None
    #: Free-text note recording what was altered, for the ground truth file only.
    defect_detail: str | None = None


def number_for(vendor: Vendor, seq: int, issued_at: date) -> str:
    index = int(vendor.id.split("-")[1]) % len(NUMBER_FORMATS)
    return NUMBER_FORMATS[index].format(
        year=issued_at.year,
        yy=issued_at.strftime("%y"),
        mm=issued_at.strftime("%m"),
        seq=seq,
        prefix=vendor.legal_name[:3].upper(),
    )


def totals_for(lines: list[Line]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = money(sum((line.line_total for line in lines), Decimal(0)))
    tax_total = money(sum((tax_of(line.line_total, line.tax_rate) for line in lines), Decimal(0)))
    return subtotal, tax_total, money(subtotal + tax_total)


def generate_invoices(
    rng: random.Random,
    vendors: list[Vendor],
    orders: list[PurchaseOrder],
    deliveries: list[Delivery],
) -> list[Invoice]:
    """One invoice per delivery, billing the delivered quantity at the PO price."""
    by_vendor = {vendor.id: vendor for vendor in vendors}
    by_po = {order.id: order for order in orders}
    invoices: list[Invoice] = []
    seq_by_vendor: dict[str, int] = {}

    for delivery in deliveries:
        order = by_po[delivery.po_id]
        vendor = by_vendor[order.vendor_id]
        po_lines = {line.line_no: line for line in order.lines}

        lines: list[Line] = []
        for line_no, delivery_line in enumerate(delivery.lines, start=1):
            po_line = po_lines[delivery_line.po_line_no]
            quantity = delivery_line.quantity_received
            lines.append(
                Line(
                    line_no=line_no,
                    sku=po_line.sku,
                    description=po_line.description,
                    uom=po_line.uom,
                    quantity=quantity,
                    unit_price=po_line.unit_price,
                    line_total=compute_line_total(quantity, po_line.unit_price),
                    tax_rate=po_line.tax_rate,
                )
            )

        issued_at = delivery.delivered_at + timedelta(days=rng.randrange(0, 11))
        seq = seq_by_vendor.get(vendor.id, 0) + 1
        seq_by_vendor[vendor.id] = seq
        subtotal, tax_total, total = totals_for(lines)

        invoices.append(
            Invoice(
                id=f"INV-{len(invoices) + 1:04d}",
                invoice_number=number_for(vendor, seq, issued_at),
                vendor_id=vendor.id,
                po_id=order.id,
                delivery_id=delivery.id,
                issued_at=issued_at,
                due_at=issued_at + timedelta(days=vendor.payment_terms_days),
                currency=order.currency,
                subtotal=subtotal,
                tax_total=tax_total,
                total=total,
                lines=lines,
            )
        )

    return invoices
