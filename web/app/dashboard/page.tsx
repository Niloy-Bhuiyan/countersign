"use client";

import { Columns, HBars } from "@/components/Charts";
import { useJson } from "@/components/data";
import { compact } from "@/components/format";
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

export default function Dashboard() {
  const { data: s, error } = useJson<Summary>("/data/summary.json");
  if (error) return <p>Could not load the summary: {error}</p>;
  if (!s) return <p className="muted">Loading…</p>;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Controller view</h1>
          <p>
            What was invoiced, what is held, where the money at risk sits, and which rules are firing.
            Computed from the same cases as the queue. Amounts in BDT; the invoices billed in another
            currency are counted as findings, not converted.
          </p>
        </div>
      </div>

      <section className="kpis">
        <div className="panel kpi">
          <div className="label">Invoiced</div>
          <div className="value">{compact(s.spendBDT)}</div>
          <div className="sub">{s.documents} documents</div>
        </div>
        <div className="panel kpi">
          <div className="label">Held for review</div>
          <div className="value">{compact(s.atRiskBDT)}</div>
          <div className="sub">{s.needsReview} invoices awaiting a decision</div>
        </div>
        <div className="panel kpi">
          <div className="label">With a failed check</div>
          <div className="value">{s.withFindings}</div>
          <div className="sub">{((s.withFindings / s.documents) * 100).toFixed(1)}% of documents</div>
        </div>
        <div className="panel kpi">
          <div className="label">Cleared by every check</div>
          <div className="value">{((s.cleared / s.documents) * 100).toFixed(1)}%</div>
          <div className="sub">{s.cleared} invoices, still awaiting approval</div>
        </div>
      </section>

      <div className="grid-3" style={{ marginBottom: 12 }}>
        <section className="panel">
          <div className="panel-head">
            <h2>Invoiced by month</h2>
          </div>
          <div className="panel-body">
            <Columns data={s.spendByMonth} />
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h2>Recommended actions</h2>
          </div>
          <div className="panel-body">
            <HBars
              data={s.actions}
              format="count"
              labelFor={(key) => ACTIONS[key]?.label ?? key}
            />
          </div>
        </section>
      </div>

      <div className="grid-2" style={{ marginBottom: 12 }}>
        <section className="panel">
          <div className="panel-head">
            <h2>Value held, by vendor</h2>
            <span className="small muted">Top 8</span>
          </div>
          <div className="panel-body">
            <HBars data={s.heldByVendor} />
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h2>Invoiced, by category</h2>
          </div>
          <div className="panel-body">
            <HBars data={s.spendByCategory} />
          </div>
        </section>
      </div>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-head">
            <h2>Findings, by rule</h2>
            <span className="small muted">Checks that failed</span>
          </div>
          <div className="panel-body">
            <HBars data={s.findingsByRule} format="count" labelFor={ruleLabel} />
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h2>Why invoices are in review</h2>
          </div>
          <div className="panel-body">
            <HBars
              data={s.reasons.filter((r) => r.label !== "cleared")}
              format="count"
              labelFor={(key) => REASONS[key] ?? key}
            />
            <h3 style={{ margin: "16px 0 8px" }}>Checks that could not judge</h3>
            <HBars data={s.abstentionsByRule} format="count" labelFor={ruleLabel} />
          </div>
        </section>
      </div>
    </>
  );
}
