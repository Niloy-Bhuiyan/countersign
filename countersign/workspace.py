"""A reviewer's workspace: documents they processed and decisions they recorded.

Each workspace is isolated. The corpus is shared and read-only; everything a
reviewer adds — an uploaded invoice, an order raised in the lab, a decision —
lives under their own prefix in the store, so two people using the public console
never overwrite each other.

Uploaded documents run through ``batch.check_case``, the function the evaluation
measured, against the buyer's records plus the workspace's own orders, and against
a ledger that already knows every corpus invoice. A resubmitted corpus invoice is
therefore caught as a duplicate, not treated as new.
"""

from __future__ import annotations

import json
import re
import secrets
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from countersign import decisions
from countersign.agent.graph import recommend
from countersign.agent.tools import Toolbox
from countersign.batch import Case, check_case
from countersign.blobstore import BlobStore, get_json, put_json
from countersign.checks.base import Ledger
from countersign.extraction.pipeline import extract_document
from countersign.reference import Reference, build, with_overlay
from countersign.serialize import case_detail

WORKSPACE_ID = re.compile(r"^[a-z0-9]{8,32}$")
ALLOWED = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
}
MAX_BYTES = 4 * 1024 * 1024
#: A public demo workspace holds this many documents, so one link cannot fill the store.
MAX_DOCUMENTS = 200


class WorkspaceError(ValueError):
    pass


@dataclass
class Snapshot:
    """The shared, read-only state every workspace starts from."""

    reference: Reference
    ledger: dict
    unread: dict[str, list[str]]
    cases: dict[str, dict]

    @classmethod
    def load(cls, directory: Path) -> Snapshot:
        def read(name: str):
            return json.loads((directory / name).read_text(encoding="utf-8"))

        return cls(
            reference=build(
                read("vendors.json"), read("purchase_orders.json"), read("deliveries.json")
            ),
            ledger=read("ledger.json"),
            unread=read("unread.json"),
            cases=read("cases.json"),
        )


class Workspace:
    def __init__(
        self,
        workspace_id: str,
        store: BlobStore,
        snapshot: Snapshot,
        category_of: Callable[[str | None], str] = lambda _sku: "Uncategorised",
    ) -> None:
        if not WORKSPACE_ID.match(workspace_id):
            raise WorkspaceError("workspace id must be 8-32 lowercase letters or digits")
        self.id = workspace_id
        self.store = store
        self.snapshot = snapshot
        self.category_of = category_of
        self.prefix = f"ws/{workspace_id}/"

    # ---- reference data and ledger -------------------------------------------------

    def _rows(self, kind: str) -> list[dict]:
        return [get_json(self.store, p) for p in self.store.list(f"{self.prefix}{kind}/")]

    def reference(self) -> Reference:
        orders = self._rows("orders")
        return with_overlay(
            self.snapshot.reference,
            [o["order"] for o in orders],
            [o["delivery"] for o in orders],
        )

    def add_order(self, order_row: dict, delivery_row: dict) -> None:
        put_json(
            self.store,
            f"{self.prefix}orders/{order_row['id']}.json",
            {"order": order_row, "delivery": delivery_row},
        )

    def ledger(self) -> Ledger:
        ledger = Ledger.from_dict(self.snapshot.ledger)
        for delta in self._rows("ledger"):
            extra = Ledger.from_dict(delta)
            ledger.seen.extend(extra.seen)
            for (po_id, line_no), quantity in extra.billed.items():
                ledger.bill(po_id, line_no, quantity)
        return ledger

    # ---- documents -----------------------------------------------------------------

    def _sequence(self) -> int:
        return len(self.store.list(f"{self.prefix}cases/")) + 1

    def ensure_room(self) -> int:
        """The next document's sequence number, or refuse if the workspace is full."""
        sequence = self._sequence()
        if sequence > MAX_DOCUMENTS:
            raise WorkspaceError(
                f"this workspace is full ({MAX_DOCUMENTS} documents); open a new one"
            )
        return sequence

    def process(self, filename: str, data: bytes, *, origin: str, note: str = "") -> dict:
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED:
            raise WorkspaceError("upload a PDF, XLSX or CSV invoice")
        if not data:
            raise WorkspaceError("the file is empty")
        if len(data) > MAX_BYTES:
            raise WorkspaceError("files over 4 MB are not accepted")

        sequence = self.ensure_room()
        stem = "LAB" if origin == "lab" else "UPL"
        document_id = f"{stem}-{self.id[:4].upper()}{sequence:03d}"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"{document_id}{suffix}"
            path.write_bytes(data)
            extraction = extract_document(path)

        reference = self.reference()
        ledger = self.ledger()
        before = ledger.to_dict()
        case = Case(
            document_id=document_id, filename=f"{document_id}{suffix}", extraction=extraction
        )
        check_case(case, reference, ledger, self.snapshot.unread)
        after = ledger.to_dict()

        recommendation = (
            recommend(case, Toolbox(reference=reference, cases={})) if case.results else None
        )
        detail = case_detail(case, reference, recommendation, self.category_of)
        detail.update(
            origin=origin,
            originalFilename=Path(filename).name,
            receivedAt=datetime.now(UTC).isoformat(timespec="seconds"),
            note=note,
        )

        before_billed = {
            (b["po_id"], b["line_no"]): Decimal(b["quantity"]) for b in before["billed"]
        }
        delta = {
            "seen": after["seen"][len(before["seen"]) :],
            "billed": [
                {
                    "po_id": b["po_id"],
                    "line_no": b["line_no"],
                    "quantity": str(
                        Decimal(b["quantity"])
                        - before_billed.get((b["po_id"], b["line_no"]), Decimal(0))
                    ),
                }
                for b in after["billed"]
                if Decimal(b["quantity"])
                != before_billed.get((b["po_id"], b["line_no"]), Decimal(0))
            ],
        }

        self.store.put(f"{self.prefix}docs/{case.filename}", data, ALLOWED[suffix])
        put_json(self.store, f"{self.prefix}ledger/{sequence:04d}-{document_id}.json", delta)
        put_json(self.store, f"{self.prefix}cases/{sequence:04d}-{document_id}.json", detail)
        return detail

    def cases(self) -> list[dict]:
        rows = []
        for detail in self._rows("cases"):
            row = {
                key: detail[key]
                for key in (
                    "id",
                    "file",
                    "format",
                    "number",
                    "vendor",
                    "vendorId",
                    "po",
                    "issued",
                    "currency",
                    "total",
                    "category",
                    "state",
                    "reason",
                    "action",
                    "failed",
                    "abstained",
                )
            }
            row.update(origin=detail.get("origin"), receivedAt=detail.get("receivedAt"))
            rows.append(row)
        return rows

    def case(self, document_id: str) -> dict | None:
        for pathname in self.store.list(f"{self.prefix}cases/"):
            if pathname.endswith(f"-{document_id}.json"):
                return get_json(self.store, pathname)
        return None

    def document(self, filename: str) -> tuple[bytes, str] | None:
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED or "/" in filename or ".." in filename:
            return None
        data = self.store.get(f"{self.prefix}docs/{filename}")
        return None if data is None else (data, ALLOWED[suffix])

    # ---- decisions -----------------------------------------------------------------

    def events(self, invoice_id: str | None = None) -> list[dict]:
        prefix = f"{self.prefix}decisions/" + (f"{invoice_id}/" if invoice_id else "")
        events = [get_json(self.store, p) for p in self.store.list(prefix)]
        return sorted(events, key=lambda e: (e["at"], e.get("seq", 0)))

    def _system_view(self, invoice_id: str) -> tuple[str, str]:
        if invoice_id in self.snapshot.cases:
            known = self.snapshot.cases[invoice_id]
            return known["state"], known["action"]
        detail = self.case(invoice_id)
        if detail is None:
            raise WorkspaceError(f"no invoice {invoice_id} in the corpus or this workspace")
        return detail["state"], detail["action"]

    def decide(self, invoice_id: str, decision: str, reviewer: str, note: str) -> dict:
        system_state, action = self._system_view(invoice_id)
        history = self.events(invoice_id)
        event = decisions.record(
            invoice_id=invoice_id,
            system_state=system_state,
            recommended_action=action,
            events=history,
            decision=decision,
            reviewer=reviewer,
            note=note,
        )
        event["seq"] = len(history) + 1
        stamp = event["at"].replace(":", "").replace("+", "Z")
        put_json(
            self.store,
            f"{self.prefix}decisions/{invoice_id}/{stamp}-{event['seq']:03d}-{secrets.token_hex(3)}.json",
            event,
        )
        return event

    def current(self) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for event in self.events():
            latest[event["invoice_id"]] = event
        return {k: v for k, v in latest.items() if v["decision"] != decisions.WITHDRAWN}
