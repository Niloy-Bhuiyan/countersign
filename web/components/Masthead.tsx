"use client";

import { Check, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { shareLink, useWorkspace } from "./api";
import { CHECK_ORDER, CHECKS, TERMS } from "./explain";

const TABS = [
  { href: "/review/", label: "Review" },
  { href: "/lab/", label: "Try it" },
  { href: "/decisions/", label: "History" },
  { href: "/dashboard/", label: "Reports" },
  { href: "/method/", label: "Accuracy" },
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
          <h2 id="help-title">Help</h2>
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
          <span className="brand-mark"><Check size={15} strokeWidth={3} aria-hidden /></span>
          <span className="word">Countersign</span>
        </Link>
        <nav className="nav" aria-label="Main">
          {TABS.map(({ href, label }) => (
            <Link key={href} href={href} aria-current={current(href) ? "page" : undefined}>
              {label}
            </Link>
          ))}
        </nav>
        <div className="header-end">
          {ws && (
            <button className="btn btn-ghost btn-sm hide-sm" onClick={copy} title="Copy a link to your workspace">
              {copied ? "Link copied" : "Share"}
            </button>
          )}
          <button className="btn btn-sm" onClick={() => setHelp(true)} aria-haspopup="dialog">
            Help
          </button>
          <Link className="btn btn-primary btn-sm hide-sm" href="/review/">Open review</Link>
        </div>
      </header>
      {help && <HelpPanel onClose={() => setHelp(false)} />}
    </>
  );
}
