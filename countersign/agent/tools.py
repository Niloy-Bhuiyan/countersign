"""The agent's tools. All six read; none writes.

This module is the complete list. There is no tool that updates a record, changes
a state, sends anything or pays anything, and ``test_agent`` asserts the registry
holds exactly these names. Adding a write tool means changing that test, which
makes the decision visible in review instead of incidental.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from countersign.reference import Reference

READ_ONLY_TOOLS = frozenset(
    {
        "get_invoice",
        "get_purchase_order",
        "get_delivery_records",
        "get_vendor_price_history",
        "get_check_results",
        "find_similar_past_exceptions",
    }
)


@dataclass
class Toolbox:
    reference: Reference
    cases: dict  # document_id -> Case, only those that arrived before the current one

    def registry(self) -> dict[str, Callable]:
        tools = {
            "get_invoice": self.get_invoice,
            "get_purchase_order": self.get_purchase_order,
            "get_delivery_records": self.get_delivery_records,
            "get_vendor_price_history": self.get_vendor_price_history,
            "get_check_results": self.get_check_results,
            "find_similar_past_exceptions": self.find_similar_past_exceptions,
        }
        assert frozenset(tools) == READ_ONLY_TOOLS
        return tools

    def get_invoice(self, document_id: str):
        case = self.cases.get(document_id)
        return case.invoice if case else None

    def get_purchase_order(self, po_id: str):
        return self.reference.orders.get(po_id)

    def get_delivery_records(self, po_id: str):
        return list(self.reference.deliveries(po_id))

    def get_vendor_price_history(self, vendor_id: str, sku: str, before, window_days: int):
        return self.reference.price_history(vendor_id, sku, before, window_days)

    def get_check_results(self, document_id: str):
        case = self.cases.get(document_id)
        return list(case.results) if case else []

    def find_similar_past_exceptions(self, rule: str, vendor_id: str, limit: int = 3):
        found = []
        for case in self.cases.values():
            if case.vendor_id != vendor_id:
                continue
            if any(result.rule == rule and result.outcome == "failed" for result in case.results):
                found.append(case.document_id)
        return found[-limit:]
