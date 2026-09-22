"""Arithmetic an invoice must satisfy before anything is persisted.

These run on every extraction, from any provider, and they only check what the
document says about itself. They need no reference data: whether the invoice
agrees with the purchase order is the checks' job, not the extractor's.

Their value is catching an extraction that is wrong but plausible. A reader that
drops a line, or takes a unit price for a line total, produces a record that
parses cleanly and is still wrong; the subtotal no longer ties, and the record is
stopped here instead of reaching a check that would trust it.

Tax is deliberately not validated here. Two of the four layouts do not print a
rate, so the tax arithmetic needs the ordered rate, which is reference data, which
makes it a check.
"""

from __future__ import annotations

from decimal import Decimal

from countersign.extraction.schema import ExtractedInvoice, FieldFailure
from countersign.money import line_total, money


def validate(invoice: ExtractedInvoice) -> list[FieldFailure]:
    failures: list[FieldFailure] = []

    for line in invoice.lines:
        expected = line_total(line.quantity, line.unit_price)
        if expected != line.line_total:
            failures.append(
                FieldFailure(
                    field=f"lines[{line.line_no}].line_total",
                    printed=str(line.line_total),
                    reason=f"{line.quantity} x {line.unit_price} is {expected}",
                )
            )

    summed = money(sum((line.line_total for line in invoice.lines), Decimal(0)))
    if summed != invoice.subtotal:
        failures.append(
            FieldFailure(
                field="subtotal",
                printed=str(invoice.subtotal),
                reason=f"the {len(invoice.lines)} lines read sum to {summed}",
            )
        )

    if money(invoice.subtotal + invoice.tax_total) != invoice.total:
        failures.append(
            FieldFailure(
                field="total",
                printed=str(invoice.total),
                reason=f"subtotal plus tax is {money(invoice.subtotal + invoice.tax_total)}",
            )
        )

    numbers = [line.line_no for line in invoice.lines]
    if numbers != list(range(1, len(numbers) + 1)):
        failures.append(
            FieldFailure(
                field="lines",
                printed=",".join(map(str, numbers)),
                reason="line numbers are not consecutive; a line was probably missed",
            )
        )

    return failures
