"use client";

import { Download, History } from "lucide-react";
import Link from "next/link";
import { useDecisions, useWorkspace } from "@/components/api";
import { NEXT_STEP } from "@/components/explain";
import { date } from "@/components/format";
import { Empty, Pill } from "@/components/ui";

const LABEL = {
  approved: { word: "Approved", tone: "ok" as const },
  held: { word: "On hold", tone: "warn" as const },
  escalated: { word: "Escalated", tone: "bad" as const },
};

export default function Decisions() {
  const ws = useWorkspace();
  const { data, error } = useDecisions(ws);
  const log = [...(data?.log ?? [])].reverse();
  const current = Object.values(data?.current ?? {});
  const count = (d: string) => current.filter((e) => e.decision === d).length;
  const overruled = current.filter((e) => e.overrules_recommendation).length;

  const stats = [
    { tone: "ok", label: "Approved", value: count("approved") },
    { tone: "warn", label: "On hold", value: count("held") },
    { tone: "bad", label: "Escalated", value: count("escalated") },
    { tone: "muted", label: "Against the suggestion", value: overruled },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Decision history</h1>
          <p>Every decision, newest first. Nothing is ever edited or deleted.</p>
        </div>
        {ws && log.length > 0 && (
          <div className="end">
            <a className="btn" href={`/api/workspaces/${ws}/decisions.csv`}><Download size={16} aria-hidden /> CSV</a>
          </div>
        )}
      </div>

      <div className="grid-4">
        {stats.map(({ tone, label, value }) => (
          <div className="card stat" key={label}>
            <div className="stat-top"><span className={`dot dot-${tone}`} aria-hidden />{label}</div>
            <div className="stat-value">{data ? value : "…"}</div>
          </div>
        ))}
      </div>

      <section className="card section">
        <div className="card-head"><h2>All decisions</h2></div>
        {error && <p className="error-box" style={{ margin: 16 }}>{error}</p>}
        {data && log.length === 0 && (
          <Empty icon={History} title="No decisions yet">
            <p className="small">Open an invoice and choose Approve, Hold or Escalate.</p>
            <Link className="btn btn-primary btn-sm" href="/review/">Go to review</Link>
          </Empty>
        )}
        {log.length > 0 && (
          <div className="table-wrap">
            <table className="t">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Invoice</th>
                  <th>Decision</th>
                  <th>By</th>
                  <th>Suggested</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {log.map((e) => {
                  const l = LABEL[e.decision as keyof typeof LABEL];
                  return (
                    <tr key={`${e.invoice_id}-${e.seq}`}>
                      <td className="num small">{date(e.at.slice(0, 10))}, {e.at.slice(11, 16)}</td>
                      <td><Link className="mono" href={`/review/?id=${e.invoice_id}`}>{e.invoice_id}</Link></td>
                      <td>{l ? <Pill tone={l.tone}>{l.word}</Pill> : <Pill tone="muted">Undone</Pill>}</td>
                      <td>{e.reviewer}</td>
                      <td className="small">
                        {NEXT_STEP[e.recommended_action]?.what ?? e.recommended_action}
                        {e.overrules_recommendation && <div className="xs" style={{ color: "var(--warn)", fontWeight: 500 }}>Overruled</div>}
                      </td>
                      <td className="small soft">{e.note || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
