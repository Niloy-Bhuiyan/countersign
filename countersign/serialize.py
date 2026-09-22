"""One description of a case, shared by the static export and the live API.

Amounts leave as decimal strings. The console groups and prints them as strings,
so no figure passes through a binary float between the checks and the screen.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from statistics import median

from countersign.batch import Case
from countersign.reference import Reference
from countersign.settings import settings


def _s(value) -> str | None:
    return None if value is None else str(value)


def queue_row(
    case: Case,
    reference: Reference,
    recommendation: dict | None,
    category_of: Callable[[str | None], str] = lambda _sku: "Uncategorised",
) -> dict:
    invoice = case.invoice
    vendor = reference.vendors.get(case.vendor_id or "")
    order = reference.orders.get(case.po_id or "")
    failed = [r for r in case.results if r.outcome == "failed"]
    abstained = [r for r in case.results if r.outcome == "abstained"]
    return {
        "id": case.document_id,
        "file": case.filename,
        "format": case.filename.rsplit(".", 1)[-1].lower(),
        "number": invoice.invoice_number if invoice else None,
        "vendor": vendor.legal_name if vendor else (invoice.vendor_name if invoice else None),
        "vendorId": case.vendor_id,
        "po": order.po_number if order else (invoice.purchase_order_ref if invoice else None),
        "issued": invoice.invoice_date.isoformat() if invoice else None,
        "currency": invoice.currency if invoice else None,
        "total": _s(invoice.total) if invoice else None,
        "category": category_of(invoice.lines[0].sku) if invoice and invoice.lines else None,
        "state": case.state,
        "reason": case.review_reason,
        "action": recommendation["action"] if recommendation else "REVIEW_MANUALLY",
        "failed": sorted({f"{r.check_code}/{r.rule}" for r in failed}),
        "abstained": sorted({f"{r.check_code}/{r.rule}" for r in abstained}),
    }


def _price_history(case: Case, reference: Reference) -> list[dict]:
    """What the variance check compared each line against, for the evidence chart."""
    invoice = case.invoice
    order = reference.orders.get(case.po_id or "")
    if not invoice or not order or not case.vendor_id:
        return []
    out = []
    for line in invoice.lines:
        if not line.sku:
            continue
        history = reference.price_history(
            case.vendor_id, line.sku, order.ordered_at, settings.price_history_window_days
        )
        prices = [price for _, _, price in history]
        centre = median(prices) if prices else None
        mad = median(abs(p - centre) for p in prices) if prices else None
        out.append(
            {
                "lineNo": line.line_no,
                "sku": line.sku,
                "billed": _s(line.unit_price),
                "points": [
                    {"po": po_id, "date": ordered.isoformat(), "price": _s(price)}
                    for po_id, ordered, price in history
                ],
                "median": _s(centre),
                "mad": _s(mad),
                "minPoints": settings.price_history_min_points,
                "materialPct": _s(settings.price_variance_min_pct),
            }
        )
    return out


def case_detail(
    case: Case,
    reference: Reference,
    recommendation: dict | None,
    category_of: Callable[[str | None], str] = lambda _sku: "Uncategorised",
) -> dict:
    invoice = case.invoice
    order = reference.orders.get(case.po_id or "")
    return {
        **queue_row(case, reference, recommendation, category_of),
        "history": case.history,
        "extraction": {
            "provider": case.extraction.provider,
            "version": case.extraction.version,
            "intake": case.extraction.intake.status,
            "sha256": case.extraction.intake.sha256,
            "failures": [f.model_dump() for f in case.extraction.failures],
        },
        "invoice": None
        if not invoice
        else {
            "vendorAsPrinted": invoice.vendor_name,
            "taxId": invoice.vendor_tax_id,
            "due": invoice.due_date.isoformat() if invoice.due_date else None,
            "subtotal": _s(invoice.subtotal),
            "tax": _s(invoice.tax_total),
            "total": _s(invoice.total),
            "lines": [
                {
                    "no": line.line_no,
                    "sku": line.sku,
                    "description": line.description,
                    "uom": line.uom,
                    "quantity": _s(line.quantity),
                    "unitPrice": _s(line.unit_price),
                    "lineTotal": _s(line.line_total),
                    "taxRate": _s(line.tax_rate),
                }
                for line in invoice.lines
            ],
        },
        "order": None
        if not order
        else {
            "number": order.po_number,
            "orderedAt": order.ordered_at.isoformat(),
            "currency": order.currency,
            "lines": [
                {
                    "no": line.line_no,
                    "sku": line.sku,
                    "description": line.description,
                    "quantity": _s(line.quantity),
                    "unitPrice": _s(line.unit_price),
                    "taxRate": _s(line.tax_rate),
                    "received": _s(
                        sum(
                            (
                                dl.quantity_received
                                for d in reference.deliveries(order.id)
                                for dl in d.lines
                                if dl.po_line_no == line.line_no
                            ),
                            Decimal(0),
                        )
                    ),
                }
                for line in order.lines
            ],
            "deliveries": [
                {
                    "id": d.id,
                    "number": d.delivery_note_number,
                    "date": d.delivered_at.isoformat(),
                    "lines": [
                        {"poLine": dl.po_line_no, "received": _s(dl.quantity_received)}
                        for dl in d.lines
                    ],
                }
                for d in reference.deliveries(order.id)
            ],
        },
        "priceHistory": _price_history(case, reference),
        "results": [r.as_dict() for r in case.results],
        "recommendation": recommendation,
    }
