"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { type Decision, readDecisions, useJson, writeDecision } from "@/components/data";
import { date, money, quantity } from "@/components/format";
import {
  ACTIONS,
  ActionTag,
  CHECKS,
  REASONS,
  STATES,
  StateTag,
  Tag,
  type Tone,
  ruleLabel,
} from "@/components/labels";

type Result = {
  check_code: string;
  outcome: "passed" | "failed" | "abstained";
  rule: string;
  line_no: number | null;
  observed: string | null;
  expected: string | null;
  tolerance: string | null;
  explanation: string;
  evidence: Record<string, string[]>;
};

type CaseDetail = {
  id: string;
  file: string;
  format: string;
  number: string | null;
  vendor: string | null;
  po: string | null;
  issued: string | null;
  currency: string | null;
  total: string | null;
  state: string;
  reason: string | null;
  action: string;
  history: string[];
  extraction: {
    provider: string;
    version: string;
    intake: string;
    sha256: string;
    failures: { field: string; printed: string; reason: string }[];
  };
  invoice: null | {
    vendorAsPrinted: string;
    taxId: string | null;
    due: string | null;
    subtotal: string;
    tax: string;
    total: string;
    lines: {
      no: number;
      sku: string | null;
      description: string;
      uom: string | null;
      quantity: string;
      unitPrice: string;
      lineTotal: string;
      taxRate: string | null;
    }[];
  };
  order: null | {
    number: string;
    orderedAt: string;
    currency: string;
    lines: { no: number; sku: string; description: string; quantity: string; unitPrice: string; taxRate: string }[];
    deliveries: { id: string; number: string; date: string; lines: { poLine: number; received: string }[] }[];
  };
  results: Result[];
  recommendation: null | {
    action: string;
    rationale: { text: string; cites: { table: string; id: string }[] }[];
    dropped_sentences: number;
    escalated_because: string | null;
    agent_version: string;
    steps_used: number;
    tool_calls_used: number;
  };
};

const OUTCOME: Record<Result["outcome"], { label: string; tone: Tone }> = {
  passed: { label: "Passed", tone: "ok" },
  failed: { label: "Failed", tone: "bad" },
  abstained: { label: "Could not judge", tone: "neutral" },
};

function disagrees(action: string, decision: Decision["decision"]): boolean {
  if (action === "CLEAR_FOR_PAYMENT") return decision !== "approved";
  if (action === "ESCALATE_TO_CONTROLLER") return decision !== "escalated";
  if (action === "REVIEW_MANUALLY") return false;
  return decision !== "held";
}

function DecisionPanel({ detail }: { detail: CaseDetail }) {
  const [saved, setSaved] = useState<Decision | null>(null);
  const [pending, setPending] = useState<Decision["decision"] | null>(null);
  const [note, setNote] = useState("");

  useEffect(() => setSaved(readDecisions()[detail.id] ?? null), [detail.id]);

  const needsNote = pending ? disagrees(detail.action, pending) : false;
  const canSave = pending && (!needsNote || note.trim().length >= 10);

  function save() {
    if (!pending || !canSave) return;
    const decision = { decision: pending, note: note.trim(), at: new Date().toISOString() };
    writeDecision(detail.id, decision);
    setSaved(decision);
    setPending(null);
    setNote("");
  }

  return (
    <section className="panel" aria-labelledby="decision-title">
      <div className="panel-head">
        <h2 id="decision-title">Decision</h2>
        {saved && <Tag tone={STATES[saved.decision].tone}>{STATES[saved.decision].label}</Tag>}
      </div>
      <div className="panel-body" style={{ display: "grid", gap: 10 }}>
        {saved ? (
          <>
            <p>
              Recorded {date(saved.at.slice(0, 10))}.{" "}
              {saved.note && <span className="muted">Note: {saved.note}</span>}
            </p>
            <div>
              <button className="btn" onClick={() => (writeDecision(detail.id, null), setSaved(null))}>
                Withdraw decision
              </button>
            </div>
          </>
        ) : (
          <>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                className="btn btn-ok"
                aria-pressed={pending === "approved"}
                onClick={() => setPending("approved")}
              >
                Approve for payment
              </button>
              <button className="btn btn-warn" aria-pressed={pending === "held"} onClick={() => setPending("held")}>
                Hold
              </button>
              <button
                className="btn btn-bad"
                aria-pressed={pending === "escalated"}
                onClick={() => setPending("escalated")}
              >
                Escalate
              </button>
            </div>
            {pending && (
              <div className="field">
                <label htmlFor="note">
                  {needsNote ? "Reason for overruling the recommendation (required)" : "Note (optional)"}
                </label>
                <textarea
                  id="note"
                  className="input"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  aria-invalid={needsNote && note.trim().length < 10}
                  aria-describedby="note-help"
                />
                <span id="note-help" className="small muted">
                  {needsNote
                    ? `This disagrees with "${ACTIONS[detail.action]?.label}". At least 10 characters.`
                    : "Stored with the decision."}
                </span>
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button className="btn btn-primary" disabled={!canSave} onClick={save}>
                    Record decision
                  </button>
                  <button className="btn" onClick={() => setPending(null)}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </>
        )}
        <p className="notice">
          Demo only. This console is a static deployment with no server, so a decision is kept in this
          browser and nowhere else. Nothing is paid, sent or recorded.
        </p>
      </div>
    </section>
  );
}

function Findings({ results }: { results: Result[] }) {
  const order = { failed: 0, abstained: 1, passed: 2 };
  const sorted = [...results].sort((a, b) => order[a.outcome] - order[b.outcome]);
  return (
    <section className="panel" aria-labelledby="findings-title">
      <div className="panel-head">
        <h2 id="findings-title">Checks</h2>
        <span className="small muted">Deterministic. No model produced any of these.</span>
      </div>
      {sorted.map((r, i) => (
        <div className="finding" key={i}>
          <div>
            <div className="small" style={{ fontWeight: 600 }}>
              {CHECKS[r.check_code] ?? r.check_code}
            </div>
            <div style={{ marginTop: 4 }}>
              <Tag tone={OUTCOME[r.outcome].tone}>{OUTCOME[r.outcome].label}</Tag>
            </div>
          </div>
          <div>
            {r.rule && <div className="rule">{ruleLabel(`${r.check_code}/${r.rule}`)}</div>}
            <p>{r.explanation}</p>
            {(r.observed || r.expected || r.tolerance) && (
              <div className="figures">
                {r.observed && (
                  <span>
                    Observed <b>{r.observed}</b>
                  </span>
                )}
                {r.expected && (
                  <span>
                    Expected <b>{r.expected}</b>
                  </span>
                )}
                {r.tolerance && (
                  <span>
                    Tolerance <b>{r.tolerance}</b>
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </section>
  );
}

function Lines({ detail }: { detail: CaseDetail }) {
  const inv = detail.invoice!;
  const order = detail.order;
  const received = (poLine: number) => {
    if (!order) return null;
    let total = 0n;
    let scale = 0;
    for (const d of order.deliveries)
      for (const l of d.lines)
        if (l.poLine === poLine) {
          const [w, f = ""] = l.received.split(".");
          scale = Math.max(scale, f.length);
          total += BigInt(w + f.padEnd(4, "0").slice(0, 4));
        }
    const s = total.toString().padStart(5, "0");
    return `${s.slice(0, -4)}.${s.slice(-4)}`;
  };
  return (
    <section className="panel" aria-labelledby="lines-title">
      <div className="panel-head">
        <h2 id="lines-title">Lines against the order</h2>
        {order && (
          <span className="small muted">
            Order {order.number}, raised {date(order.orderedAt)}, {order.deliveries.length} delivery note(s)
          </span>
        )}
      </div>
      <div className="table-wrap">
        <table className="plain">
          <thead>
            <tr>
              <th>#</th>
              <th>Item</th>
              <th className="num">Billed qty</th>
              <th className="num">Received</th>
              <th className="num">Billed price</th>
              <th className="num">Ordered price</th>
              <th className="num">Line total</th>
            </tr>
          </thead>
          <tbody>
            {inv.lines.map((line) => {
              const poLine = order?.lines.find((l) => l.sku === line.sku);
              const rec = poLine ? received(poLine.no) : null;
              return (
                <tr key={line.no}>
                  <td className="mono small">{line.no}</td>
                  <td className="clip" title={line.description}>
                    <span className="chip">{line.sku ?? "no SKU"}</span>
                    {line.description}
                  </td>
                  <td className="num">
                    {quantity(line.quantity)} <span className="muted small">{line.uom}</span>
                  </td>
                  <td className="num">{rec ? quantity(rec) : "—"}</td>
                  <td className="num">{money(line.unitPrice)}</td>
                  <td className="num">{poLine ? money(poLine.unitPrice) : "—"}</td>
                  <td className="num">{money(line.lineTotal)}</td>
                </tr>
              );
            })}
            <tr>
              <td colSpan={6} className="num muted">
                Subtotal
              </td>
              <td className="num">{money(inv.subtotal)}</td>
            </tr>
            <tr>
              <td colSpan={6} className="num muted">
                Tax
              </td>
              <td className="num">{money(inv.tax)}</td>
            </tr>
            <tr>
              <td colSpan={6} className="num" style={{ fontWeight: 600 }}>
                Total payable
              </td>
              <td className="num" style={{ fontWeight: 600 }}>
                {money(inv.total, detail.currency)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Recommendation({ rec }: { rec: NonNullable<CaseDetail["recommendation"]> }) {
  return (
    <section className="panel" aria-labelledby="rec-title">
      <div className="panel-head">
        <h2 id="rec-title">Recommendation</h2>
        <ActionTag action={rec.action} />
        <span className="small muted" style={{ marginLeft: "auto" }}>
          {rec.agent_version}, {rec.steps_used} steps, {rec.tool_calls_used} read-only tool calls
        </span>
      </div>
      <div className="panel-body">
        <ol className="rationale" style={{ paddingLeft: 18, margin: 0 }}>
          {rec.rationale.map((s, i) => (
            <li key={i}>
              {s.text}
              {s.cites.length > 0 && (
                <div className="cite">
                  cites {s.cites.map((c) => `${c.table}:${c.id}`).join(", ")}
                </div>
              )}
            </li>
          ))}
        </ol>
        {(rec.dropped_sentences > 0 || rec.escalated_because) && (
          <p className="notice" style={{ marginTop: 10 }}>
            {rec.dropped_sentences > 0 &&
              `${rec.dropped_sentences} sentence(s) removed because their citations did not verify. `}
            {rec.escalated_because && `Escalated because ${rec.escalated_because}.`}
          </p>
        )}
        <p className="small muted" style={{ marginTop: 10 }}>
          A draft. It changes nothing until a person records a decision below.
        </p>
      </div>
    </section>
  );
}

function Document({ detail }: { detail: CaseDetail }) {
  const src = `/documents/${detail.file}`;
  const inv = detail.invoice;
  return (
    <section className="panel" aria-labelledby="doc-title">
      <div className="panel-head">
        <h2 id="doc-title">Source document</h2>
        <span className="chip">{detail.format.toUpperCase()}</span>
        <a href={src} className="small" style={{ marginLeft: "auto" }}>
          Open original
        </a>
      </div>
      {detail.format === "pdf" && detail.extraction.intake !== "quarantined_unreadable" && detail.extraction.intake !== "quarantined_encrypted" ? (
        <iframe className="doc-frame" src={src} title={`Source document ${detail.file}`} />
      ) : (
        <div className="panel-body">
          <p className="notice">
            {detail.format !== "pdf"
              ? "Spreadsheet invoices cannot be previewed in the browser. Open the original to compare."
              : "This file cannot be displayed: " + (REASONS[detail.extraction.intake] ?? detail.extraction.intake) + "."}
          </p>
        </div>
      )}
      <div className="panel-body" style={{ borderTop: "1px solid var(--line)" }}>
        <h3 style={{ marginBottom: 10 }}>What was read</h3>
        <dl className="dl">
          <dt>Vendor as printed</dt>
          <dd>{inv?.vendorAsPrinted ?? "—"}</dd>
          <dt>Tax ID</dt>
          <dd className="mono">{inv?.taxId ?? "—"}</dd>
          <dt>Matched vendor</dt>
          <dd>{detail.vendor ?? "—"}</dd>
          <dt>Invoice date</dt>
          <dd className="mono">{date(detail.issued)}</dd>
          <dt>Due</dt>
          <dd className="mono">{date(inv?.due ?? null)}</dd>
          <dt>Reader</dt>
          <dd className="mono small">
            {detail.extraction.provider} / {detail.extraction.version}
          </dd>
          <dt>Content hash</dt>
          <dd className="mono small" style={{ wordBreak: "break-all" }}>
            {detail.extraction.sha256}
          </dd>
        </dl>
        {detail.extraction.failures.length > 0 && (
          <>
            <h3 style={{ margin: "14px 0 8px" }}>Why it was not accepted</h3>
            <table className="plain">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Printed</th>
                  <th>Problem</th>
                </tr>
              </thead>
              <tbody>
                {detail.extraction.failures.map((f, i) => (
                  <tr key={i}>
                    <td className="mono small">{f.field}</td>
                    <td className="mono small">{f.printed || "—"}</td>
                    <td className="small">{f.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </section>
  );
}

function CaseView() {
  const id = useSearchParams().get("id");
  const { data: detail, error } = useJson<CaseDetail>(id ? `/data/case/${id}.json` : null);

  if (!id) return <p>No invoice selected. <Link href="/">Back to the queue</Link>.</p>;
  if (error) return <p>Could not load {id}. <Link href="/">Back to the queue</Link>.</p>;
  if (!detail) return <p className="muted">Loading {id}…</p>;

  return (
    <>
      <div className="page-head">
        <div>
          <Link href="/" className="small">
            &larr; Review queue
          </Link>
          <h1 style={{ marginTop: 6 }}>
            <span className="mono">{detail.number ?? detail.id}</span>
            <span className="muted" style={{ fontWeight: 400 }}>
              {" "}
              {detail.vendor ?? "vendor not identified"}
            </span>
          </h1>
          <div className="timeline" style={{ marginTop: 8 }} aria-label="State history">
            {detail.history.map((s, i) => (
              <span key={i}>{STATES[s]?.label ?? s}</span>
            ))}
            {detail.reason && detail.reason !== "check_findings" && (
              <span className="muted">({REASONS[detail.reason] ?? detail.reason})</span>
            )}
          </div>
        </div>
        <div className="actions" style={{ alignItems: "center" }}>
          <span className="num" style={{ fontSize: 18 }}>
            {money(detail.total, detail.currency)}
          </span>
          <StateTag state={detail.state} />
        </div>
      </div>

      <div className="case-grid">
        <div style={{ display: "grid", gap: 12 }}>
          {detail.recommendation && <Recommendation rec={detail.recommendation} />}
          {detail.results.length > 0 && <Findings results={detail.results} />}
          {detail.invoice && <Lines detail={detail} />}
          <DecisionPanel detail={detail} />
        </div>
        <div style={{ display: "grid", gap: 12 }}>
          <Document detail={detail} />
        </div>
      </div>
    </>
  );
}

export default function CasePage() {
  return (
    <Suspense fallback={<p className="muted">Loading…</p>}>
      <CaseView />
    </Suspense>
  );
}
