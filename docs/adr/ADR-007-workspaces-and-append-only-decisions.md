# ADR-007: Isolated workspaces over append-only decision storage

**Status:** Accepted · **Date:** 2026-09-22

## Context

The first console kept a reviewer's decisions in the browser. That was honest — the page
said so — but it meant the most important thing the system does, recording who decided
what and why, was not real. Making it real raised three questions.

1. **Where does the rule live?** If the browser enforces "a reason is required to overrule
   the recommendation", anyone with developer tools can skip it.
2. **Who shares state?** The console is public. If every visitor writes to one shared
   ledger, the first visitor to approve everything decides the demo for everyone after.
3. **What does the audit trail look like after a mistake?** An approval that is later
   corrected must not disappear.

## Decision

- **Decisions are validated on the server** by `countersign.decisions.record`, which runs
  the same `states.transition` guard as the pipeline and the note and signature rules. The
  browser explains the rules in advance; it cannot relax them.
- **Every reviewer gets a workspace**: an unguessable id created on first visit, carried in
  the URL so it opens on another device or for a colleague. The corpus is shared and
  read-only; uploads, lab orders and decisions live under the workspace's own prefix.
- **Decisions are append-only.** Each decision, and each withdrawal, is a new object in a
  private Vercel Blob store. None is overwritten. The current state is the latest event; the
  audit trail is all of them, exportable as CSV.
- **Private store, proxied reads.** A blob URL alone returns 403. Every read goes through
  the API with the store token, which never reaches the browser.

## Consequences

**Good.** The audit trail survives mistakes, because correcting one is itself recorded. The
rules cannot be bypassed from the client. Strangers cannot overwrite each other's work.
An uploaded document is judged by `batch.check_case`, the function the evaluation measured,
against a ledger snapshot that already holds every corpus invoice — so re-uploading a corpus
invoice is caught as a duplicate.

**Costs.** A workspace is identified by possession of its id, not by an account. Anyone
with the link can act in it. That is appropriate for a public demonstration and wrong for
production, where the reviewer's identity would come from single sign-on and `decided_by`
would not be typed. Listing a workspace's decisions costs one read per decision; fine at
demonstration scale, and the reason a real deployment would use the PostgreSQL schema in
`countersign/db` instead.

## Alternatives considered

**A database (Postgres).** The schema and migrations exist and are the right production
answer. Rejected for the deployed demo because every managed option available required
accepting a third party's terms on the owner's behalf; Blob is first-party to the host.

**One shared public ledger.** Rejected: one visitor's clicks would become everyone's demo.

**Keep decisions in the browser.** Rejected: that is the thing being replaced.
