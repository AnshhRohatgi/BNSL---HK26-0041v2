const COLUMNS = [
  ["date", "Date"],
  ["building", "Building"],
  ["resource", "Resource"],
  ["consumption", "Consumption"],
  ["unit", "Unit"],
  ["unit_cost", "Unit cost (₹)"],
  ["cost", "Cost (₹)"],
];
const NUMERIC = new Set(["consumption", "unit_cost", "cost"]);

export default function DataTable({ rows }) {
  return (
    <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {COLUMNS.map(([key, label]) => (
              <th key={key} className={`px-4 py-3 font-medium ${NUMERIC.has(key) ? "text-right" : ""}`}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r, i) => (
            <tr key={`${r.date}-${r.building}-${r.resource}-${i}`} className="hover:bg-slate-50">
              {COLUMNS.map(([key]) => (
                <td key={key} className={`whitespace-nowrap px-4 py-2.5 ${NUMERIC.has(key) ? "text-right tabular-nums" : ""}`}>
                  {key === "cost"
                    ? r[key].toFixed(2)
                    : key === "unit_cost"
                      ? Number(r[key]).toFixed(2)
                      : key === "consumption"
                        ? Number(r[key]).toLocaleString("en-IN")
                        : r[key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
