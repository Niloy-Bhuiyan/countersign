"""The live API, end to end, against an in-memory store.

The lab renders a real PDF and the API reads it back, so each scenario here is a
full pass: compose, render, extract, check, recommend, persist. Each tamper must
be caught by the check it targets, and the clean scenario must clear.
"""

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SNAPSHOT = Path("api/_data")
pytestmark = pytest.mark.skipif(
    not (SNAPSHOT / "ledger.json").exists(), reason="run python -m scripts.export_web first"
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    module = importlib.import_module("api.index")
    module.store.cache_clear()
    return TestClient(module.app)


WS = "testspace01"


def failed(detail) -> set[str]:
    return {f"{r['check_code']}/{r['rule']}" for r in detail["results"] if r["outcome"] == "failed"}


def lab(client, tamper, vendor="VEN-004", ws=WS):
    response = client.post(f"/api/workspaces/{ws}/lab", json={"vendorId": vendor, "tamper": tamper})
    assert response.status_code == 200, response.text
    return response.json()


def test_health_reports_memory_storage_without_a_token(client):
    body = client.get("/api/health").json()
    assert body["ok"] and body["storage"] == "memory"
    assert body["corpus_cases"] == 500


def test_a_clean_lab_invoice_clears(client):
    detail = lab(client, "clean")
    assert detail["state"] == "cleared", detail["results"]
    assert detail["extraction"]["intake"] == "readable"
    assert detail["action"] == "CLEAR_FOR_PAYMENT"


@pytest.mark.parametrize(
    ("tamper", "rule"),
    [
        ("overbill", "THREE_WAY_MATCH/quantity_over_received"),
        ("price_above_order", "THREE_WAY_MATCH/price_above_order"),
        ("tax_error", "TAX_ARITHMETIC/tax_total"),
        ("currency", "THREE_WAY_MATCH/currency"),
        ("inflated_order", "PRICE_VARIANCE/above_history"),
    ],
)
def test_each_tamper_is_caught_by_the_check_it_targets(client, tamper, rule):
    detail = lab(client, tamper, ws=f"tamper{tamper.replace('_', '')[:20]}")
    assert rule in failed(detail)
    assert detail["state"] == "needs_review"


def test_an_inflated_order_passes_the_match_and_only_variance_catches_it(client):
    detail = lab(client, "inflated_order", ws="inflatedonly")
    assert not any(key.startswith("THREE_WAY_MATCH") for key in failed(detail))


def test_resubmitting_the_last_lab_invoice_is_a_duplicate(client):
    lab(client, "clean", ws="resubmits")
    again = lab(client, "resubmit", ws="resubmits")
    assert {"DUPLICATE_INVOICE/same_number", "DUPLICATE_INVOICE/same_bytes"} <= failed(again)


def test_uploading_a_corpus_invoice_again_is_caught_as_a_duplicate(client):
    path = Path("data/corpus/documents/INV-0240.pdf")
    if not path.exists():
        pytest.skip("corpus documents not generated")
    response = client.post(
        f"/api/workspaces/{WS}/documents",
        files={"file": ("INV-0240.pdf", path.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    assert "DUPLICATE_INVOICE/same_bytes" in failed(response.json())


def test_an_unsupported_file_is_refused(client):
    response = client.post(
        f"/api/workspaces/{WS}/documents", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400


def test_the_source_document_is_served_back(client):
    detail = lab(client, "clean", ws="documents1")
    response = client.get(f"/api/workspaces/documents1/files/{detail['file']}")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert client.get("/api/workspaces/documents1/files/..%2Fsecret.pdf").status_code == 404


def test_workspaces_are_isolated(client):
    lab(client, "clean", ws="isolatedaa")
    assert client.get("/api/workspaces/isolatedbb/cases").json() == []
    assert len(client.get("/api/workspaces/isolatedaa/cases").json()) == 1


def test_a_malformed_workspace_id_is_refused(client):
    assert client.get("/api/workspaces/BAD!/cases").status_code in (400, 404)


# ---- decisions ------------------------------------------------------------------


def decide(client, ws, invoice, decision, reviewer="A. Reviewer", note=""):
    return client.post(
        f"/api/workspaces/{ws}/decisions",
        json={"invoiceId": invoice, "decision": decision, "reviewer": reviewer, "note": note},
    )


def test_a_decision_is_recorded_and_becomes_current(client):
    detail = lab(client, "clean", ws="decisions1")
    response = decide(client, "decisions1", detail["id"], "approved")
    assert response.status_code == 200, response.text
    body = client.get("/api/workspaces/decisions1/decisions").json()
    assert body["current"][detail["id"]]["decision"] == "approved"
    assert len(body["log"]) == 1


def test_an_invoice_cannot_be_decided_twice_without_a_withdrawal(client):
    detail = lab(client, "clean", ws="decisions2")
    assert decide(client, "decisions2", detail["id"], "approved").status_code == 200
    assert (
        decide(
            client, "decisions2", detail["id"], "held", note="changed my mind entirely"
        ).status_code
        == 422
    )
    assert (
        decide(
            client, "decisions2", detail["id"], "withdrawn", note="approved the wrong one"
        ).status_code
        == 200
    )
    assert (
        decide(
            client, "decisions2", detail["id"], "held", note="holding pending a call"
        ).status_code
        == 200
    )
    log = client.get("/api/workspaces/decisions2/decisions").json()["log"]
    assert [e["decision"] for e in log] == ["approved", "withdrawn", "held"]


def test_overruling_the_recommendation_needs_a_reason(client):
    detail = lab(client, "overbill", ws="decisions3")
    assert detail["action"] != "CLEAR_FOR_PAYMENT"
    assert decide(client, "decisions3", detail["id"], "approved").status_code == 422
    ok = decide(
        client, "decisions3", detail["id"], "approved", note="vendor sent the missing delivery note"
    )
    assert ok.status_code == 200
    assert ok.json()["overrules_recommendation"] is True


def test_an_unsigned_decision_is_refused(client):
    detail = lab(client, "clean", ws="decisions4")
    assert decide(client, "decisions4", detail["id"], "approved", reviewer=" ").status_code == 422


def test_corpus_invoices_can_be_decided_in_a_workspace(client):
    assert decide(client, "decisions5", "INV-0240", "held").status_code == 200


def test_an_unknown_invoice_cannot_be_decided(client):
    assert decide(client, "decisions6", "INV-9999", "approved").status_code == 400


def test_the_audit_trail_exports_as_csv(client):
    decide(client, "decisions7", "INV-0240", "held")
    response = client.get("/api/workspaces/decisions7/decisions.csv")
    assert response.status_code == 200
    assert response.text.splitlines()[0].startswith("at,invoice_id,decision")
    assert "INV-0240" in response.text
