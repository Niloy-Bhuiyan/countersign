"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { type Decision, type QueueRow, readDecisions, useJson } from "@/components/data";
import { compact, compareDecimal, date, money } from "@/components/format";
import { ACTIONS, ActionTag, REASONS, STATES, StateTag, Tag, ruleLabel } from "@/components/labels";

type Summary = {
  documents: number;
  cleared: number;
  needsReview: number;
  spendBDT: string;
  atRiskBDT: string;
  withFindings: number;
};

type View = "review" | "cleared" | "all";

export default function Queue() {
  const router = useRouter();
  const { data: rows, error } = useJson<QueueRow[]>("/data/queue.json");
  const { data: summary } = useJson<Summary>("/data/summary.json");
  const [view, setView] = useState<View>("review");
  const [action, setAction] = useState("");
  const [finding, setFinding] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const search = useRef<HTMLInputElement>(null);
  const body = useRef<HTMLTableSectionElement>(null);

  useEffect(() => setDecisions(readDecisions()), []);

  const findings = useMemo(() => {
    const keys = new Set<string>();
    rows?.forEach((row) => row.failed.concat(row.abstained).forEach((key) => keys.add(key)));
    return [...keys].sort((a, b) => ruleLabel(a).localeCompare(ruleLabel(b)));
  }, [rows]);

  const counts = useMemo(() => {
    const review = rows?.filter((r) => r.state === "needs_review").length ?? 0;
    return { review, cleared: (rows?.length ?? 0) - review, all: rows?.length ?? 0 };
  }, [rows]);

  const visible = useMemo(() => {
    if (!rows) return [];
    const q = query.trim().toLowerCase();
    return rows
      .filter((r) =>
        view === "all" ? true : view === "review" ? r.state === "needs_review" : r.state === "cleared",
      )
      .filter((r) => !action || r.action === action)
      .filter((r) => !finding || r.failed.includes(finding) || r.abstained.includes(finding))
      .filter(
        (r) =>
          !q ||
          [r.id, r.number, r.vendor, r.po].some((field) => field?.toLowerCase().includes(q)),
      )
      .sort((a, b) =>
        view === "cleared"
          ? (b.issued ?? "").localeCompare(a.issued ?? "")
          : compareDecimal(b.total, a.total),
      );
  }, [rows, view, action, finding, query]);

  useEffect(() => setSelected(0), [view, action, finding, query]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const typing = (event.target as HTMLElement)?.closest("input, select, textarea");
      if (event.key === "/" && !typing) {
        event.preventDefault();
        search.current?.focus();
        return;
      }
      if (typing) {
        if (event.key === "Escape") (event.target as HTMLElement).blur();
        return;
      }
      if (event.key === "j" || event.key === "ArrowDown") {
        event.preventDefault();
        setSelected((i) => Math.min(i + 1, visible.length - 1));
      } else if (event.key === "k" || event.key === "ArrowUp") {
        event.preventDefault();
        setSelected((i) => Math.max(i - 1, 0));
      } else if (event.key === "Enter" && visible[selected]) {
        router.push(`/case/?id=${visible[selected].id}`);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, selected, router]);

  useEffect(() => {
    body.current?.children[selected]?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Review queue</h1>
          <p>
            Invoices the system could not clear on its own, with the finding stated in numbers and a
            recommended action. Nothing here is paid until a person decides.
          </p>
        </div>
        <div className="actions">
          <a className="btn" href="/exports/countersign-lines.xlsx">
            Export XLSX
          </a>
          <a className="btn" href="/exports/countersign-lines.csv">
            Export CSV
          </a>
        </div>
      </div>

      <section className="kpis" aria-label="Summary">
        <div className="panel kpi">
          <div className="label">Invoiced, BDT</div>
          <div className="value">{summary ? compact(summary.spendBDT) : "—"}</div>
          <div className="sub">{summary ? `${summary.documents} documents received` : ""}</div>
        </div>
        <div className="panel kpi">
          <div className="label">Awaiting a decision</div>
          <div className="value">{summary?.needsReview ?? "—"}</div>
          <div className="sub">{summary ? `${summary.withFindings} with a failed check` : ""}</div>
        </div>
        <div className="panel kpi">
          <div className="label">Value held for review, BDT</div>
          <div className="value">{summary ? compact(summary.atRiskBDT) : "—"}</div>
          <div className="sub">Not payable until decided</div>
        </div>
        <div className="panel kpi">
          <div className="label">Cleared by every check</div>
          <div className="value">{summary?.cleared ?? "—"}</div>
          <div className="sub">
            {summary ? `${((summary.cleared / summary.documents) * 100).toFixed(1)}% of documents` : ""}
          </div>
        </div>
      </section>

      <section className="panel" aria-label="Invoices">
        <div className="filters">
          <div className="segmented" role="group" aria-label="Show">
            {(
              [
                ["review", "Needs review"],
                ["cleared", "Cleared"],
                ["all", "All"],
              ] as const
            ).map(([key, label]) => (
              <button key={key} aria-pressed={view === key} onClick={() => setView(key)}>
                {label}
                <span className="count">{counts[key]}</span>
              </button>
            ))}
          </div>
          <select
            className="select"
            aria-label="Recommended action"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          >
            <option value="">Any recommendation</option>
            {Object.entries(ACTIONS).map(([key, a]) => (
              <option key={key} value={key}>
                {a.label}
              </option>
            ))}
          </select>
          <select
            className="select"
            aria-label="Finding"
            value={finding}
            onChange={(e) => setFinding(e.target.value)}
          >
            <option value="">Any finding</option>
            {findings.map((key) => (
              <option key={key} value={key}>
                {ruleLabel(key)}
              </option>
            ))}
          </select>
          <input
            ref={search}
            className="input"
            type="search"
            placeholder="Invoice, vendor or order"
            aria-label="Search invoices"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <span className="small muted" style={{ marginLeft: "auto" }}>
            <kbd>j</kbd> <kbd>k</kbd> move &nbsp; <kbd>Enter</kbd> open &nbsp; <kbd>/</kbd> search
          </span>
        </div>

        <div className="table-wrap">
          <table aria-label="Invoice queue" aria-rowcount={visible.length}>
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Vendor</th>
                <th>Order</th>
                <th>Dated</th>
                <th className="num">Amount</th>
                <th>Findings</th>
                <th>Recommendation</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody ref={body}>
              {visible.map((row, index) => {
                const decided = decisions[row.id];
                const notes = row.failed.length ? row.failed : row.abstained;
                return (
                  <tr
                    key={row.id}
                    aria-selected={index === selected}
                    onClick={() => router.push(`/case/?id=${row.id}`)}
                    onMouseEnter={() => setSelected(index)}
                  >
                    <td>
                      <span className="mono">{row.number ?? row.id}</span>
                      {!row.number && <span className="muted small"> unread</span>}
                    </td>
                    <td className="clip" title={row.vendor ?? ""}>
                      {row.vendor ?? <span className="muted">Unknown</span>}
                    </td>
                    <td className="mono small">{row.po ?? "—"}</td>
                    <td className="mono small">{date(row.issued)}</td>
                    <td className="num">{money(row.total, row.currency)}</td>
                    <td className="clip">
                      {row.reason && row.reason !== "check_findings" ? (
                        <span className="small">{REASONS[row.reason] ?? row.reason}</span>
                      ) : notes.length ? (
                        <span className="small" title={notes.map(ruleLabel).join(", ")}>
                          {ruleLabel(notes[0])}
                          {notes.length > 1 && <span className="muted"> +{notes.length - 1}</span>}
                          {!row.failed.length && <span className="muted"> (could not judge)</span>}
                        </span>
                      ) : (
                        <span className="muted small">None</span>
                      )}
                    </td>
                    <td>
                      <ActionTag action={row.action} />
                    </td>
                    <td>
                      {decided ? (
                        <Tag tone={STATES[decided.decision].tone}>{STATES[decided.decision].label}</Tag>
                      ) : (
                        <StateTag state={row.state} />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {error && <p className="panel-body">Could not load the queue: {error}</p>}
          {!error && !rows && <p className="panel-body muted">Loading invoices…</p>}
          {rows && visible.length === 0 && (
            <p className="panel-body muted">
              Nothing matches these filters.{" "}
              {view === "review" && !action && !finding && !query && "The queue is empty."}
            </p>
          )}
        </div>
      </section>
    </>
  );
}
