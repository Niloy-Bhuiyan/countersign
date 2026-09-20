# ADR-006: One guarded transition function, not scattered checks

**Status:** Accepted · **Date:** 2026-09-20

## Context

The promise Countersign makes is that an invoice cannot quietly become payable. That promise
is only as strong as its weakest code path. If each service sets `invoice.state` itself and
checks the preconditions it remembers, then the guarantee is distributed across every caller,
and a new endpoint added in six months is one forgotten `if` away from breaking it.

This is the kind of invariant that is cheap to enforce structurally and nearly impossible to
restore once it has leaked.

## Decision

All state changes go through one function, `countersign.states.transition()`. Services never
assign to `invoice.state`.

The function owns both guards:

- **`cleared` requires the check outcomes**, and every one must be `passed`. An empty run is
  not a pass — a zero-length list means no check ran. An abstention is not a pass either: the
  check declined to judge, which is a reason for a person to look, not a reason to clear.
- **`approved`, `held` and `escalated` require `has_approval=True`**, which the service layer
  sets only from a stored `approvals` row.

The permitted transitions are a table, so what is reachable from where is readable in one
screen rather than inferred from the codebase.

## Consequences

**Good.** The safety property is testable in isolation, with no database and no services. Ten
tests cover it, including one that asserts `cleared` is reachable only from `checked` by
inspecting the transition table itself — so adding a new edge into `cleared` fails the suite
rather than passing silently.

**Costs.** Callers must supply the outcomes and the approval flag, which is slightly more
ceremony than assignment. That ceremony is the point: it makes the guarantee impossible to
forget rather than easy to remember.

## Alternatives considered

**Database constraints and triggers.** Stronger in principle — the guarantee would survive a
direct SQL update. Rejected for now because the logic ("every check passed") spans rows and
would be awkward in a trigger, and because it would only hold on PostgreSQL while the project
also runs on SQLite offline. Worth revisiting when the schema stabilises.

**Preconditions in each service.** Rejected above: it distributes an invariant that must not
be distributed.

**A state machine library.** Rejected as unnecessary weight. The table is twenty lines and
the two guards are domain rules a library would not express any more clearly.
