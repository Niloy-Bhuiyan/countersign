"""The agent's limits: what it can call, how far it can go, what it can claim."""

import inspect
from dataclasses import dataclass, field
from pathlib import Path

import countersign
from countersign.agent import graph
from countersign.agent.tools import READ_ONLY_TOOLS, Toolbox
from countersign.checks.base import ABSTAINED, FAILED, PASSED, CheckResult
from countersign.reference import Reference
from countersign.settings import settings


@dataclass
class FakeCase:
    document_id: str = "INV-1"
    vendor_id: str = "VEN-1"
    po_id: str | None = None
    results: list = field(default_factory=list)
    invoice: object = None


def toolbox(*cases):
    return Toolbox(
        reference=Reference(vendors={}, orders={}, deliveries_by_po={}),
        cases={case.document_id: case for case in cases},
    )


def test_the_registry_holds_exactly_the_six_read_tools():
    assert set(toolbox().registry()) == READ_ONLY_TOOLS
    assert len(READ_ONLY_TOOLS) == 6


def test_no_tool_name_suggests_writing():
    verbs = ("set", "update", "write", "delete", "approve", "pay", "send", "create", "move")
    for name in READ_ONLY_TOOLS:
        assert not name.startswith(verbs), name


def test_the_agent_module_never_calls_a_state_transition():
    assert "transition(" not in inspect.getsource(graph)


def test_a_case_where_everything_passed_is_recommended_for_clearing():
    case = FakeCase(results=[CheckResult("TAX_ARITHMETIC", PASSED, "ok")])
    assert graph.recommend(case, toolbox(case))["action"] == graph.CLEAR


def test_the_most_serious_finding_decides_the_action():
    case = FakeCase(
        results=[
            CheckResult("TAX_ARITHMETIC", FAILED, "tax off", rule="tax_total"),
            CheckResult("DUPLICATE_INVOICE", FAILED, "seen before", rule="same_number"),
        ]
    )
    out = graph.recommend(case, toolbox(case))
    assert out["action"] == graph.ESCALATE
    assert {"tax off", "seen before"} <= {s["text"] for s in out["rationale"]}


def test_only_abstentions_means_a_person_must_look():
    case = FakeCase(results=[CheckResult("PRICE_VARIANCE", ABSTAINED, "thin", rule="x")])
    assert graph.recommend(case, toolbox(case))["action"] == graph.MANUAL


def test_a_sentence_citing_a_record_that_does_not_exist_is_removed():
    case = FakeCase(
        results=[
            CheckResult(
                "TAX_ARITHMETIC",
                FAILED,
                "cites a ghost",
                rule="tax_total",
                evidence={"purchase_orders": ["PO-DOES-NOT-EXIST"]},
            )
        ]
    )
    out = graph.recommend(case, toolbox(case))
    assert "cites a ghost" not in {s["text"] for s in out["rationale"]}
    assert out["dropped_sentences"] == 1


def test_an_unverifiable_action_escalates_instead_of_emitting():
    case = FakeCase(po_id="PO-GONE", results=[CheckResult("TAX_ARITHMETIC", PASSED, "ok")])
    out = graph.recommend(case, toolbox(case))
    assert out["action"] == graph.ESCALATE
    assert out["escalated_because"]


def test_the_step_cap_ends_in_escalation(monkeypatch):
    monkeypatch.setattr(settings, "agent_max_steps", 2)
    case = FakeCase(results=[CheckResult("TAX_ARITHMETIC", PASSED, "ok")])
    out = graph.recommend(case, toolbox(case))
    assert out["action"] == graph.ESCALATE
    assert "step cap" in out["escalated_because"]


def test_the_tool_call_cap_ends_in_escalation(monkeypatch):
    monkeypatch.setattr(settings, "agent_max_tool_calls", 0)
    case = FakeCase(results=[CheckResult("TAX_ARITHMETIC", PASSED, "ok")])
    assert "tool-call cap" in graph.recommend(case, toolbox(case))["escalated_because"]


def test_nothing_in_the_pipeline_reads_the_ground_truth():
    """The evaluation may read it. Nothing that makes a decision may."""
    package = Path(countersign.__file__).parent
    for source in package.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "ground_truth" not in text, source
        assert "invoices.json" not in text, source
