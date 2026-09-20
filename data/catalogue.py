"""Vendor and item catalogue for the synthetic corpus.

Vendor names are assembled at generation time from three word lists rather than
written out by hand. That is deliberate: a hand-written list of plausible
Bangladeshi supplier names would eventually collide with a real company. A
combination drawn from generic place words, trade words and legal suffixes is
visibly synthetic and cannot be mistaken for a real trading relationship.

Prices are in BDT and are order-of-magnitude plausible for the categories named.
They are not market data and should not be read as such.
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

PLACE_WORDS = [
    "Padma", "Jamuna", "Meghna", "Titas", "Surma", "Karnaphuli", "Rupsha",
    "Shitalakshya", "Brahmaputra", "Teesta", "Sangu", "Halda",
]

TRADE_WORDS = [
    "Steel", "Cement", "Traders", "Industries", "Commodities", "Materials",
    "Textile", "Jute", "Packaging", "Engineering", "Supply", "Agro",
]

SUFFIXES = [
    "Ltd", "Limited", "Trading Ltd", "Industries Ltd", "Enterprise",
    "& Sons", "Corporation", "Trading House",
]


class Item(NamedTuple):
    sku: str
    description: str
    uom: str
    base_price: Decimal
    tax_rate: Decimal
    category: str


#: The purchasing catalogue. Categories match what a building-materials group
#: actually buys, which is what makes the spend dashboard mean anything.
CATALOGUE: list[Item] = [
    # Cement and clinker
    Item("CEM-OPC-50", "Ordinary Portland Cement 50kg bag", "BAG", Decimal("545.00"), Decimal("15"), "Cement"),
    Item("CEM-PCC-50", "Portland Composite Cement 50kg bag", "BAG", Decimal("520.00"), Decimal("15"), "Cement"),
    Item("RAW-CLK-BULK", "Imported clinker, bulk", "MT", Decimal("9850.00"), Decimal("15"), "Raw material"),
    Item("RAW-GYP-BULK", "Gypsum, bulk", "MT", Decimal("6200.00"), Decimal("15"), "Raw material"),
    Item("RAW-FLY-BULK", "Fly ash, bulk", "MT", Decimal("2400.00"), Decimal("15"), "Raw material"),
    Item("RAW-LST-BULK", "Limestone, crushed", "MT", Decimal("3100.00"), Decimal("15"), "Raw material"),
    # Steel
    Item("STL-ROD-10", "MS deformed bar 10mm", "MT", Decimal("89500.00"), Decimal("15"), "Steel"),
    Item("STL-ROD-12", "MS deformed bar 12mm", "MT", Decimal("89000.00"), Decimal("15"), "Steel"),
    Item("STL-ROD-16", "MS deformed bar 16mm", "MT", Decimal("88500.00"), Decimal("15"), "Steel"),
    Item("STL-BIL-125", "MS billet 125mm square", "MT", Decimal("72000.00"), Decimal("15"), "Steel"),
    Item("STL-SCR-HMS", "HMS scrap, sorted", "MT", Decimal("48000.00"), Decimal("15"), "Steel"),
    Item("STL-GI-SHEET", "GI corrugated sheet 0.42mm", "PCS", Decimal("1150.00"), Decimal("15"), "Steel"),
    # Textile and jute
    Item("TEX-YRN-30S", "Cotton yarn 30s carded", "KG", Decimal("395.00"), Decimal("7.5"), "Textile"),
    Item("TEX-YRN-40S", "Cotton yarn 40s combed", "KG", Decimal("455.00"), Decimal("7.5"), "Textile"),
    Item("JUT-HES-BTC", "Hessian cloth, B-twill", "PCS", Decimal("78.00"), Decimal("7.5"), "Jute"),
    Item("JUT-SAK-50", "Jute sack 50kg capacity", "PCS", Decimal("62.00"), Decimal("7.5"), "Jute"),
    # Packaging
    Item("PKG-PPB-50", "PP woven bag 50kg printed", "PCS", Decimal("18.50"), Decimal("15"), "Packaging"),
    Item("PKG-STR-12", "Steel strapping 12mm", "KG", Decimal("142.00"), Decimal("15"), "Packaging"),
    Item("PKG-SHR-FILM", "Shrink wrap film 500mm", "KG", Decimal("235.00"), Decimal("15"), "Packaging"),
    # Spares and consumables
    Item("SPR-BRG-6205", "Deep groove ball bearing 6205", "PCS", Decimal("480.00"), Decimal("15"), "Spares"),
    Item("SPR-BLT-B98", "V-belt B98", "PCS", Decimal("720.00"), Decimal("15"), "Spares"),
    Item("SPR-LUB-EP2", "Lithium grease EP2, 15kg", "PAIL", Decimal("4200.00"), Decimal("15"), "Spares"),
    Item("SPR-FLT-HYD", "Hydraulic filter element", "PCS", Decimal("2650.00"), Decimal("15"), "Spares"),
    Item("SPR-RFR-BRK", "Refractory brick, high alumina", "PCS", Decimal("310.00"), Decimal("15"), "Spares"),
    # Services
    Item("SVC-FRT-INL", "Inland freight, truck load", "TRIP", Decimal("14500.00"), Decimal("5"), "Freight"),
    Item("SVC-FRT-BRG", "River barge freight", "MT", Decimal("620.00"), Decimal("5"), "Freight"),
    Item("SVC-HND-LBR", "Loading and unloading labour", "MT", Decimal("185.00"), Decimal("5"), "Services"),
]

BY_SKU = {item.sku: item for item in CATALOGUE}

CATEGORIES = sorted({item.category for item in CATALOGUE})
