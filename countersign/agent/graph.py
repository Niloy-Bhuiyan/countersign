"""The recommendation agent: a bounded graph over the check results.

    load_context -> review_checks -> gather_evidence (loop, bounded)
                 -> draft_recommendation -> verify_citations -> emit | escalate

It reasons about findings; it never produces one. It cannot recompute or overturn
a check, it holds only read tools (see ``tools``), and what it emits is a draft
that has no effect until a person records an approval.

Two hard caps, both configured and both tested: steps through the graph, and tool
calls. Exceeding either ends the run in ``escalate``, never in a recommendation.

Every sentence of the rationale carries citations to records. ``verify_citations``
removes any sentence whose cited record does not exist; if the opening sentence —
the one that carries the action — cannot be verified, the run escalates rather
than emitting a recommendation it cannot support.

In this release the drafting node is a deterministic policy. The graph is built so
that node can be a language model call; the citation check is what would stop a
model from asserting something the records do not say.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from countersign.agent.tools import Toolbox
from countersign.checks.base import ABSTAINED, FAILED
from countersign.settings import settings

VERSION = "policy-v1"

CLEAR = "CLEAR_FOR_PAYMENT"
CREDIT_NOTE = "HOLD_REQUEST_CREDIT_NOTE"
DELIVERY_PROOF = "HOLD_REQUEST_DELIVERY_PROOF"
ESCALATE = "ESCALATE_TO_CONTROLLER"
MANUAL = "REVIEW_MANUALLY"

#: Rule -> action, most serious first. The first failed rule found in this order
#: decides the action; the others are still listed in the rationale.
RULE_ACTIONS: tuple[tuple[str, str], ...] = (
    ("same_bytes", ESCALATE),
    ("same_number", ESCALATE),
    ("same_order_same_amount", ESCALATE),
    ("po_not_found", ESCALATE),
    ("po_other_vendor", ESCALATE),
    ("currency", ESCALATE),
    ("above_history", ESCALATE),
    ("line_unmatched", ESCALATE),
    ("no_delivery", DELIVERY_PROOF),
    ("quantity_over_received", DELIVERY_PROOF),
    ("price_above_order", CREDIT_NOTE),
    ("tax_total", CREDIT_NOTE),
)


class LimitExceeded(Exception):
    pass


@dataclass
class Sentence:
    text: str
    cites: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Run:
    case: object
    toolbox: Toolbox
    steps: int = 0
    tool_calls: int = 0
    failed: list = field(default_factory=list)
    abstained: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    action: str | None = None
    sentences: list[Sentence] = field(default_factory=list)
    dropped: list[Sentence] = field(default_factory=list)
    escalated_because: str | None = None

    def step(self) -> None:
        self.steps += 1
        if self.steps > settings.agent_max_steps:
            raise LimitExceeded(f"step cap of {settings.agent_max_steps} reached")

    def call(self, name: str, *args):
        self.tool_calls += 1
        if self.tool_calls > settings.agent_max_tool_calls:
            raise LimitExceeded(f"tool-call cap of {settings.agent_max_tool_calls} reached")
        return self.toolbox.registry()[name](*args)


def _load_context(run: Run) -> None:
    run.step()
    run.call("get_check_results", run.case.document_id)


def _review_checks(run: Run) -> None:
    run.step()
    run.failed = [r for r in run.case.results if r.outcome == FAILED]
    run.abstained = [r for r in run.case.results if r.outcome == ABSTAINED]


def _gather_evidence(run: Run) -> None:
    run.step()
    po_id = run.case.po_id
    if po_id:
        run.evidence["order"] = run.call("get_purchase_order", po_id)
        run.evidence["deliveries"] = run.call("get_delivery_records", po_id)
    for result in run.failed:
        run.step()
        run.evidence.setdefault("precedents", {})[result.rule] = run.call(
            "find_similar_past_exceptions", result.rule, run.case.vendor_id
        )


def _draft(run: Run) -> None:
    run.step()
    order_cite = [("purchase_orders", run.case.po_id)] if run.case.po_id else []

    if not run.failed and not run.abstained:
        run.action = CLEAR
        run.sentences.append(
            Sentence(
                "Every check passed: price and quantity agree with the order and deliveries, "
                "no earlier invoice matches, and the tax recomputes exactly.",
                order_cite,
            )
        )
        return

    rules = {result.rule for result in run.failed}
    run.action = next((action for rule, action in RULE_ACTIONS if rule in rules), MANUAL)
    if run.failed:
        lead = {
            ESCALATE: "Escalate: the findings below point at the paperwork, not only the amount.",
            DELIVERY_PROOF: "Hold and ask the vendor for proof of delivery.",
            CREDIT_NOTE: "Hold and ask the vendor for a credit note for the difference.",
        }.get(run.action, "Review manually.")
        run.sentences.append(Sentence(lead, order_cite))
    else:
        run.sentences.append(
            Sentence(
                "Review manually: nothing failed, but at least one check could not judge this "
                "invoice, so the system cannot clear it.",
                order_cite,
            )
        )

    for result in run.failed + run.abstained:
        cites = [(table, ref) for table, refs in result.evidence.items() for ref in refs]
        run.sentences.append(Sentence(result.explanation, cites))

    for rule, precedents in run.evidence.get("precedents", {}).items():
        earlier = [p for p in precedents if p != run.case.document_id]
        if earlier:
            run.sentences.append(
                Sentence(
                    f"This vendor has {len(earlier)} earlier invoice(s) with the same finding "
                    f"({rule}).",
                    [("documents", ref) for ref in earlier],
                )
            )


def _exists(run: Run, table: str, ref: str) -> bool:
    if table == "purchase_orders":
        return ref in run.toolbox.reference.orders
    if table == "deliveries":
        return any(
            d.id == ref for ds in run.toolbox.reference.deliveries_by_po.values() for d in ds
        )
    if table == "documents":
        return ref in run.toolbox.cases
    return False


def _verify_citations(run: Run) -> None:
    run.step()
    kept = []
    for sentence in run.sentences:
        if all(_exists(run, table, ref) for table, ref in sentence.cites):
            kept.append(sentence)
        else:
            run.dropped.append(sentence)
    if run.sentences and run.sentences[0] in run.dropped:
        run.escalated_because = (
            "the sentence carrying the action cites a record that does not exist"
        )
        run.action = ESCALATE
    run.sentences = kept


def recommend(case, toolbox: Toolbox) -> dict:
    run = Run(case=case, toolbox=toolbox)
    try:
        for node in (_load_context, _review_checks, _gather_evidence, _draft, _verify_citations):
            node(run)
    except LimitExceeded as exc:
        run.action = ESCALATE
        run.escalated_because = str(exc)
        run.sentences = [Sentence(f"Escalated: the agent stopped because the {exc}.")]

    return {
        "action": run.action,
        "rationale": [
            {"text": s.text, "cites": [{"table": t, "id": r} for t, r in s.cites]}
            for s in run.sentences
        ],
        "dropped_sentences": len(run.dropped),
        "escalated_because": run.escalated_because,
        "agent_version": VERSION,
        "steps_used": run.steps,
        "tool_calls_used": run.tool_calls,
    }
