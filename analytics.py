"""Aggregations. Resources are never combined in consumption; only INR cost is summed across resources."""
import pandas as pd

from .data_loader import RESOURCE_ORDER

_ORDER = {r: i for i, r in enumerate(RESOURCE_ORDER)}


def _grouped(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return df.groupby(keys, as_index=False).agg(
        unit=("unit", "first"),
        total_consumption=("consumption", "sum"),
        total_cost=("cost", "sum"),
        records=("consumption", "size"),
    )


def _row(r) -> dict:
    return {
        "unit": str(r["unit"]),
        "total_consumption": round(float(r["total_consumption"]), 2),
        "total_cost": round(float(r["total_cost"]), 2),
        "records": int(r["records"]),
    }


def resource_totals(df: pd.DataFrame) -> list[dict]:
    out = [{"resource": r["resource"], **_row(r)} for _, r in _grouped(df, ["resource"]).iterrows()]
    return sorted(out, key=lambda x: _ORDER[x["resource"]])


def build_dashboard(df: pd.DataFrame, source: str, limit: int = 50) -> dict:
    if df.empty:
        return {"source": source, "synthetic": source == "sample", "currency": "INR",
                "meta": None, "summary": [], "building_resource": [], "records": []}
    br = [{"building": r["building"], "resource": r["resource"], **_row(r)}
          for _, r in _grouped(df, ["building", "resource"]).iterrows()]
    br.sort(key=lambda x: (x["building"].lower(), _ORDER[x["resource"]]))

    preview = df.head(limit).copy()
    preview["date"] = preview["date"].dt.strftime("%Y-%m-%d")
    preview["cost"] = preview["cost"].round(2)
    cols = ["date", "building", "resource", "consumption", "unit", "unit_cost", "cost"]
    return {
        "source": source,
        "synthetic": source == "sample",
        "currency": "INR",
        "meta": {
            "total_records": int(len(df)),
            "buildings": int(df["building"].nunique()),
            "date_start": df["date"].min().strftime("%Y-%m-%d"),
            "date_end": df["date"].max().strftime("%Y-%m-%d"),
            "preview_rows": int(len(preview)),
        },
        "summary": resource_totals(df),
        "building_resource": br,
        "records": preview[cols].to_dict(orient="records"),
    }


def build_analytics(df: pd.DataFrame, source: str) -> dict:
    buildings = {}
    for _, r in _grouped(df, ["building", "resource"]).iterrows():
        b = buildings.setdefault(r["building"], {"building": r["building"], "total_cost": 0.0, "resources": {}})
        b["resources"][r["resource"]] = {k: v for k, v in _row(r).items() if k != "records"}
        b["total_cost"] += float(r["total_cost"])
    building_totals = sorted(buildings.values(), key=lambda b: b["building"].lower())
    for b in building_totals:
        b["total_cost"] = round(b["total_cost"], 2)
    return {
        "source": source,
        "currency": "INR",
        "total_cost": round(float(df["cost"].sum()), 2) if not df.empty else 0.0,
        "resource_totals": resource_totals(df) if not df.empty else [],
        "building_totals": building_totals,
    }
