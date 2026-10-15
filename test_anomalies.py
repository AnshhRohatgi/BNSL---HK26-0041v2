"""Run from backend/:  pytest -q"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.anomalies import detect_anomalies, loo_median, severity_for
from app.data_loader import load_sample, validate_csv_bytes
from app.main import app

client = TestClient(app)
UP = Path(__file__).resolve().parent.parent / "data" / "test_uploads"


def frame(values, building="A", resource="electricity", unit="kWh", cost=8.0, start="2026-10-01"):
    dates = pd.date_range(start, periods=len(values))
    return pd.DataFrame({"date": dates, "building": building, "resource": resource, "consumption": values,
                         "unit": unit, "unit_cost": cost, "cost": np.array(values, dtype=float) * cost})


def test_sample_has_exactly_the_two_injected_anomalies():
    r = detect_anomalies(load_sample())
    got = {(a["date"], a["building"], a["resource"]): a for a in r["anomalies"]}
    assert set(got) == {("2026-09-28", "Computer Lab 3", "electricity"), ("2026-09-20", "Hostel", "water")}
    e = got[("2026-09-28", "Computer Lab 3", "electricity")]
    assert (e["observed"], e["baseline"], e["deviation_pct"], e["unit"], e["baseline_source"]) == (580, 400, 45.0, "kWh", "history")
    w = got[("2026-09-20", "Hostel", "water")]
    assert (w["observed"], w["baseline"], w["deviation_pct"], w["unit"]) == (18000, 12000, 50.0, "L")
    assert r["summary"]["records_not_evaluated"] == 0 and r["summary"]["anomalies_total"] == 2


def test_baseline_matches_independent_pandas_median():
    df = load_sample()
    s = df[(df.building == "Computer Lab 3") & (df.resource == "electricity")].sort_values("date")
    prior = s[s.date < "2026-09-28"].consumption
    assert prior.median() == 400 and len(prior) == 27


def test_threshold_is_configurable_and_strict():
    df = load_sample()
    assert detect_anomalies(df, 25)["summary"]["anomalies_total"] == 2
    assert detect_anomalies(df, 40)["summary"]["anomalies_total"] == 2
    assert [a["resource"] for a in detect_anomalies(df, 45)["anomalies"]] == ["water"]  # 45.0 is not > 45
    assert detect_anomalies(df, 50)["summary"]["anomalies_total"] == 0                  # 50.0 is not > 50


def test_severity_bands_scale_with_threshold():
    assert severity_for(30, 25) == "low" and severity_for(37.5, 25) == "medium"
    assert severity_for(74.9, 25) == "medium" and severity_for(75, 25) == "high"
    assert severity_for(60, 40) == "medium" and severity_for(120, 40) == "high"


def test_zero_baseline_is_safe_and_reports_no_percentage():
    r = detect_anomalies(frame([0] * 10 + [5]))
    assert r["anomalies"] == []
    assert r["summary"]["not_evaluated_reasons"]["zero_baseline"] >= 1
    assert r["summary"]["records_evaluated"] + r["summary"]["records_not_evaluated"] == 11


def test_insufficient_history_not_evaluated():
    r = detect_anomalies(frame([100, 100, 100, 500, 100]))
    assert r["summary"]["records_evaluated"] == 0 and r["summary"]["not_evaluated_reasons"]["insufficient_history"] == 5
    assert r["anomalies"] == []


def test_fallback_baseline_is_labelled():
    r = detect_anomalies(frame([100, 100, 300, 100, 100, 100, 100, 100, 100, 100]))
    a = r["anomalies"][0]
    assert a["date"] == "2026-10-03" and a["baseline_source"] == "series_fallback" and a["baseline"] == 100
    assert "Fallback" in a["baseline_basis"] and a["baseline_records"] == 9
    assert r["summary"]["records_evaluated_with_fallback"] == 7


def test_series_are_kept_separate_by_building_and_resource():
    a, b = frame([100] * 12, building="A"), frame([1000] * 12, building="B")
    assert detect_anomalies(pd.concat([a, b]))["anomalies"] == []  # B's level is not compared with A's


@pytest.mark.parametrize("n", [2, 3, 8, 9, 31])
def test_loo_median_matches_bruteforce(n):
    rng = np.random.default_rng(n)
    v = rng.integers(0, 20, n).astype(float)
    brute = np.array([np.median(np.delete(v, i)) for i in range(n)])
    assert np.allclose(loo_median(v), brute)


def test_api_sample_anomalies_and_threshold_validation():
    j = client.get("/api/anomalies").json()
    assert j["threshold_pct"] == 25 and len(j["anomalies"]) == 2
    assert "not a trained AI/ML model" in j["disclaimer"] and "not confirmed waste" in j["disclaimer"]
    assert client.get("/api/anomalies?threshold=50").json()["summary"]["anomalies_total"] == 0
    assert client.get("/api/anomalies?threshold=0").status_code == 422
    assert client.get("/api/anomalies?threshold=501").status_code == 422


def test_api_upload_includes_anomalies_and_reanalysis_endpoint():
    data = (UP / "anomaly_upload.csv").read_bytes()
    j = client.post("/api/upload", files={"file": ("anomaly_upload.csv", data, "text/csv")}).json()
    an = j["anomalies"]
    assert an["summary"]["anomalies_total"] == 1 and an["anomalies"][0]["building"] == "Science Block"
    assert an["anomalies"][0]["deviation_pct"] == 50.0 and an["summary"]["not_evaluated_reasons"]["insufficient_history"] == 5
    r = client.post("/api/anomalies", files={"file": ("a.csv", data, "text/csv")}, data={"threshold": "60"})
    assert r.status_code == 200 and r.json()["summary"]["anomalies_total"] == 0 and r.json()["threshold_pct"] == 60
    bad = client.post("/api/anomalies", files={"file": ("a.csv", data, "text/csv")}, data={"threshold": "0"})
    assert bad.status_code == 422


def test_rejected_rows_never_reach_detection():
    body = b"date,building,resource,consumption,unit,unit_cost\n" + b"".join(
        f"2026-10-{d:02d},A,water,100,L,0.08\n".encode() for d in range(1, 10)
    ) + b"2026-10-10,A,water,-999,L,0.08\n2026-10-11,A,water,abc,L,0.08\n"
    df, rep = validate_csv_bytes(body)
    assert rep["rejected_rows"] == 2 and len(df) == 9 and detect_anomalies(df)["anomalies"] == []
