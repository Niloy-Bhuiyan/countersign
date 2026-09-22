/**
 * Every status is a word first and a colour second. Colour never carries meaning alone.
 */

export type Tone = "ok" | "warn" | "bad" | "neutral";

export const ACTIONS: Record<string, { label: string; tone: Tone; short: string }> = {
  CLEAR_FOR_PAYMENT: { label: "Clear for payment", tone: "ok", short: "Clear" },
  HOLD_REQUEST_CREDIT_NOTE: { label: "Hold, request credit note", tone: "warn", short: "Credit note" },
  HOLD_REQUEST_DELIVERY_PROOF: { label: "Hold, request delivery proof", tone: "warn", short: "Delivery proof" },
  ESCALATE_TO_CONTROLLER: { label: "Escalate to controller", tone: "bad", short: "Escalate" },
  REVIEW_MANUALLY: { label: "Review manually", tone: "neutral", short: "Manual review" },
};

export const STATES: Record<string, { label: string; tone: Tone }> = {
  cleared: { label: "Cleared", tone: "ok" },
  needs_review: { label: "Needs review", tone: "warn" },
  approved: { label: "Approved", tone: "ok" },
  held: { label: "Held", tone: "warn" },
  escalated: { label: "Escalated", tone: "bad" },
};

export const REASONS: Record<string, string> = {
  check_findings: "Check findings",
  extraction_failed: "Could not be read reliably",
  quarantined_image_only: "Scanned image, no text",
  quarantined_unreadable: "Corrupt file",
  quarantined_encrypted: "Password protected",
  vendor_not_on_master: "Vendor not on master",
  vendor_ambiguous: "Vendor ambiguous",
  vendor_tax_id_mismatch: "Tax ID contradicts name",
};

export const RULES: Record<string, string> = {
  "THREE_WAY_MATCH/price_above_order": "Price above order",
  "THREE_WAY_MATCH/quantity_over_received": "Billed more than received",
  "THREE_WAY_MATCH/no_delivery": "No delivery recorded",
  "THREE_WAY_MATCH/currency": "Currency differs from order",
  "THREE_WAY_MATCH/po_not_found": "Order not found",
  "THREE_WAY_MATCH/po_other_vendor": "Order belongs to another vendor",
  "THREE_WAY_MATCH/line_unmatched": "Line not on order",
  "THREE_WAY_MATCH/order_has_unread_document": "Order has an unread document",
  "PRICE_VARIANCE/above_history": "Price above vendor history",
  "PRICE_VARIANCE/insufficient_history": "Too little price history",
  "PRICE_VARIANCE/zero_spread": "No price spread to judge",
  "PRICE_VARIANCE/no_order": "No order to date history",
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

export function Tag({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return <span className={`tag tag-${tone}`}>{children}</span>;
}

export function ActionTag({ action }: { action: string }) {
  const a = ACTIONS[action] ?? { label: action, tone: "neutral" as Tone, short: action };
  return <Tag tone={a.tone}>{a.short}</Tag>;
}

export function StateTag({ state }: { state: string }) {
  const s = STATES[state] ?? { label: state, tone: "neutral" as Tone };
  return <Tag tone={s.tone}>{s.label}</Tag>;
}

export function ruleLabel(key: string): string {
  return RULES[key] ?? key;
}
