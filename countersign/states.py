"""The invoice state machine and the guards that protect it.

The whole point of Countersign is that an invoice cannot quietly become payable.
Two rules enforce that, and both live here rather than being spread across the
services that call them:

1. An invoice reaches ``cleared`` only when every check passed. A check that
   failed or abstained sends it to ``needs_review``.
2. An invoice reaches ``approved``, ``held`` or ``escalated`` only with a human
   decision attached.

``transition`` is the only way to change an invoice's state. Services do not
assign to ``invoice.state`` directly.
"""

from __future__ import annotations

RECEIVED = "received"
EXTRACTED = "extracted"
CHECKED = "checked"
CLEARED = "cleared"
NEEDS_REVIEW = "needs_review"
APPROVED = "approved"
HELD = "held"
ESCALATED = "escalated"

#: States that mean a person has decided.
DECIDED = frozenset({APPROVED, HELD, ESCALATED})

#: States reachable only from a completed check run.
_AFTER_CHECKS = frozenset({CLEARED, NEEDS_REVIEW})

TRANSITIONS: dict[str, frozenset[str]] = {
    RECEIVED: frozenset({EXTRACTED, NEEDS_REVIEW}),
    EXTRACTED: frozenset({CHECKED, NEEDS_REVIEW}),
    CHECKED: _AFTER_CHECKS,
    CLEARED: frozenset({APPROVED, HELD, ESCALATED}),
    NEEDS_REVIEW: frozenset({APPROVED, HELD, ESCALATED}),
    APPROVED: frozenset(),
    HELD: frozenset({NEEDS_REVIEW}),
    ESCALATED: frozenset({NEEDS_REVIEW}),
}


class TransitionError(Exception):
    """Raised when a state change is not permitted."""


def all_checks_passed(outcomes: list[str]) -> bool:
    """True only when at least one check ran and every one of them passed.

    An empty run is not a pass. An abstention is not a pass either: the check
    declined to judge, which is a reason for a person to look, not a reason to
    clear.
    """
    return bool(outcomes) and all(outcome == "passed" for outcome in outcomes)


def transition(
    current: str,
    target: str,
    *,
    check_outcomes: list[str] | None = None,
    has_approval: bool = False,
) -> str:
    """Return ``target`` if the move is permitted, else raise ``TransitionError``."""
    if current not in TRANSITIONS:
        raise TransitionError(f"unknown state {current!r}")
    if target not in TRANSITIONS:
        raise TransitionError(f"unknown state {target!r}")
    if target not in TRANSITIONS[current]:
        raise TransitionError(f"{current} cannot move to {target}")

    if target == CLEARED:
        if check_outcomes is None:
            raise TransitionError("clearing requires the check outcomes")
        if not all_checks_passed(check_outcomes):
            raise TransitionError(
                "cannot clear: "
                f"{sum(1 for o in check_outcomes if o != 'passed')} of "
                f"{len(check_outcomes)} checks did not pass"
            )

    if target in DECIDED and not has_approval:
        raise TransitionError(f"cannot move to {target} without a human decision")

    return target
