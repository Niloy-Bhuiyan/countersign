"""Duplicate and near-duplicate invoices.

Three rules, cheapest first:

1. **Same bytes.** A document whose content hash has been seen before.
2. **Same number.** The same vendor has already issued this invoice number.
   Numbers are compared after removing case, spaces and punctuation, and only
   within a vendor: two suppliers may legitimately use the same number, and the
   corpus contains exactly that case.
3. **Same order, same amount.** Another invoice from this vendor on this purchase
   order for the same total, within ``near_duplicate_window_days``, when there are
   now more such invoices than deliveries on the order. Two equal invoices against
   an order delivered in two equal shipments are normal; three are not.

Vendors are identified through the committed normalisation table (ADR-004), never
by string similarity.
"""

from __future__ import annotations

from countersign.checks.base import (
    DUPLICATE_INVOICE,
    FAILED,
    CheckResult,
    Ledger,
    SeenInvoice,
    normalise_number,
    passed,
)
from countersign.extraction.schema import ExtractedInvoice
from countersign.reference import PurchaseOrder, Reference, Vendor
from countersign.settings import settings


def run(
    invoice: ExtractedInvoice,
    vendor: Vendor,
    order: PurchaseOrder | None,
    reference: Reference,
    ledger: Ledger,
    *,
    document_id: str,
    sha256: str,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    number = normalise_number(invoice.invoice_number)

    for earlier in ledger.seen:
        if earlier.sha256 == sha256:
            results.append(
                CheckResult(
                    DUPLICATE_INVOICE,
                    FAILED,
                    f"This file is byte-for-byte the document already received as "
                    f"{earlier.document_id}.",
                    rule="same_bytes",
                    evidence={"documents": [earlier.document_id]},
                )
            )
            break

    for earlier in ledger.seen:
        if earlier.vendor_id == vendor.id and normalise_number(earlier.invoice_number) == number:
            results.append(
                CheckResult(
                    DUPLICATE_INVOICE,
                    FAILED,
                    f"{vendor.legal_name} already issued invoice {earlier.invoice_number} on "
                    f"{earlier.issued_at.isoformat()} for {earlier.total}.",
                    rule="same_number",
                    observed=invoice.total,
                    expected=earlier.total,
                    evidence={"documents": [earlier.document_id]},
                )
            )
            break

    if order is not None and not any(r.rule == "same_number" for r in results):
        window = settings.near_duplicate_window_days
        twins = [
            earlier
            for earlier in ledger.seen
            if earlier.vendor_id == vendor.id
            and earlier.po_id == order.id
            and earlier.total == invoice.total
            and abs((invoice.invoice_date - earlier.issued_at).days) <= window
        ]
        deliveries = len(reference.deliveries(order.id))
        if twins and len(twins) + 1 > deliveries:
            results.append(
                CheckResult(
                    DUPLICATE_INVOICE,
                    FAILED,
                    f"Invoice {twins[0].invoice_number} already billed {invoice.total} on order "
                    f"{order.po_number} within {window} days; that makes {len(twins) + 1} "
                    f"equal invoices against {deliveries} delivery note(s).",
                    rule="same_order_same_amount",
                    observed=invoice.total,
                    expected=twins[0].total,
                    evidence={
                        "documents": [twin.document_id for twin in twins],
                        "purchase_orders": [order.id],
                    },
                )
            )

    ledger.seen.append(
        SeenInvoice(
            document_id=document_id,
            sha256=sha256,
            vendor_id=vendor.id,
            po_id=order.id if order else None,
            invoice_number=invoice.invoice_number,
            issued_at=invoice.invoice_date,
            total=invoice.total,
        )
    )

    if results:
        return results
    return [passed(DUPLICATE_INVOICE, "No earlier invoice matches by content, number or amount.")]
