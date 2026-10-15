import { useRef } from "react";
import { IssueList } from "./ValidationReport.jsx";

export default function UploadPanel({ source, filename, uploading, error, onUpload, onReset }) {
  const inputRef = useRef(null);

  function handleChange(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (file) onUpload(file);
  }

  return (
    <section aria-label="Data source" className="rounded-xl bg-white p-4 shadow-sm sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">Data source</p>
          <p className="font-semibold">
            {source === "upload" ? `Uploaded file: ${filename}` : "Bundled sample data (synthetic)"}
          </p>
        </div>
        <div className="flex gap-2">
          <input ref={inputRef} type="file" accept=".csv,text/csv" className="hidden" onChange={handleChange} />
          <button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-60"
          >
            {uploading ? "Validating…" : "Upload CSV"}
          </button>
          {source === "upload" && (
            <button
              onClick={onReset}
              disabled={uploading}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-60"
            >
              Use sample data
            </button>
          )}
        </div>
      </div>

      <details className="mt-3 text-sm text-slate-600">
        <summary className="cursor-pointer font-medium">Required CSV format</summary>
        <p className="mt-2">
          Columns (exact names): <code className="rounded bg-slate-100 px-1">date,building,resource,consumption,unit,unit_cost</code>
        </p>
        <ul className="mt-1 list-inside list-disc">
          <li>date: YYYY-MM-DD</li>
          <li>resource / unit: electricity / kWh, water / L, paper / sheets (no unit conversion)</li>
          <li>consumption and unit_cost (INR per unit): numbers ≥ 0</li>
          <li>Max 5 MB. Uploaded data is analysed for this session only and is not stored.</li>
        </ul>
      </details>

      {error && (
        <div role="alert" className="mt-3 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          <p className="font-semibold">Upload failed: {error.message}</p>
          {error.validation && (
            <p className="mt-1">
              {error.validation.total_rows} rows read, {error.validation.rejected_rows} rejected.
            </p>
          )}
          <IssueList issues={error.issues} total={error.validation?.issues_total} truncated={error.validation?.issues_truncated} />
          <p className="mt-2 text-red-700">Your previous data is still shown below.</p>
        </div>
      )}
    </section>
  );
}
