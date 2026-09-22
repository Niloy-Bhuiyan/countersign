"use client";

import { Banknote, BarChart3, BadgeCheck, FileSearch, XCircle } from "lucide-react";
import { useJson } from "@/components/api";
import { NEXT_STEP, REASONS, shortLabel } from "@/components/explain";
import { compact, money } from "@/components/format";
import { Tip } from "@/components/ui";

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
  tone?: "bad" | "ok";
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
          <span className="v">{format === "money" ? `BDT ${compact(String(d.value))}` : d.value}</span>
        </div>
      ))}
    </div>
  );
}

function Months({ data }: { data: { period: string; value: string }[] }) {
  const w = 900, h = 220, pl = 56, pb = 28, pt = 16;
  const max = Math.max(...data.map((d) => Number(d.value)), 1);
  const band = (w - pl - 10) / data.length;
  const ticks = [0, 0.5, 1];
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Value of invoices received each month">
      {ticks.map((t) => {
        const y = h - pb - (h - pb - pt) * t;
        return (
          <g key={t}>
            <line x1={pl} x2={w} y1={y} y2={y} stroke="#e2e8f0" />
            <text x={pl - 8} y={y + 4} textAnchor="end">{compact(String(Math.round(max * t)))}</text>
          </g>
        );
      })}
      {data.map((d, i) => {
        const bh = ((h - pb - pt) * Number(d.value)) / max;
        const x = pl + i * band + band * 0.18;
        const [year, month] = d.period.split("-");
        return (
          <g key={d.period}>
            <rect x={x} y={h - pb - bh} width={band * 0.64} height={bh} rx={4} fill="#2563eb">
              <title>{`${names[Number(month) - 1]} ${year}: BDT ${money(d.value)}`}</title>
            </rect>
            <text x={x + band * 0.32} y={h - 8} textAnchor="middle">{names[Number(month) - 1]} {year.slice(2)}</text>
          </g>
        );
      })}
    </svg>
  );
}

export default function Reports() {
  const { data: s, error } = useJson<Summary>("/data/summary.json");
  if (error) return <div className="page"><p className="error-box">Couldn&rsquo;t load the report: {error}</p></div>;
  if (!s) return <div className="page"><p className="muted">Loading the report…</p></div>;

  const cards = [
    { icon: FileSearch, tone: "tone-primary", label: "Total invoiced", value: `BDT ${compact(s.spendBDT)}`, meaning: `Across ${s.documents} invoices.`, tip: "The combined value of every invoice received, in Bangladeshi taka (M = million). Invoices in other currencies aren't added in." },
    { icon: Banknote, tone: "tone-warn", label: "Money on hold", value: `BDT ${compact(s.atRiskBDT)}`, meaning: `${s.needsReview} invoices waiting for a decision.`, tip: "Invoices that need a closer look. None of this money is paid until someone approves." },
    { icon: XCircle, tone: "tone-bad", label: "Problems found", value: String(s.withFindings), meaning: "Invoices where at least one check failed.", tip: "Overcharges, billing for goods not delivered, duplicates, wrong VAT, and so on." },
    { icon: BadgeCheck, tone: "tone-ok", label: "Passed every check", value: `${((s.cleared / s.documents) * 100).toFixed(0)}%`, meaning: `${s.cleared} invoices, awaiting approval.`, tip: "The share of invoices with nothing wrong. They still wait for a person to approve them." },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Reports</h1>
          <p>The big picture for a finance manager: how much came in, how much is on hold and why, and which suppliers it involves.</p>
        </div>
      </div>

      <div className="grid-4">
        {cards.map(({ icon: Icon, tone, label, value, meaning, tip }) => (
          <div className="card stat" key={label}>
            <div className="stat-top"><span className={`stat-icon ${tone}`}><Icon size={18} aria-hidden /></span>{label}<Tip>{tip}</Tip></div>
            <div className="stat-value">{value}</div>
            <div className="stat-meaning">{meaning}</div>
          </div>
        ))}
      </div>

      <section className="card section">
        <div className="card-head">
          <BarChart3 size={18} className="muted" aria-hidden />
          <div>
            <h2>Invoices received each month</h2>
            <p className="card-sub">Total value of supplier invoices by the month they were issued, in BDT. Hover a bar for the exact amount.</p>
          </div>
        </div>
        <div className="card-pad"><Months data={s.spendByMonth} /></div>
      </section>

      <div className="grid-2 section">
        <section className="card">
          <div className="card-head"><div><h2>Which suppliers have money on hold</h2><p className="card-sub">The eight suppliers with the most invoice value waiting for a decision.</p></div></div>
          <div className="card-pad"><Bars data={s.heldByVendor} format="money" tone="bad" /></div>
        </section>
        <section className="card">
          <div className="card-head"><div><h2>What we buy</h2><p className="card-sub">Total invoiced by type of goods or service.</p></div></div>
          <div className="card-pad"><Bars data={s.spendByCategory} format="money" /></div>
        </section>
      </div>

      <div className="grid-2 section">
        <section className="card">
          <div className="card-head"><div><h2>Most common problems</h2><p className="card-sub">How many invoices each kind of problem was found on.</p></div></div>
          <div className="card-pad"><Bars data={s.findingsByRule} format="count" name={shortLabel} tone="bad" /></div>
        </section>
        <section className="card">
          <div className="card-head"><div><h2>What the system suggests</h2><p className="card-sub">The next step suggested for each invoice. A person makes the actual decision.</p></div></div>
          <div className="card-pad stack">
            <Bars data={s.actions} format="count" name={(k) => NEXT_STEP[k]?.what ?? k} />
            <p className="small" style={{ fontWeight: 700, marginTop: 8 }}>Why some invoices couldn&rsquo;t be checked fully</p>
            <Bars
              data={[...s.reasons.filter((r) => r.label !== "cleared" && r.label !== "check_findings"), ...s.abstentionsByRule]}
              format="count"
              name={(k) => REASONS[k]?.short ?? shortLabel(k)}
            />
          </div>
        </section>
      </div>
    </div>
  );
}
