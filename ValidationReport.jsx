export function IssueList({ issues, total, truncated }) {
  if (!issues?.length) return null;
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full text-left text-xs">
        <thead className="bg-slate-100 uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">CSV row</th>
            <th className="px-3 py-2 font-medium">Field</th>
            <th className="px-3 py-2 font-medium">Problem</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {issues.map((i, k) => (
            <tr key={k}>
              <td className="px-3 py-1.5 tabular-nums">{i.row}</td>
              <td className="px-3 py-1.5 font-mono">{i.field}</td>
              <td className="px-3 py-1.5">{i.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {truncated && (
        <p className="border-t border-slate-100 px-3 py-2 text-slate-500">
          Showing the first {issues.length} of {total} problems.
        </p>
      )}
    </div>
  );
}

export default function ValidationReport({ validation }) {
  if (!validation) return null;
  const { total_rows, accepted_rows, rejected_rows, issues, issues_total, issues_truncated, warnings } = validation;
  return (
    <div className="rounded-xl bg-white p-4 text-sm shadow-sm">
      <p className="font-semibold">Validation report</p>
      <p className="mt-1 text-slate-600">
        {total_rows} rows read · <span className="font-medium text-emerald-700">{accepted_rows} accepted</span> ·{" "}
        <span className={rejected_rows ? "font-medium text-red-700" : ""}>{rejected_rows} rejected</span>
        {rejected_rows > 0 && " (rejected rows are excluded from all totals, not replaced with zero)"}
      </p>
      {warnings?.map((w, i) => (
        <p key={i} className="mt-1 text-amber-700">⚠ {w}</p>
      ))}
      <IssueList issues={issues} total={issues_total} truncated={issues_truncated} />
    </div>
  );
}
