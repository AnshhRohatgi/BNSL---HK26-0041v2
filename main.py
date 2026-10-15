"""GreenPulse AI - FastAPI backend (Hour 2: data pipeline, upload validation, analytics)."""
import os

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .analytics import build_analytics, build_dashboard
from .anomalies import DEFAULT_THRESHOLD, detect_anomalies
from .data_loader import MAX_UPLOAD_BYTES, CsvValidationError, load_sample, validate_csv_bytes

app = FastAPI(title="GreenPulse AI API", version="0.3.0")

origins = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])


def _sample():
    try:
        return load_sample()
    except (OSError, CsvValidationError) as exc:
        raise HTTPException(status_code=500, detail={"message": f"Could not load sample data: {exc}"}) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "greenpulse-ai-api"}


@app.get("/api/dashboard")
def dashboard(limit: int = Query(50, ge=1, le=500)) -> dict:
    return build_dashboard(_sample(), "sample", limit)


@app.get("/api/sample-data")  # Hour 1 endpoint, kept for compatibility
def sample_data(limit: int = Query(50, ge=1, le=500)) -> dict:
    return build_dashboard(_sample(), "sample", limit)


@app.get("/api/analytics")
def analytics() -> dict:
    return build_analytics(_sample(), "sample")


@app.get("/api/anomalies")
def anomalies(threshold: float = Query(DEFAULT_THRESHOLD, ge=1, le=500)) -> dict:
    """Potential anomalies in the sample data. threshold = % above baseline that triggers review."""
    return detect_anomalies(_sample(), threshold)


async def _read_valid_csv(file: UploadFile):
    """Shared by upload endpoints. Stateless: nothing is stored or logged."""
    name = file.filename or "upload.csv"
    if not name.lower().endswith(".csv"):
        raise HTTPException(422, detail={"message": "Please upload a .csv file."})
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail={"message": f"File is too large (limit {MAX_UPLOAD_BYTES // 1024 // 1024} MB)."})
    try:
        df, validation = validate_csv_bytes(content)
    except CsvValidationError as exc:
        detail = {"message": exc.message}
        if exc.validation:
            detail["validation"] = exc.validation
            detail["issues"] = exc.validation["issues"]
        raise HTTPException(422, detail=detail) from exc
    return name, df, validation


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), threshold: float = Form(DEFAULT_THRESHOLD, ge=1, le=500)) -> dict:
    """Validate an uploaded CSV and return its analysis, including potential anomalies."""
    name, df, validation = await _read_valid_csv(file)
    return {
        "filename": name,
        "validation": validation,
        "dashboard": build_dashboard(df, "upload"),
        "analytics": build_analytics(df, "upload"),
        "anomalies": detect_anomalies(df, threshold),
    }


@app.post("/api/anomalies")
async def anomalies_for_upload(file: UploadFile = File(...), threshold: float = Form(DEFAULT_THRESHOLD, ge=1, le=500)) -> dict:
    """Re-run anomaly detection on an uploaded CSV with a different threshold (server keeps no state)."""
    _, df, _ = await _read_valid_csv(file)
    return detect_anomalies(df, threshold)
