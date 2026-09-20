"""Documents, extractions and the invoices derived from them.

An invoice is never created directly. It is always the parsed result of a
document, so every field on it can be traced back to the file it came from and
the extraction run that produced it.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from countersign.db.base import Base, Money, created_at_column, pk


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = pk()
    source_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    media_type: Mapped[str] = mapped_column(String(80), nullable=False)
    # Content hash. Two uploads of the same bytes are the same document, which is
    # the cheapest duplicate signal available and runs before any extraction cost.
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # readable | quarantined_unreadable | quarantined_encrypted | quarantined_image_only
    intake_status: Mapped[str] = mapped_column(String(40), default="readable", nullable=False)
    uploaded_at: Mapped[datetime] = created_at_column()

    extractions: Mapped[list[Extraction]] = relationship(back_populates="document")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = pk()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    # Which committed prompt directory produced this. Recorded on every row so a
    # result can be reproduced against the prompt that actually generated it.
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text)
    parsed_payload: Mapped[dict | None] = mapped_column(JSON)
    field_confidences: Mapped[dict | None] = mapped_column(JSON)
    validator_failures: Mapped[list | None] = mapped_column(JSON)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extraction_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at_column()

    document: Mapped[Document] = relationship(back_populates="extractions")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = pk()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    extraction_id: Mapped[str | None] = mapped_column(ForeignKey("extractions.id"))
    invoice_number: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    vendor_id: Mapped[str | None] = mapped_column(ForeignKey("vendors.id"), index=True)
    po_id: Mapped[str | None] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    issued_at: Mapped[date | None] = mapped_column(Date)
    due_at: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str | None] = mapped_column(String(3))
    subtotal: Mapped[Decimal | None] = mapped_column(Money)
    tax_total: Mapped[Decimal | None] = mapped_column(Money)
    total: Mapped[Decimal | None] = mapped_column(Money)
    # See countersign.states for the permitted transitions.
    state: Mapped[str] = mapped_column(String(20), default="received", index=True, nullable=False)
    created_at: Mapped[datetime] = created_at_column()

    lines: Mapped[list[InvoiceLine]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    __table_args__ = (UniqueConstraint("invoice_id", "line_no"),)

    id: Mapped[str] = pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    uom: Mapped[str | None] = mapped_column(String(12))
    quantity: Mapped[Decimal] = mapped_column(Money, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Money, nullable=False)
    tax_rate: Mapped[Decimal | None] = mapped_column(Money)
    # Set by the three-way match, not by extraction.
    matched_po_line_id: Mapped[str | None] = mapped_column(ForeignKey("po_lines.id"))
    match_confidence: Mapped[float | None] = mapped_column(Float)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
