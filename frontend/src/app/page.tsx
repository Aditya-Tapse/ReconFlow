"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Invoice, listInvoices } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import StatusBadge from "@/components/StatusBadge";

const STAT_DEFS: { key: string; label: string; match: (status: string) => boolean; dot: string }[] = [
  { key: "total", label: "Total Invoices", match: () => true, dot: "bg-slate-400" },
  { key: "approved", label: "Approved", match: (s) => s === "APPROVED", dot: "bg-emerald-500" },
  { key: "review", label: "Manual Review", match: (s) => s === "MANUAL_REVIEW", dot: "bg-amber-500" },
  { key: "rejected", label: "Rejected", match: (s) => s === "REJECTED", dot: "bg-rose-500" },
];

function vendorInitials(name: string | null | undefined): string {
  if (!name) return "—";
  const parts = name.trim().split(/\s+/);
  return (parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "");
}

export default function DashboardPage() {
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listInvoices()
      .then(setInvoices)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Invoices</h1>
          <p className="mt-1 text-sm text-slate-500">
            Every invoice case, its matched purchase order, and the final decision.
          </p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center gap-1.5 rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-indigo-600/25 transition-colors hover:bg-indigo-500"
        >
          <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
            <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          </svg>
          Upload Invoice
        </Link>
      </div>

      {invoices !== null && invoices.length > 0 && (
        <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {STAT_DEFS.map((stat) => (
            <div key={stat.key} className="rounded-xl border border-slate-200/70 bg-white p-4 shadow-sm">
              <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
                <span className={`h-1.5 w-1.5 rounded-full ${stat.dot}`} />
                {stat.label}
              </div>
              <p className="mt-1.5 text-2xl font-semibold text-slate-900">
                {invoices.filter((i) => stat.match(i.status)).length}
              </p>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          Could not load invoices: {error}. Is the backend running at the configured API URL?
        </div>
      )}

      {!error && invoices === null && (
        <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-12 text-center text-sm text-slate-500 shadow-sm">
          Loading…
        </div>
      )}

      {invoices !== null && invoices.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-16 text-center">
          <p className="text-sm text-slate-500">No invoices yet.</p>
          <Link href="/upload" className="mt-2 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-500">
            Upload your first invoice →
          </Link>
        </div>
      )}

      {invoices !== null && invoices.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200/70 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Vendor</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Matched PO</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Received</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/70">
                  <td className="px-4 py-3">
                    <Link href={`/invoices/${invoice.id}`} className="font-medium text-slate-900 hover:text-indigo-600">
                      {invoice.invoice_number ?? `Case #${invoice.id}`}
                    </Link>
                    <div className="text-xs text-slate-400">{invoice.filename}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    <div className="flex items-center gap-2">
                      {invoice.vendor_name && (
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-[10px] font-semibold uppercase text-indigo-600">
                          {vendorInitials(invoice.vendor_name)}
                        </span>
                      )}
                      {invoice.vendor_name ?? "—"}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-700">{formatCurrency(invoice.total, invoice.currency)}</td>
                  <td className="px-4 py-3 text-slate-700">{invoice.matched_po?.po_number ?? "—"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={invoice.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500">{formatDateTime(invoice.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
