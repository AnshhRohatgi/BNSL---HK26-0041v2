"""Run from backend/:  pip install pytest httpx && pytest -q"""
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data_loader import CsvValidationError, validate_csv_bytes
from app.main import app

client = TestClient(app)
UP = Path(__file__).resolve().parent.parent / "data" / "test_uploads"


def csv(*rows, header="date,building,resource,consumption,unit,unit_cost"):
    return ("\n".join([header, *rows]) + "\n").encode()


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_dashboard_sample_values():
    j = client.get("/api/dashboard").json()
    assert j["source"] == "sample" and j["synthetic"] is True
    assert j["meta"]["total_records"] == 270 and j["meta"]["buildings"] == 4
    s = {r["resource"]: r for r in j["summary"]}
    assert (s["electricity"]["total_consumption"], s["electricity"]["unit"], s["electricity"]["total_cost"]) == (37630, "kWh", 301040.0)
    assert (s["water"]["total_consumption"], s["water"]["unit"], s["water"]["total_cost"]) == (515320, "L", 41225.6)
    assert (s["paper"]["total_consumption"], s["paper"]["unit"], s["paper"]["total_cost"]) == (10486, "sheets", 5243.0)
    assert len(j["building_resource"]) == 9 and len(j["records"]) == 50


def test_dashboard_matches_independent_pandas():
    raw = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "sample_consumption.csv")
    exp = (raw.consumption * raw.unit_cost).groupby(raw.resource).sum().round(2).to_dict()
    got = {r["resource"]: r["total_cost"] for r in client.get("/api/dashboard").json()["summary"]}
    assert got == exp


def test_analytics_sample():
    j = client.get("/api/analytics").json()
    assert len(j["building_totals"]) == 4
    assert j["total_cost"] == round(301040.0 + 41225.6 + 5243.0, 2)
    assert round(sum(b["total_cost"] for b in j["building_totals"]), 2) == j["total_cost"]
    hostel = next(b for b in j["building_totals"] if b["building"] == "Hostel")
    assert hostel["resources"]["water"]["unit"] == "L" and "paper" not in hostel["resources"]


def test_sample_data_legacy_endpoint():
    assert client.get("/api/sample-data").status_code == 200


def test_upload_valid():
    r = client.post("/api/upload", files={"file": ("valid_upload.csv", (UP / "valid_upload.csv").read_bytes(), "text/csv")})
    assert r.status_code == 200
    j = r.json()
    assert j["validation"]["accepted_rows"] == 5 and j["validation"]["rejected_rows"] == 0
    assert j["dashboard"]["synthetic"] is False and j["dashboard"]["meta"]["total_records"] == 5
    s = {x["resource"]: x for x in j["dashboard"]["summary"]}
    assert s["electricity"]["total_cost"] == 500 * 8.0 + 300 * 8.0
    assert s["water"]["total_consumption"] == 10000 and s["water"]["total_cost"] == 800.0
    assert s["paper"]["total_cost"] == 100.0


def test_upload_partial_rejects_reported_with_row_numbers():
    r = client.post("/api/upload", files={"file": ("x.csv", (UP / "invalid_mixed.csv").read_bytes(), "text/csv")})
    assert r.status_code == 200
    v = r.json()["validation"]
    assert (v["total_rows"], v["accepted_rows"], v["rejected_rows"]) == (9, 2, 7)
    msgs = {(i["row"], i["field"]): i["message"] for i in v["issues"]}
    assert "invalid date" in msgs[(3, "date")]
    assert "building is missing" in msgs[(4, "building")]
    assert "unsupported resource 'gas'" in msgs[(5, "resource")]
    assert "negative" in msgs[(6, "consumption")]
    assert "consumption is missing" in msgs[(7, "consumption")]
    assert "incompatible unit 'L' for electricity (expected kWh)" in msgs[(8, "unit")]
    assert "not a valid number" in msgs[(9, "consumption")]
    # invalid values must not have been turned into zeros: only the 2 valid rows count
    assert r.json()["dashboard"]["meta"]["total_records"] == 2


def test_upload_missing_columns():
    r = client.post("/api/upload", files={"file": ("m.csv", (UP / "missing_columns.csv").read_bytes(), "text/csv")})
    assert r.status_code == 422
    assert "unit, unit_cost" in r.json()["detail"]["message"]


@pytest.mark.parametrize("name,content,fragment", [
    ("e.csv", b"", "empty"),
    ("h.csv", b"date,building,resource,consumption,unit,unit_cost\n", "no data rows"),
    ("a.txt", b"x", ".csv"),
    ("b.csv", b"\xff\xfe\x00bad", "UTF-8"),
])
def test_upload_file_level_errors(name, content, fragment):
    r = client.post("/api/upload", files={"file": (name, content, "text/csv")})
    assert r.status_code == 422 and fragment in r.json()["detail"]["message"]


def test_upload_all_rows_invalid():
    body = csv("bad,,gas,-1,x,-2")
    r = client.post("/api/upload", files={"file": ("a.csv", body, "text/csv")})
    assert r.status_code == 422
    d = r.json()["detail"]
    assert "No valid records" in d["message"] and d["validation"]["accepted_rows"] == 0 and d["issues"]


def test_upload_too_large():
    big = b"date,building,resource,consumption,unit,unit_cost\n" + b"x" * (5 * 1024 * 1024 + 10)
    r = client.post("/api/upload", files={"file": ("big.csv", big, "text/csv")})
    assert r.status_code == 413


def test_zero_allowed_and_case_normalised_and_extra_column_warning():
    df, rep = validate_csv_bytes(csv("2026-10-01,A,Electricity,0,kwh,8,hello", header="date,building,resource,consumption,unit,unit_cost,note"))
    assert df.loc[0, "consumption"] == 0 and df.loc[0, "unit"] == "kWh" and df.loc[0, "resource"] == "electricity"
    assert any("note" in w for w in rep["warnings"])


def test_nan_and_inf_rejected():
    with pytest.raises(CsvValidationError):
        validate_csv_bytes(csv("2026-10-01,A,water,nan,L,0.08", "2026-10-01,A,water,inf,L,0.08"))


def test_duplicate_rows_warning_but_kept():
    df, rep = validate_csv_bytes(csv("2026-10-01,A,water,10,L,0.08", "2026-10-01,A,water,10,L,0.08"))
    assert len(df) == 2 and any("repeat" in w for w in rep["warnings"])


def test_cors_allows_local_dev_origin_only():
    ok = client.get("/health", headers={"Origin": "http://localhost:5173"})
    bad = client.get("/health", headers={"Origin": "http://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
