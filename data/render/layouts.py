"""Four invoice layouts, differing in the ways real suppliers differ.

Extraction is only a real problem if the documents disagree with each other. Each
layout changes the things that actually break a naive parser:

* what the document calls a field: ``Invoice No.`` / ``Bill Number`` / ``Doc #``
* how it writes a date: ``15 Mar 2026`` / ``2026-03-15`` / ``15/03/2026``
* how it writes money: ``BDT 1,234.56`` / ``Tk. 1,234.56`` / ``1,234.56``
* whether the line table carries a tax column, a discount column, or neither
* whether totals sit under the table or in a block to one side

A layout is assigned per vendor, not per invoice, because a supplier's invoices
look the same as each other. That also means a parser that overfits to one vendor
fails on a predictable, reproducible subset rather than at random.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Layout:
    key: str
    title: str
    number_label: str
    date_label: str
    due_label: str
    po_label: str
    bill_to_label: str
    date_format: str
    money_style: str
    columns: tuple[str, ...]
    show_tax_column: bool
    totals_on_right: bool


LAYOUTS: tuple[Layout, ...] = (
    Layout(
        key="A",
        title="INVOICE",
        number_label="Invoice No.",
        date_label="Date",
        due_label="Due Date",
        po_label="P.O. Number",
        bill_to_label="Bill To",
        date_format="%d %b %Y",
        money_style="prefix_bdt",
        columns=("#", "Description", "Qty", "UoM", "Unit Price", "Amount"),
        show_tax_column=False,
        totals_on_right=True,
    ),
    Layout(
        key="B",
        title="TAX INVOICE",
        number_label="Bill Number",
        date_label="Issue Date",
        due_label="Payment Due",
        po_label="Against PO",
        bill_to_label="Buyer",
        date_format="%Y-%m-%d",
        money_style="suffix_bdt",
        columns=("Sl", "Particulars", "Quantity", "Unit", "Rate", "VAT %", "Value"),
        show_tax_column=True,
        totals_on_right=False,
    ),
    Layout(
        key="C",
        title="COMMERCIAL INVOICE",
        number_label="Doc #",
        date_label="Dated",
        due_label="Due On",
        po_label="Order Ref",
        bill_to_label="Consignee",
        date_format="%d/%m/%Y",
        money_style="prefix_tk",
        columns=("Item", "Goods Description", "Qty", "UOM", "Price", "Total"),
        show_tax_column=False,
        totals_on_right=True,
    ),
    Layout(
        key="D",
        title="SUPPLIER INVOICE",
        number_label="INV NO",
        date_label="DT",
        due_label="DUE",
        po_label="PO REF",
        bill_to_label="TO",
        date_format="%b %d, %Y",
        money_style="plain",
        columns=("LN", "ITEM / DESCRIPTION", "QTY", "UM", "RATE", "VAT%", "AMOUNT"),
        show_tax_column=True,
        totals_on_right=False,
    ),
)

BY_KEY = {layout.key: layout for layout in LAYOUTS}


def layout_for_vendor(vendor_id: str) -> Layout:
    """Stable assignment, so a vendor's documents always look the same."""
    return LAYOUTS[int(vendor_id.split("-")[1]) % len(LAYOUTS)]


def format_date(value: date, layout: Layout) -> str:
    return value.strftime(layout.date_format)


def format_money(value: Decimal, layout: Layout, currency: str = "BDT") -> str:
    grouped = f"{value:,.2f}"
    if layout.money_style == "prefix_bdt":
        return f"{currency} {grouped}"
    if layout.money_style == "suffix_bdt":
        return f"{grouped} {currency}"
    if layout.money_style == "prefix_tk":
        return f"Tk. {grouped}" if currency == "BDT" else f"{currency} {grouped}"
    return grouped


def format_quantity(value: Decimal) -> str:
    """Drop a trailing ``.00`` the way an invoice would print it."""
    if value == value.to_integral_value():
        return f"{value.to_integral_value():,}"
    return f"{value:,.2f}"
