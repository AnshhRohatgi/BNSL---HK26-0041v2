const ACCENTS = {
  electricity: "border-amber-400",
  water: "border-sky-400",
  paper: "border-emerald-400",
};

export default function MetricCard({ resource, unit, totalConsumption, totalCost, records }) {
  const label = resource.charAt(0).toUpperCase() + resource.slice(1);
  return (
    <div className={`rounded-xl border-t-4 bg-white p-5 shadow-sm ${ACCENTS[resource] || "border-slate-300"}`}>
      <p className="text-sm font-medium text-slate-500">{label} consumption</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums">
        {totalConsumption.toLocaleString("en-IN")}
        <span className="ml-1.5 text-base font-normal text-slate-500">{unit}</span>
      </p>
      <p className="mt-3 text-sm text-slate-600">
        Cost: <span className="font-medium tabular-nums">₹{totalCost.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
      </p>
      <p className="mt-1 text-xs text-slate-400">{records} records</p>
    </div>
  );
}
