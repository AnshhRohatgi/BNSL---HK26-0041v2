import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, fetchAnomalies, fetchSample, uploadCsv } from "./api.js";
import AnomalyPanel from "./components/AnomalyPanel.jsx";
import { BuildingResourceTable, BuildingTotals } from "./components/BuildingTables.jsx";
import DataTable from "./components/DataTable.jsx";
import MetricCard from "./components/MetricCard.jsx";
import StatTile from "./components/StatTile.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import ValidationReport from "./components/ValidationReport.jsx";

export default function App() {
  // view = { dashboard, analytics, anomalies, source: "sample" | "upload", filename, validation, file }
  const [state, setState] = useState({ status: "loading", view: null, error: "" });
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [threshold, setThreshold] = useState(25);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [anomalyError, setAnomalyError] = useState("");
  const anomalyReq = useRef(0); // ignore out-of-order responses

  const loadSample = useCallback((signal, th = 25) => {
    setUploadError(null);
    setAnomalyError("");
    setState({ status: "loading", view: null, error: "" });
    fetchSample(th, signal)
      .then(({ dashboard, analytics, anomalies }) =>
        setState({ status: "ready", view: { dashboard, analytics, anomalies, source: "sample", filename: "", validation: null, file: null }, error: "" })
      )
      .catch((err) => {
        if (err.name !== "AbortError") setState({ status: "error", view: null, error: err.message });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadSample(controller.signal);
    return () => controller.abort();
  }, [loadSample]);

  async function handleUpload(file) {
    setUploading(true);
    setUploadError(null);
    try {
      const res = await uploadCsv(file, threshold);
      anomalyReq.current += 1;
      setAnomalyError("");
      setState({
        status: "ready",
        view: { dashboard: res.dashboard, analytics: res.analytics, anomalies: res.anomalies, source: "upload", filename: res.filename, validation: res.validation, file },
        error: "",
      });
    } catch (err) {
      setUploadError({ message: err.message, issues: err.issues || [], validation: err.validation || null });
    } finally {
      setUploading(false);
    }
  }

  async function handleThreshold(value) {
    const req = ++anomalyReq.current;
    setThreshold(value);
    setAnomalyLoading(true);
    setAnomalyError("");
    try {
      const anomalies = await fetchAnomalies(value, state.view?.file);
      if (req === anomalyReq.current) setState((s) => ({ ...s, view: { ...s.view, anomalies } }));
    } catch (err) {
      if (req === anomalyReq.current) setAnomalyError(err.message);
    } finally {
      if (req === anomalyReq.current) setAnomalyLoading(false);
    }
  }

  const { status, view, error } = state;
  const data = view?.dashboard;
  const isEmpty = status === "ready" && (!data?.meta || data.records.length === 0);

  return (
    <div className="min-h-screen">
      <header className="bg-emerald-800 text-white">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          <h1 className="text-3xl font-bold tracking-tight">🌿 GreenPulse AI</h1>
          <p className="mt-2 max-w-2xl text-emerald-100">
            Campus Resource Waste Intelligence Platform — a prototype that analyses electricity, water and paper
            consumption records to help spot unusual usage.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        {status === "ready" && (
          <UploadPanel
            source={view.source}
            filename={view.filename}
            uploading={uploading}
            error={uploadError}
            onUpload={handleUpload}
            onReset={() => loadSample(undefined, threshold)}
          />
        )}

        {data?.synthetic ? (
          <div role="note" className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <strong>Synthetic sample data.</strong> These records are illustrative, not real campus data. Currency is INR (₹).
          </div>
        ) : (
          data && (
            <div role="note" className="rounded-lg border border-sky-300 bg-sky-50 px-4 py-3 text-sm text-sky-900">
              <strong>Your uploaded data.</strong> Analysed for this session only; nothing is stored. Currency is INR (₹).
            </div>
          )
        )}

        {status === "loading" && <p role="status" className="py-16 text-center text-slate-500">Loading data…</p>}

        {status === "error" && (
          <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">
            <p className="font-semibold">Could not load data</p>
            <p className="mt-1">{error}</p>
            <p className="mt-1 text-red-600">API: {API_BASE}</p>
            <button onClick={() => loadSample(undefined, threshold)} className="mt-3 rounded-md bg-red-700 px-3 py-1.5 font-medium text-white hover:bg-red-800">
              Retry
            </button>
          </div>
        )}

        {isEmpty && (
          <p className="rounded-lg bg-white py-12 text-center text-slate-500 shadow-sm">No records were returned by the API.</p>
        )}

        {status === "ready" && !isEmpty && (
          <>
            <ValidationReport validation={view.validation} />

            <section aria-label="Dataset summary" className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatTile label="Total records" value={data.meta.total_records.toLocaleString("en-IN")} />
              <StatTile label="Buildings" value={data.meta.buildings} />
              <StatTile label="Date range" value={`${data.meta.date_start} → ${data.meta.date_end}`} />
            </section>

            <section aria-label="Resource consumption">
              <h2 className="mb-3 text-lg font-semibold">Consumption by resource</h2>
              <p className="mb-3 text-sm text-slate-500">
                Each resource is totalled separately in its own unit. Cost = consumption × unit cost.
              </p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {data.summary.map((s) => (
                  <MetricCard
                    key={s.resource}
                    resource={s.resource}
                    unit={s.unit}
                    totalConsumption={s.total_consumption}
                    totalCost={s.total_cost}
                    records={s.records}
                  />
                ))}
              </div>
            </section>

            {view.anomalies && (
              <AnomalyPanel
                result={view.anomalies}
                threshold={threshold}
                loading={anomalyLoading}
                error={anomalyError}
                onThresholdChange={handleThreshold}
              />
            )}

            <section aria-label="Building totals">
              <h2 className="mb-3 text-lg font-semibold">Building-wise totals</h2>
              <BuildingTotals buildingTotals={view.analytics.building_totals} totalCost={view.analytics.total_cost} />
            </section>

            <section aria-label="Building and resource summary">
              <h2 className="mb-3 text-lg font-semibold">Building × resource summary</h2>
              <BuildingResourceTable rows={data.building_resource} />
            </section>

            <section aria-label="Data preview">
              <h2 className="mb-3 text-lg font-semibold">
                Data preview{" "}
                <span className="text-sm font-normal text-slate-500">
                  (first {data.meta.preview_rows} of {data.meta.total_records} accepted records)
                </span>
              </h2>
              <DataTable rows={data.records} />
            </section>
          </>
        )}
      </main>

      <footer className="mx-auto max-w-6xl px-4 py-8 text-xs text-slate-400 sm:px-6">
        GreenPulse AI · Hour 3 prototype · Chakravyuh 1.0 · Sample data is synthetic.
      </footer>
    </div>
  );
}
