"""Clean and profile the Assam procurement CSV bundle without altering raw data.

Usage (from project root):
    python src/clean_assam_procurement.py

The script reads the original ZIP under data/raw/, preserves all source rows,
creates an analysis-ready CSV under data/processed/, and writes audit reports.
"""
from __future__ import annotations

import csv
import io
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports"

EXPECTED_ZIP_HINT = "datasets_of_assam_public_procurement_data"
MISSING_TOKENS = {"", "na", "n/a", "n.a.", "nil", "null", "none", "nan"}

# Columns known to be misleading or non-informative based on the audit of this
# specific Assam export. Detection is still run against observed values below.
SEMANTICALLY_EXCLUDED = {
    "date": "Export/download date (2022-09-29), not the tender's event date.",
    "initiationType": "Constant metadata: 'tender' for every record.",
    "tag": "Constant metadata: 'tender' for every record.",
    "id": "Constant export-level ID: '1' for every record; not a unique tender ID.",
    "tender/status": "All values are NA in this export; carries no usable status information.",
    "tender/milestones/title": "Constant milestone text; not record-specific.",
    "tender/milestones/code": "Constant milestone text; inconsistent with milestone title and not record-specific.",
    "tender/milestones/type": "Constant milestone type; not record-specific.",
    "tender/milestones/dueDate": "All values are NA; no usable record-specific milestone date.",
    "tender/milestones/type.1": "Repeated constant milestone metadata; not record-specific.",
    "tender/milestones/title.1": "Repeated constant milestone metadata; not record-specific.",
    "tender/milestones/dueDate.1": "All values are NA; no usable record-specific milestone date.",
}

DATE_COLUMNS = ["tender/datePublished", "tender/bidOpening/date"]
NUMERIC_COLUMNS = [
    "tender/value/amount",
    "tender/numberOfTenderers",
    "tender/tenderPeriod/durationInDays",
]


def find_source_zip() -> Path:
    candidates = sorted(RAW_DIR.glob("*.zip"))
    if not candidates:
        raise FileNotFoundError(
            f"No ZIP found in {RAW_DIR}. Copy the original Assam procurement ZIP into data/raw/."
        )
    hinted = [p for p in candidates if EXPECTED_ZIP_HINT.lower() in p.name.lower()]
    if hinted:
        return hinted[0]
    # If only one ZIP exists, use it; otherwise ask the user to avoid selecting the wrong archive.
    if len(candidates) == 1:
        return candidates[0]
    names = ", ".join(p.name for p in candidates)
    raise FileNotFoundError(
        f"More than one ZIP is present in {RAW_DIR} and none matched '{EXPECTED_ZIP_HINT}'. "
        f"Keep the Assam source ZIP there with a recognizable filename. Found: {names}"
    )


def read_csv_members(zip_path: Path) -> tuple[pd.DataFrame, list[str]]:
    pieces: list[pd.DataFrame] = []
    source_members: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        members = sorted(
            n for n in zf.namelist()
            if n.lower().endswith(".csv") and n.lower().startswith("data/")
        )
        if not members:
            raise ValueError("No CSV files found under the ZIP's data/ directory.")
        expected_headers: list[str] | None = None
        for member in members:
            with zf.open(member) as binary:
                text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
                frame = pd.read_csv(text, dtype=str, keep_default_na=False, low_memory=False)
            if expected_headers is None:
                expected_headers = list(frame.columns)
            elif list(frame.columns) != expected_headers:
                raise ValueError(f"Column schema differs in {member}; source files need review.")
            frame["source_csv_file"] = Path(member).name
            pieces.append(frame)
            source_members.append(member)
    combined = pd.concat(pieces, ignore_index=True)
    return combined, source_members


def normalize_missing_tokens(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert blank/NA/NIL-like text to real missing values in the working copy."""
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == "object" or pd.api.types.is_string_dtype(out[col].dtype):
            s = out[col].astype("string").str.strip()
            out[col] = s.mask(s.str.lower().isin(MISSING_TOKENS), pd.NA)
    return out


def parse_mixed_date(value: object) -> pd.Timestamp | pd.NaT:
    if value is None or pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text or text.lower() in MISSING_TOKENS:
        return pd.NaT
    # Source has both ISO-like dates and dates like DD-MM-YYYY HH:MM.
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            return pd.to_datetime(text, errors="coerce", yearfirst=True, dayfirst=False)
        return pd.to_datetime(text, errors="coerce", dayfirst=True)
    except (ValueError, TypeError, OverflowError):
        return pd.NaT


def make_quality_report(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    nrows = len(frame)
    for col in frame.columns:
        s = frame[col]
        non_missing = s.dropna()
        unique_non_missing = int(non_missing.nunique(dropna=True))
        top_values = non_missing.value_counts(dropna=True).head(3)
        top_text = " | ".join(f"{str(k)[:70]} ({int(v)})" for k, v in top_values.items())
        rows.append({
            "column": col,
            "dtype_before_conversion": str(s.dtype),
            "row_count": nrows,
            "missing_count": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 2) if nrows else 0.0,
            "unique_non_missing_values": unique_non_missing,
            "constant_or_all_missing": unique_non_missing <= 1,
            "top_values": top_text,
        })
    return pd.DataFrame(rows).sort_values(
        ["missing_pct", "unique_non_missing_values"], ascending=[False, True]
    )


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    source_zip = find_source_zip()
    print(f"Source ZIP: {source_zip}")
    raw, members = read_csv_members(source_zip)
    original_rows = len(raw)
    original_cols = [c for c in raw.columns if c != "source_csv_file"]
    print(f"Source CSV files: {len(members)}")
    print(f"Rows loaded: {original_rows:,}")
    print(f"Original source columns: {len(original_cols)}")

    # Keep this in-memory copy for the row-integrity check. Raw ZIP is never edited.
    data = normalize_missing_tokens(raw)
    quality = make_quality_report(data.drop(columns=["source_csv_file"], errors="ignore"))
    quality.to_csv(REPORT_DIR / "assam_field_quality_report.csv", index=False, encoding="utf-8-sig")

    # Detect constant / empty columns empirically, with interpretation notes.
    constant_rows = []
    for col in original_cols:
        s = data[col]
        non_missing = s.dropna()
        unique_count = int(non_missing.nunique(dropna=True))
        all_missing = int(s.notna().sum()) == 0
        constant = unique_count <= 1
        reason = SEMANTICALLY_EXCLUDED.get(col, "")
        if all_missing and not reason:
            reason = "All values are missing after normalizing missing tokens."
        elif constant and not reason:
            reason = "Only one distinct non-missing value in this extract; review before using as a feature."
        constant_rows.append({
            "column": col,
            "non_missing_count": int(s.notna().sum()),
            "missing_count": int(s.isna().sum()),
            "unique_non_missing_values": unique_count,
            "all_missing": all_missing,
            "constant_or_all_missing": constant,
            "exclude_from_analytical_table": bool(col in SEMANTICALLY_EXCLUDED or constant),
            "reason": reason,
        })
    constant_report = pd.DataFrame(constant_rows)
    constant_report.to_csv(REPORT_DIR / "assam_constant_and_excluded_columns.csv", index=False, encoding="utf-8-sig")

    excluded = {
        row["column"] for row in constant_rows
        if row["exclude_from_analytical_table"]
    }
    # Explicitly remove the source export stamp even if a future snapshot varies it;
    # it describes extraction time, not the procurement event.
    excluded.add("date")
    # Preserve provenance in source_csv_file and preserve OCID as the record identifier.
    analytical = data.drop(columns=[c for c in excluded if c in data.columns], errors="ignore").copy()

    # Convert numeric measures to numeric values while keeping zeros (zeros are audited separately).
    for col in NUMERIC_COLUMNS:
        if col in analytical.columns:
            cleaned = analytical[col].astype("string").str.replace(",", "", regex=False).str.replace("₹", "", regex=False).str.strip()
            analytical[col] = pd.to_numeric(cleaned, errors="coerce")

    # Parse only real event date fields. The export-level `date` has already been excluded.
    for col in DATE_COLUMNS:
        if col in analytical.columns:
            analytical[col] = analytical[col].map(parse_mixed_date)

    # OCID is the source identifier. Do not silently drop duplicate rows; report them.
    ocid_col = "ocid" if "ocid" in data.columns else None
    duplicate_ocid_rows = int(data[ocid_col].duplicated(keep="first").sum()) if ocid_col else None
    null_ocid_rows = int(data[ocid_col].isna().sum()) if ocid_col else None
    amount_col = "tender/value/amount"
    zero_amount_count = None
    missing_amount_count = None
    if amount_col in analytical.columns:
        zero_amount_count = int((analytical[amount_col] == 0).sum())
        missing_amount_count = int(analytical[amount_col].isna().sum())

    clean_path = PROCESSED_DIR / "assam_procurement_cleaned.csv"
    analytical.to_csv(clean_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M:%S")

    summary_path = REPORT_DIR / "assam_cleaning_summary.md"
    summary_lines = [
        "# Assam Procurement Cleaning Summary",
        "",
        f"- Source ZIP: `{source_zip.name}`",
        f"- CSV members loaded: {len(members)}",
        f"- Original rows: {original_rows:,}",
        f"- Original source columns (excluding script-added provenance): {len(original_cols)}",
        f"- Rows in analytical output: {len(analytical):,}",
        f"- Columns in analytical output: {len(analytical.columns)}",
        f"- Duplicate OCID rows (reported, not silently removed): {duplicate_ocid_rows}",
        f"- Missing OCID rows: {null_ocid_rows}",
        f"- Zero tender-value rows (preserved and flagged): {zero_amount_count}",
        f"- Missing tender-value rows after normalization: {missing_amount_count}",
        "",
        "## Handling decisions",
        "",
        "- The original ZIP is never modified.",
        "- No tender rows are removed by this script.",
        "- Constant, all-missing, export-metadata and non-record-specific milestone columns are excluded from the analytical CSV and documented in `assam_constant_and_excluded_columns.csv`.",
        "- The `date` field is treated as the source export date, not a tender event date.",
        "- The source event dates `tender/datePublished` and `tender/bidOpening/date` are parsed to datetimes where parseable.",
        "- Tender amount, tenderer count and tender-period duration are converted to numeric where parseable.",
        "- Zero tender values are retained as zero and reported separately; they are not automatically converted to missing.",
        "- Source filenames are retained in `source_csv_file` for traceability.",
        "- A constant field is not proof of a universal truth; these exclusions apply to this specific export and should be revisited if new source data is added.",
        "",
        "## Files written",
        "",
        f"- Cleaned analytical table: `{clean_path.relative_to(PROJECT_ROOT)}`",
        "- Field quality report: `reports/assam_field_quality_report.csv`",
        "- Constant/excluded columns review: `reports/assam_constant_and_excluded_columns.csv`",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    if len(analytical) != original_rows:
        print("ERROR: Row count changed unexpectedly; do not proceed without review.", file=sys.stderr)
        return 2

    print("\nCleaning complete.")
    print(f"Rows preserved: {len(analytical):,} / {original_rows:,}")
    print(f"Columns in analytical table: {len(analytical.columns)}")
    print(f"Duplicate OCID rows (not removed): {duplicate_ocid_rows}")
    print(f"Cleaned data: {clean_path}")
    print(f"Field-quality report: {REPORT_DIR / 'assam_field_quality_report.csv'}")
    print(f"Constant/excluded columns report: {REPORT_DIR / 'assam_constant_and_excluded_columns.csv'}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
