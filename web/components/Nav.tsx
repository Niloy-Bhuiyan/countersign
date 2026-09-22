"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Review queue" },
  { href: "/dashboard/", label: "Controller view" },
  { href: "/method/", label: "How it works" },
];

export default function Nav() {
  const path = usePathname();
  const current = (href: string) =>
    href === "/" ? path === "/" || path.startsWith("/case") : path.startsWith(href.replace(/\/$/, ""));

  return (
    <header className="topbar">
      <Link href="/" className="brand" aria-label="Countersign, review queue">
        <span className="brand-mark" aria-hidden="true" />
        Countersign
      </Link>
      <nav className="nav" aria-label="Main">
        {LINKS.map((link) => (
          <Link key={link.href} href={link.href} aria-current={current(link.href) ? "page" : undefined}>
            {link.label}
          </Link>
        ))}
      </nav>
      <div className="topbar-right">
        <span className="synthetic" title="No real vendor, company or transaction appears in this data.">
          Synthetic data, no real companies
        </span>
        <a href="https://github.com/Niloy-Bhuiyan/countersign" className="small">
          Source
        </a>
      </div>
    </header>
  );
}
