# ADR-002: Exact decimal money, floats refused at the boundary

**Status:** Accepted · **Date:** 2026-09-20

## Context

Countersign's tax check recomputes line tax, subtotal, tax total and grand total and
compares them against what the invoice printed. The comparison is an equality test on money.

In binary floating point, `0.1 + 0.1 + ... ` seven times is `0.7000000000000001`. Python's
`round(2.675, 2)` is `2.67`, because the nearest double to 2.675 is slightly below it. Either
would make the tax check fail on a correct invoice — and, with a tolerance added to paper
over it, pass on an incorrect one.

The trap is that it mostly works. Three lines of `0.1` drift; thirty do not. A bug that
appears on some invoices and not others is one nobody finds from the symptom.

## Decision

`Decimal` end to end, with floats rejected rather than converted.

- `countersign.money.to_decimal` raises `MoneyError` on a `float`. It does not coerce:
  `Decimal(0.1)` is not `0.1`, and accepting one puts an inexact value where nothing
  downstream can identify it.
- Rounding policy: two places, `ROUND_HALF_UP`, applied at every step. Half-up is what the
  invoices themselves use; banker's rounding would disagree with the supplier's arithmetic
  on exact halves.
- `line_total` rounds once at the end, not per factor.
- The database column type refuses a float bind parameter, and returns `Decimal` on SQLite
  too — otherwise the guarantee would hold only on PostgreSQL.

## Consequences

**Good.** The tax check is an equality test with no tolerance, so it detects a one-cent
error rather than hiding it. The failure mode is a loud exception at the boundary instead of
a wrong number in the middle.

**Costs.** Callers must pass `str`, `int` or `Decimal`. Anything reading JSON has to keep
amounts as strings — the corpus serialises them that way for exactly this reason. Arithmetic
is slower, which is irrelevant at this volume.

## Alternatives considered

**Float with an epsilon tolerance.** Rejected: it converts an exact check into an approximate
one, and the epsilon has to exceed the drift, which means it also exceeds real one-cent errors.

**Integer minor units (paisa).** Genuinely viable and used widely. Rejected because tax rates
are percentages that produce fractional minor units, so rounding decisions reappear anyway,
and `Decimal` expresses the rounding policy explicitly rather than burying it in integer
division.
