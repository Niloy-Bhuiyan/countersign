"""The invoice lab: raise an order, receive it, and have the supplier bill for it.

A reviewer picks a vendor and, optionally, one thing to get wrong. The lab then
does what procurement does: it raises a purchase order at the vendor's usual
prices, records a delivery against it, and issues the supplier's invoice as a PDF
in that vendor's layout. The PDF is rendered to bytes and then *read back* by the
same pipeline as any other document. Nothing is passed around as structured data
that a real supplier would not send.

The order and delivery live only in the reviewer's workspace. They are reference
data the invoice is checked against, exactly as the corpus's are.
"""

from __future__ import annotations

import random
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median

from countersign.money import line_total, money
from countersign.reference import Reference
from data.catalogue import BY_SKU
from data.invoices import Invoice, number_for, totals_for
from data.records import Line
from data.records import Vendor as VendorRecord
from data.render.pdf import render

TAMPERS: dict[str, dict[str, str]] = {
    "clean": {
        "label": "Nothing wrong",
        "effect": "Bills exactly what was delivered, at the ordered price.",
        "expect": "Every check passes and the invoice clears.",
    },
    "overbill": {
        "label": "Bill more than was delivered",
        "effect": "One line is billed at 115% of the quantity received.",
        "expect": "Three-way match fails on quantity.",
    },
    "price_above_order": {
        "label": "Charge above the ordered price",
        "effect": "One line's unit price is 8% above the order.",
        "expect": "Three-way match fails on price.",
    },
    "tax_error": {
        "label": "Misstate the VAT",
        "effect": "The VAT total is understated by about a fifth; everything else ties.",
        "expect": "Tax arithmetic fails.",
    },
    "inflated_order": {
        "label": "Inflate the order itself",
        "effect": "The order is raised 60% above this vendor's usual price, and the invoice "
        "matches it exactly.",
        "expect": "The paperwork agrees with itself; only price variance catches it.",
    },
    "currency": {
        "label": "Bill in the wrong currency",
        "effect": "The invoice is issued in USD against a BDT order.",
        "expect": "Three-way match fails on currency.",
    },
    "resubmit": {
        "label": "Resubmit the last lab invoice",
        "effect": "The previous lab invoice is sent again under the same number.",
        "expect": "Duplicate detection fails.",
    },
}


@dataclass
class Scenario:
    order_row: dict
    delivery_row: dict
    invoice_number: str
    document: bytes
    filename: str
    tamper: str


def _vendor_record(reference: Reference, vendor_id: str) -> VendorRecord:
    vendor = reference.vendors[vendor_id]
    skus = sorted(
        {
            line.sku
            for order in reference.orders.values()
            if order.vendor_id == vendor_id
            for line in order.lines
        }
    )
    return VendorRecord(
        id=vendor.id,
        legal_name=vendor.legal_name,
        normalised_name=vendor.normalised_name,
        tax_id=vendor.tax_id,
        payment_terms_days=vendor.payment_terms_days,
        currency=vendor.currency,
        skus=skus,
        price_factor=Decimal(1),
    )


def _usual_price(reference: Reference, vendor_id: str, sku: str, today: date) -> Decimal:
    history = reference.price_history(vendor_id, sku, today, 365)
    prices = [price for _, _, price in history[-8:]]
    return money(median(prices)) if prices else BY_SKU[sku].base_price


def _order_row(order_id: str, number: str, vendor_id: str, ordered_at: date, lines: list[Line]):
    subtotal, tax_total, total = totals_for(lines)
    return {
        "id": order_id,
        "po_number": number,
        "vendor_id": vendor_id,
        "ordered_at": ordered_at.isoformat(),
        "currency": "BDT",
        "subtotal": str(subtotal),
        "tax_total": str(tax_total),
        "total": str(total),
        "status": "open",
        "lines": [
            {
                "line_no": line.line_no,
                "sku": line.sku,
                "description": line.description,
                "uom": line.uom,
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price),
                "line_total": str(line.line_total),
                "tax_rate": str(line.tax_rate),
            }
            for line in lines
        ],
    }


def _render(invoice: Invoice, vendor: VendorRecord) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        path = render(invoice, vendor, Path(tmp) / "invoice.pdf")
        return path.read_bytes()


def compose(
    reference: Reference,
    *,
    vendor_id: str,
    tamper: str,
    sequence: int,
    workspace: str,
    today: date,
    previous: Scenario | None = None,
    rng: random.Random | None = None,
) -> Scenario:
    if tamper not in TAMPERS:
        raise ValueError(f"unknown tamper {tamper!r}")
    if vendor_id not in reference.vendors:
        raise ValueError(f"unknown vendor {vendor_id!r}")
    rng = rng or random.Random(f"{workspace}-{sequence}")
    vendor = _vendor_record(reference, vendor_id)

    if tamper == "resubmit":
        if previous is None:
            raise ValueError("create a test invoice first, then send it again")
        # The same attachment sent again, the way a supplier's accounts system
        # re-sends an unpaid invoice: identical bytes, identical number.
        return Scenario(
            order_row=previous.order_row,
            delivery_row=previous.delivery_row,
            invoice_number=previous.invoice_number,
            document=previous.document,
            filename=previous.filename,
            tamper="resubmit",
        )

    ordered_at = today - timedelta(days=12)
    delivered_at = today - timedelta(days=5)
    tag = f"{workspace[:6].upper()}{sequence:03d}"
    order_id = f"PO-L{tag}"

    # Prefer items with enough earlier prices for the variance check to judge.
    # Otherwise it correctly abstains, and even a clean invoice goes to review —
    # right, but not what the reviewer asked the lab to show.
    judged = [
        sku
        for sku in vendor.skus
        if len(reference.price_history(vendor_id, sku, ordered_at, 365)) >= 5
    ]
    pool = judged or vendor.skus
    skus = rng.sample(pool, k=min(len(pool), rng.randint(1, 2)))
    order_lines: list[Line] = []
    for line_no, sku in enumerate(skus, start=1):
        item = BY_SKU[sku]
        price = _usual_price(reference, vendor_id, sku, ordered_at)
        if tamper == "inflated_order":
            price = money(price * Decimal("1.6"))
        quantity = money(rng.choice([10, 20, 25, 40, 50, 80, 120, 200, 400]))
        order_lines.append(
            Line(
                line_no,
                sku,
                item.description,
                item.uom,
                quantity,
                price,
                line_total(quantity, price),
                item.tax_rate,
            )
        )
    order_row = _order_row(
        order_id, f"PO/{ordered_at.year}/L{tag}", vendor_id, ordered_at, order_lines
    )
    delivery_row = {
        "id": f"DN-L{tag}",
        "delivery_note_number": f"DN/{delivered_at.year}/L{tag}",
        "po_id": order_id,
        "delivered_at": delivered_at.isoformat(),
        "received_by": "Workspace receiving",
        "lines": [
            {
                "po_line_no": line.line_no,
                "quantity_received": str(line.quantity),
                "condition": "good",
            }
            for line in order_lines
        ],
    }

    lines = [Line(**vars(line)) for line in order_lines]
    target = lines[0]
    if tamper == "overbill":
        target.quantity = money(target.quantity * Decimal("1.15"))
        target.line_total = line_total(target.quantity, target.unit_price)
    elif tamper == "price_above_order":
        target.unit_price = money(target.unit_price * Decimal("1.08"))
        target.line_total = line_total(target.quantity, target.unit_price)

    subtotal, tax_total, total = totals_for(lines)
    if tamper == "tax_error":
        tax_total = money(tax_total * Decimal("0.8"))
        total = money(subtotal + tax_total)

    issued_at = today - timedelta(days=2)
    invoice = Invoice(
        id=f"LAB-{tag}",
        invoice_number=number_for(vendor, 7000 + sequence, issued_at),
        vendor_id=vendor_id,
        po_id=order_id,
        delivery_id=delivery_row["id"],
        issued_at=issued_at,
        due_at=issued_at + timedelta(days=vendor.payment_terms_days),
        currency="USD" if tamper == "currency" else "BDT",
        subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        lines=lines,
    )
    return Scenario(
        order_row=order_row,
        delivery_row=delivery_row,
        invoice_number=invoice.invoice_number,
        document=_render(invoice, vendor),
        filename=f"LAB-{tag}.pdf",
        tamper=tamper,
    )
