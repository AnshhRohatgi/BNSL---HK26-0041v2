const RESOURCES = ["electricity", "water", "paper"];
const inr = (n) => `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const label = (s) => s.charAt(0).toUpperCase() + s.slice(1);

export function BuildingTotals({ buildingTotals, totalCost }) {
  const unitOf = {};
  buildingTotals.forEach((b) => Object.entries(b.resources).forEach(([r, v]) => (unitOf[r] = v.unit)));
  const cols = RESOURCES.filter((r) => unitOf[r]);
  return (
    <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">Building</th>
            {cols.map((r) => (
              <th key={r} className="px-4 py-3 text-right font-medium">{label(r)} ({unitOf[r]})</th>
            ))}
            <th className="px-4 py-3 text-right font-medium">Total cost (₹)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {buildingTotals.map((b) => (
            <tr key={b.building} className="hover:bg-slate-50">
              <td className="px-4 py-2.5 font-medium">{b.building}</td>
              {cols.map((r) => (
                <td key={r} className="px-4 py-2.5 text-right tabular-nums">
                  {b.resources[r] ? b.resources[r].total_consumption.toLocaleString("en-IN") : "—"}
                </td>
              ))}
              <td className="px-4 py-2.5 text-right tabular-nums">{inr(b.total_cost).slice(1)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-slate-50 text-sm font-semibold">
          <tr>
            <td className="px-4 py-2.5" colSpan={cols.length + 1}>All buildings (cost only; consumption is never combined across resources)</td>
            <td className="px-4 py-2.5 text-right tabular-nums">{inr(totalCost).slice(1)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export function BuildingResourceTable({ rows }) {
  return (
    <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">Building</th>
            <th className="px-4 py-3 font-medium">Resource</th>
            <th className="px-4 py-3 text-right font-medium">Records</th>
            <th className="px-4 py-3 text-right font-medium">Consumption</th>
            <th className="px-4 py-3 text-right font-medium">Cost (₹)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={`${r.building}-${r.resource}`} className="hover:bg-slate-50">
              <td className="px-4 py-2.5">{r.building}</td>
              <td className="px-4 py-2.5">{label(r.resource)}</td>
              <td className="px-4 py-2.5 text-right tabular-nums">{r.records}</td>
              <td className="px-4 py-2.5 text-right tabular-nums">{r.total_consumption.toLocaleString("en-IN")} {r.unit}</td>
              <td className="px-4 py-2.5 text-right tabular-nums">{inr(r.total_cost).slice(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
