"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, useDecisions, useJson, useWorkspace } from "@/components/api";
import CaseView, { type CaseDetail } from "@/components/CaseView";
import { compact, compareDecimal, date, money } from "@/components/format";
import { ActionMark, DecisionMark, REASONS, ruleLabel } from "@/components/labels";

type Row = {
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
  origin?: string;
};

type View = "awaiting" | "cleared" | "decided" | "workspace" | "all";

const VIEWS: { key: View; label: string }[] = [
  { key: "awaiting", label: "Awaiting" },
  { key: "cleared", label: "Cleared" },
  { key: "decided", label: "Decided" },
  { key: "workspace", label: "Mine" },
  { key: "all", label: "All" },
];

function sumBDT(rows: Row[]): string {
  // Integer paisa via BigInt: the headline total is exact, like every other figure.
  let paisa = 0n;
  for (const r of rows) {
    if (r.currency !== "BDT" || !r.total) continue;
    const [w, f = ""] = r.total.split(".");
    paisa += BigInt(w + f.padEnd(2, "0").slice(0, 2));
  }
  const s = paisa.toString().padStart(3, "0");
  return `${s.slice(0, -2)}.${s.slice(-2)}`;
}

function Review() {
  const router = useRouter();
  const params = useSearchParams();
  const selectedId = params.get("id");
  const ws = useWorkspace();
  const { data: corpus, error } = useJson<Row[]>("/data/queue.json");
  const { data: decisions, reload: reloadDecisions } = useDecisions(ws);
  const [mine, setMine] = useState<Row[]>([]);
  const [view, setView] = useState<View>("awaiting");
  const [query, setQuery] = useState("");
  const [finding, setFinding] = useState("");
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [preset, setPreset] = useState<"approved" | "held" | "escalated" | null>(null);
  const search = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ws) return;
    api<Row[]>(`/api/workspaces/${ws}/cases`).then(setMine).catch(() => setMine([]));
  }, [ws]);

  const mineIds = useMemo(() => new Set(mine.map((r) => r.id)), [mine]);
  const rows = useMemo(() => [...mine, ...(corpus ?? [])], [mine, corpus]);
  const current = decisions?.current ?? {};

  const findings = useMemo(() => {
    const keys = new Set<string>();
    rows.forEach((r) => [...r.failed, ...r.abstained].forEach((k) => keys.add(k)));
    return [...keys].sort((a, b) => ruleLabel(a).localeCompare(ruleLabel(b)));
  }, [rows]);

  const inView = useCallback(
    (r: Row, v: View) => {
      const decided = Boolean(current[r.id]);
      if (v === "awaiting") return r.state === "needs_review" && !decided;
      if (v === "cleared") return r.state === "cleared" && !decided;
      if (v === "decided") return decided;
      if (v === "workspace") return mineIds.has(r.id);
      return true;
    },
    [current, mineIds],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows
      .filter((r) => inView(r, view))
      .filter((r) => !finding || r.failed.includes(finding) || r.abstained.includes(finding))
      .filter((r) => !q || [r.id, r.number, r.vendor, r.po].some((f) => f?.toLowerCase().includes(q)))
      .sort((a, b) =>
        view === "workspace" || view === "decided" ? 0 : view === "cleared"
          ? (b.issued ?? "").localeCompare(a.issued ?? "")
          : compareDecimal(b.total, a.total),
      );
  }, [rows, view, finding, query, inView]);

  const counts = useMemo(
    () => Object.fromEntries(VIEWS.map((v) => [v.key, rows.filter((r) => inView(r, v.key)).length])) as Record<View, number>,
    [rows, inView],
  );
  const awaitingValue = useMemo(() => sumBDT(rows.filter((r) => inView(r, "awaiting"))), [rows, inView]);

  const select = useCallback(
    (id: string) => {
      const next = new URLSearchParams(window.location.search);
      next.set("id", id);
      router.replace(`/?${next.toString()}`, { scroll: false });
      setPreset(null);
    },
    [router],
  );

  useEffect(() => {
    if (!selectedId && visible.length) select(visible[0].id);
  }, [selectedId, visible, select]);

  const selectedRow = rows.find((r) => r.id === selectedId) ?? null;
  const isMine = selectedId ? mineIds.has(selectedId) : false;

  useEffect(() => {
    if (!selectedId || (!corpus && !isMine)) return;
    let live = true;
    setDetailError(null);
    const path = isMine && ws ? `/api/workspaces/${ws}/cases/${selectedId}` : `/data/case/${selectedId}.json`;
    api<CaseDetail>(path)
      .then((d) => live && setDetail(d))
      .catch((e: Error) => live && setDetailError(e.message));
    return () => {
      live = false;
    };
  }, [selectedId, isMine, ws, corpus]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const typing = (event.target as HTMLElement)?.closest("input, textarea, select");
      if (typing) {
        if (event.key === "Escape") (event.target as HTMLElement).blur();
        return;
      }
      const index = visible.findIndex((r) => r.id === selectedId);
      if (event.key === "/") {
        event.preventDefault();
        search.current?.focus();
      } else if ((event.key === "j" || event.key === "ArrowDown") && index < visible.length - 1) {
        event.preventDefault();
        select(visible[index + 1].id);
      } else if ((event.key === "k" || event.key === "ArrowUp") && index > 0) {
        event.preventDefault();
        select(visible[index - 1].id);
      } else if (event.key === "a") setPreset("approved");
      else if (event.key === "h") setPreset("held");
      else if (event.key === "e") setPreset("escalated");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, selectedId, select]);

  useEffect(() => {
    list.current?.querySelector('[aria-current="true"]')?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);

  const events = (decisions?.log ?? []).filter((e) => e.invoice_id === selectedId);
  const docUrl = detail
    ? isMine && ws
      ? `/api/workspaces/${ws}/files/${detail.file}`
      : `/documents/${detail.file}`
    : "";

  return (
    <div className="review">
      <aside className="ledger" aria-label="Invoices">
        <div className="ledger-head">
          <p className="ledger-summary">
            {corpus ? (
              <>
                <em>{counts.awaiting}</em> invoices await a decision, holding BDT {compact(awaitingValue)}.{" "}
                {counts.cleared} cleared every check and wait for a countersignature.
              </>
            ) : error ? (
              `Could not load the ledger: ${error}`
            ) : (
              "Loading the ledger…"
            )}
          </p>
          <div className="ledger-tools">
            <div className="switch" role="group" aria-label="Show">
              {VIEWS.map((v) => (
                <button key={v.key} aria-pressed={view === v.key} onClick={() => setView(v.key)}>
                  {v.label}
                  <span className="n">{counts[v.key]}</span>
                </button>
              ))}
            </div>
            <div className="row">
              <input ref={search} className="input" type="search" placeholder="Invoice, vendor or order"
                aria-label="Search" value={query} onChange={(e) => setQuery(e.target.value)} />
              <select className="select" aria-label="Finding" value={finding} onChange={(e) => setFinding(e.target.value)}
                style={{ maxWidth: 170 }}>
                <option value="">Any finding</option>
                {findings.map((k) => <option key={k} value={k}>{ruleLabel(k)}</option>)}
              </select>
            </div>
          </div>
        </div>

        <div className="ledger-list" ref={list}>
          {visible.map((r) => {
            const note = r.reason && r.reason !== "check_findings"
              ? REASONS[r.reason] ?? r.reason
              : r.failed.length
                ? ruleLabel(r.failed[0]) + (r.failed.length > 1 ? ` +${r.failed.length - 1}` : "")
                : r.abstained.length
                  ? `Could not judge: ${ruleLabel(r.abstained[0]).toLowerCase()}`
                  : "No findings";
            const decided = current[r.id];
            return (
              <button key={r.id} className="entry" aria-current={r.id === selectedId} onClick={() => select(r.id)}>
                <span className="id">
                  {r.number ?? r.id}{" "}
                  {r.origin && <span className="origin">{r.origin === "lab" ? "Lab" : "Upload"}</span>}
                </span>
                <span className="amount fig">{r.total ? money(r.total) : "—"}</span>
                <span className="who">{r.vendor ?? "Unread document"}</span>
                <span className="small muted fig">{date(r.issued)}</span>
                <span className="meta">
                  <span className={`finding${r.failed.length ? " red" : ""}`}>{note}</span>
                  {decided ? <DecisionMark decision={decided.decision} /> : <ActionMark action={r.action} />}
                </span>
              </button>
            );
          })}
          {corpus && visible.length === 0 && (
            <p className="paper-empty" style={{ height: "auto" }}>
              {view === "workspace"
                ? "Nothing of yours yet. Issue an invoice in the lab or upload one."
                : "Nothing matches."}
            </p>
          )}
        </div>
        <div className="ledger-foot">
          <span><kbd>j</kbd> <kbd>k</kbd> move</span>
          <span><kbd>a</kbd> <kbd>h</kbd> <kbd>e</kbd> decide</span>
          <span><kbd>/</kbd> search</span>
          <a href="/exports/countersign-lines.xlsx">Export XLSX</a>
        </div>
      </aside>

      <main className="paper">
        {detail && detail.id === selectedId ? (
          <div className="paper-inner">
            <CaseView c={detail} ws={ws} events={events} documentUrl={docUrl} preset={preset}
              onDecided={reloadDecisions} />
          </div>
        ) : (
          <div className="paper-empty">
            {detailError ? `Could not open ${selectedId}: ${detailError}` : selectedRow ? "Opening…" : "Select an invoice."}
          </div>
        )}
      </main>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<div className="paper-empty">Loading…</div>}>
      <Review />
    </Suspense>
  );
}
