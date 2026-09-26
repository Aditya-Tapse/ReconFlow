import { AuditEvent } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const EVENT_LABELS: Record<string, string> = {
  INVOICE_RECEIVED: "Document received",
  PDF_TEXT_EXTRACTED: "PDF text extracted",
  OCR_USED: "Vision/OCR extraction used",
  INVOICE_FIELDS_EXTRACTED: "Invoice fields extracted",
  EXTRACTION_FAILED: "Extraction failed",
  VALIDATION_COMPLETED: "Validation completed",
  VENDOR_MATCHED: "Vendor matched",
  VENDOR_NOT_MATCHED: "Vendor not matched",
  PO_MATCHED: "Purchase order matched",
  PO_NOT_MATCHED: "Purchase order not matched",
  PROCESSING_FAILED: "Processing failed",
  DECISION_CREATED: "Decision produced",
  DECISION_FAILED: "Decision failed",
};

function markerFor(eventType: string): { symbol: string; className: string } {
  if (eventType.includes("FAILED") || eventType.includes("NOT_MATCHED")) {
    return { symbol: "!", className: "bg-amber-100 text-amber-700" };
  }
  return { symbol: "✓", className: "bg-emerald-100 text-emerald-700" };
}

export default function ProcessingTimeline({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-slate-500">No events recorded yet.</p>;
  }

  return (
    <ol className="space-y-4">
      {events.map((event, i) => {
        const marker = markerFor(event.event_type);
        return (
          <li key={i} className="flex gap-3">
            <span
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${marker.className}`}
            >
              {marker.symbol}
            </span>
            <div>
              <p className="text-sm font-medium text-slate-800">
                {EVENT_LABELS[event.event_type] ?? event.event_type}
              </p>
              {event.message && <p className="text-sm text-slate-500">{event.message}</p>}
              <p className="text-xs text-slate-400">{formatDateTime(event.created_at)}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
