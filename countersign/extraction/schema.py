"""The contract between the extraction model and the rest of the system.

Two layers, deliberately:

``RawInvoice`` is what a model returns: every field a string, copied from the
document as printed. Asking a model to emit a typed date or a decimal invites it
to normalise, and a model that normalises is a model that quietly corrects — which
is the last thing wanted from the component reading hostile input.

``ExtractedInvoice`` is what the rest of the system uses: dates, decimals and a
currency code, produced by :mod:`countersign.extraction.parsing`.

``parse_raw`` moves between them and collects *every* field that failed rather
than raising on the first. A document with three unreadable fields should produce
one review item listing three problems, not three round trips.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from countersign.extraction.parsing import (
    ParseError,
    parse_amount,
    parse_currency,
    parse_date,
    parse_quantity,
    parse_rate,
)


class RawLine(BaseModel):
    """One line as printed. Every value is the document's own text."""

    model_config = ConfigDict(extra="forbid")

    line_no: int
    sku: str | None = None
    description: str = ""
    uom: str | None = None
    quantity: str = ""
    unit_price: str = ""
    line_total: str = ""
    tax_rate: str | None = None


class RawInvoice(BaseModel):
    """An invoice as printed. This is the model's entire output surface.

    There is no field here that means "approved", "verified" or "priority". A
    document instructing the model to set one has nothing to set: see
    docs/security.md, threat T1.
    """

    model_config = ConfigDict(extra="forbid")

    invoice_number: str = ""
    vendor_name: str = ""
    invoice_date: str = ""
    due_date: str | None = None
    purchase_order_ref: str | None = None
    currency: str = ""
    lines: list[RawLine] = Field(default_factory=list)
    subtotal: str = ""
    tax_total: str = ""
    total: str = ""


class ExtractedLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_no: int
    sku: str | None
    description: str
    uom: str | None
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    tax_rate: Decimal | None


class ExtractedInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: str
    vendor_name: str
    invoice_date: date
    due_date: date | None
    purchase_order_ref: str | None
    currency: str
    lines: list[ExtractedLine]
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal


class FieldFailure(BaseModel):
    """One field that could not be read, and what the document said."""

    model_config = ConfigDict(extra="forbid")

    field: str
    printed: str
    reason: str


class ParseOutcome(BaseModel):
    """Either an invoice or the list of reasons there is not one."""

    model_config = ConfigDict(extra="forbid")

    invoice: ExtractedInvoice | None = None
    failures: list[FieldFailure] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.invoice is not None


def _attempt(failures: list[FieldFailure], field: str, printed, fn):
    try:
        return fn(printed)
    except ParseError as exc:
        failures.append(FieldFailure(field=field, printed=str(printed), reason=str(exc)))
        return None


def parse_raw(raw: RawInvoice) -> ParseOutcome:
    """Type a raw extraction, collecting every failure instead of the first."""
    failures: list[FieldFailure] = []

    invoice_date = _attempt(failures, "invoice_date", raw.invoice_date, parse_date)
    due_date = _attempt(failures, "due_date", raw.due_date, parse_date) if raw.due_date else None
    currency = _attempt(failures, "currency", raw.currency, parse_currency)
    subtotal = _attempt(failures, "subtotal", raw.subtotal, parse_amount)
    tax_total = _attempt(failures, "tax_total", raw.tax_total, parse_amount)
    total = _attempt(failures, "total", raw.total, parse_amount)

    lines: list[ExtractedLine] = []
    for raw_line in raw.lines:
        prefix = f"lines[{raw_line.line_no}]"
        quantity = _attempt(failures, f"{prefix}.quantity", raw_line.quantity, parse_quantity)
        unit_price = _attempt(failures, f"{prefix}.unit_price", raw_line.unit_price, parse_amount)
        line_total = _attempt(failures, f"{prefix}.line_total", raw_line.line_total, parse_amount)
        tax_rate = (
            _attempt(failures, f"{prefix}.tax_rate", raw_line.tax_rate, parse_rate)
            if raw_line.tax_rate is not None
            else None
        )
        if quantity is None or unit_price is None or line_total is None:
            continue
        lines.append(
            ExtractedLine(
                line_no=raw_line.line_no,
                sku=raw_line.sku or None,
                description=raw_line.description.strip(),
                uom=(raw_line.uom or None),
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
                tax_rate=tax_rate,
            )
        )

    if not raw.invoice_number.strip():
        failures.append(
            FieldFailure(field="invoice_number", printed="", reason="no invoice number found")
        )
    if not raw.vendor_name.strip():
        failures.append(
            FieldFailure(field="vendor_name", printed="", reason="no vendor name found")
        )
    if not raw.lines:
        failures.append(FieldFailure(field="lines", printed="", reason="no line items found"))

    if failures:
        return ParseOutcome(failures=failures)

    return ParseOutcome(
        invoice=ExtractedInvoice(
            invoice_number=raw.invoice_number.strip(),
            vendor_name=raw.vendor_name.strip(),
            invoice_date=invoice_date,
            due_date=due_date,
            purchase_order_ref=(raw.purchase_order_ref or "").strip() or None,
            currency=currency,
            lines=lines,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
        )
    )
