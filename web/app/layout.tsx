import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Masthead from "@/components/Masthead";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist", display: "swap" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Countersign — check supplier invoices before you pay",
  description:
    "Countersign reads supplier invoices, checks them against purchase orders and deliveries, flags problems in plain language, and waits for a person to approve. Demo with made-up data.",
};

const REPO = "https://github.com/Niloy-Bhuiyan/countersign";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geist.variable} ${mono.variable}`}>
      <body>
        <Masthead />
        {children}
        <footer className="foot">
          <span>Countersign · demo with made-up data</span>
          <a href={REPO}>Source</a>
          <a href="/api/docs">API</a>
          <a href="/method/">Accuracy</a>
          <span className="end">Nothing here is ever paid.</span>
        </footer>
      </body>
    </html>
  );
}
