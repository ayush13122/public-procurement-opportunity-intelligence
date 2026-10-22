"""Inspect known taxonomy mapping edge cases and other keyword candidates.

Run from project root: python src/inspect_mapping_examples.py
Writes an auditable CSV instead of relying on a one-off PowerShell Where-Object.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENTS = ROOT / "reports" / "assam_record_niche_assignments.csv"
OUT_DIR = ROOT / "reports" / "terminal_checks"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PATTERN = r"Plant Protection Materials|Rental Price of Factory Building|\bLAN\b|software|network"
SELECT_COLUMNS = [
    "ocid", "fiscal_year", "tender/title", "tender/mainProcurementCategory",
    "tenderclassification/description", "buyer/name", "tender/value/amount",
    "tender/datePublished", "tender/stage", "tender/numberOfTenderers",
    "suggested_analytical_niche", "mapping_method", "mapping_rationale",
    "manual_review_required",
]


def main() -> int:
    if not ASSIGNMENTS.exists():
        print(f"ERROR: Missing assignment file: {ASSIGNMENTS}")
        return 2
    df = pd.read_csv(ASSIGNMENTS, low_memory=False)
    if "tender/title" not in df.columns:
        print("ERROR: tender/title column is missing.")
        return 2
    mask = df["tender/title"].astype("string").fillna("").str.contains(PATTERN, case=False, regex=True)
    matched = df.loc[mask].copy()
    cols = [c for c in SELECT_COLUMNS if c in matched.columns]
    matched = matched[cols]
    matched.to_csv(OUT_DIR / "taxonomy_mapping_examples.csv", index=False)
    print("Matched example records:", len(matched))
    print("Output:", OUT_DIR / "taxonomy_mapping_examples.csv")
    if matched.empty:
        print("No matching titles found. Try reviewing the source file and adjust PATTERN if needed.")
    else:
        print(matched.to_string(index=False, max_colwidth=80))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
