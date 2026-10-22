"""Reproduce the earlier one-line cleaned-dataset checks as a reusable Python script.

Run from project root: python src/inspect_cleaned_dataset.py
Writes detailed CSV and Markdown outputs to reports/terminal_checks/.
"""
from __future__ import annotations
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "processed" / "assam_procurement_cleaned.csv"
OUT = ROOT / "reports" / "terminal_checks"
OUT.mkdir(parents=True, exist_ok=True)

BROAD_COL = "tender/mainProcurementCategory"
CLASS_COL = "tenderclassification/description"
TITLE_COL = "tender/title"
ID_COL = "ocid"
VALUE_COL = "tender/value/amount"
DATE_COL = "tender/datePublished"


def as_numeric(series: pd.Series) -> pd.Series:
    """Parse numeric values even if source strings contain thousands separators."""
    return pd.to_numeric(
        series.astype("string").str.replace(",", "", regex=False).str.strip()
        .replace({"": pd.NA, "NA": pd.NA, "N/A": pd.NA, "nan": pd.NA, "None": pd.NA}),
        errors="coerce",
    )


def main() -> int:
    if not DATA_FILE.exists():
        print(f"ERROR: Cleaned CSV not found: {DATA_FILE}")
        return 2
    df = pd.read_csv(DATA_FILE, low_memory=False)
    print("=== CLEANED DATASET VALIDATION ===")
    print("Python:", sys.executable)
    print("Shape:", df.shape)
    print("Unique OCIDs:", df[ID_COL].nunique(dropna=True) if ID_COL in df else "OCID column missing")
    if ID_COL in df:
        print("Duplicate OCID rows:", int(df[ID_COL].duplicated(keep=False).sum()))

    broad = (df[BROAD_COL].fillna("(MISSING)").value_counts(dropna=False)
             .rename_axis("category").reset_index(name="records")) if BROAD_COL in df else pd.DataFrame()
    classes = (df[CLASS_COL].fillna("(MISSING)").value_counts(dropna=False)
               .rename_axis("classification").reset_index(name="records")) if CLASS_COL in df else pd.DataFrame()
    missing = pd.DataFrame({"column": df.columns,
                            "missing_count": df.isna().sum().values,
                            "missing_pct": (df.isna().mean().values * 100).round(2)})
    missing = missing.sort_values(["missing_pct", "missing_count"], ascending=False)
    if VALUE_COL in df:
        val = as_numeric(df[VALUE_COL])
        value_stats = {
            "positive_values": int((val > 0).sum()),
            "zero_values": int((val == 0).sum()),
            "missing_or_non_numeric": int(val.isna().sum()),
            "negative_values": int((val < 0).sum()),
            "median_positive_value": float(val[val > 0].median()) if (val > 0).any() else None,
        }
    else:
        value_stats = {"note": f"Column {VALUE_COL} is missing"}
    date_stats = {}
    if DATE_COL in df:
        parsed = pd.to_datetime(df[DATE_COL], errors="coerce")
        date_stats = {"publication_dates_parsed": int(parsed.notna().sum()),
                      "publication_date_rows": len(df),
                      "earliest_publication": str(parsed.min()) if parsed.notna().any() else None,
                      "latest_publication": str(parsed.max()) if parsed.notna().any() else None}

    broad.to_csv(OUT / "cleaned_broad_category_counts.csv", index=False)
    classes.head(15).to_csv(OUT / "cleaned_top15_classifications.csv", index=False)
    missing.to_csv(OUT / "cleaned_field_missingness.csv", index=False)
    lines = ["# Cleaned Dataset Validation", "", f"- Input file: `{DATA_FILE.relative_to(ROOT)}`",
             f"- Rows: {len(df):,}", f"- Columns: {df.shape[1]}",
             f"- Unique OCIDs: {df[ID_COL].nunique(dropna=True):,}" if ID_COL in df else "- OCID column missing",
             f"- Duplicate OCID rows: {int(df[ID_COL].duplicated(keep=False).sum()):,}" if ID_COL in df else "- Duplicate check skipped",
             "", "## Broad Category Counts", "", broad.to_markdown(index=False) if not broad.empty else "Category column not found.",
             "", "## Top 15 Detailed Classifications", "", classes.head(15).to_markdown(index=False) if not classes.empty else "Classification column not found.",
             "", "## Tender Value Checks", ""]
    lines += [f"- {k}: {v}" for k, v in value_stats.items()]
    lines += ["", "## Publication Date Checks", ""]
    lines += [f"- {k}: {v}" for k, v in date_stats.items()]
    lines += ["", "## Top 10 Fields by Missing Percentage", "", missing.head(10).to_markdown(index=False), ""]
    report = OUT / "cleaned_dataset_validation.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\nBROAD CATEGORIES\n", broad.to_string(index=False))
    print("\nTOP 15 CLASSIFICATIONS\n", classes.head(15).to_string(index=False))
    print("\nTOP 10 MISSING FIELDS (%)\n", missing.head(10).to_string(index=False))
    print("\nTENDER VALUE CHECKS\n", value_stats)
    print("\nReports saved to:", OUT)
    print("Summary:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
