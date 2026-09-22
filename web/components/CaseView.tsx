"use client";

import {
  AlertTriangle,
  Building2,
  Calculator,
  Calendar,
  Check,
  CheckCircle2,
  CircleHelp,
  Copy,
  Eye,
  EyeOff,
  FileText,
  Hash,
  Lightbulb,
  PackageCheck,
  TrendingUp,
  XCircle,
} from "lucide-react";
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

const CHECK_ICONS: Record<string, React.ElementType> = {
  THREE_WAY_MATCH: PackageCheck,
  PRICE_VARIANCE: TrendingUp,
  DUPLICATE_INVOICE: Copy,
  TAX_ARITHMETIC: Calculator,
};

function Progress({ decided }: { decided: boolean }) {
  const steps = [
    { label: "Received", done: true },
    { label: "Read", done: true },
    { label: "Checked", done: true },
    { label: decided ? "Decided" : "Your decision", done: decided },
  ];
  return (
    <div className="progress" aria-label="Progress">
      {steps.map((s, i) => (
        <span key={s.label} style={{ display: "inline-flex", alignItems: "center" }}>
          {i > 0 && <span className="line" aria-hidden />}
          <span className="p">
            <span className={`dot${s.done ? "" : " now"}`} aria-hidden>
              {s.done ? <Check size={12} /> : <span style={{ fontSize: 11, fontWeight: 800 }}>{i + 1}</span>}
            </span>
            {s.label}
          </span>
        </span>
      ))}
    </div>
  );
}

function Lines({ c }: { c: CaseDetail }) {
  const inv = c.invoice!;
  const order = c.order;
  return (
    <div className="card">
      <div className="card-head">
        <FileText size={18} className="muted" aria-hidden />
        <div>
          <h3>Invoice compared with the purchase order</h3>
          <p className="card-sub">
            {order
              ? `Purchase order ${order.number}, raised ${date(order.orderedAt)}. ${order.deliveries.length} delivery note(s) on record.`
              : "No purchase order found for this invoice."}{" "}
            Cells in red don&rsquo;t match.
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
            <tr className="total"><td colSpan={6} className="r">Amount to pay</td><td className="r">{c.currency} {money(inv.total)}</td></tr>
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
    ? "We couldn't read this invoice"
    : problems.length
      ? `${problems.length} problem${problems.length === 1 ? "" : "s"} found`
      : unsure.length
        ? "Nothing wrong found, but one check couldn't decide"
        : "Nothing wrong found";

  return (
    <div className="detail">
      <section className="card detail-head">
        <div>
          <div className="kicker">
            {c.origin === "lab" ? <Pill tone="info" icon={false}>Your test invoice</Pill>
              : c.origin === "upload" ? <Pill tone="info" icon={false}>Your upload</Pill> : null}
            <span>Invoice from</span>
          </div>
          <h1>{c.vendor ?? c.invoice?.vendorAsPrinted ?? "Unknown supplier"}</h1>
        </div>
        <div className="amount">
          <div className="l">Amount to pay</div>
          <div className="v">{c.total ? `${c.currency} ${money(c.total)}` : "—"}</div>
          <div style={{ marginTop: 6 }}><StatusPill status={status} /></div>
        </div>
        <div className="facts">
          <span><Hash size={14} aria-hidden /> Invoice <b className="mono">{c.number ?? "unreadable"}</b></span>
          <span><Building2 size={14} aria-hidden /> Purchase order <b className="mono">{c.po ?? "—"}</b></span>
          <span><Calendar size={14} aria-hidden /> Issued {date(c.issued)}</span>
          <span><Calendar size={14} aria-hidden /> Due {date(c.invoice?.due ?? null)}</span>
        </div>
        <Progress decided={Boolean(decision)} />
      </section>

      <section className={`card summary`}>
        <h2>
          {unreadable ? <AlertTriangle size={20} color="var(--warn)" aria-hidden />
            : problems.length ? <XCircle size={20} color="var(--bad)" aria-hidden />
            : unsure.length ? <CircleHelp size={20} color="var(--warn)" aria-hidden />
            : <CheckCircle2 size={20} color="var(--ok)" aria-hidden />}
          {headline}
        </h2>
        <ul>
          {unreadable && (
            <li><AlertTriangle size={16} color="var(--warn)" aria-hidden />{REASONS[c.reason!]?.long ?? c.reason}</li>
          )}
          {problems.map((r, i) => (
            <li key={`p${i}`}><XCircle size={16} color="var(--bad)" aria-hidden />{findingSentence(r)}</li>
          ))}
          {unsure.map((r, i) => (
            <li key={`u${i}`}><CircleHelp size={16} color="var(--warn)" aria-hidden />{findingSentence(r)}</li>
          ))}
          {!unreadable && problems.length === 0 && unsure.length === 0 && (
            <li><CheckCircle2 size={16} color="var(--ok)" aria-hidden />All four checks passed. The quantities, prices, tax and invoice number are all as expected.</li>
          )}
        </ul>
        <div className="next-step">
          <Lightbulb size={20} color="var(--primary)" aria-hidden style={{ flex: "none", marginTop: 2 }} />
          <div>
            <div className="label">Suggested next step</div>
            <div className="what">{next.what}</div>
            <div className="why">{next.why}</div>
            {c.recommendation && (
              <details className="tech">
                <summary>Why this suggestion?</summary>
                <div className="body">
                  {c.recommendation.rationale.slice(1).map((s, i) => <p key={i} style={{ margin: "4px 0" }}>{s.text}</p>)}
                  <p style={{ marginTop: 8 }}>
                    Drafted by a rule-based assistant ({c.recommendation.agent_version}) that can only read records, never
                    change them. Every claim above points to a record that exists. You make the decision.
                  </p>
                </div>
              </details>
            )}
          </div>
        </div>
      </section>

      {c.results.length > 0 && (
        <section className="card">
          <div className="card-head">
            <PackageCheck size={18} className="muted" aria-hidden />
            <div>
              <h3>The four checks</h3>
              <p className="card-sub">Each one answers a simple question. None of them uses AI; the rules are fixed and repeatable.</p>
            </div>
          </div>
          <div className="checklist">
            {CHECK_ORDER.map((code) => {
              const mine = c.results.filter((r) => r.check_code === code);
              const failed = mine.filter((r) => r.outcome === "failed");
              const abstained = mine.filter((r) => r.outcome === "abstained");
              const tone = failed.length ? "bad" : abstained.length ? "warn" : "ok";
              const Icon = CHECK_ICONS[code];
              const said = failed.length ? failed : abstained;
              return (
                <div className="check-row" key={code}>
                  <span className={`ic tone-${tone}`}><Icon size={18} aria-hidden /></span>
                  <div>
                    <h4>{CHECKS[code].name}</h4>
                    <div className="q">{CHECKS[code].question}</div>
                    <div className="says">
                      {said.length ? said.map((r, i) => <p key={i}>{findingSentence(r)}</p>) : passSentence(code)}
                    </div>
                    <details className="tech">
                      <summary>Show the technical details</summary>
                      <div className="body">
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
                  <Pill tone={tone}>{failed.length ? "Problem" : abstained.length ? "Couldn't decide" : "Passed"}</Pill>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {c.invoice && <Lines c={c} />}

      {history.length > 0 && (
        <section className="card card-pad stack">
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
              Is the price normal for this supplier?
              <Tip>
                Each blue dot is a price this supplier charged us for the same item on an earlier order. The grey line is
                their usual price. A price is only flagged if it is above the red line: unusually high <b>and</b> at least
                10% above usual.
              </Tip>
            </h3>
            <p className="card-sub">Compares this invoice with the supplier&rsquo;s own past prices for the same item.</p>
          </div>
          {history.map((h) => <PriceHistory key={h.lineNo} h={h} description={itemName(h.sku)} />)}
        </section>
      )}

      <section className="card">
        <div className="card-head">
          <FileText size={18} className="muted" aria-hidden />
          <div>
            <h3>Original document</h3>
            <p className="card-sub">The file exactly as the supplier sent it ({c.format.toUpperCase()}).</p>
          </div>
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
          <p className="card-pad small soft">
            {c.format !== "pdf" ? "Spreadsheets can't be previewed here. Download to open it." : REASONS[c.extraction.intake]?.long}
          </p>
        )}
      </section>

      {ws && (
        <section className="card card-pad stack" id="decide">
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 700 }}>Your decision</h3>
            <p className="card-sub">Nothing happens to this invoice until someone decides.</p>
          </div>
          <Decision ws={ws} invoiceId={c.id} action={c.action} events={events} onRecorded={onDecided} preset={preset} />
        </section>
      )}
    </div>
  );
}
