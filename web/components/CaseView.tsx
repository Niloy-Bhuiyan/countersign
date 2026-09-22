"use client";

import { useState } from "react";
import type { DecisionEvent } from "./api";
import Decision from "./Decision";
import { date, money, quantity } from "./format";
import { ACTIONS, CHECKS, Glyph, REASONS, ruleLabel } from "./labels";
import PriceHistory, { type History } from "./PriceHistory";

export type Result = {
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

export type CaseDetail = {
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
  origin?: string;
  originalFilename?: string;
  note?: string;
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
    lines: { no: number; sku: string; description: string; quantity: string; unitPrice: string; taxRate: string; received: string }[];
    deliveries: { id: string; number: string; date: string }[];
  };
  priceHistory?: History[];
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

const STATE_WORD: Record<string, string> = {
  received: "Received",
  extracted: "Read",
  checked: "Checked",
  cleared: "Cleared every check",
  needs_review: "Needs review",
};

function cmp(a: string | null | undefined, b: string | null | undefined): number {
  if (a == null || b == null) return 0;
  const x = Number(a);
  const y = Number(b);
  return x === y ? 0 : x > y ? 1 : -1;
}

function Lines({ c }: { c: CaseDetail }) {
  const inv = c.invoice!;
  const order = c.order;
  return (
    <div className="sheet-wrap">
      <table className="sheet">
        <thead>
          <tr>
            <th>Item</th>
            <th className="num">Ordered</th>
            <th className="num">Received</th>
            <th className="num">Billed</th>
            <th className="num">Order price</th>
            <th className="num">Billed price</th>
            <th className="num">Line total</th>
          </tr>
        </thead>
        <tbody>
          {inv.lines.map((line) => {
            const po = order?.lines.find((l) => l.sku === line.sku);
            const over = po ? cmp(line.quantity, po.received) > 0 : false;
            const dearer = po ? Number(line.unitPrice) > Number(po.unitPrice) * 1.02 : false;
            return (
              <tr key={line.no}>
                <td>
                  <span className="id">{line.sku ?? "no SKU"}</span>
                  <div className="small soft">{line.description}</div>
                </td>
                <td className="num">{po ? quantity(po.quantity) : "—"}</td>
                <td className="num">{po ? quantity(po.received) : "—"}</td>
                <td className={`num${over ? " off" : ""}`}>
                  {quantity(line.quantity)} <span className="muted small">{line.uom}</span>
                </td>
                <td className="num">{po ? money(po.unitPrice) : "—"}</td>
                <td className={`num${dearer ? " off" : ""}`}>{money(line.unitPrice)}</td>
                <td className="num">{money(line.lineTotal)}</td>
              </tr>
            );
          })}
          <tr className="total">
            <td colSpan={6} className="num muted">Subtotal</td>
            <td className="num">{money(inv.subtotal)}</td>
          </tr>
          <tr className="total">
            <td colSpan={6} className="num muted">VAT</td>
            <td className="num">{money(inv.tax)}</td>
          </tr>
          <tr className="grand">
            <td colSpan={6} className="num">Total payable</td>
            <td className="num">{money(inv.total, c.currency)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export default function CaseView({
  c,
  ws,
  events,
  onDecided,
  documentUrl,
  preset,
}: {
  c: CaseDetail;
  ws: string | null;
  events: DecisionEvent[];
  onDecided: () => void;
  documentUrl: string;
  preset?: "approved" | "held" | "escalated" | null;
}) {
  const [view, setView] = useState<"paper" | "document">("paper");
  const rec = c.recommendation;
  const order = { failed: 0, abstained: 1, passed: 2 } as const;
  const results = [...c.results].sort((a, b) => order[a.outcome] - order[b.outcome]);
  const history = (c.priceHistory ?? []).filter((h) => h.points.length > 0);
  const previewable = c.format === "pdf" && !["quarantined_unreadable", "quarantined_encrypted"].includes(c.extraction.intake);

  return (
    <article>
      <header className="case-head">
        <div>
          <p className="label">
            {c.origin === "lab" ? "Lab invoice" : c.origin === "upload" ? "Uploaded invoice" : "Invoice"} · {c.id}
          </p>
          <h1 className="title id" style={{ fontFamily: "var(--mono)", fontSize: 26 }}>{c.number ?? "Unread document"}</h1>
          <p className="vendor">{c.vendor ?? c.invoice?.vendorAsPrinted ?? "Vendor not identified"}</p>
        </div>
        <div className="total fig">
          {c.total ? money(c.total) : "—"}
          <small>{c.currency}</small>
        </div>
        <div className="facts">
          <span>Order <b className="id">{c.po ?? "—"}</b></span>
          <span>Dated <b>{date(c.issued)}</b></span>
          <span>Due <b>{date(c.invoice?.due ?? null)}</b></span>
          <span className="trail" aria-label="State history">
            {c.history.map((s, i) => <span key={i}>{STATE_WORD[s] ?? s}</span>)}
          </span>
        </div>
      </header>

      <div className="switch paper-switch" role="group" aria-label="View">
        <button aria-pressed={view === "paper"} onClick={() => setView("paper")}>Working paper</button>
        <button aria-pressed={view === "document"} onClick={() => setView("document")}>
          Source document <span className="n">{c.format.toUpperCase()}</span>
        </button>
      </div>

      {view === "document" ? (
        <section className="block">
          {previewable ? (
            <iframe className="doc-frame" src={documentUrl} title={`Source document ${c.file}`} />
          ) : (
            <p className="notice">
              {c.format !== "pdf"
                ? "Spreadsheet invoices cannot be previewed in the browser."
                : `This file cannot be displayed: ${REASONS[c.extraction.intake] ?? c.extraction.intake}.`}{" "}
              <a href={documentUrl}>Download the original</a>.
            </p>
          )}
          <p className="small muted" style={{ marginTop: 8 }}>
            Read by {c.extraction.provider} / {c.extraction.version}. Content hash <span className="id">{c.extraction.sha256.slice(0, 16)}…</span>{" "}
            <a href={documentUrl}>Open the original</a>
          </p>
        </section>
      ) : (
        <>
          {c.reason && c.reason !== "check_findings" && (
            <section className="block">
              <div className="block-head"><h3>Why this is in review</h3></div>
              <p className="verdict red">{REASONS[c.reason] ?? c.reason}</p>
              {c.extraction.failures.length > 0 && (
                <table className="sheet" style={{ marginTop: 12 }}>
                  <thead><tr><th>Field</th><th>As printed</th><th>Problem</th></tr></thead>
                  <tbody>
                    {c.extraction.failures.map((f, i) => (
                      <tr key={i}>
                        <td className="id">{f.field}</td>
                        <td className="id">{f.printed || "—"}</td>
                        <td>{f.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          )}

          {rec && (
            <section className="block">
              <div className="block-head">
                <h3>Recommendation</h3>
                <span className="aside">
                  {rec.agent_version} · {rec.steps_used} steps · {rec.tool_calls_used} read-only tool calls
                </span>
              </div>
              <p className="verdict">{ACTIONS[rec.action]?.verdict ?? rec.action}</p>
              <ol className="rationale">
                {rec.rationale.slice(1).map((s, i) => (
                  <li key={i}>
                    {s.text}
                    {s.cites.length > 0 && <span className="cites">{s.cites.map((x) => `${x.table}:${x.id}`).join("  ")}</span>}
                  </li>
                ))}
              </ol>
              {(rec.dropped_sentences > 0 || rec.escalated_because) && (
                <p className="notice" style={{ marginTop: 10 }}>
                  {rec.dropped_sentences > 0 && `${rec.dropped_sentences} sentence(s) removed because their citations did not verify. `}
                  {rec.escalated_because && `Escalated because ${rec.escalated_because}.`}
                </p>
              )}
            </section>
          )}

          {results.length > 0 && (
            <section className="block">
              <div className="block-head">
                <h3>Checks</h3>
                <span className="aside">Deterministic. No model produced any of these.</span>
              </div>
              <div className="checks">
                {results.map((r, i) => (
                  <div className="check" key={i}>
                    <span className={r.outcome === "failed" ? "red" : r.outcome === "passed" ? "green" : "muted"}
                      aria-label={r.outcome === "abstained" ? "could not judge" : r.outcome}>
                      <Glyph kind={r.outcome} size={18} />
                    </span>
                    <div>
                      <div className="name">{CHECKS[r.check_code] ?? r.check_code}</div>
                      {r.rule && <div className="rule">{ruleLabel(`${r.check_code}/${r.rule}`)}</div>}
                    </div>
                    <div>
                      <p>{r.explanation}</p>
                      {(r.observed || r.expected || r.tolerance) && (
                        <div className="figs">
                          {r.observed && <span>Observed <b className="fig">{r.observed}</b></span>}
                          {r.expected && <span>Expected <b className="fig">{r.expected}</b></span>}
                          {r.tolerance && <span>Tolerance <b className="fig">{r.tolerance}</b></span>}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {c.invoice && (
            <section className="block">
              <div className="block-head">
                <h3>Against the order and deliveries</h3>
                {c.order && (
                  <span className="aside">
                    Order raised {date(c.order.orderedAt)} · {c.order.deliveries.length} delivery note(s)
                  </span>
                )}
              </div>
              <Lines c={c} />
            </section>
          )}

          {history.length > 0 && (
            <section className="block">
              <div className="block-head"><h3>Price against this vendor&rsquo;s history</h3></div>
              <div style={{ display: "grid", gap: 18 }}>
                {history.map((h) => <PriceHistory key={h.lineNo} h={h} />)}
              </div>
            </section>
          )}
        </>
      )}

      {ws && (
        <section className="block">
          <div className="block-head"><h3>Decision</h3></div>
          <Decision ws={ws} invoiceId={c.id} action={c.action} events={events} onRecorded={onDecided} preset={preset} />
        </section>
      )}
    </article>
  );
}
