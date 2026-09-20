"""The safety invariants. If these pass, no invoice can become payable on its own."""

import pytest

from countersign import states
from countersign.states import TransitionError, transition


def test_happy_path_to_cleared():
    assert transition(states.RECEIVED, states.EXTRACTED) == states.EXTRACTED
    assert transition(states.EXTRACTED, states.CHECKED) == states.CHECKED
    assert (
        transition(states.CHECKED, states.CLEARED, check_outcomes=["passed", "passed"])
        == states.CLEARED
    )


def test_a_failed_check_blocks_clearing():
    with pytest.raises(TransitionError, match="1 of 3 checks did not pass"):
        transition(states.CHECKED, states.CLEARED, check_outcomes=["passed", "failed", "passed"])


def test_an_abstention_blocks_clearing():
    # Abstaining is the check declining to judge. That is a reason to look, not
    # a reason to clear.
    with pytest.raises(TransitionError):
        transition(states.CHECKED, states.CLEARED, check_outcomes=["passed", "abstained"])


def test_an_empty_check_run_blocks_clearing():
    with pytest.raises(TransitionError):
        transition(states.CHECKED, states.CLEARED, check_outcomes=[])


def test_clearing_without_supplying_outcomes_is_refused():
    with pytest.raises(TransitionError, match="requires the check outcomes"):
        transition(states.CHECKED, states.CLEARED)


@pytest.mark.parametrize("decision", [states.APPROVED, states.HELD, states.ESCALATED])
def test_no_decision_state_is_reachable_without_a_human(decision):
    with pytest.raises(TransitionError, match="without a human decision"):
        transition(states.NEEDS_REVIEW, decision)
    assert transition(states.NEEDS_REVIEW, decision, has_approval=True) == decision


def test_extraction_cannot_skip_the_checks():
    with pytest.raises(TransitionError):
        transition(states.EXTRACTED, states.CLEARED, check_outcomes=["passed"])


def test_received_cannot_jump_straight_to_approved():
    with pytest.raises(TransitionError):
        transition(states.RECEIVED, states.APPROVED, has_approval=True)


def test_approved_is_terminal():
    assert states.TRANSITIONS[states.APPROVED] == frozenset()


def test_no_state_reaches_cleared_except_checked():
    reaching_cleared = {
        source for source, targets in states.TRANSITIONS.items() if states.CLEARED in targets
    }
    assert reaching_cleared == {states.CHECKED}
