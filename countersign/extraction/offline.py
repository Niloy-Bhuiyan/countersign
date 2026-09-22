"""The offline extractor: a label-aware reader for the text layer.

This is the default provider. It needs no network and no key, so the whole system
and its evaluation run from a fresh clone. It returns the same ``RawInvoice`` a
language model would, holding the document's own strings, and hands them to the
same deterministic parsers — so swapping it for a model changes where the strings
come from and nothing else.

It is deliberately not told which layout a document uses. It knows the vocabulary
suppliers use for each field (``Invoice No.``, ``Bill Number``, ``Doc #``...) and
looks for all of them on every document. That is the honest version of what it
does, and it is also why the evaluation reports it separately from any model: on
a corpus generated from four known layouts, a vocabulary-driven reader is expected
to do well, and its accuracy is an upper bound rather than a finding.
"""

from __future__ import annotations

import re

from countersign.extraction.schema import RawInvoice, RawLine
from countersign.intake import Intake

NAME = "offline"
VERSION = "rules-v1"

#: Label as printed -> schema field. Longer labels first where one contains another.
HEADER_LABELS: dict[str, str] = {
    "Invoice Number": "invoice_number",
    "Invoice No.": "invoice_number",
    "Bill Number": "invoice_number",
    "Doc #": "invoice_number",
    "INV NO": "invoice_number",
    "Invoice Date": "invoice_date",
    "Issue Date": "invoice_date",
    "Payment Due": "due_date",
    "Due Date": "due_date",
    "Due On": "due_date",
    "Dated": "invoice_date",
    "Date": "invoice_date",
    "DUE": "due_date",
    "DT": "invoice_date",
    "P.O. Number": "purchase_order_ref",
    "Purchase Order": "purchase_order_ref",
    "Against PO": "purchase_order_ref",
    "Order Ref": "purchase_order_ref",
    "PO REF": "purchase_order_ref",
    "Currency": "currency",
}

TOTAL_LABELS: dict[str, str] = {
    "Subtotal": "subtotal",
    "VAT / Tax": "tax_total",
    "Tax": "tax_total",
    "Total Payable": "total",
}

UNITS = ("MT", "BAG", "KG", "PCS", "TRIP", "PAIL")

_HEADER = re.compile(
    r"(?:^|\s)(" + "|".join(re.escape(label) for label in HEADER_LABELS) + r"):\s*(.+?)\s*$"
)
_TOTAL = re.compile(r"^(Subtotal|VAT / Tax|Total Payable):\s*(.+?)\s*$")
# Whitespace around the quantity and the unit is optional: in the two layouts
# with a tax column, a long description or a large price can run into the next
# column, and the text layer then has no space between them ("MT10,187.84").
# Text that is interleaved rather than merely touching cannot be recovered and is
# left to fail, which routes the document to a person.
_LINE = re.compile(
    r"^(?P<no>\d+)\s+(?P<sku>[A-Z]{3}-[A-Z0-9]+-[A-Z0-9]+)\s+(?P<desc>.+?)\s*"
    r"(?P<qty>[\d,]+(?:\.\d+)?)\s+(?P<uom>" + "|".join(UNITS) + r")\s*(?P<rest>.+)$"
)
_MONEY = re.compile(r"(?:(?:BDT|USD|Tk\.)\s)?[\d,]+\.\d{2}(?:\s(?:BDT|USD)\b)?")


def _split_rest(rest: str) -> tuple[str, str | None, str] | None:
    """Unit price, optional tax rate, and line total from the tail of a row."""
    amounts = _MONEY.findall(rest)
    if len(amounts) != 2:
        return None
    between = _MONEY.sub(" ", rest).split()
    rate = between[0] if between else None
    return amounts[0], rate, amounts[1]


def from_text(text: str) -> RawInvoice:
    fields: dict[str, str] = {}
    lines: list[RawLine] = []
    rows = [row.strip() for row in text.splitlines() if row.strip()]

    for index, row in enumerate(rows):
        if row.startswith("BIN/TIN:") and index > 0 and "vendor_name" not in fields:
            fields["vendor_name"] = rows[index - 1]
            continue

        total = _TOTAL.match(row)
        if total:
            fields.setdefault(TOTAL_LABELS[total.group(1)], total.group(2))
            continue

        line = _LINE.match(row)
        if line:
            split = _split_rest(line.group("rest"))
            if split:
                unit_price, rate, line_total = split
                lines.append(
                    RawLine(
                        line_no=int(line.group("no")),
                        sku=line.group("sku"),
                        description=line.group("desc"),
                        uom=line.group("uom"),
                        quantity=line.group("qty"),
                        unit_price=unit_price,
                        line_total=line_total,
                        tax_rate=rate,
                    )
                )
            continue

        header = _HEADER.search(row)
        if header:
            fields.setdefault(HEADER_LABELS[header.group(1)], header.group(2))

    return RawInvoice(lines=lines, **fields)


def from_rows(rows: list[list[str]]) -> RawInvoice:
    """Spreadsheets: a key-value block, a header row, the lines, then totals."""
    fields: dict[str, str] = {}
    lines: list[RawLine] = []
    columns: list[str] | None = None

    for position, row in enumerate(rows):
        cells = [cell for cell in row]
        filled = [cell for cell in cells if cell]
        if not filled:
            continue
        if position == 0:
            fields["vendor_name"] = filled[0]
            continue

        if columns is None:
            if cells[0] == "Line":
                columns = [cell for cell in cells if cell]
                continue
            if len(filled) >= 2 and filled[0] in HEADER_LABELS:
                fields.setdefault(HEADER_LABELS[filled[0]], filled[1])
            continue

        if cells[0].isdigit():
            record = dict(zip(columns, cells, strict=False))
            lines.append(
                RawLine(
                    line_no=int(record["Line"]),
                    sku=record.get("SKU") or None,
                    description=record.get("Description", ""),
                    uom=record.get("UoM") or None,
                    quantity=record.get("Quantity", ""),
                    unit_price=record.get("Unit Price", ""),
                    line_total=record.get("Amount", ""),
                    tax_rate=record.get("Tax %") or None,
                )
            )
        elif len(filled) >= 2 and filled[-2] in TOTAL_LABELS:
            fields.setdefault(TOTAL_LABELS[filled[-2]], filled[-1])

    return RawInvoice(lines=lines, **fields)


def extract(intake: Intake) -> RawInvoice:
    if intake.rows:
        return from_rows(intake.rows)
    return from_text("\n".join(intake.pages))
