"""The rules a reviewer's decision has to satisfy before it is recorded.

These run on the server, not in the browser. A decision that breaks one is
refused with a reason, and nothing is written.

1. The decision is one of approved, held, escalated, or a withdrawal of the last.
2. The state machine permits it (``states.transition`` with the approval that this
   decision is). A case that is not in the review queue or cleared cannot be
   decided again until the earlier decision is withdrawn.
3. A reviewer is named. An approval nobody signed is not an approval.
4. Disagreeing with the recommendation needs a written reason of at least ten
   characters, so overruling the system always leaves an explanation behind.
"""

from __future__ import annotations

from datetime import UTC, datetime

from countersign import states

DECISIONS = (states.APPROVED, states.HELD, states.ESCALATED)
WITHDRAWN = "withdrawn"
MIN_NOTE = 10
MAX_NOTE = 1000


class DecisionError(ValueError):
    pass


def disagrees(action: str, decision: str) -> bool:
    if action == "CLEAR_FOR_PAYMENT":
        return decision != states.APPROVED
    if action == "ESCALATE_TO_CONTROLLER":
        return decision != states.ESCALATED
    if action in ("HOLD_REQUEST_CREDIT_NOTE", "HOLD_REQUEST_DELIVERY_PROOF"):
        return decision != states.HELD
    return False


def current_state(system_state: str, events: list[dict]) -> str:
    """The invoice's state after the recorded events, oldest first."""
    state = system_state
    for event in events:
        state = system_state if event["decision"] == WITHDRAWN else event["decision"]
    return state


def record(
    *,
    invoice_id: str,
    system_state: str,
    recommended_action: str,
    events: list[dict],
    decision: str,
    reviewer: str,
    note: str,
    now: datetime | None = None,
) -> dict:
    reviewer = " ".join(reviewer.split())
    note = note.strip()
    state = current_state(system_state, events)

    if len(reviewer) < 2 or len(reviewer) > 80:
        raise DecisionError("name the reviewer recording this decision")
    if len(note) > MAX_NOTE:
        raise DecisionError(f"keep the note under {MAX_NOTE} characters")

    if decision == WITHDRAWN:
        if state not in DECISIONS:
            raise DecisionError("there is no decision to withdraw")
        if len(note) < MIN_NOTE:
            raise DecisionError(f"say why the decision is withdrawn ({MIN_NOTE}+ characters)")
    elif decision in DECISIONS:
        if state in DECISIONS:
            raise DecisionError(f"already {state}; withdraw that decision first")
        try:
            states.transition(state, decision, has_approval=True)
        except states.TransitionError as exc:
            raise DecisionError(str(exc)) from exc
        if disagrees(recommended_action, decision) and len(note) < MIN_NOTE:
            raise DecisionError(
                f"this overrules the recommendation; give a reason ({MIN_NOTE}+ characters)"
            )
    else:
        raise DecisionError(f"unknown decision {decision!r}")

    return {
        "invoice_id": invoice_id,
        "decision": decision,
        "from_state": state,
        "reviewer": reviewer,
        "note": note,
        "recommended_action": recommended_action,
        "overrules_recommendation": decision in DECISIONS
        and disagrees(recommended_action, decision),
        "at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
    }
