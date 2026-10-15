import { useEffect, useState } from "react";

const SEV = {
  high: "bg-red-100 text-red-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-yellow-50 text-yellow-800 ring-1 ring-yellow-200",
};
const fmt = (n) => Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

export default function AnomalyPanel({ result, threshold, loading, error, onThresholdChange }) {
  const [input, setInput] = useState(String(threshold));
  useEffect(() => setInput(String(threshold)), [threshold]);

  // Debounced commit of a valid threshold (1-500 %).
  useEffect(() => {
    const v = Number(input);
    if (input === "" || !Number.isFinite(v) || v < 1 || v > 500 || v === threshold) return;
    const t = setTimeout(() => onThresholdChange(v), 400);
    return () => clearTimeout(t);
  }, [input]); // eslint-disable-line react-hooks/exhaustive-deps

  const invalid = input !== "" && !(Number(input) >= 1 && Number(input) <= 500);
  const s = result?.summary;

  return (
    <section aria-label="Potential anomalies">
      <h2 className="mb-3 text-lg font-semibold">Potential anomalies for review</h2>

      <div role="note" className="mb-3 rounded-lg border border-slate-300 bg-slate-100 px-4 py-3 text-sm text-slate-700">
        {result?.disclaimer ||
          "Flags are potential issues that need human review, not confirmed waste. This is a threshold rule, not a trained AI/ML model."}
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-4 rounded-xl bg-white p-4 shadow-sm">
        <label className="text-sm">
          <span className="block font-medium">Review threshold (% above baseline)</span>
          <input
            type="number"
            min="1"
            max="500"
            step="1"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className={`mt-1 w-28 rounded-md border px-2 py-1.5 tabular-nums ${invalid ? "border-red-400" : "border-slate-300"}`}
          />
          {invalid && <span className="ml-2 text-xs text-red-600">Enter 1–500</span>}
        </label>
        {s && (
          <p className="text-sm text-slate-600">
            <strong className="text-slate-900">{s.anomalies_total}</strong> flagged ·{" "}
            {s.by_severity.high} high · {s.by_severity.medium} medium · {s.by_severity.low} low
            <br />
            {s.records_evaluated.toLocaleString("en-IN")} of {s.records_total.toLocaleString("en-IN")} records evaluated
            {s.records_evaluated_with_fallback > 0 && ` (${s.records_evaluated_with_fallback.toLocaleString("en-IN")} using a labelled fallback baseline)`}
            {loading && <span className="ml-2 text-emerald-700">Updating…</span>}
          </p>
        )}
      </div>

      {s && s.records_not_evaluated > 0 && (
        <p className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {s.records_not_evaluated.toLocaleString("en-IN")} record(s) could not be evaluated:{" "}
          {s.not_evaluated_reasons.insufficient_history > 0 && `${s.not_evaluated_reasons.insufficient_history} with too little history for their building/resource`}
          {s.not_evaluated_reasons.insufficient_history > 0 && s.not_evaluated_reasons.zero_baseline > 0 && "; "}
          {s.not_evaluated_reasons.zero_baseline > 0 && `${s.not_evaluated_reasons.zero_baseline} with a zero baseline (percentage not calculable)`}
          . They are not flagged and no substitute baseline was used.
        </p>
      )}

      {error && (
        <p role="alert" className="mb-3 rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-800">
          Could not update anomalies: {error}
        </p>
      )}

      {result && result.anomalies.length === 0 && (
        <p className="rounded-xl bg-white py-8 text-center text-sm text-slate-500 shadow-sm">
          No records exceeded the {result.threshold_pct}% threshold.
        </p>
      )}

      {result && result.anomalies.length > 0 && (
        <div className={`overflow-x-auto rounded-xl bg-white shadow-sm ${loading ? "opacity-60" : ""}`}>
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-3 font-medium">Severity</th>
                <th className="px-3 py-3 font-medium">Date</th>
                <th className="px-3 py-3 font-medium">Building</th>
                <th className="px-3 py-3 font-medium">Resource</th>
                <th className="px-3 py-3 text-right font-medium">Observed</th>
                <th className="px-3 py-3 text-right font-medium">Baseline</th>
                <th className="px-3 py-3 text-right font-medium">Deviation</th>
                <th className="min-w-56 px-3 py-3 font-medium">Reason</th>
                <th className="min-w-48 px-3 py-3 font-medium">Suggested action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 align-top">
              {result.anomalies.map((a, i) => (
                <tr key={`${a.date}-${a.building}-${a.resource}-${i}`}>
                  <td className="px-3 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${SEV[a.severity]}`}>{cap(a.severity)}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3">{a.date}</td>
                  <td className="px-3 py-3">{a.building}</td>
                  <td className="px-3 py-3">{cap(a.resource)}</td>
                  <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums">{fmt(a.observed)} {a.unit}</td>
                  <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums">
                    {fmt(a.baseline)} {a.unit}
                    <span className="block text-[11px] text-slate-400">
                      {a.baseline_source === "history" ? `median of previous ${a.baseline_records}` : `median of ${a.baseline_records} others`}
                    </span>
                    <span
                      title={a.baseline_basis}
                      className={`cursor-help rounded px-1 text-[10px] uppercase ${a.baseline_source === "history" ? "bg-slate-100 text-slate-600" : "bg-amber-100 text-amber-800"}`}
                    >
                      {a.baseline_source === "history" ? "history" : "fallback"}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-right font-semibold tabular-nums">+{a.deviation_pct.toFixed(1)}%</td>
                  <td className="px-3 py-3 text-slate-700">{a.reason}</td>
                  <td className="px-3 py-3 text-slate-700">{a.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.anomalies_truncated && (
            <p className="border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
              Showing the first {result.anomalies.length} of {s.anomalies_total} flagged records (highest severity first).
            </p>
          )}
        </div>
      )}

      {result?.method && (
        <details className="mt-3 text-sm text-slate-600">
          <summary className="cursor-pointer font-medium">How are anomalies detected?</summary>
          <p className="mt-2"><strong>{result.method.name}.</strong> {result.method.description}</p>
          <p className="mt-1">Severity: {result.method.severity}</p>
        </details>
      )}
    </section>
  );
}
