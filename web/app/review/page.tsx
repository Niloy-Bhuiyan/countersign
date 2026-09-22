"use client";

import { Inbox, Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, useDecisions, useJson, useWorkspace } from "@/components/api";
import CaseView, { type CaseDetail } from "@/components/CaseView";
import { shortIssue, shortLabel, statusOf } from "@/components/explain";
import { compareDecimal, money } from "@/components/format";
import { Empty } from "@/components/ui";

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

type View = "attention" | "ready" | "decided" | "mine" | "all";

const VIEWS: { key: View; label: string; help: string }[] = [
  { key: "attention", label: "To check", help: "Something is wrong or unclear. Biggest amounts first." },
  { key: "ready", label: "Ready", help: "Passed all four checks. Each still needs a person to approve it." },
  { key: "decided", label: "Decided", help: "Invoices you've approved, held or escalated in this workspace." },
  { key: "mine", label: "My tests", help: "Invoices you created or uploaded on the Try it page." },
  { key: "all", label: "All", help: "Every invoice in the demo." },
];

const TOUR = [
  "Pick an invoice. What's wrong with it is shown in plain words.",
  "Red dot: a problem. Amber: unsure. Green: fine.",
  "Scroll down to approve, hold or escalate. Every decision is signed and kept.",
];

const TOUR_KEY = "countersign.tour.review";

function Tour() {
  const [step, setStep] = useState<number | null>(null);
  useEffect(() => {
    try {
      setStep(window.localStorage.getItem(TOUR_KEY) ? null : 0);
    } catch {
      setStep(0);
    }
  }, []);
  const done = () => {
    try {
      window.localStorage.setItem(TOUR_KEY, "done");
    } catch {
      /* not remembered */
    }
    setStep(null);
  };
  if (step === null) return null;
  return (
    <section className="tour" aria-label="Quick guide">
      <p>{TOUR[step]}</p>
      <div className="row">
        <span className="dots" aria-hidden>{TOUR.map((_, i) => <i key={i} className={i === step ? "on" : ""} />)}</span>
        <button className="btn btn-sm" onClick={done}>Skip</button>
        {step < TOUR.length - 1
          ? <button className="btn btn-primary btn-sm" onClick={() => setStep(step + 1)}>Next</button>
          : <button className="btn btn-primary btn-sm" onClick={done}>Got it</button>}
      </div>
    </section>
  );
}

/** Once decided, the list says what was decided; before that, the main problem. */
function decisionWord(label: string, issue: string): string {
  return ["Approved", "On hold", "Escalated"].includes(label) ? `${label} · ${issue}` : issue;
}

function Review() {
  const router = useRouter();
  const params = useSearchParams();
  const selectedId = params.get("id");
  const ws = useWorkspace();
  const { data: corpus, error } = useJson<Row[]>("/data/queue.json");
  const { data: decisions, reload: reloadDecisions } = useDecisions(ws);
  const [mine, setMine] = useState<Row[]>([]);
  const [view, setView] = useState<View>("attention");
  const [query, setQuery] = useState("");
  const [issue, setIssue] = useState("");
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

  const issues = useMemo(() => {
    const keys = new Set<string>();
    rows.forEach((r) => [...r.failed, ...r.abstained].forEach((k) => keys.add(k)));
    return [...keys].sort((a, b) => shortLabel(a).localeCompare(shortLabel(b)));
  }, [rows]);

  const inView = useCallback(
    (r: Row, v: View) => {
      const decided = Boolean(current[r.id]);
      if (v === "attention") return r.state === "needs_review" && !decided;
      if (v === "ready") return r.state === "cleared" && !decided;
      if (v === "decided") return decided;
      if (v === "mine") return mineIds.has(r.id);
      return true;
    },
    [current, mineIds],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows
      .filter((r) => inView(r, view))
      .filter((r) => !issue || r.failed.includes(issue) || r.abstained.includes(issue))
      .filter((r) => !q || [r.id, r.number, r.vendor, r.po].some((f) => f?.toLowerCase().includes(q)))
      .sort((a, b) => (view === "mine" || view === "decided" ? 0 : compareDecimal(b.total, a.total)));
  }, [rows, view, issue, query, inView]);

  const counts = useMemo(
    () => Object.fromEntries(VIEWS.map((v) => [v.key, rows.filter((r) => inView(r, v.key)).length])) as Record<View, number>,
    [rows, inView],
  );

  const select = useCallback(
    (id: string) => {
      const next = new URLSearchParams(window.location.search);
      next.set("id", id);
      router.replace(`/review/?${next.toString()}`, { scroll: false });
      setPreset(null);
    },
    [router],
  );

  useEffect(() => {
    if (!selectedId && visible.length) select(visible[0].id);
  }, [selectedId, visible, select]);

  const isMine = selectedId ? mineIds.has(selectedId) : false;

  useEffect(() => {
    if (!selectedId || (!corpus && !isMine)) return;
    let live = true;
    setDetailError(null);
    const path = isMine && ws ? `/api/workspaces/${ws}/cases/${selectedId}` : `/data/case/${selectedId}.json`;
    api<CaseDetail>(path).then((d) => live && setDetail(d)).catch((e: Error) => live && setDetailError(e.message));
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
      } else if (["a", "h", "e"].includes(event.key)) {
        setPreset(event.key === "a" ? "approved" : event.key === "h" ? "held" : "escalated");
        document.getElementById("decide")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, selectedId, select]);

  useEffect(() => {
    list.current?.querySelector('[aria-current="true"]')?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);

  const events = (decisions?.log ?? []).filter((e) => e.invoice_id === selectedId);
  const docUrl = detail ? (isMine && ws ? `/api/workspaces/${ws}/files/${detail.file}` : `/documents/${detail.file}`) : "";

  return (
    <div className="review">
      <aside className="card list-card" aria-label="Invoices">
        <div className="list-head">
          <h1>Invoices</h1>
          <div className="tabs" role="group" aria-label="Show">
            {VIEWS.map((v) => (
              <button key={v.key} className="tab" aria-pressed={view === v.key} onClick={() => setView(v.key)} title={v.help}>
                {v.label} <span className="count">{counts[v.key]}</span>
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <label className="search">
              <span className="sr-only">Search invoices</span>
              <Search size={16} aria-hidden />
              <input ref={search} className="input" type="search" placeholder="Search"
                value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
            <select className="select" aria-label="Filter by issue" value={issue} onChange={(e) => setIssue(e.target.value)} style={{ flex: "1 1 150px" }}>
              <option value="">Any problem</option>
              {issues.map((k) => <option key={k} value={k}>{shortLabel(k)}</option>)}
            </select>
          </div>
        </div>
        <div className="list" ref={list}>
          {visible.map((r) => {
            const status = statusOf(r, current[r.id]?.decision);
            return (
              <button key={r.id} className="item" aria-current={r.id === selectedId} onClick={() => select(r.id)}>
                <span className={`dot dot-${status.tone}`} aria-hidden />
                <span className="who">{r.vendor ?? "Unreadable document"}</span>
                <span className="amt">{r.total ? money(r.total) : "—"}</span>
                <span className="issue">
                  <span className="sr-only">{status.label}: </span>
                  {decisionWord(status.label, shortIssue(r.failed, r.abstained, r.reason))}
                </span>
              </button>
            );
          })}
          {corpus && visible.length === 0 && (
            <Empty icon={Inbox} title={view === "mine" ? "No test invoices yet" : "Nothing here"}>
              <p className="small">
                {view === "mine"
                  ? "Create one on the “Try it yourself” page and it will appear here."
                  : view === "decided"
                    ? "Decisions you make will be listed here."
                    : "No invoices match your search."}
              </p>
              {view === "mine" && <a className="btn btn-primary btn-sm" href="/lab/">Try it yourself</a>}
            </Empty>
          )}
          {error && <p className="error-box" style={{ margin: 16 }}>Couldn&rsquo;t load invoices: {error}</p>}
          {!corpus && !error && <p className="small muted" style={{ padding: 16 }}>Loading invoices…</p>}
        </div>
        <div className="list-foot">
          <span><kbd>j</kbd> <kbd>k</kbd> move</span>
          <span><kbd>/</kbd> search</span>
          <span><kbd>a</kbd> <kbd>h</kbd> <kbd>e</kbd> decide</span>
        </div>
      </aside>

      <main className="detail" style={{ gap: 16 }}>
        <Tour />
        {detail && detail.id === selectedId ? (
          <CaseView c={detail} ws={ws} events={events} documentUrl={docUrl} preset={preset} onDecided={reloadDecisions} />
        ) : (
          <div className="card">
            <Empty icon={Inbox} title={detailError ? "Couldn't open this invoice" : "Pick an invoice"}>
              <p className="small">{detailError ?? "Choose one from the list to see its checks."}</p>
            </Empty>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<p className="page muted">Loading…</p>}>
      <Review />
    </Suspense>
  );
}
