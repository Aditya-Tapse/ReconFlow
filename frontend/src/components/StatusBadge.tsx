const STATUS_STYLES: Record<string, { label: string; className: string; dot: string }> = {
  PROCESSING: { label: "Processing", className: "bg-slate-100 text-slate-700 ring-slate-300", dot: "bg-slate-400" },
  EXTRACTED: { label: "Extracted", className: "bg-sky-50 text-sky-700 ring-sky-300", dot: "bg-sky-500" },
  VALIDATED: { label: "Validated", className: "bg-sky-50 text-sky-700 ring-sky-300", dot: "bg-sky-500" },
  APPROVED: { label: "Approved", className: "bg-emerald-50 text-emerald-700 ring-emerald-300", dot: "bg-emerald-500" },
  MANUAL_REVIEW: { label: "Manual Review", className: "bg-amber-50 text-amber-800 ring-amber-300", dot: "bg-amber-500" },
  REJECTED: { label: "Rejected", className: "bg-rose-50 text-rose-700 ring-rose-300", dot: "bg-rose-500" },
  EXTRACTION_FAILED: { label: "Extraction Failed", className: "bg-rose-50 text-rose-700 ring-rose-300", dot: "bg-rose-500" },
  PROCESSING_FAILED: { label: "Processing Failed", className: "bg-rose-50 text-rose-700 ring-rose-300", dot: "bg-rose-500" },
  DECISION_FAILED: { label: "Decision Failed", className: "bg-rose-50 text-rose-700 ring-rose-300", dot: "bg-rose-500" },
};

export default function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? {
    label: status,
    className: "bg-slate-100 text-slate-700 ring-slate-300",
    dot: "bg-slate-400",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${style.className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}
