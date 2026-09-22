/**
 * Every status is a glyph and a word. Colour follows the word and never carries the
 * meaning alone, so the console reads the same in greyscale and to a screen reader.
 */

type Kind = "ok" | "bad" | "hold" | "plain";

export const ACTIONS: Record<string, { label: string; verdict: string; kind: Kind }> = {
  CLEAR_FOR_PAYMENT: { label: "Clear", verdict: "Clear for payment", kind: "ok" },
  HOLD_REQUEST_CREDIT_NOTE: { label: "Credit note", verdict: "Hold and request a credit note", kind: "hold" },
  HOLD_REQUEST_DELIVERY_PROOF: { label: "Delivery proof", verdict: "Hold and request proof of delivery", kind: "hold" },
  ESCALATE_TO_CONTROLLER: { label: "Escalate", verdict: "Escalate to the controller", kind: "bad" },
  REVIEW_MANUALLY: { label: "Manual review", verdict: "Review manually", kind: "plain" },
};

export const DECISION_LABEL: Record<string, { stamp: string; phrase: string; kind: Kind }> = {
  approved: { stamp: "Countersigned", phrase: "Approved for payment", kind: "ok" },
  held: { stamp: "Held", phrase: "Held pending the vendor", kind: "hold" },
  escalated: { stamp: "Escalated", phrase: "Escalated to the controller", kind: "bad" },
};

export const REASONS: Record<string, string> = {
  check_findings: "Check findings",
  extraction_failed: "Could not be read reliably",
  quarantined_image_only: "Scanned image, no text layer",
  quarantined_unreadable: "Corrupt file",
  quarantined_encrypted: "Password protected",
  vendor_not_on_master: "Vendor not on the vendor master",
  vendor_ambiguous: "Vendor ambiguous",
  vendor_tax_id_mismatch: "Tax ID contradicts the name",
};

export const RULES: Record<string, string> = {
  "THREE_WAY_MATCH/price_above_order": "Price above the order",
  "THREE_WAY_MATCH/quantity_over_received": "Billed more than received",
  "THREE_WAY_MATCH/no_delivery": "No delivery recorded",
  "THREE_WAY_MATCH/currency": "Currency differs from the order",
  "THREE_WAY_MATCH/po_not_found": "Order not found",
  "THREE_WAY_MATCH/po_other_vendor": "Order belongs to another vendor",
  "THREE_WAY_MATCH/line_unmatched": "Line not on the order",
  "THREE_WAY_MATCH/order_has_unread_document": "Order has an unread document",
  "PRICE_VARIANCE/above_history": "Price above the vendor's history",
  "PRICE_VARIANCE/insufficient_history": "Too little price history",
  "PRICE_VARIANCE/zero_spread": "No price spread to judge",
  "PRICE_VARIANCE/no_order": "No order to date the history",
  "DUPLICATE_INVOICE/same_number": "Invoice number already used",
  "DUPLICATE_INVOICE/same_bytes": "Identical file received before",
  "DUPLICATE_INVOICE/same_order_same_amount": "Same order, same amount",
  "TAX_ARITHMETIC/tax_total": "Tax does not recompute",
  "TAX_ARITHMETIC/no_rate": "No tax rate available",
};

export const CHECKS: Record<string, string> = {
  THREE_WAY_MATCH: "Three-way match",
  PRICE_VARIANCE: "Price variance",
  DUPLICATE_INVOICE: "Duplicate",
  TAX_ARITHMETIC: "Tax arithmetic",
};

export function ruleLabel(key: string): string {
  return RULES[key] ?? key;
}

/** Tick, cross, query, dash: the marks an auditor puts in a margin. */
export function Glyph({ kind, size = 14 }: { kind: "passed" | "failed" | "abstained" | Kind; size?: number }) {
  const k = kind === "passed" ? "ok" : kind === "failed" ? "bad" : kind === "abstained" ? "plain" : kind;
  const common = { width: size, height: size, viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", strokeWidth: 1.8, "aria-hidden": true as const };
  if (k === "ok")
    return (
      <svg {...common}>
        <path d="M3 8.5l3.2 3L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (k === "bad")
    return (
      <svg {...common}>
        <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
      </svg>
    );
  if (k === "hold")
    return (
      <svg {...common}>
        <path d="M5.5 3.5v9M10.5 3.5v9" strokeLinecap="round" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="M6 6.2a2 2 0 113 1.7c-.7.4-1 .8-1 1.6M8 12v.2" strokeLinecap="round" />
    </svg>
  );
}

export function Mark({ kind, children }: { kind: Kind; children: React.ReactNode }) {
  return (
    <span className={`mark mark-${kind}`}>
      <Glyph kind={kind} size={13} />
      {children}
    </span>
  );
}

export function ActionMark({ action }: { action: string }) {
  const a = ACTIONS[action] ?? { label: action, kind: "plain" as Kind };
  return <Mark kind={a.kind}>{a.label}</Mark>;
}

export function DecisionMark({ decision }: { decision: string }) {
  const d = DECISION_LABEL[decision];
  return d ? <Mark kind={d.kind}>{d.stamp}</Mark> : null;
}
