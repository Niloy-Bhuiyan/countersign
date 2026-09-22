"""Tax arithmetic, recomputed exactly.

Line tax is ``line_total x rate``, rounded half-up to two places, and the stated
tax total must equal their sum to the cent. There is no tolerance: the money path
is exact (ADR-002), so a one-cent difference is a real difference.

Two of the four layouts do not print a rate. The rate then comes from the matched
purchase order line — which is why this is a check and not an extraction
validator. When a line has neither a printed rate nor a matched order line, the
check abstains rather than assuming one.
"""

from __future__ import annotations

from decimal import Decimal

from countersign.checks.base import ABSTAINED, FAILED, TAX_ARITHMETIC, CheckResult, passed
from countersign.checks.matching import match_line
from countersign.extraction.schema import ExtractedInvoice
from countersign.money import money, tax_of
from countersign.reference import PurchaseOrder


def run(invoice: ExtractedInvoice, order: PurchaseOrder | None) -> list[CheckResult]:
    computed = Decimal(0)
    for line in invoice.lines:
        rate = line.tax_rate
        if rate is None and order is not None:
            po_line, _ = match_line(line, order)
            rate = po_line.tax_rate if po_line else None
        if rate is None:
            return [
                CheckResult(
                    TAX_ARITHMETIC,
                    ABSTAINED,
                    f"Line {line.line_no} prints no tax rate and matches no order line, so its "
                    "tax cannot be recomputed.",
                    rule="no_rate",
                    line_no=line.line_no,
                )
            ]
        computed += tax_of(line.line_total, rate)

    computed = money(computed)
    if computed != invoice.tax_total:
        return [
            CheckResult(
                TAX_ARITHMETIC,
                FAILED,
                f"Stated tax {invoice.tax_total} against {computed} recomputed from the lines, "
                f"a difference of {money(invoice.tax_total - computed)}.",
                rule="tax_total",
                observed=invoice.tax_total,
                expected=computed,
                tolerance=Decimal("0.00"),
                evidence={"purchase_orders": [order.id]} if order else {},
            )
        ]
    return [passed(TAX_ARITHMETIC, f"Tax {computed} recomputes exactly from the lines.")]
