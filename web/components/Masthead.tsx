"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { shareLink, useWorkspace } from "./api";

const TABS = [
  { href: "/", label: "Review" },
  { href: "/lab/", label: "Invoice lab" },
  { href: "/decisions/", label: "Decisions" },
  { href: "/dashboard/", label: "Controller" },
  { href: "/method/", label: "Method" },
];

export default function Masthead() {
  const path = usePathname();
  const ws = useWorkspace();
  const [copied, setCopied] = useState(false);

  const current = (href: string) =>
    href === "/" ? path === "/" || path.startsWith("/case") : path.startsWith(href.replace(/\/$/, ""));

  async function copy() {
    if (!ws) return;
    try {
      await navigator.clipboard.writeText(shareLink(ws));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.prompt("Copy this link to open the same workspace elsewhere:", shareLink(ws));
    }
  }

  return (
    <header className="masthead">
      <Link href="/" className="wordmark" aria-label="Countersign review">
        <b>Countersign</b>
        <span>Accounts payable</span>
      </Link>
      <nav className="tabs" aria-label="Main">
        {TABS.map((tab) => (
          <Link key={tab.href} href={tab.href} aria-current={current(tab.href) ? "page" : undefined}>
            {tab.label}
          </Link>
        ))}
      </nav>
      <div className="masthead-end">
        <span className="synthetic" title="No real vendor, company or transaction appears in this data.">
          Synthetic data
        </span>
        {ws && (
          <span className="workspace-chip" title="Your uploads, lab invoices and decisions are stored under this workspace.">
            Workspace <span className="id">{ws.slice(0, 6)}</span>
            <button className="link-button" onClick={copy}>
              {copied ? "Link copied" : "Share"}
            </button>
          </span>
        )}
      </div>
    </header>
  );
}
