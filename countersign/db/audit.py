"""Check results, agent recommendations and human approvals.

These three tables are the audit trail. A controller asked why an invoice was held
should be able to answer from them alone: which rule fired, on what values, what
the agent proposed, and who decided.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from countersign.db.base import Base, Money, created_at_column, pk


class CheckResult(Base):
    """One deterministic check, run once against one invoice.

    ``observed``, ``expected`` and ``tolerance`` are stored rather than only the
    outcome, so the finding can be restated to a person as a sentence about
    numbers instead of a severity badge.
    """

    __tablename__ = "check_results"

    id: Mapped[str] = pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    # THREE_WAY_MATCH | PRICE_VARIANCE | DUPLICATE_INVOICE | TAX_ARITHMETIC
    check_code: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    # passed | failed | abstained
    outcome: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    # info | warning | blocking
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    invoice_line_id: Mapped[str | None] = mapped_column(ForeignKey("invoice_lines.id"))
    observed: Mapped[Decimal | None] = mapped_column(Money)
    expected: Mapped[Decimal | None] = mapped_column(Money)
    tolerance: Mapped[Decimal | None] = mapped_column(Money)
    # A sentence a controller can act on, naming the rule and the numbers.
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # Records this check actually consulted, as {"table": [ids]}.
    evidence_refs: Mapped[dict | None] = mapped_column(JSON)
    ran_at: Mapped[datetime] = created_at_column()


class Recommendation(Base):
    """A draft produced by the agent. It has no effect until a human approves it."""

    __tablename__ = "recommendations"

    id: Mapped[str] = pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    # CLEAR_FOR_PAYMENT | HOLD_REQUEST_CREDIT_NOTE | HOLD_REQUEST_DELIVERY_PROOF
    # | ESCALATE_TO_CONTROLLER
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    # One entry per sentence of the rationale, each pointing at a record that
    # exists. Sentences whose citation fails verification are removed before the
    # recommendation is written.
    citations: Mapped[list | None] = mapped_column(JSON)
    agent_version: Mapped[str] = mapped_column(String(20), nullable=False)
    steps_used: Mapped[int | None] = mapped_column()
    tool_calls_used: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = created_at_column()


class Approval(Base):
    """A human decision. Nothing leaves the review queue without one."""

    __tablename__ = "approvals"

    id: Mapped[str] = pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True, nullable=False)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("recommendations.id"))
    # approved | held | escalated
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(120), nullable=False)
    # Required when the decision disagrees with the recommendation.
    note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = created_at_column()
