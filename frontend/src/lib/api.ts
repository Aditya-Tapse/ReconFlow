export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type InvoiceStatus =
  | "PROCESSING"
  | "EXTRACTED"
  | "EXTRACTION_FAILED"
  | "VALIDATED"
  | "PROCESSING_FAILED"
  | "APPROVED"
  | "MANUAL_REVIEW"
  | "REJECTED"
  | "DECISION_FAILED";

export interface InvoiceLineItem {
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  amount: number | null;
}

export interface MatchedVendor {
  id: number;
  name: string;
  tax_id: string | null;
}

export interface MatchedPO {
  id: number;
  po_number: string;
  currency: string;
  total_amount: number;
  invoiced_amount: number;
  status: string;
}

export interface Invoice {
  id: number;
  filename: string;
  status: InvoiceStatus;
  extraction_method: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  vendor_name: string | null;
  vendor_tax_id: string | null;
  po_reference: string | null;
  currency: string | null;
  subtotal: number | null;
  tax: number | null;
  total: number | null;
  created_at: string;
  line_items: InvoiceLineItem[];

  matched_vendor_id: number | null;
  vendor_match_confidence: number | null;
  vendor_match_method: string | null;
  vendor_match_reason: string | null;
  matched_vendor: MatchedVendor | null;

  matched_po_id: number | null;
  po_match_confidence: number | null;
  po_match_method: string | null;
  po_match_reason: string | null;
  matched_po: MatchedPO | null;
}

export interface AuditEvent {
  event_type: string;
  message: string | null;
  created_at: string;
}

export interface EvidenceItem {
  field: string;
  value: string | null;
  source_text: string | null;
}

export interface ValidationResult {
  rule_id: string;
  status: string;
  severity: string | null;
  expected: number | null;
  actual: number | null;
  variance_pct: number | null;
  allowed_variance_pct: number | null;
  message: string | null;
  created_at: string;
}

export interface POMatchCandidate {
  po_id: number;
  score: number;
  vendor_score: number | null;
  amount_score: number | null;
  line_item_score: number | null;
  date_score: number | null;
  reason: string | null;
}

export interface Decision {
  decision: string;
  reason: string | null;
  created_at: string;
}

export interface UploadResponse {
  invoice_id: string;
  status: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function listInvoices(): Promise<Invoice[]> {
  return apiFetch<Invoice[]>("/api/invoices");
}

export function getInvoice(id: number): Promise<Invoice> {
  return apiFetch<Invoice>(`/api/invoices/${id}`);
}

export function getAuditTrail(id: number): Promise<AuditEvent[]> {
  return apiFetch<AuditEvent[]>(`/api/invoices/${id}/audit-trail`);
}

export function getEvidence(id: number): Promise<EvidenceItem[]> {
  return apiFetch<EvidenceItem[]>(`/api/invoices/${id}/evidence`);
}

export function getValidationResults(id: number): Promise<ValidationResult[]> {
  return apiFetch<ValidationResult[]>(`/api/invoices/${id}/validation-results`);
}

export function getPoCandidates(id: number): Promise<POMatchCandidate[]> {
  return apiFetch<POMatchCandidate[]>(`/api/invoices/${id}/po-candidates`);
}

export async function getDecision(id: number): Promise<Decision | null> {
  const res = await fetch(`${API_URL}/api/invoices/${id}/decision`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to load decision");
  return res.json() as Promise<Decision>;
}

export async function uploadInvoice(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_URL}/api/invoices`, { method: "POST", body: formData });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  return res.json() as Promise<UploadResponse>;
}

export function fileUrl(id: number): string {
  return `${API_URL}/api/invoices/${id}/file`;
}
