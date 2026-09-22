"use client";

import { ArrowRight, CheckCircle2, CircleHelp, Download, FileUp, FlaskConical } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { api, useWorkspace } from "@/components/api";
import type { CaseDetail } from "@/components/CaseView";
import { findingSentence, MISTAKES, NEXT_STEP, REASONS, statusOf } from "@/components/explain";
import { money } from "@/components/format";
import { Stamp } from "@/components/motion";
import { Empty, StatusPill } from "@/components/ui";

type Options = {
  vendors: { id: string; name: string; category: string; items: string[]; historyReady: boolean }[];
  tampers: { id: string; label: string; effect: string; expect: string }[];
};

type Outcome = CaseDetail & { scenario?: { tamper: string; label: string; expect: string } };

function Result({ c, ws }: { c: Outcome; ws: string }) {
  const tamper = c.scenario?.tamper ?? null;
  const target = MISTAKES.find((m) => m.id === tamper)?.target ?? null;
  const found = c.results.filter((r) => r.outcome === "failed");
  const unsure = c.results.filter((r) => r.outcome === "abstained");
  const keys = found.map((r) => `${r.check_code}/${r.rule}`);
  const caught = target === "cleared" ? c.state === "cleared" : target ? keys.includes(target) : null;
  const unreadable = c.reason && c.reason !== "check_findings";

  return (
    <div className="stack">
      {caught !== null && (
        <div className={`callout${caught ? " callout-ok strong" : ""}`}>
          {caught ? <CheckCircle2 size={22} aria-hidden /> : <CircleHelp size={22} color="var(--warn)" aria-hidden />}
          <div>
            <h4>
              {target === "cleared"
                ? caught ? "Correct. It passed every check." : "The correct invoice was sent for review."
                : caught ? "Caught it." : "Not caught by the expected check."}
            </h4>
            {!caught && <p>{c.scenario?.expect}</p>}
          </div>
          {caught && <Stamp className="stamp-on-ink" size={88} tone="paper" word={target === "cleared" ? "PASSED" : "CAUGHT"} />}
        </div>
      )}

      <div className="card card-pad stack">
        <div style={{ display: "flex", gap: 12, alignItems: "start", flexWrap: "wrap" }}>
          <div style={{ minWidth: 0 }}>
            <h3 style={{ fontSize: 20, letterSpacing: "-0.02em" }}>{c.vendor ?? "Unknown supplier"}</h3>
            <p className="small muted">
              <span className="mono">{c.number ?? "unreadable"}</span> · {c.total ? `${c.currency} ${money(c.total)}` : "no total"}
            </p>
          </div>
          <div style={{ marginLeft: "auto" }}><StatusPill status={statusOf(c)} /></div>
        </div>
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 8 }}>
          {unreadable && <li className="small"><span className="dot dot-warn" aria-hidden /> {REASONS[c.reason!]?.long}</li>}
          {found.map((r, i) => (
            <li key={i} style={{ display: "flex", gap: 10, alignItems: "baseline" }}><span className="dot dot-bad" aria-hidden />{findingSentence(r)}</li>
          ))}
          {unsure.map((r, i) => (
            <li key={`u${i}`} style={{ display: "flex", gap: 10, alignItems: "baseline" }}><span className="dot dot-warn" aria-hidden />{findingSentence(r)}</li>
          ))}
          {!unreadable && !found.length && !unsure.length && (
            <li style={{ display: "flex", gap: 10, alignItems: "baseline" }}><span className="dot dot-ok" aria-hidden />All four checks passed.</li>
          )}
        </ul>
        <div className="verdict-row">
          <div className="verdict-box"><div className="l">Suggested</div><div className="v">{NEXT_STEP[c.action]?.what}</div></div>
          <div className="verdict-box"><div className="l">Saved to</div><div className="v">Review · My tests</div></div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link className="btn btn-primary" href={`/review/?id=${c.id}`}>Open in review <ArrowRight size={16} aria-hidden /></Link>
          <a className="btn" href={`/api/workspaces/${ws}/files/${c.file}`}><Download size={16} aria-hidden /> {c.format.toUpperCase()}</a>
        </div>
      </div>
    </div>
  );
}

export default function Lab() {
  const ws = useWorkspace();
  const [options, setOptions] = useState<Options | null>(null);
  const [vendor, setVendor] = useState("");
  const [tamper, setTamper] = useState("overbill");
  const [busy, setBusy] = useState<"lab" | "upload" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [over, setOver] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("t");
    if (t && MISTAKES.some((m) => m.id === t)) setTamper(t);
  }, []);

  useEffect(() => {
    if ((outcome || error) && window.innerWidth <= 1100) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [outcome, error]);

  useEffect(() => {
    api<Options>("/api/lab/options")
      .then((o) => {
        setOptions(o);
        setVendor(o.vendors[0]?.id ?? "");
      })
      .catch((e: Error) => setError(`The test service isn't responding: ${e.message}`));
  }, []);

  const chosen = useMemo(() => options?.vendors.find((v) => v.id === vendor), [options, vendor]);
  const mistakes = MISTAKES.filter((m) => !options || options.tampers.some((t) => t.id === m.id));
  const mistake = MISTAKES.find((m) => m.id === tamper);

  async function issue() {
    if (!ws) return;
    setBusy("lab");
    setError(null);
    setOutcome(null);
    try {
      setOutcome(await api<Outcome>(`/api/workspaces/${ws}/lab`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ vendorId: vendor, tamper }),
      }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function upload(f: File | undefined) {
    if (!ws || !f) return;
    setBusy("upload");
    setError(null);
    setOutcome(null);
    const form = new FormData();
    form.append("file", f);
    try {
      setOutcome(await api<Outcome>(`/api/workspaces/${ws}/documents`, { method: "POST", body: form }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
      if (file.current) file.current.value = "";
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Try it yourself</h1>
          <p>Plant a mistake in a real PDF invoice and see if it gets caught.</p>
        </div>
      </div>

      <div className="lab">
        <div className="stack">
          <section className="card card-pad">
            <div className="step-label">Mistake</div>
            <div className="chips" role="group" aria-label="Mistake">
              {mistakes.map((m) => (
                <button key={m.id} className="chip" aria-pressed={tamper === m.id}
                  onClick={() => setTamper(m.id)}>
                  {m.label}
                </button>
              ))}
            </div>
            {mistake && <p className="chip-body">{mistake.effect}</p>}
          </section>

          <section className="card card-pad">
            <div className="step-label">Supplier</div>
            <select className="select" style={{ width: "100%" }} value={vendor} onChange={(e) => setVendor(e.target.value)} disabled={!options} aria-label="Supplier">
              {options?.vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.name}{v.historyReady ? "" : " (little price history)"}</option>
              ))}
            </select>
            {chosen && <p className="hint" style={{ marginTop: 10, paddingLeft: 4 }}>{chosen.category}</p>}
            <button className="btn btn-primary btn-lg" style={{ width: "100%", marginTop: 20 }} onClick={issue} disabled={!options || !ws || busy !== null}>
              {busy === "lab" ? <span className="spinner" aria-hidden /> : null}
              {busy === "lab" ? "Checking…" : "Create and check"}
            </button>
          </section>

          <label className="dropzone" data-over={over}
            onDragOver={(e) => (e.preventDefault(), setOver(true))}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); upload(e.dataTransfer.files[0]); }}>
            <input ref={file} type="file" accept=".pdf,.xlsx,.csv" hidden onChange={(e) => upload(e.target.files?.[0])} />
            {busy === "upload" ? <span className="spinner" aria-hidden /> : <FileUp size={22} aria-hidden />}
            <span style={{ fontWeight: 500 }}>{busy === "upload" ? "Checking…" : "Or drop your own invoice"}</span>
            <span className="hint">PDF, Excel or CSV · up to 4 MB</span>
          </label>
        </div>

        <section aria-live="polite" ref={resultRef} className="lab-result">
          {error && <p className="error-box" role="alert">{error}</p>}
          {outcome && ws ? (
            <Result c={outcome} ws={ws} />
          ) : (
            !error && (
              <div className="card">
                <Empty icon={FlaskConical} title="Your result shows here" />
              </div>
            )
          )}
        </section>
      </div>
    </div>
  );
}
