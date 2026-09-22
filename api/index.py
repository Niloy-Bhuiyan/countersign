"""The live API behind the console. Deployed as a Vercel Python function.

Thin on purpose: HTTP, input validation and storage wiring only. Every rule — what
a document says, whether it passes the checks, what the agent recommends, whether
a decision is allowed — is the tested code in ``countersign``, the same code the
evaluation measured.

Storage is a private Vercel Blob store when ``BLOB_READ_WRITE_TOKEN`` is set, and
an in-memory store otherwise (local runs and tests). ``/api/health`` says which.
"""

from __future__ import annotations

import csv
import io
import os
import sys
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated

# In the repository the packages sit at the root. In the deployment they are
# bundled under api/_pkg, because the static console already owns /data/.
HERE = Path(__file__).resolve().parent
for candidate in (HERE / "_pkg", HERE.parent):
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from countersign.blobstore import (  # noqa: E402
    BlobExists,
    MemoryBlob,
    StorageError,
    VercelBlob,
    get_json,
    put_json,
)
from countersign.decisions import DecisionError  # noqa: E402
from countersign.workspace import MAX_BYTES, Snapshot, Workspace, WorkspaceError  # noqa: E402
from data.catalogue import BY_SKU  # noqa: E402
from data.lab import TAMPERS, Scenario, compose  # noqa: E402

SNAPSHOT_DIR = Path(os.environ.get("COUNTERSIGN_SNAPSHOT_DIR", Path(__file__).parent / "_data"))

app = FastAPI(title="Countersign", docs_url="/api/docs", openapi_url="/api/openapi.json")


def category_of(sku: str | None) -> str:
    item = BY_SKU.get(sku or "")
    return item.category if item else "Uncategorised"


@lru_cache(maxsize=1)
def snapshot() -> Snapshot:
    return Snapshot.load(SNAPSHOT_DIR)


@lru_cache(maxsize=1)
def store():
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    return VercelBlob(token) if token else MemoryBlob()


def workspace(ws: str) -> Workspace:
    try:
        return Workspace(ws, store(), snapshot(), category_of)
    except WorkspaceError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.exception_handler(WorkspaceError)
async def _workspace_error(_request, exc: WorkspaceError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(DecisionError)
async def _decision_error(_request, exc: DecisionError):
    return JSONResponse({"detail": str(exc)}, status_code=422)


@app.exception_handler(BlobExists)
async def _blob_exists(_request, _exc: BlobExists):
    return JSONResponse({"detail": "two saves collided; try again"}, status_code=409)


@app.exception_handler(StorageError)
async def _storage_error(_request, _exc: StorageError):
    return JSONResponse(
        {"detail": "storage is unavailable right now; try again in a moment"}, status_code=503
    )


#: Served back to the browser, an uploaded file is inert: no scripts, no sniffing.
FILE_HEADERS = {
    "cache-control": "private, max-age=3600",
    "content-security-policy": "sandbox",
    "x-content-type-options": "nosniff",
}


def _csv_cell(value):
    """Neutralise text a spreadsheet would run as a formula (CSV injection)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@app.get("/api/health")
def health():
    snap = snapshot()
    return {
        "ok": True,
        "storage": "vercel-blob" if isinstance(store(), VercelBlob) else "memory",
        "corpus_cases": len(snap.cases),
        "orders": len(snap.reference.orders),
        "ledger_invoices": len(snap.ledger["seen"]),
    }


@app.get("/api/lab/options")
def lab_options():
    reference = snapshot().reference
    vendors = []
    for vendor in sorted(reference.vendors.values(), key=lambda v: v.legal_name):
        skus = sorted(
            {
                line.sku
                for o in reference.orders.values()
                if o.vendor_id == vendor.id
                for line in o.lines
            }
        )
        # Whether any item has enough earlier prices for the variance check to judge
        # a lab invoice. Without that, "inflate the order" can only make it abstain.
        order_day = date.today() - timedelta(days=12)
        ready = any(
            len(reference.price_history(vendor.id, sku, order_day, 365)) >= 5 for sku in skus
        )
        vendors.append(
            {
                "id": vendor.id,
                "name": vendor.legal_name,
                "category": category_of(skus[0]) if skus else "Uncategorised",
                "items": [BY_SKU[s].description for s in skus if s in BY_SKU],
                "historyReady": ready,
            }
        )
    vendors.sort(key=lambda v: (not v["historyReady"], v["name"]))
    return {"vendors": vendors, "tampers": [{"id": k, **v} for k, v in TAMPERS.items()]}


class LabRequest(BaseModel):
    vendorId: str
    tamper: str


def _previous_scenario(ws: Workspace) -> Scenario | None:
    metas = ws.store.list(f"{ws.prefix}lab/")
    if not metas:
        return None
    meta = get_json(ws.store, metas[-1])
    document = ws.store.get(f"{ws.prefix}lab-docs/{meta['filename']}")
    return Scenario(
        order_row=meta["order_row"],
        delivery_row=meta["delivery_row"],
        invoice_number=meta["invoice_number"],
        document=document or b"",
        filename=meta["filename"],
        tamper=meta["tamper"],
    )


@app.post("/api/workspaces/{ws}/lab")
def run_lab(ws: str, body: LabRequest):
    space = workspace(ws)
    if body.tamper not in TAMPERS:
        raise HTTPException(400, "unknown scenario")
    space.ensure_room()
    previous = _previous_scenario(space)
    sequence = len(space.store.list(f"{space.prefix}lab/")) + 1
    try:
        scenario = compose(
            space.reference(),
            vendor_id=body.vendorId
            if body.tamper != "resubmit" or previous is None
            else previous.order_row["vendor_id"],
            tamper=body.tamper,
            sequence=sequence,
            workspace=space.id,
            today=date.today(),
            previous=previous,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    if body.tamper != "resubmit":
        # A resubmission reuses the earlier order and the stored original: the same
        # bytes sent twice. Stored objects are never overwritten.
        space.add_order(scenario.order_row, scenario.delivery_row)
        space.store.put(
            f"{space.prefix}lab-docs/{scenario.filename}", scenario.document, "application/pdf"
        )
    put_json(
        space.store,
        f"{space.prefix}lab/{sequence:04d}.json",
        {
            "order_row": scenario.order_row,
            "delivery_row": scenario.delivery_row,
            "invoice_number": scenario.invoice_number,
            "filename": scenario.filename,
            "tamper": scenario.tamper,
        },
    )
    detail = space.process(
        scenario.filename, scenario.document, origin="lab", note=TAMPERS[scenario.tamper]["label"]
    )
    detail["scenario"] = {"tamper": scenario.tamper, **TAMPERS[scenario.tamper]}
    return detail


@app.post("/api/workspaces/{ws}/documents")
async def upload(ws: str, file: Annotated[UploadFile, File()], note: Annotated[str, Form()] = ""):
    space = workspace(ws)
    data = await file.read(MAX_BYTES + 1)
    return space.process(file.filename or "upload", data, origin="upload", note=note[:200])


@app.get("/api/workspaces/{ws}/cases")
def list_cases(ws: str):
    return workspace(ws).cases()


@app.get("/api/workspaces/{ws}/cases/{case_id}")
def get_case(ws: str, case_id: str):
    detail = workspace(ws).case(case_id)
    if detail is None:
        raise HTTPException(404, "no such case in this workspace")
    return detail


@app.get("/api/workspaces/{ws}/files/{filename}")
def get_file(ws: str, filename: str):
    found = workspace(ws).document(filename)
    if found is None:
        raise HTTPException(404, "no such document")
    data, content_type = found
    return Response(data, media_type=content_type, headers=FILE_HEADERS)


class DecisionRequest(BaseModel):
    invoiceId: str
    decision: str
    reviewer: str
    note: str = ""


@app.get("/api/workspaces/{ws}/decisions")
def list_decisions(ws: str):
    space = workspace(ws)
    return {"current": space.current(), "log": space.events()}


@app.post("/api/workspaces/{ws}/decisions")
def post_decision(ws: str, body: DecisionRequest):
    return workspace(ws).decide(body.invoiceId, body.decision, body.reviewer, body.note)


@app.get("/api/workspaces/{ws}/decisions.csv")
def decisions_csv(ws: str):
    events = workspace(ws).events()
    buffer = io.StringIO()
    columns = [
        "at",
        "invoice_id",
        "decision",
        "from_state",
        "reviewer",
        "recommended_action",
        "overrules_recommendation",
        "note",
    ]
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows({k: _csv_cell(v) for k, v in event.items()} for event in events)
    return Response(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"content-disposition": f'attachment; filename="countersign-decisions-{ws}.csv"'},
    )
