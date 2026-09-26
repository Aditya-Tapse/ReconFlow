"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AuditEvent,
  Decision,
  EvidenceItem,
  Invoice,
  POMatchCandidate,
  ValidationResult,
  fileUrl,
  getAuditTrail,
  getDecision,
  getEvidence,
  getInvoice,
  getPoCandidates,
  getValidationResults,
} from "@/lib/api";
import { formatCurrency, formatDate, formatDateTime, formatPercent } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";
import ProcessingTimeline from "@/components/ProcessingTimeline";
import ValidationResultsTable from "@/components/ValidationResultsTable";
import Collapsible from "@/components/Collapsible";

const DECISION_STYLES: Record<string, { label: string; className: string; iconClassName: string; icon: React.ReactNode }> = {
  APPROVED: {
    label: "APPROVED",
    className: "bg-emerald-50 border-emerald-300 text-emerald-800",
    iconClassName: "bg-emerald-100 text-emerald-600",
    icon: (
      <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
  MANUAL_REVIEW: {
    label: "MANUAL REVIEW",
    className: "bg-amber-50 border-amber-300 text-amber-800",
    iconClassName: "bg-amber-100 text-amber-600",
    icon: (
      <path
        d="M12 8v5m0 3h.01M10.29 3.86 1.82 18a1 1 0 0 0 .86 1.5h18.64a1 1 0 0 0 .86-1.5L13.71 3.86a1 1 0 0 0-1.72 0Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  REJECTED: {
    label: "REJECTED",
    className: "bg-rose-50 border-rose-300 text-rose-800",
    iconClassName: "bg-rose-100 text-rose-600",
    icon: (
      <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    ),
  },
};

interface DetailData {
  invoice: Invoice;
  auditTrail: AuditEvent[];
  evidence: EvidenceItem[];
  validationResults: ValidationResult[];
  poCandidates: POMatchCandidate[];
  decision: Decision | null;
}

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const invoiceId = Number(params.id);

  const [data, setData] = useState<DetailData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!invoiceId) return;
    Promise.all([
      getInvoice(invoiceId),
      getAuditTrail(invoiceId),
      getEvidence(invoiceId),
      getValidationResults(invoiceId),
      getPoCandidates(invoiceId),
      getDecision(invoiceId),
    ])
      .then(([invoice, auditTrail, evidence, validationResults, poCandidates, decision]) =>
        setData({ invoice, auditTrail, evidence, validationResults, poCandidates, decision })
      )
      .catch((err: Error) => setError(err.message));
  }, [invoiceId]);

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        Could not load invoice: {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-12 text-center text-sm text-slate-500 shadow-sm">
        Loading…
      </div>
    );
  }

  const { invoice, auditTrail, evidence, validationResults, poCandidates, decision } = data;
  const decisionStyle = decision ? DECISION_STYLES[decision.decision] : null;
  const remaining =
    invoice.matched_po ? invoice.matched_po.total_amount - invoice.matched_po.invoiced_amount : null;
  const invoiceAmount = invoice.subtotal ?? invoice.total;
  const difference = remaining !== null && invoiceAmount !== null ? invoiceAmount - remaining : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {invoice.invoice_number ?? `Case #${invoice.id}`}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {invoice.filename} · received {formatDateTime(invoice.created_at)}
          </p>
        </div>
        <StatusBadge status={invoice.status} />
      </div>

      {decision && decisionStyle && (
        <div className={`flex flex-col items-center gap-3 rounded-xl border-2 px-6 py-6 shadow-sm ${decisionStyle.className}`}>
          <span className={`flex h-10 w-10 items-center justify-center rounded-full ${decisionStyle.iconClassName}`}>
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
              {decisionStyle.icon}
            </svg>
          </span>
          <p className="text-center text-xl font-bold tracking-wide">{decisionStyle.label}</p>
          <p className="text-center text-sm">{decision.reason}</p>
        </div>
      )}

      {!decision && (
        <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 px-6 py-6 text-center text-sm text-slate-600">
          No decision has been produced for this invoice yet ({invoice.status}). See the processing
          timeline below for what happened.
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryStat label="Invoice Total" value={formatCurrency(invoice.total, invoice.currency)} />
        <SummaryStat label="Matched Vendor" value={invoice.matched_vendor?.name ?? "—"} />
        <SummaryStat label="Matched PO" value={invoice.matched_po?.po_number ?? "—"} />
        <SummaryStat
          label="PO Remaining Balance"
          value={remaining !== null ? formatCurrency(remaining, invoice.matched_po?.currency) : "—"}
        />
      </div>

      {difference !== null && (
        <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
          Invoice amount {formatCurrency(invoiceAmount, invoice.currency)} vs. remaining PO balance{" "}
          {formatCurrency(remaining, invoice.matched_po?.currency)} — difference{" "}
          <span className={difference > 0 ? "font-medium text-rose-600" : "font-medium text-emerald-600"}>
            {formatCurrency(Math.abs(difference), invoice.currency)}
            {difference > 0 ? " over" : " under"}
          </span>
          .
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200/70 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Processing Timeline
          </h2>
          <ProcessingTimeline events={auditTrail} />
        </section>

        <section className="rounded-xl border border-slate-200/70 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Validation &amp; Reconciliation Checks
          </h2>
          <ValidationResultsTable results={validationResults} />
        </section>
      </div>

      <div className="space-y-3">
        <Collapsible title="Extracted invoice fields">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
            <Field label="Invoice number" value={invoice.invoice_number} />
            <Field label="Invoice date" value={formatDate(invoice.invoice_date)} />
            <Field label="Vendor" value={invoice.vendor_name} />
            <Field label="Vendor tax ID" value={invoice.vendor_tax_id} />
            <Field label="PO reference" value={invoice.po_reference} />
            <Field label="Currency" value={invoice.currency} />
            <Field label="Subtotal" value={formatCurrency(invoice.subtotal, invoice.currency)} />
            <Field label="Tax" value={formatCurrency(invoice.tax, invoice.currency)} />
            <Field label="Total" value={formatCurrency(invoice.total, invoice.currency)} />
            <Field label="Extraction method" value={invoice.extraction_method} />
          </dl>

          {invoice.line_items.length > 0 && (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3">Description</th>
                    <th className="py-2 pr-3">Qty</th>
                    <th className="py-2 pr-3">Unit Price</th>
                    <th className="py-2">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.line_items.map((line, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="py-2 pr-3 text-slate-700">{line.description ?? "—"}</td>
                      <td className="py-2 pr-3 text-slate-500">{line.quantity ?? "—"}</td>
                      <td className="py-2 pr-3 text-slate-500">{formatCurrency(line.unit_price)}</td>
                      <td className="py-2 text-slate-700">{formatCurrency(line.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Collapsible>

        <Collapsible title="Source evidence">
          {evidence.length === 0 ? (
            <p className="text-sm text-slate-500">No evidence recorded (nothing extracted, or the LLM provider didn&apos;t return any).</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-3">Field</th>
                  <th className="py-2 pr-3">Value</th>
                  <th className="py-2">Source text</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((item, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="py-2 pr-3 font-mono text-xs text-slate-700">{item.field}</td>
                    <td className="py-2 pr-3 text-slate-600">{item.value ?? "—"}</td>
                    <td className="py-2 text-slate-500 italic">&ldquo;{item.source_text ?? "—"}&rdquo;</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Collapsible>

        <Collapsible title={`Candidate PO matches (${poCandidates.length})`}>
          {poCandidates.length === 0 ? (
            <p className="text-sm text-slate-500">
              No candidates were scored — either the invoice had an explicit PO reference, or no
              vendor/open POs were available to score against.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-3">PO</th>
                  <th className="py-2 pr-3">Overall</th>
                  <th className="py-2 pr-3">Vendor</th>
                  <th className="py-2 pr-3">Amount</th>
                  <th className="py-2 pr-3">Line Items</th>
                  <th className="py-2">Date</th>
                </tr>
              </thead>
              <tbody>
                {poCandidates.map((candidate) => (
                  <tr key={candidate.po_id} className="border-t border-slate-100">
                    <td className="py-2 pr-3 font-medium text-slate-800">PO #{candidate.po_id}</td>
                    <td className="py-2 pr-3 font-medium text-slate-800">{formatPercent(candidate.score)}</td>
                    <td className="py-2 pr-3 text-slate-500">{formatPercent(candidate.vendor_score)}</td>
                    <td className="py-2 pr-3 text-slate-500">{formatPercent(candidate.amount_score)}</td>
                    <td className="py-2 pr-3 text-slate-500">{formatPercent(candidate.line_item_score)}</td>
                    <td className="py-2 text-slate-500">{formatPercent(candidate.date_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Collapsible>

        <Collapsible title="Original PDF">
          <a
            href={fileUrl(invoice.id)}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
          >
            Open {invoice.filename} in a new tab
          </a>
          <iframe src={fileUrl(invoice.id)} className="mt-3 h-[500px] w-full rounded-lg border border-slate-200" />
        </Collapsible>
      </div>
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200/70 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-800">{value}</p>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-slate-800">{value ?? "—"}</dd>
    </div>
  );
}
