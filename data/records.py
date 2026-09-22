"""Seeded generation of the procurement records an invoice is checked against.

Two properties of this generator matter more than realism:

* **Every vendor has price history.** A vendor supplies a small fixed set of SKUs
  and is ordered from repeatedly across the period, so the price-variance check
  has something to compare against. A corpus of one-off purchases would make that
  check abstain on every invoice and prove nothing.
* **Clean invoices are exactly clean.** An invoice with no planted defect agrees
  with its purchase order and delivery to the cent. Any check that fires on one is
  a false positive, with no ambiguity about whether the corpus was at fault.

Defects are applied afterwards, in ``data.defects``, so the two concerns stay
separable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from countersign.money import line_total as compute_line_total
from countersign.money import money, tax_of
from countersign.vendors import normalise_vendor_name
from data.catalogue import CATALOGUE, PLACE_WORDS, SUFFIXES, TRADE_WORDS, Item

#: The corpus covers 14 months so that a 365-day price-history window is full for
#: invoices near the end of the period.
PERIOD_END = date(2026, 9, 1)
PERIOD_DAYS = 425

N_VENDORS = 40
N_PURCHASE_ORDERS = 460

#: Closed orders from the year before the period. A real order book goes back
#: years before any window being audited; without it, an invoice early in the
#: period has no earlier price to be judged against and the variance check can
#: only abstain. These orders are reference data only: no invoice bills them.
HISTORY_ORDERS_PER_VENDOR = 12
HISTORY_DAYS = 365


@dataclass
class Line:
    line_no: int
    sku: str
    description: str
    uom: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    tax_rate: Decimal


@dataclass
class Vendor:
    id: str
    legal_name: str
    normalised_name: str
    tax_id: str
    payment_terms_days: int
    currency: str
    skus: list[str]
    # Multiplier on catalogue price. A cheap vendor stays cheap, which is what
    # makes a price jump on one invoice detectable against that vendor's own past.
    price_factor: Decimal


@dataclass
class PurchaseOrder:
    id: str
    po_number: str
    vendor_id: str
    ordered_at: date
    currency: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    status: str
    lines: list[Line] = field(default_factory=list)


@dataclass
class DeliveryLine:
    po_line_no: int
    quantity_received: Decimal
    condition: str


@dataclass
class Delivery:
    id: str
    delivery_note_number: str
    po_id: str
    delivered_at: date
    received_by: str
    lines: list[DeliveryLine] = field(default_factory=list)


RECEIVERS = [
    "Store Officer, Plant 1",
    "Store Officer, Plant 2",
    "Warehouse Supervisor, Dhaka",
    "Warehouse Supervisor, Chattogram",
    "Site Storekeeper, Unit C",
]


def _quantity_for(rng: random.Random, item: Item) -> Decimal:
    """Order sizes that suit the unit of measure."""
    if item.uom == "MT":
        return money(rng.randrange(5, 120))
    if item.uom == "BAG":
        return money(rng.randrange(200, 4000, 50))
    if item.uom == "KG":
        return money(rng.randrange(100, 5000, 50))
    if item.uom == "TRIP":
        return money(rng.randrange(1, 12))
    if item.uom == "PAIL":
        return money(rng.randrange(2, 30))
    return money(rng.randrange(20, 1500, 10))


def _price_for(rng: random.Random, item: Item, vendor: Vendor, ordered_at: date) -> Decimal:
    """Catalogue price, adjusted for the vendor and drifted slowly over time.

    Drift is small and monotonic-ish so that a genuine market move does not look
    like a defect, while a single invoice priced 30% above the vendor's own median
    still stands out.
    """
    months_back = (PERIOD_END - ordered_at).days / 30
    drift = Decimal(1) - Decimal(str(round(months_back * 0.004, 4)))
    jitter = Decimal(str(round(rng.uniform(0.985, 1.015), 4)))
    return money(item.base_price * vendor.price_factor * drift * jitter)


def _totals(lines: list[Line]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = money(sum((line.line_total for line in lines), Decimal(0)))
    tax_total = money(sum((tax_of(line.line_total, line.tax_rate) for line in lines), Decimal(0)))
    return subtotal, tax_total, money(subtotal + tax_total)


def generate_vendors(rng: random.Random) -> list[Vendor]:
    names: set[str] = set()
    vendors: list[Vendor] = []

    while len(vendors) < N_VENDORS:
        legal_name = f"{rng.choice(PLACE_WORDS)} {rng.choice(TRADE_WORDS)} {rng.choice(SUFFIXES)}"
        if legal_name in names:
            continue
        names.add(legal_name)

        # A vendor supplies one category, the way a real supplier does.
        category = rng.choice(sorted({item.category for item in CATALOGUE}))
        in_category = [item.sku for item in CATALOGUE if item.category == category]
        skus = rng.sample(in_category, k=min(len(in_category), rng.randint(2, 4)))

        vendors.append(
            Vendor(
                id=f"VEN-{len(vendors) + 1:03d}",
                legal_name=legal_name,
                normalised_name=normalise_vendor_name(legal_name),
                tax_id=f"{rng.randrange(10**8, 10**9)}",
                payment_terms_days=rng.choice([15, 30, 30, 45, 60]),
                currency="BDT",
                skus=skus,
                price_factor=Decimal(str(round(rng.uniform(0.94, 1.07), 4))),
            )
        )
    return vendors


def generate_purchase_orders(rng: random.Random, vendors: list[Vendor]) -> list[PurchaseOrder]:
    by_sku = {item.sku: item for item in CATALOGUE}
    orders: list[PurchaseOrder] = []

    for n in range(1, N_PURCHASE_ORDERS + 1):
        vendor = rng.choice(vendors)
        ordered_at = PERIOD_END - timedelta(days=rng.randrange(0, PERIOD_DAYS))
        chosen = rng.sample(vendor.skus, k=min(len(vendor.skus), rng.randint(1, 3)))

        lines = []
        for line_no, sku in enumerate(chosen, start=1):
            item = by_sku[sku]
            quantity = _quantity_for(rng, item)
            unit_price = _price_for(rng, item, vendor, ordered_at)
            lines.append(
                Line(
                    line_no=line_no,
                    sku=item.sku,
                    description=item.description,
                    uom=item.uom,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=compute_line_total(quantity, unit_price),
                    tax_rate=item.tax_rate,
                )
            )

        subtotal, tax_total, total = _totals(lines)
        orders.append(
            PurchaseOrder(
                id=f"PO-{n:04d}",
                po_number=f"PO/{ordered_at.year}/{n:05d}",
                vendor_id=vendor.id,
                ordered_at=ordered_at,
                currency=vendor.currency,
                subtotal=subtotal,
                tax_total=tax_total,
                total=total,
                status="open",
                lines=lines,
            )
        )
    return orders


def generate_deliveries(rng: random.Random, orders: list[PurchaseOrder]) -> list[Delivery]:
    """Deliver most orders in full, some in two shipments, and leave some open.

    The undelivered tail is not noise. It is what the "invoiced against a PO that
    was never delivered" defect is planted into, and what makes the three-way
    match abstain rather than pass when a delivery note is genuinely absent.
    """
    deliveries: list[Delivery] = []
    counter = 0

    for order in orders:
        roll = rng.random()
        if roll < 0.08:
            continue  # never delivered

        shipments = 2 if roll > 0.88 else 1
        for shipment in range(shipments):
            counter += 1
            delivered_at = order.ordered_at + timedelta(days=rng.randrange(3, 28))
            if delivered_at > PERIOD_END:
                delivered_at = PERIOD_END

            lines = []
            for po_line in order.lines:
                if shipments == 1:
                    received = po_line.quantity
                else:
                    half = money(po_line.quantity / 2)
                    received = half if shipment == 0 else money(po_line.quantity - half)
                lines.append(
                    DeliveryLine(
                        po_line_no=po_line.line_no,
                        quantity_received=received,
                        condition="good",
                    )
                )

            deliveries.append(
                Delivery(
                    id=f"DN-{counter:04d}",
                    delivery_note_number=f"DN/{delivered_at.year}/{counter:05d}",
                    po_id=order.id,
                    delivered_at=delivered_at,
                    received_by=rng.choice(RECEIVERS),
                    lines=lines,
                )
            )

    return deliveries


def generate_order_history(rng: random.Random, vendors: list[Vendor]) -> list[PurchaseOrder]:
    """Closed purchase orders from the year before the period, for price history."""
    by_sku = {item.sku: item for item in CATALOGUE}
    period_start = PERIOD_END - timedelta(days=PERIOD_DAYS)
    orders: list[PurchaseOrder] = []

    for vendor in vendors:
        for _ in range(HISTORY_ORDERS_PER_VENDOR):
            ordered_at = period_start - timedelta(days=rng.randrange(1, HISTORY_DAYS))
            chosen = rng.sample(vendor.skus, k=min(len(vendor.skus), rng.randint(1, 3)))
            lines = []
            for line_no, sku in enumerate(chosen, start=1):
                item = by_sku[sku]
                quantity = _quantity_for(rng, item)
                unit_price = _price_for(rng, item, vendor, ordered_at)
                lines.append(
                    Line(
                        line_no=line_no,
                        sku=item.sku,
                        description=item.description,
                        uom=item.uom,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=compute_line_total(quantity, unit_price),
                        tax_rate=item.tax_rate,
                    )
                )
            subtotal, tax_total, total = _totals(lines)
            n = len(orders) + 1
            orders.append(
                PurchaseOrder(
                    id=f"PO-H{n:04d}",
                    po_number=f"PO/{ordered_at.year}/H{n:04d}",
                    vendor_id=vendor.id,
                    ordered_at=ordered_at,
                    currency=vendor.currency,
                    subtotal=subtotal,
                    tax_total=tax_total,
                    total=total,
                    status="closed",
                    lines=lines,
                )
            )
    return orders
