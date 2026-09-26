import { ValidationResult } from "@/lib/api";

function statusIcon(status: string): { symbol: string; className: string } {
  if (status === "PASS") return { symbol: "✓", className: "text-emerald-600" };
  if (status === "SKIPPED") return { symbol: "–", className: "text-slate-400" };
  return { symbol: "✕", className: "text-rose-600" };
}

export default function ValidationResultsTable({ results }: { results: ValidationResult[] }) {
  if (results.length === 0) {
    return <p className="text-sm text-slate-500">No validation results yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <th className="py-2 pr-3">Rule</th>
            <th className="py-2 pr-3">Result</th>
            <th className="py-2 pr-3">Severity</th>
            <th className="py-2">Detail</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result, i) => {
            const icon = statusIcon(result.status);
            return (
              <tr key={i} className="border-t border-slate-100 align-top">
                <td className="py-2 pr-3 font-mono text-xs text-slate-700">{result.rule_id}</td>
                <td className={`py-2 pr-3 font-medium ${icon.className}`}>{icon.symbol}</td>
                <td className="py-2 pr-3 text-xs text-slate-500">{result.severity ?? "—"}</td>
                <td className="py-2 text-slate-600">{result.message ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
