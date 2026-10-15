// API base URL comes from the environment (Vite exposes only VITE_* variables).
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, issues = [], validation = null) {
    super(message);
    this.issues = issues;
    this.validation = validation;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, options);
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(`Cannot reach the API at ${API_BASE}. Is the backend running?`);
  }
  if (!res.ok) {
    let detail = null;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* non-JSON error body */
    }
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      throw new ApiError(detail.message || `API error ${res.status}`, detail.issues || [], detail.validation || null);
    }
    throw new ApiError(typeof detail === "string" ? detail : `API error ${res.status}`);
  }
  return res.json();
}

export async function fetchSample(threshold, signal) {
  const [dashboard, analytics, anomalies] = await Promise.all([
    request("/api/dashboard?limit=50", { signal }),
    request("/api/analytics", { signal }),
    request(`/api/anomalies?threshold=${threshold}`, { signal }),
  ]);
  return { dashboard, analytics, anomalies };
}

function csvForm(file, threshold) {
  const body = new FormData();
  body.append("file", file);
  body.append("threshold", String(threshold));
  return body;
}

export function uploadCsv(file, threshold) {
  return request("/api/upload", { method: "POST", body: csvForm(file, threshold) });
}

// Re-run detection with a new threshold. The server keeps no state, so uploaded files are re-sent.
export function fetchAnomalies(threshold, file) {
  if (file) return request("/api/anomalies", { method: "POST", body: csvForm(file, threshold) });
  return request(`/api/anomalies?threshold=${threshold}`);
}

export { API_BASE };
