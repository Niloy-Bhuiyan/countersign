"use client";

import {
  BarChart3,
  BookOpen,
  CircleHelp,
  FileCheck2,
  FlaskConical,
  History,
  Home,
  Inbox,
  Link2,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { shareLink, useWorkspace } from "./api";
import { CHECK_ORDER, CHECKS, TERMS } from "./explain";

const TABS = [
  { href: "/", label: "Overview", icon: Home },
  { href: "/review/", label: "Review invoices", icon: Inbox },
  { href: "/lab/", label: "Try it yourself", icon: FlaskConical },
  { href: "/decisions/", label: "Decision history", icon: History },
  { href: "/dashboard/", label: "Reports", icon: BarChart3 },
  { href: "/method/", label: "How accurate?", icon: BookOpen },
];

function HelpPanel({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="scrim" onClick={onClose} aria-hidden />
      <aside className="panel" role="dialog" aria-modal="true" aria-labelledby="help-title">
        <div className="panel-head">
          <CircleHelp size={20} className="muted" aria-hidden />
          <h2 id="help-title">Help and glossary</h2>
          <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto" }} onClick={onClose} aria-label="Close help">
            <X size={18} aria-hidden />
          </button>
        </div>
        <div className="panel-body">
          <div className="term">
            <h3>What is Countersign?</h3>
            <p>
              A tool that checks supplier invoices before they are paid. It reads each invoice, compares it with what we
              ordered and what arrived, flags anything wrong, and waits for a person to approve it. Nothing is ever paid
              automatically.
            </p>
          </div>
          <div className="term">
            <h3>The four checks</h3>
            {CHECK_ORDER.map((code) => (
              <p key={code}>
                <b>{CHECKS[code].name}.</b> {CHECKS[code].plain}
              </p>
            ))}
          </div>
          {TERMS.map((t) => (
            <div className="term" key={t.term}>
              <h3>{t.term}</h3>
              <p>{t.means}</p>
            </div>
          ))}
          <div className="term">
            <h3>Keyboard shortcuts</h3>
            <p>
              On the review page: <kbd>j</kbd> / <kbd>k</kbd> next and previous invoice, <kbd>/</kbd> search,{" "}
              <kbd>a</kbd> approve, <kbd>h</kbd> hold, <kbd>e</kbd> escalate.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}

export default function Masthead() {
  const path = usePathname();
  const ws = useWorkspace();
  const [help, setHelp] = useState(false);
  const [copied, setCopied] = useState(false);

  const current = (href: string) =>
    href === "/" ? path === "/" : path.startsWith(href.replace(/\/$/, ""));

  async function copy() {
    if (!ws) return;
    try {
      await navigator.clipboard.writeText(shareLink(ws));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.prompt("Copy this link to open your workspace elsewhere:", shareLink(ws));
    }
  }

  return (
    <>
      <header className="header">
        <Link href="/" className="brand" aria-label="Countersign home">
          <span className="brand-mark"><FileCheck2 size={18} aria-hidden /></span>
          Countersign
        </Link>
        <nav className="nav" aria-label="Main">
          {TABS.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} aria-current={current(href) ? "page" : undefined} title={label}>
              <Icon size={16} aria-hidden />
              <span className="label">{label}</span>
            </Link>
          ))}
        </nav>
        <div className="header-end">
          <span className="demo-pill" title="Every supplier and invoice here is made up. No real company is involved.">
            Demo · made-up data
          </span>
          {ws && (
            <button className="btn btn-ghost btn-sm" onClick={copy} title="Copy a link to your workspace">
              <Link2 size={15} aria-hidden /> {copied ? "Link copied" : "Share"}
            </button>
          )}
          <button className="btn btn-sm" onClick={() => setHelp(true)} aria-haspopup="dialog">
            <CircleHelp size={15} aria-hidden /> Help
          </button>
        </div>
      </header>
      {help && <HelpPanel onClose={() => setHelp(false)} />}
    </>
  );
}
