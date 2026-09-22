# ADR-004: A committed normalisation table, not fuzzy matching

**Status:** Accepted · **Date:** 2026-09-20

## Context

Duplicate detection compares vendors, and the same supplier arrives spelled several ways
across documents: `Meghna Steel Ltd`, `MEGHNA STEEL LIMITED`, `Meghna  Steel`,
`Meghna Steel Ltd.`. Raw string comparison misses the duplicate.

The standard fix is fuzzy matching — Levenshtein, token-set ratio, or embeddings with a
similarity threshold. It works on the examples above and fails in a way that matters: a
controller asked why two invoices were treated as the same vendor gets "0.91 similarity" as
the answer, and there is no rule to point at, no way to reproduce the judgement by hand, and
no way to fix one bad merge without moving a threshold that silently changes every other case.

## Decision

A committed, ordered table of legal-form suffixes and a deterministic normalisation
procedure in [`countersign/vendors.py`](../../countersign/vendors.py):

1. Case-fold, collapse punctuation and whitespace, drop a leading `the`.
2. Strip legal-form suffixes repeatedly, longest first, until none matches.

Only **legal form** is stripped — `ltd`, `limited`, `corporation`, `& sons` and so on. Trade
words are part of the name and stay: stripping `Industries` would merge `Padma Industries`
into `Padma`, which are different suppliers. A test asserts those two do not collide.

The table is ordered longest-first so `private limited` is removed as a unit before
`limited` can match inside it, and applied in a loop so stacked suffixes (`Trading Co Ltd`)
all come off regardless of order.

## Consequences

**Good.** Two names are the same vendor or they are not, and the rule that made them equal
is readable. Adding a supplier whose name needs a new suffix is a one-line change to a
reviewed table, with a test. A wrong merge is a bug with a location.

**Costs.** It will miss variants nobody anticipated — a transposition, a missing word, a
transliteration difference. Those need a human and a table entry. That is the trade: a
known, visible gap instead of an invisible threshold.

**Guarded by a test.** The corpus writes vendor names in several spellings across documents.
`test_every_name_variant_normalises_to_the_same_key` checks all 40 vendors against 40 draws
each. If a variant stops normalising, duplicate detection silently stops working for that
vendor, so it fails loudly instead.

## Alternatives considered

**Fuzzy string similarity with a threshold.** Rejected above.

**Embeddings over vendor names.** Same objection, with more machinery and less inspectability.

**Match on tax ID only.** Attractive — tax IDs are canonical. Rejected as the sole mechanism
because the tax ID is itself extracted from the document and can be missing or misread; it is
useful as corroboration, not as the key.

## Addendum, after the first evaluation: two companies, one key

The corpus contains *Teesta Industries Ltd* and *Teesta Industries Corporation*, and *Surma
Industries Corporation* and *Surma Industries Limited*: four real-looking, different
companies that differ only in legal form. Stripping legal form is the table's job, so each
pair collapsed to one key, and 22 clean invoices were matched to the wrong vendor.

The fix follows the corroboration this record already anticipated, without loosening the
table. The name narrows the candidates; the tax ID printed on the document decides between
them (`Reference.identify_vendor`). A tax ID that contradicts the name resolves in neither
direction and goes to a person. Tests cover both twins, the ambiguous case with no tax ID,
and the contradiction.
