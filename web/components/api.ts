"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * A workspace is where a reviewer's uploads, lab invoices and decisions live on the
 * server. It is created on first visit, kept in this browser, and carried in the URL
 * (?ws=) so the same workspace opens on another device or for a colleague.
 */

const KEY = "countersign.workspace";
const NAME_KEY = "countersign.reviewer";
const PATTERN = /^[a-z0-9]{8,32}$/;

function freshId(): string {
  const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
}

function safeGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable: the workspace still works for this tab */
  }
}

export function useWorkspace(): string | null {
  const [ws, setWs] = useState<string | null>(null);
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("ws");
    const id = fromUrl && PATTERN.test(fromUrl) ? fromUrl : safeGet(KEY) ?? freshId();
    safeSet(KEY, id);
    setWs(id);
  }, []);
  return ws;
}

export function shareLink(ws: string): string {
  const url = new URL(window.location.href);
  url.searchParams.set("ws", ws);
  return url.toString();
}

export function readReviewer(): string {
  return safeGet(NAME_KEY) ?? "";
}

export function saveReviewer(name: string): void {
  safeSet(NAME_KEY, name);
}

export class ApiError extends Error {}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.");
  }
  if (!response.ok) {
    let detail =
      response.status >= 500
        ? "Something went wrong on the server. Try again in a moment."
        : `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail.charAt(0).toUpperCase() + detail.slice(1));
  }
  return response.json() as Promise<T>;
}

export type DecisionEvent = {
  invoice_id: string;
  decision: "approved" | "held" | "escalated" | "withdrawn";
  from_state: string;
  reviewer: string;
  note: string;
  recommended_action: string;
  overrules_recommendation: boolean;
  at: string;
  seq: number;
};

export type Decisions = { current: Record<string, DecisionEvent>; log: DecisionEvent[] };

/** Load, and reload on demand, the workspace's decisions. */
export function useDecisions(ws: string | null) {
  const [data, setData] = useState<Decisions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(() => {
    if (!ws) return;
    api<Decisions>(`/api/workspaces/${ws}/decisions`)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [ws]);
  useEffect(reload, [reload]);
  return { data, error, reload };
}

export function useJson<T>(path: string | null): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!path) return;
    let live = true;
    setData(null);
    setError(null);
    fetch(path)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} loading ${path}`);
        return r.json();
      })
      .then((json) => live && setData(json))
      .catch((e: Error) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [path]);
  return { data, error };
}
