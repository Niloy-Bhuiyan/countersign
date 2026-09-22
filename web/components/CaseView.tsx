"use client";

import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import type { DecisionEvent } from "./api";
import Decision from "./Decision";
import {
  CHECK_ORDER,
  CHECKS,
  findingSentence,
  NEXT_STEP,
  passSentence,
  REASONS,
  type Result,
  statusOf,
} from "./explain";
import { date, money, quantity } from "./format";
import PriceHistory, { type History } from "./PriceHistory";
import { Pill, StatusPill, Tip } from "./ui";

export type { Result };

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
  failed: string[];
  abstained: string[];
  history: string[];
  origin?: string;
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

function Lines({ c }: { c: CaseDetail }) {
  const inv = c.invoice!;
  const order = c.order;
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3>Invoice vs. purchase order</h3>
          <p className="card-sub">
            {order ? `${order.number} · ${date(order.orderedAt)} · ${order.deliveries.length} delivered` : "No purchase order found"}
          </p>
        </div>
      </div>
      <div className="table-wrap">
        <table className="t">
          <thead>
            <tr>
              <th>Item</th>
              <th className="r">Ordered</th>
              <th className="r">Delivered</th>
              <th className="r">Billed</th>
              <th className="r">Agreed price</th>
              <th className="r">Price charged</th>
              <th className="r">Line total</th>
            </tr>
          </thead>
          <tbody>
            {inv.lines.map((line) => {
              const po = order?.lines.find((l) => l.sku === line.sku);
              const over = po ? Number(line.quantity) > Number(po.received) : false;
              const dearer = po ? Number(line.unitPrice) > Number(po.unitPrice) * 1.02 : false;
              return (
                <tr key={line.no}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{line.description}</div>
                    <div className="xs muted mono">{line.sku ?? "no item code"}</div>
                  </td>
                  <td className="r">{po ? quantity(po.quantity) : "—"}</td>
                  <td className="r">{po ? quantity(po.received) : "—"}</td>
                  <td className={`r${over ? " flag" : ""}`}>{quantity(line.quantity)} <span className="xs muted">{line.uom}</span></td>
                  <td className="r">{po ? money(po.unitPrice) : "—"}</td>
                  <td className={`r${dearer ? " flag" : ""}`}>{money(line.unitPrice)}</td>
                  <td className="r">{money(line.lineTotal)}</td>
                </tr>
              );
            })}
            <tr><td colSpan={6} className="r muted">Subtotal</td><td className="r">{money(inv.subtotal)}</td></tr>
            <tr><td colSpan={6} className="r muted">VAT</td><td className="r">{money(inv.tax)}</td></tr>
            <tr className="total"><td colSpan={6} className="r">Total</td><td className="r">{c.currency} {money(inv.total)}</td></tr>
          </tbody>
        </table>
      </div>
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
  const [showDoc, setShowDoc] = useState(false);
  const latest = events.length ? events[events.length - 1] : null;
  const decision = latest && latest.decision !== "withdrawn" ? latest.decision : undefined;
  const status = statusOf(c, decision);
  const problems = c.results.filter((r) => r.outcome === "failed");
  const unsure = c.results.filter((r) => r.outcome === "abstained");
  const unreadable = c.reason && c.reason !== "check_findings";
  const next = NEXT_STEP[c.action] ?? NEXT_STEP.REVIEW_MANUALLY;
  const history = (c.priceHistory ?? []).filter((h) => h.points.length > 0);
  const previewable = c.format === "pdf" && !["quarantined_unreadable", "quarantined_encrypted"].includes(c.extraction.intake);
  const itemName = (sku: string) => c.invoice?.lines.find((l) => l.sku === sku)?.description ?? sku;

  const headline = unreadable
    ? "Couldn't read this invoice"
    : problems.length
      ? `${problems.length} problem${problems.length === 1 ? "" : "s"} found`
      : unsure.length
        ? "One check couldn't decide"
        : "Nothing wrong";

  return (
    <div className="detail">
      <section className="card detail-head">
        <div>
          <div className="kicker">
            {c.origin === "lab" ? <Pill tone="info">Your test</Pill>
              : c.origin === "upload" ? <Pill tone="info">Your upload</Pill> : null}
            <span className="mono">{c.number ?? "No invoice number"}</span>
          </div>
          <h1>{c.vendor ?? c.invoice?.vendorAsPrinted ?? "Unknown supplier"}</h1>
        </div>
        <div className="amount">
          <div className="v">{c.total ? `${c.currency} ${money(c.total)}` : "—"}</div>
          <div style={{ marginTop: 8 }}><StatusPill status={status} /></div>
        </div>
        <div className="facts">
          <span>PO <b className="mono">{c.po ?? "—"}</b></span>
          <span>Issued <b>{date(c.issued)}</b></span>
          <span>Due <b>{date(c.invoice?.due ?? null)}</b></span>
        </div>
      </section>

      <section className="card summary">
        <h2>
          <span className={`dot dot-${problems.length ? "bad" : unreadable || unsure.length ? "warn" : "ok"}`} aria-hidden />
          {headline}
        </h2>
        {(unreadable || problems.length > 0 || unsure.length > 0) && (
          <ul>
            {unreadable && <li><span className="dot dot-warn" aria-hidden />{REASONS[c.reason!]?.long ?? c.reason}</li>}
            {problems.map((r, i) => <li key={`p${i}`}><span className="dot dot-bad" aria-hidden />{findingSentence(r)}</li>)}
            {unsure.map((r, i) => <li key={`u${i}`}><span className="dot dot-warn" aria-hidden />{findingSentence(r)}</li>)}
          </ul>
        )}
        <div className="next-step">
          <div style={{ flex: "1 1 240px" }}>
            <div className="label">Suggested next step</div>
            <div className="what">{next.what}</div>
            <details className="tech">
              <summary>Why</summary>
              <div className="body">
                <p>{next.why}</p>
                {c.recommendation?.rationale.slice(1).map((s, i) => <p key={i} style={{ margin: "6px 0 0" }}>{s.text}</p>)}
              </div>
            </details>
          </div>
          {ws && <a className="btn btn-sm" style={{ background: "#fff", color: "var(--fg)" }} href="#decide">Decide</a>}
        </div>
      </section>

      {c.results.length > 0 && (
        <section className="card">
          <div className="card-head"><h3>The four checks</h3></div>
          <div className="checklist">
            {CHECK_ORDER.map((code) => {
              const mine = c.results.filter((r) => r.check_code === code);
              const failed = mine.filter((r) => r.outcome === "failed");
              const abstained = mine.filter((r) => r.outcome === "abstained");
              const tone = failed.length ? "bad" : abstained.length ? "warn" : "ok";
              const said = failed.length ? failed : abstained;
              return (
                <div className="check-row" key={code}>
                  <span className={`dot dot-${tone}`} aria-hidden />
                  <div>
                    <h4>{CHECKS[code].name}</h4>
                    <div className="says">
                      {said.length ? said.map((r, i) => <p key={i}>{findingSentence(r)}</p>) : passSentence(code)}
                    </div>
                    <details className="tech">
                      <summary>Details</summary>
                      <div className="body">
                        <p style={{ margin: "0 0 6px" }}>{CHECKS[code].plain}</p>
                        {mine.map((r, i) => (
                          <p key={i} style={{ margin: "4px 0" }}>
                            {r.explanation}
                            {(r.observed || r.expected) && (
                              <> (found {r.observed ?? "—"}, expected {r.expected ?? "—"}{r.tolerance ? `, allowed difference ${r.tolerance}` : ""})</>
                            )}
                          </p>
                        ))}
                      </div>
                    </details>
                  </div>
                  <span className="xs muted">{failed.length ? "Problem" : abstained.length ? "Unsure" : "Passed"}</span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {c.invoice && <Lines c={c} />}

      {history.length > 0 && (
        <section className="card card-pad stack">
          <h3 style={{ fontSize: 17, display: "flex", alignItems: "center", gap: 6 }}>
            Price vs. this supplier&rsquo;s history
            <Tip>
              Each dot is a price this supplier charged for the same item before. A price is only flagged above the red
              line: unusually high <b>and</b> at least 10% above usual.
            </Tip>
          </h3>
          {history.map((h) => <PriceHistory key={h.lineNo} h={h} description={itemName(h.sku)} />)}
        </section>
      )}

      <section className="card">
        <div className="card-head" style={{ paddingBottom: 20 }}>
          <h3>Original file <span className="xs muted">{c.format.toUpperCase()}</span></h3>
          <div className="end" style={{ display: "flex", gap: 8 }}>
            {previewable && (
              <button className="btn btn-sm" onClick={() => setShowDoc((v) => !v)} aria-expanded={showDoc}>
                {showDoc ? <EyeOff size={15} aria-hidden /> : <Eye size={15} aria-hidden />} {showDoc ? "Hide" : "Show"}
              </button>
            )}
            <a className="btn btn-sm" href={documentUrl}>Download</a>
          </div>
        </div>
        {showDoc && previewable && <iframe className="doc-frame" src={documentUrl} title={`Original document ${c.file}`} />}
        {!previewable && (
          <p className="small soft" style={{ padding: "0 28px 24px" }}>
            {c.format !== "pdf" ? "Spreadsheets can't be previewed. Download to open it." : REASONS[c.extraction.intake]?.long}
          </p>
        )}
      </section>

      {ws && (
        <section className="card card-pad stack" id="decide">
          <h3 style={{ fontSize: 17 }}>Your decision</h3>
          <Decision ws={ws} invoiceId={c.id} action={c.action} events={events} onRecorded={onDecided} preset={preset} />
        </section>
      )}
    </div>
  );
}
