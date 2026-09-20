"""Tables for the procurement records Countersign reconciles against.

Purchase orders and deliveries are the reference data an invoice is checked
against. They are treated as given: Countersign does not create or amend them.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from countersign.db.base import Base, Money, created_at_column, pk


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[str] = pk()
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Case-folded, suffix-stripped form used for duplicate detection. Derived by
    # a committed normalisation table, never inferred at read time.
    normalised_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(40))
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BDT", nullable=False)
    created_at: Mapped[datetime] = created_at_column()

    purchase_orders: Mapped[list[PurchaseOrder]] = relationship(back_populates="vendor")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = pk()
    po_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), index=True, nullable=False)
    ordered_at: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Money, nullable=False)
    tax_total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)

    vendor: Mapped[Vendor] = relationship(back_populates="purchase_orders")
    lines: Mapped[list[POLine]] = relationship(back_populates="po", cascade="all, delete-orphan")
    deliveries: Mapped[list[Delivery]] = relationship(back_populates="po")


class POLine(Base):
    __tablename__ = "po_lines"
    __table_args__ = (UniqueConstraint("po_id", "line_no"),)

    id: Mapped[str] = pk()
    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"), index=True, nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    sku: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    uom: Mapped[str] = mapped_column(String(12), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Money, nullable=False)

    po: Mapped[PurchaseOrder] = relationship(back_populates="lines")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[str] = pk()
    delivery_note_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"), index=True, nullable=False)
    delivered_at: Mapped[date] = mapped_column(Date, nullable=False)
    received_by: Mapped[str] = mapped_column(String(120), nullable=False)

    po: Mapped[PurchaseOrder] = relationship(back_populates="deliveries")
    lines: Mapped[list[DeliveryLine]] = relationship(
        back_populates="delivery", cascade="all, delete-orphan"
    )


class DeliveryLine(Base):
    __tablename__ = "delivery_lines"

    id: Mapped[str] = pk()
    delivery_id: Mapped[str] = mapped_column(
        ForeignKey("deliveries.id"), index=True, nullable=False
    )
    po_line_id: Mapped[str] = mapped_column(ForeignKey("po_lines.id"), index=True, nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Money, nullable=False)
    condition: Mapped[str] = mapped_column(String(20), default="good", nullable=False)

    delivery: Mapped[Delivery] = relationship(back_populates="lines")
