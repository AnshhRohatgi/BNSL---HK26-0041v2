"""CSV loading and strict validation. Invalid rows are rejected and reported - never coerced to zero."""
import io
from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_consumption.csv"
REQUIRED_COLUMNS = ["date", "building", "resource", "consumption", "unit", "unit_cost"]
RESOURCE_ORDER = ["electricity", "water", "paper"]
RESOURCE_UNITS = {"electricity": "kWh", "water": "L", "paper": "sheets"}  # one allowed unit per resource
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ROWS = 100_000
MAX_ISSUES_RETURNED = 50


class CsvValidationError(Exception):
    """Whole-file failure. `validation` optionally carries row counts and issues for the UI."""

    def __init__(self, message: str, validation: dict | None = None):
        super().__init__(message)
        self.message = message
        self.validation = validation


def parse_csv_bytes(content: bytes) -> pd.DataFrame:
    """Parse raw bytes into an all-string DataFrame (no type coercion yet)."""
    if not content.strip():
        raise CsvValidationError("The file is empty.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CsvValidationError("The file is not valid UTF-8 text. Save it as a UTF-8 CSV and try again.")
    try:
        raw = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise CsvValidationError(f"Could not parse the CSV: {exc}")
    raw.columns = [str(c).strip() for c in raw.columns]
    return raw.fillna("")


def validate_dataframe(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, validation_report). Raises CsvValidationError if nothing usable."""
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise CsvValidationError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Required columns are exactly: {', '.join(REQUIRED_COLUMNS)}."
        )
    if raw.empty:
        raise CsvValidationError("The file has a header but no data rows.")
    if len(raw) > MAX_ROWS:
        raise CsvValidationError(f"The file has {len(raw):,} rows; the limit is {MAX_ROWS:,}.")

    df = raw[REQUIRED_COLUMNS].copy()
    for col in REQUIRED_COLUMNS:
        df[col] = df[col].astype(str).str.strip()

    invalid = pd.Series(False, index=df.index)
    issues: list[dict] = []

    def flag(field: str, mask: pd.Series, message) -> None:
        nonlocal invalid
        for i in df.index[mask]:
            issues.append({"row": int(i) + 2, "field": field, "message": message(df.at[i, field])})
        invalid = invalid | mask

    # building
    flag("building", df["building"] == "", lambda v: "building is missing")

    # date (strict ISO: YYYY-MM-DD)
    blank = df["date"] == ""
    parsed_date = pd.to_datetime(df["date"].where(~blank), format="ISO8601", errors="coerce", utc=True)
    flag("date", blank, lambda v: "date is missing")
    flag("date", ~blank & parsed_date.isna(), lambda v: f"invalid date '{v}' (expected YYYY-MM-DD)")

    # resource
    resource = df["resource"].str.lower()
    blank = resource == ""
    valid_resource = resource.isin(RESOURCE_UNITS)
    flag("resource", blank, lambda v: "resource is missing")
    flag(
        "resource",
        ~blank & ~valid_resource,
        lambda v: f"unsupported resource '{v}' (supported: {', '.join(RESOURCE_ORDER)})",
    )

    # unit must match the resource's single allowed unit (no conversion is attempted)
    expected_unit = resource.map(RESOURCE_UNITS)
    unit_blank = df["unit"] == ""
    flag("unit", unit_blank, lambda v: "unit is missing")
    bad_unit = ~unit_blank & valid_resource & (df["unit"].str.lower() != expected_unit.str.lower())
    for i in df.index[bad_unit]:
        issues.append({
            "row": int(i) + 2,
            "field": "unit",
            "message": f"incompatible unit '{df.at[i, 'unit']}' for {resource[i]} (expected {expected_unit[i]})",
        })
    invalid = invalid | bad_unit

    # numeric fields
    numbers = {}
    for col in ("consumption", "unit_cost"):
        blank = df[col] == ""
        num = pd.to_numeric(df[col].where(~blank), errors="coerce").astype(float)
        flag(col, blank, lambda v, c=col: f"{c} is missing")
        flag(col, ~blank & ~np.isfinite(num), lambda v, c=col: f"{c} '{v}' is not a valid number")
        flag(col, np.isfinite(num) & (num < 0), lambda v, c=col: f"{c} '{v}' is negative")
        numbers[col] = num

    issues.sort(key=lambda x: (x["row"], x["field"]))
    total_rows = len(df)
    rejected = int(invalid.sum())
    report = {
        "total_rows": total_rows,
        "accepted_rows": total_rows - rejected,
        "rejected_rows": rejected,
        "issues": issues[:MAX_ISSUES_RETURNED],
        "issues_total": len(issues),
        "issues_truncated": len(issues) > MAX_ISSUES_RETURNED,
        "warnings": [],
    }
    extra = [c for c in raw.columns if c not in REQUIRED_COLUMNS]
    if extra:
        report["warnings"].append(f"Ignored extra column(s): {', '.join(map(str, extra))}.")

    if rejected == total_rows:
        raise CsvValidationError(
            "No valid records found. Fix the issues below and upload the file again.", report
        )

    ok = ~invalid
    clean = pd.DataFrame(
        {
            "date": parsed_date[ok].dt.tz_localize(None).dt.normalize(),
            "building": df.loc[ok, "building"],
            "resource": resource[ok],
            "consumption": numbers["consumption"][ok],
            "unit": expected_unit[ok],  # canonical spelling, e.g. 'kwh' -> 'kWh'
            "unit_cost": numbers["unit_cost"][ok],
        }
    ).reset_index(drop=True)
    clean["cost"] = clean["consumption"] * clean["unit_cost"]  # INR = consumption x unit_cost

    dupes = int(clean.duplicated(["date", "building", "resource"]).sum())
    if dupes:
        report["warnings"].append(
            f"{dupes} accepted row(s) repeat an earlier date/building/resource combination. They were kept; check for double entries."
        )
    return clean, report


def validate_csv_bytes(content: bytes) -> tuple[pd.DataFrame, dict]:
    return validate_dataframe(parse_csv_bytes(content))


@cache
def load_sample() -> pd.DataFrame:
    """Bundled synthetic sample, passed through the same validation as uploads."""
    clean, _ = validate_csv_bytes(SAMPLE_PATH.read_bytes())
    return clean
