"""The buyer's own records: vendors, purchase orders and deliveries.

This is what an invoice is checked *against*, and the supplier never touches it.
That asymmetry is the security property the whole design rests on (see
docs/security.md): the document is hostile, the reference data is not.

The loader reads exactly three files. It never opens the invoice truth or the
ground truth; a test asserts that nothing in ``countersign`` does.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from countersign.vendors import normalise_vendor_name


@dataclass(frozen=True)
class Vendor:
    id: str
    legal_name: str
    normalised_name: str
    tax_id: str
    payment_terms_days: int
    currency: str


@dataclass(frozen=True)
class POLine:
    po_id: str
    line_no: int
    sku: str
    description: str
    uom: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal


@dataclass(frozen=True)
class PurchaseOrder:
    id: str
    po_number: str
    vendor_id: str
    ordered_at: date
    currency: str
    total: Decimal
    lines: tuple[POLine, ...]


@dataclass(frozen=True)
class DeliveryLine:
    po_line_no: int
    quantity_received: Decimal


@dataclass(frozen=True)
class Delivery:
    id: str
    delivery_note_number: str
    po_id: str
    delivered_at: date
    lines: tuple[DeliveryLine, ...]


@dataclass
class Reference:
    vendors: dict[str, Vendor]
    orders: dict[str, PurchaseOrder]
    deliveries_by_po: dict[str, list[Delivery]]
    by_normalised_name: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.by_normalised_name = {}
        for vendor in self.vendors.values():
            self.by_normalised_name.setdefault(vendor.normalised_name, []).append(vendor.id)

    def identify_vendor(self, written: str, tax_id: str | None) -> tuple[Vendor | None, str]:
        """Resolve the supplier from the name and tax ID the document prints.

        The normalisation table strips legal form by design, so "Teesta Industries
        Ltd" and "Teesta Industries Corporation" share a key while being two
        companies. The name narrows the candidates; the tax ID decides between
        them. A tax ID that contradicts the name is not resolved in either
        direction: it goes to a person.
        """
        candidates = [
            self.vendors[vendor_id]
            for vendor_id in self.by_normalised_name.get(normalise_vendor_name(written), [])
        ]
        if not candidates:
            return None, "vendor_not_on_master"
        if tax_id:
            for vendor in candidates:
                if vendor.tax_id == tax_id:
                    return vendor, "name_and_tax_id"
            return None, "vendor_tax_id_mismatch"
        if len(candidates) == 1:
            return candidates[0], "name_only"
        return None, "vendor_ambiguous"

    def deliveries(self, po_id: str) -> list[Delivery]:
        return self.deliveries_by_po.get(po_id, [])

    def price_history(self, vendor_id: str, sku: str, before: date, window_days: int):
        """Prices this vendor agreed for this item on earlier orders in the window."""
        history = []
        for order in self.orders.values():
            if order.vendor_id != vendor_id or not order.ordered_at < before:
                continue
            if (before - order.ordered_at).days > window_days:
                continue
            for line in order.lines:
                if line.sku == sku:
                    history.append((order.id, order.ordered_at, line.unit_price))
        return sorted(history, key=lambda item: item[1])


def _d(value) -> Decimal:
    return Decimal(str(value)) if not isinstance(value, str) else Decimal(value)


def load(directory: Path) -> Reference:
    vendors_raw = json.loads((directory / "vendors.json").read_text(encoding="utf-8"))
    orders_raw = json.loads((directory / "purchase_orders.json").read_text(encoding="utf-8"))
    deliveries_raw = json.loads((directory / "deliveries.json").read_text(encoding="utf-8"))

    vendors = {
        row["id"]: Vendor(
            id=row["id"],
            legal_name=row["legal_name"],
            normalised_name=row["normalised_name"],
            tax_id=row["tax_id"],
            payment_terms_days=row["payment_terms_days"],
            currency=row["currency"],
        )
        for row in vendors_raw
    }

    orders = {}
    for row in orders_raw:
        lines = tuple(
            POLine(
                po_id=row["id"],
                line_no=line["line_no"],
                sku=line["sku"],
                description=line["description"],
                uom=line["uom"],
                quantity=_d(line["quantity"]),
                unit_price=_d(line["unit_price"]),
                tax_rate=_d(line["tax_rate"]),
            )
            for line in row["lines"]
        )
        orders[row["id"]] = PurchaseOrder(
            id=row["id"],
            po_number=row["po_number"],
            vendor_id=row["vendor_id"],
            ordered_at=date.fromisoformat(row["ordered_at"]),
            currency=row["currency"],
            total=_d(row["total"]),
            lines=lines,
        )

    deliveries_by_po: dict[str, list[Delivery]] = {}
    for row in deliveries_raw:
        delivery = Delivery(
            id=row["id"],
            delivery_note_number=row["delivery_note_number"],
            po_id=row["po_id"],
            delivered_at=date.fromisoformat(row["delivered_at"]),
            lines=tuple(
                DeliveryLine(line["po_line_no"], _d(line["quantity_received"]))
                for line in row["lines"]
            ),
        )
        deliveries_by_po.setdefault(delivery.po_id, []).append(delivery)

    return Reference(vendors=vendors, orders=orders, deliveries_by_po=deliveries_by_po)
