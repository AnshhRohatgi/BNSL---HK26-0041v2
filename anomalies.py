"""Explainable baseline-threshold anomaly rule. This is NOT a trained AI/ML model.

For every record, observed usage is compared with a baseline for the SAME building + resource + unit:
  1. "history"         - median of the previous (up to 30) records of that series; needs >= 7 prior records.
  2. "series_fallback" - when fewer than 7 prior records exist but the series has >= 8 records, the median of
                         ALL OTHER records of that series (may include later dates). Always labelled as a fallback.
  3. otherwise the record is NOT evaluated (insufficient history). No other baseline is ever substituted.
A baseline <= 0 cannot produce a percentage, so those records are not evaluated either.
Deviation % = (observed - baseline) / baseline * 100; flagged when strictly above the review threshold.
"""
import numpy as np
import pandas as pd

from .data_loader import RESOURCE_ORDER

WINDOW = 30        # most recent prior records used for the history baseline
MIN_HISTORY = 7    # prior records required for a history baseline
DEFAULT_THRESHOLD = 25.0
MAX_ANOMALIES_RETURNED = 200

DISCLAIMER = (
    "Flags show usage above a statistical baseline. They are potential issues that need human review, "
    "not confirmed waste, faults or misconduct. This is a transparent threshold rule, not a trained AI/ML model."
)
METHOD = {
    "name": "Median-baseline threshold rule",
    "description": (
        f"Observed usage is compared with the median of the previous {WINDOW} records (at least {MIN_HISTORY}) "
        "for the same building, resource and unit. A record is flagged when it is more than the review threshold "
        "above that baseline. If fewer than "
        f"{MIN_HISTORY} earlier records exist, the median of all other records in the series is used and the "
        "alert is labelled 'fallback'. Records without a usable baseline are listed as not evaluated."
    ),
    "severity": "Low: above threshold but below 1.5x threshold; Medium: 1.5x to below 3x; High: 3x threshold or more.",
    "min_history": MIN_HISTORY,
    "window": WINDOW,
}
SOURCE_LABELS = {
    "history": "Median of the previous {n} records for this building and resource",
    "series_fallback": "Fallback: median of all {n} other records for this building and resource (fewer than "
                       f"{MIN_HISTORY} earlier records available)",
}
SHORT_BASIS = {"history": "median of the previous {n} records", "series_fallback": "fallback: median of all {n} other records"}
ACTIONS = {
    "electricity": "Review AC usage, operating hours, idle equipment and shutdown practices for this building.",
    "water": "Inspect for leaks, running taps, abnormal flow and water-intensive activities in this building.",
    "paper": "Review unnecessary printing, double-sided defaults and digital alternatives in this building.",
}
_SEV_RANK = {"high": 0, "medium": 1, "low": 2}


def loo_median(v: np.ndarray) -> np.ndarray:
    """Median of all other elements, for each element (leave-one-out). Requires len(v) >= 2."""
    n = len(v)
    order = np.argsort(v, kind="stable")
    s = v[order]
    rank = np.empty(n, dtype=int)
    rank[order] = np.arange(n)
    k = n - 1  # size of the remaining array

    def at(j: int) -> np.ndarray:  # j-th element of the sorted remaining values, for every removed rank
        return np.where(j < rank, s[j], s[j + 1])

    return at(k // 2) if k % 2 == 1 else (at(k // 2 - 1) + at(k // 2)) / 2


def severity_for(deviation_pct: float, threshold_pct: float) -> str:
    if deviation_pct >= 3 * threshold_pct:
        return "high"
    if deviation_pct >= 1.5 * threshold_pct:
        return "medium"
    return "low"


def _fmt(x: float) -> str:
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


def detect_anomalies(df: pd.DataFrame, threshold_pct: float = DEFAULT_THRESHOLD) -> dict:
    d = df.sort_values("date", kind="stable").reset_index(drop=True)
    n_rows = len(d)
    baseline = np.full(n_rows, np.nan)
    n_obs = np.zeros(n_rows, dtype=int)
    source = np.full(n_rows, "", dtype=object)
    values = d["consumption"].to_numpy(dtype=float)

    for pos in d.groupby(["building", "resource", "unit"], sort=False).indices.values():
        v = values[pos]
        hist = pd.Series(v).rolling(WINDOW, min_periods=MIN_HISTORY).median().shift(1).to_numpy()
        prior = np.minimum(np.arange(len(v)), WINDOW)
        b, o, src = hist.copy(), prior.copy(), np.where(np.isnan(hist), "", "history").astype(object)
        if len(v) > MIN_HISTORY:
            miss = np.isnan(hist)
            b[miss] = loo_median(v)[miss]
            o[miss] = len(v) - 1
            src[miss] = "series_fallback"
        baseline[pos], n_obs[pos], source[pos] = b, o, src

    no_baseline = np.isnan(baseline)
    zero_baseline = ~no_baseline & (baseline <= 0)
    evaluated = ~no_baseline & ~zero_baseline
    deviation = np.full(n_rows, np.nan)
    deviation[evaluated] = np.round((values[evaluated] - baseline[evaluated]) / baseline[evaluated] * 100, 6)
    flagged = evaluated & (deviation > threshold_pct)

    anomalies = []
    for i in np.flatnonzero(flagged):
        r = d.iloc[i]
        dev = float(deviation[i])
        sev = severity_for(dev, threshold_pct)
        unit, res, b = r["unit"], r["resource"], float(baseline[i])
        basis = SOURCE_LABELS[source[i]].format(n=int(n_obs[i]))
        anomalies.append({
            "date": r["date"].strftime("%Y-%m-%d"),
            "building": r["building"],
            "resource": res,
            "unit": unit,
            "observed": round(float(values[i]), 2),
            "baseline": round(b, 2),
            "baseline_source": str(source[i]),
            "baseline_basis": basis,
            "baseline_records": int(n_obs[i]),
            "deviation_pct": round(dev, 1),
            "severity": sev,
            "reason": (
                f"{res.capitalize()} use of {_fmt(values[i])} {unit} was {dev:.1f}% above the baseline of "
                f"{_fmt(b)} {unit} ({SHORT_BASIS[source[i]].format(n=int(n_obs[i]))}), "
                f"exceeding the {threshold_pct:g}% review threshold."
            ),
            "recommended_action": ACTIONS[res] + " Treat this as a prompt to check, not proof of waste.",
        })
    anomalies.sort(key=lambda a: (_SEV_RANK[a["severity"]], -a["deviation_pct"], a["date"], a["building"]))
    by_sev = {s: sum(a["severity"] == s for a in anomalies) for s in ("high", "medium", "low")}
    return {
        "threshold_pct": float(threshold_pct),
        "method": METHOD,
        "disclaimer": DISCLAIMER,
        "summary": {
            "records_total": int(n_rows),
            "records_evaluated": int(evaluated.sum()),
            "records_evaluated_with_fallback": int((evaluated & (source == "series_fallback")).sum()),
            "records_not_evaluated": int(n_rows - evaluated.sum()),
            "not_evaluated_reasons": {
                "insufficient_history": int(no_baseline.sum()),
                "zero_baseline": int(zero_baseline.sum()),
            },
            "anomalies_total": len(anomalies),
            "by_severity": by_sev,
        },
        "anomalies": anomalies[:MAX_ANOMALIES_RETURNED],
        "anomalies_truncated": len(anomalies) > MAX_ANOMALIES_RETURNED,
    }
