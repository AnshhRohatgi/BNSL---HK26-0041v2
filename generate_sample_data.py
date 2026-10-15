"""Generate the illustrative GreenPulse AI sample dataset (deterministic, no randomness).

Run from backend/:  python scripts/generate_sample_data.py
Output: backend/data/sample_consumption.csv
ILLUSTRATIVE DATA ONLY - not real campus data.
"""
import csv
from datetime import date, timedelta
from pathlib import Path

START = date(2026, 9, 1)
DAYS = 30  # 2026-09-01 .. 2026-09-30

# Weekly variation pattern: zero sum and zero median, so the typical
# (median) daily value of each series equals its base value exactly.
PATTERN = [-0.03, -0.01, 0.0, 0.01, 0.03, 0.0, 0.0]

# (building, resource, unit, base daily consumption, unit_cost in INR)
SERIES = [
    ("Computer Lab 3", "electricity", "kWh", 400, 8.0),
    ("Library", "electricity", "kWh", 250, 8.0),
    ("Hostel", "electricity", "kWh", 600, 8.0),
    ("Computer Lab 3", "water", "L", 3000, 0.08),
    ("Library", "water", "L", 2000, 0.08),
    ("Hostel", "water", "L", 12000, 0.08),
    ("Administrative Office", "paper", "sheets", 150, 0.50),
    ("Library", "paper", "sheets", 80, 0.50),
    ("Computer Lab 3", "paper", "sheets", 120, 0.50),
]

# Deliberately injected anomalies: (building, resource, date) -> consumption
ANOMALIES = {
    ("Computer Lab 3", "electricity", date(2026, 9, 28)): 580,  # +45% vs 400 kWh
    ("Hostel", "water", date(2026, 9, 20)): 18000,              # +50% vs 12000 L
}

rows = []
for i in range(DAYS):
    d = START + timedelta(days=i)
    for building, resource, unit, base, cost in SERIES:
        value = round(base * (1 + PATTERN[i % 7]))
        value = ANOMALIES.get((building, resource, d), value)
        rows.append([d.isoformat(), building, resource, value, unit, cost])

out = Path(__file__).resolve().parent.parent / "data" / "sample_consumption.csv"
out.parent.mkdir(exist_ok=True)
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "building", "resource", "consumption", "unit", "unit_cost"])
    w.writerows(rows)
print(f"Wrote {len(rows)} rows to {out}")
