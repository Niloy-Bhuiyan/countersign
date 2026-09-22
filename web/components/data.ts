"use client";

import { useEffect, useState } from "react";

export type QueueRow = {
  id: string;
  file: string;
  format: string;
  number: string | null;
  vendor: string | null;
  vendorId: string | null;
  po: string | null;
  issued: string | null;
  currency: string | null;
  total: string | null;
  category: string | null;
  state: string;
  reason: string | null;
  action: string;
  failed: string[];
  abstained: string[];
};

export type Decision = { decision: "approved" | "held" | "escalated"; note: string; at: string };

export function useJson<T>(path: string | null): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setData(null);
    setError(null);
    fetch(path)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} loading ${path}`);
        return response.json();
      })
      .then((json) => live && setData(json))
      .catch((err: Error) => live && setError(err.message));
    return () => {
      live = false;
    };
  }, [path]);
  return { data, error };
}

const KEY = "countersign.decisions.v1";

/**
 * Demo decisions live in this browser only. The deployed console is read-only: there
 * is no server to record an approval, and pretending otherwise would misstate what
 * the system does.
 */
export function readDecisions(): Record<string, Decision> {
  try {
    return JSON.parse(window.localStorage.getItem(KEY) ?? "{}");
  } catch {
    return {};
  }
}

export function writeDecision(id: string, decision: Decision | null): Record<string, Decision> {
  const all = readDecisions();
  if (decision) all[id] = decision;
  else delete all[id];
  try {
    window.localStorage.setItem(KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable: the decision simply is not remembered */
  }
  return all;
}
