"""Render an invoice to PDF in one of the four layouts.

The text layer matters more than the appearance: this is what ``pdfplumber`` will
read back, so the column positions have to be stable enough to reconstruct a table
and varied enough between layouts that a parser cannot hard-code them.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

from data.invoices import Invoice
from data.records import Vendor
from data.render.layouts import (
    Layout,
    format_date,
    format_money,
    format_quantity,
    layout_for_vendor,
)

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm

# The buyer is a fictional entity. Naming a real company as the recipient of five
# hundred fabricated invoices would produce documents that could be mistaken for
# records of a real trading relationship.
BUYER_BLOCK = [
    "Meridian Industrial Group Ltd",
    "Fictional buyer, synthetic corpus",
    "Dhaka, Bangladesh",
]


def _column_x(layout: Layout) -> list[float]:
    """Right edges for numeric columns, left edges for text ones."""
    if layout.show_tax_column:
        return [
            MARGIN,
            MARGIN + 14 * mm,
            MARGIN + 88 * mm,
            MARGIN + 104 * mm,
            MARGIN + 124 * mm,
            MARGIN + 142 * mm,
            PAGE_W - MARGIN,
        ]
    return [
        MARGIN,
        MARGIN + 14 * mm,
        MARGIN + 96 * mm,
        MARGIN + 114 * mm,
        MARGIN + 142 * mm,
        PAGE_W - MARGIN,
    ]


def _header(c: pdfcanvas.Canvas, invoice: Invoice, vendor: Vendor, layout: Layout) -> float:
    y = PAGE_H - MARGIN

    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN, y, vendor.legal_name)
    y -= 6 * mm
    c.setFont("Helvetica", 8.5)
    c.drawString(MARGIN, y, f"BIN/TIN: {vendor.tax_id}")
    y -= 4 * mm
    c.drawString(MARGIN, y, "Supplier address withheld in synthetic data")

    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN, layout.title)

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN, y, layout.bill_to_label.upper())
    c.setFont("Helvetica", 9)
    for offset, line in enumerate(BUYER_BLOCK, start=1):
        c.drawString(MARGIN, y - offset * 4.4 * mm, line)

    fields = [
        (layout.number_label, invoice.invoice_number),
        (layout.date_label, format_date(invoice.issued_at, layout)),
        (layout.due_label, format_date(invoice.due_at, layout)),
        (layout.po_label, invoice.po_id or "-"),
        ("Currency", invoice.currency),
    ]
    fy = y
    for label, value in fields:
        c.setFont("Helvetica", 9)
        c.drawRightString(PAGE_W - MARGIN - 42 * mm, fy, f"{label}:")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(PAGE_W - MARGIN, fy, str(value))
        fy -= 5 * mm

    return min(y - len(BUYER_BLOCK) * 4.4 * mm, fy) - 8 * mm


def _table(c: pdfcanvas.Canvas, invoice: Invoice, layout: Layout, y: float) -> float:
    xs = _column_x(layout)

    c.setFont("Helvetica-Bold", 8.5)
    c.line(MARGIN, y + 3 * mm, PAGE_W - MARGIN, y + 3 * mm)
    for index, heading in enumerate(layout.columns):
        if index <= 1:
            c.drawString(xs[index], y, heading)
        else:
            c.drawRightString(xs[index], y, heading)
    y -= 2 * mm
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 5 * mm

    c.setFont("Helvetica", 8.5)
    for line in invoice.lines:
        cells = [
            str(line.line_no),
            f"{line.sku}  {line.description}",
            format_quantity(line.quantity),
            line.uom,
            format_money(line.unit_price, layout, invoice.currency),
        ]
        if layout.show_tax_column:
            cells.append(f"{line.tax_rate:g}")
        cells.append(format_money(line.line_total, layout, invoice.currency))

        for index, cell in enumerate(cells):
            if index <= 1:
                c.drawString(xs[index], y, cell)
            else:
                c.drawRightString(xs[index], y, cell)
        y -= 5 * mm

    c.line(MARGIN, y + 1.5 * mm, PAGE_W - MARGIN, y + 1.5 * mm)
    return y - 6 * mm


def _totals(c: pdfcanvas.Canvas, invoice: Invoice, layout: Layout, y: float) -> None:
    rows = [
        ("Subtotal", invoice.subtotal),
        ("VAT / Tax", invoice.tax_total),
        ("Total Payable", invoice.total),
    ]
    right = PAGE_W - MARGIN if layout.totals_on_right else MARGIN + 92 * mm
    label_right = right - 38 * mm

    for index, (label, amount) in enumerate(rows):
        bold = index == len(rows) - 1
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 9.5 if bold else 9)
        c.drawRightString(label_right, y, f"{label}:")
        c.drawRightString(right, y, format_money(amount, layout, invoice.currency))
        y -= 5.5 * mm

    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(
        MARGIN,
        MARGIN,
        "Synthetic document generated for the Countersign project. Not a real invoice.",
    )


def render(invoice: Invoice, vendor: Vendor, path: Path) -> Path:
    layout = layout_for_vendor(vendor.id)
    path.parent.mkdir(parents=True, exist_ok=True)

    c = pdfcanvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"{layout.title} {invoice.invoice_number}")
    y = _header(c, invoice, vendor, layout)
    y = _table(c, invoice, layout, y)
    _totals(c, invoice, layout, y)
    c.showPage()
    c.save()
    return path
