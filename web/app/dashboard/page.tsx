"use client";

import { useJson } from "@/components/api";
import { compact, money } from "@/components/format";
import { ACTIONS, REASONS, ruleLabel } from "@/components/labels";

type Summary = {
  documents: number;
  cleared: number;
  needsReview: number;
  spendBDT: string;
  atRiskBDT: string;
  withFindings: number;
  spendByMonth: { period: string; value: string }[];
  spendByCategory: { label: string; value: string }[];
  heldByVendor: { label: string; value: string }[];
  findingsByRule: { label: string; value: number }[];
  abstentionsByRule: { label: string; value: number }[];
  actions: { label: string; value: number }[];
  reasons: { label: string; value: number }[];
};

function Bars({ data, format, name = (s: string) => s, tone }: {
  data: { label: string; value: string | number }[];
  format: "money" | "count";
  name?: (s: string) => string;
  tone?: "red";
}) {
  const max = Math.max(...data.map((d) => Number(d.value)), 1);
  return (
    <div className="bars" role="list">
      {data.map((d) => (
        <div className="bar" role="listitem" key={d.label}>
          <span className="name" title={name(d.label)}>{name(d.label)}</span>
          <span className="track" aria-hidden="true">
            <span className={`fill${tone ? ` ${tone}` : ""}`} style={{ width: `${(Number(d.value) / max) * 100}%`, display: "block" }} />
          </span>
          <span className="v">{format === "money" ? money(String(d.value)) : d.value}</span>
        </div>
      ))}
    </div>
  );
}

function Months({ data }: { data: { period: string; value: string }[] }) {
  const w = 900, h = 170, pl = 8, pb = 22, pt = 18;
  const max = Math.max(...data.map((d) => Number(d.value)), 1);
  const band = (w - pl * 2) / data.length;
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Invoiced value by month">
      <line x1={0} x2={w} y1={h - pb} y2={h - pb} stroke="var(--ink)" />
      {data.map((d, i) => {
        const bh = ((h - pb - pt) * Number(d.value)) / max;
        const x = pl + i * band + band * 0.28;
        return (
          <g key={d.period}>
            <rect x={x} y={h - pb - bh} width={band * 0.44} height={bh} fill="var(--ink)">
              <title>{`${d.period}: BDT ${money(d.value)}`}</title>
            </rect>
            <text x={x + band * 0.22} y={h - 6} textAnchor="middle">{d.period.slice(5)}/{d.period.slice(2, 4)}</text>
            {Number(d.value) === max && (
              <text x={x + band * 0.22} y={h - pb - bh - 6} textAnchor="middle" style={{ fill: "var(--ink)", fontWeight: 600 }}>
                {compact(d.value)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export default function Controller() {
  const { data: s, error } = useJson<Summary>("/data/summary.json");
  if (error) return <div className="page"><p className="flash">Could not load: {error}</p></div>;
  if (!s) return <div className="page"><p className="muted">Loading…</p></div>;
  const share = ((s.cleared / s.documents) * 100).toFixed(1);

  return (
    <div className="page">
      <h1 className="page-title">Controller&rsquo;s view</h1>
      <p className="statement" style={{ marginTop: 18 }}>
        BDT <b>{compact(s.spendBDT)}</b> was invoiced across {s.documents} documents.{" "}
        <span className="red">BDT {compact(s.atRiskBDT)} is held</span> on {s.needsReview} invoices awaiting a
        decision; {s.withFindings} of them failed a check. {share}% cleared every check and wait only for a
        countersignature.
      </p>

      <div className="figures-row" style={{ marginTop: 28 }}>
        <div><span className="label">Invoiced</span><div className="big fig">{compact(s.spendBDT)}</div><div className="sub">BDT, {s.documents} documents</div></div>
        <div><span className="label">Held</span><div className="big fig red">{compact(s.atRiskBDT)}</div><div className="sub">{s.needsReview} awaiting a decision</div></div>
        <div><span className="label">Failed a check</span><div className="big fig">{s.withFindings}</div><div className="sub">of {s.documents} documents</div></div>
        <div><span className="label">Cleared</span><div className="big fig">{share}%</div><div className="sub">{s.cleared} invoices</div></div>
      </div>

      <section className="section">
        <div className="section-head"><h2>Invoiced by month</h2><span className="aside">BDT; foreign-currency invoices are findings, not converted</span></div>
        <Months data={s.spendByMonth} />
      </section>

      <div className="two section">
        <section>
          <div className="section-head"><h2>Where the held money sits</h2><span className="aside">Top 8 vendors</span></div>
          <Bars data={s.heldByVendor} format="money" tone="red" />
        </section>
        <section>
          <div className="section-head"><h2>What was bought</h2></div>
          <Bars data={s.spendByCategory} format="money" />
        </section>
      </div>

      <div className="two section">
        <section>
          <div className="section-head"><h2>Which rules fire</h2></div>
          <Bars data={s.findingsByRule} format="count" name={ruleLabel} tone="red" />
        </section>
        <section>
          <div className="section-head"><h2>What the agent recommends</h2></div>
          <Bars data={s.actions} format="count" name={(k) => ACTIONS[k]?.verdict ?? k} />
          <div className="section-head" style={{ marginTop: 28 }}><h2>Why the rest are in review</h2></div>
          <Bars data={[...s.reasons.filter((r) => r.label !== "cleared" && r.label !== "check_findings"), ...s.abstentionsByRule]}
            format="count" name={(k) => REASONS[k] ?? ruleLabel(k)} />
        </section>
      </div>
    </div>
  );
}
