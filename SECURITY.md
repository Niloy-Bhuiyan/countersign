# Security

## Scope

Countersign is a portfolio project running on a synthetic corpus. It holds no real supplier
data, no real company data and no payment credentials, and it cannot move money. The threat
model in [docs/security.md](docs/security.md) describes what it would need before it could.

## Reporting

Open a GitHub issue, or email niloybhuiyann@gmail.com. There is no bounty and no SLA.

## What is deliberately not here

- **No payment capability.** There is no code path that pays, transfers or instructs a
  payment, and no credentials that would allow one.
- **No write tool for the agent.** The tool registry contains only read operations, asserted
  by a test.
- **No secrets in the repository.** `.env` is ignored; `.env.example` carries no values. The
  default configuration needs no keys at all.

## Dependencies

Dependabot raises weekly Python and monthly Actions updates.
