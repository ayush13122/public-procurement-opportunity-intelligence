"""Validate generated business-analysis outputs against the latest source files.

Run from the project root:
    python src/validate_business_analysis_outputs.py

This script does not modify source data or existing business-analysis reports.
It writes validation findings to reports/business_analysis_validation/.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEANED_FILE = PROJECT_ROOT / "data" / "processed" / "assam_procurement_cleaned.csv"
ASSIGNMENTS_FILE = PROJECT_ROOT / "reports" / "assam_record_niche_assignments.csv"
BA_DIR = PROJECT_ROOT / "reports" / "business_analysis"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "business_analysis_validation"

REQUIRED_REPORTS = {
    "market_overview": BA_DIR / "01_market_overview.json",
    "broad_category_profile": BA_DIR / "02_broad_category_profile.csv",
    "provisional_niche_profile": BA_DIR / "03_provisional_niche_profile.csv",
    "fiscal_year_profile": BA_DIR / "04_fiscal_year_profile.csv",
    "top_buyers": BA_DIR / "05_top_buyers.csv",
    "tender_stage_profile": BA_DIR / "06_tender_stage_profile.csv",
    "source_classification_vs_niche": BA_DIR / "07_source_classification_vs_niche.csv",
}


def _normalise(series: pd.Series, missing_label: str = "Unknown / Missing") -> pd.Series:
    """Standardise string keys without changing the underlying source files."""
    result = series.astype("string").str.strip()
    return result.mask(result.isna() | result.eq(""), missing_label).astype(str)


def _count_map(series: pd.Series, key_name: str) -> pd.DataFrame:
    values = _normalise(series)
    return values.value_counts(dropna=False).rename_axis(key_name).reset_index(name="latest_count")


def _compare_counts(
    report_df: pd.DataFrame,
    report_key: str,
    report_count_col: str,
    current_df: pd.DataFrame,
    current_key: str,
    output_name: str,
) -> tuple[pd.DataFrame, bool]:
    """Compare an existing report to counts recomputed from current source files."""
    left = report_df[[report_key, report_count_col]].copy()
    left[report_key] = _normalise(left[report_key])
    left[report_count_col] = pd.to_numeric(left[report_count_col], errors="coerce").fillna(0).astype(int)
    left = left.rename(columns={report_key: "key", report_count_col: "report_count"})

    right = current_df[[current_key, "latest_count"]].copy()
    right[current_key] = _normalise(right[current_key])
    right = right.rename(columns={current_key: "key"})

    comparison = left.merge(right, on="key", how="outer")
    comparison[["report_count", "latest_count"]] = comparison[["report_count", "latest_count"]].fillna(0).astype(int)
    comparison["difference_report_minus_latest"] = comparison["report_count"] - comparison["latest_count"]
    comparison["status"] = comparison["difference_report_minus_latest"].map(lambda x: "PASS" if x == 0 else "MISMATCH")
    comparison = comparison.sort_values(["status", "key"], ascending=[False, True]).reset_index(drop=True)
    comparison.to_csv(OUTPUT_DIR / output_name, index=False, encoding="utf-8-sig")
    return comparison, bool((comparison["difference_report_minus_latest"] == 0).all())


def _group_count(df: pd.DataFrame, column: str, output_key: str) -> pd.DataFrame:
    values = _normalise(df[column])
    return values.value_counts(dropna=False).rename_axis(output_key).reset_index(name="latest_count")


def _crosswalk_counts(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "tender/mainProcurementCategory",
        "tenderclassification/description",
        "suggested_analytical_niche",
    ]
    for column in required:
        if column not in df.columns:
            raise KeyError(f"Required assignment column missing: {column}")
    temp = pd.DataFrame({
        "main_category_clean": _normalise(df[required[0]]),
        "source_classification_clean": _normalise(df[required[1]]),
        "niche_clean": _normalise(df[required[2]]),
    })
    return (
        temp.groupby(list(temp.columns), dropna=False)
        .size().reset_index(name="latest_count")
    )


def _compare_reported_subset(
    report_df: pd.DataFrame,
    report_key: str,
    report_count_col: str,
    current_df: pd.DataFrame,
    current_key: str,
    output_name: str,
) -> tuple[pd.DataFrame, bool]:
    """Compare only keys included by a top-N report (e.g. top 30 buyers)."""
    left = report_df[[report_key, report_count_col]].copy()
    left[report_key] = _normalise(left[report_key])
    left[report_count_col] = pd.to_numeric(left[report_count_col], errors="coerce").fillna(0).astype(int)
    left = left.rename(columns={report_key: "key", report_count_col: "report_count"})

    right = current_df[[current_key, "latest_count"]].copy()
    right[current_key] = _normalise(right[current_key])
    right = right.rename(columns={current_key: "key"})

    comparison = left.merge(right, on="key", how="left")
    comparison["latest_count"] = comparison["latest_count"].fillna(0).astype(int)
    comparison["difference_report_minus_latest"] = comparison["report_count"] - comparison["latest_count"]
    comparison["status"] = comparison["difference_report_minus_latest"].map(lambda x: "PASS" if x == 0 else "MISMATCH")
    comparison = comparison.sort_values(["status", "key"], ascending=[False, True]).reset_index(drop=True)
    comparison.to_csv(OUTPUT_DIR / output_name, index=False, encoding="utf-8-sig")
    return comparison, bool((comparison["difference_report_minus_latest"] == 0).all())


def _compare_crosswalk(report: pd.DataFrame, current: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    keys = ["main_category_clean", "source_classification_clean", "niche_clean"]
    report_side = report[keys + ["records"]].copy()
    report_side["records"] = pd.to_numeric(report_side["records"], errors="coerce").fillna(0).astype(int)
    report_side = report_side.rename(columns={"records": "report_count"})
    merged = report_side.merge(current, on=keys, how="outer")
    merged[["report_count", "latest_count"]] = merged[["report_count", "latest_count"]].fillna(0).astype(int)
    merged["difference_report_minus_latest"] = merged["report_count"] - merged["latest_count"]
    merged["status"] = merged["difference_report_minus_latest"].map(lambda x: "PASS" if x == 0 else "MISMATCH")
    merged = merged.sort_values(["status", "latest_count"], ascending=[False, False]).reset_index(drop=True)
    merged.to_csv(OUTPUT_DIR / "07_source_classification_vs_niche_validation.csv", index=False, encoding="utf-8-sig")
    return merged, bool((merged["difference_report_minus_latest"] == 0).all())


def _markdown_report(checks: list[dict], metrics: dict, mismatch_files: list[str]) -> str:
    lines = [
        "# Business Analysis Output Validation",
        "",
        "This report compares previously generated business-analysis reports with the latest cleaned dataset and niche assignments.",
        "It does not change or overwrite source data or analytical reports.",
        "",
        "## Source integrity checks",
        "",
        f"- Latest cleaned rows: **{metrics['cleaned_rows']:,}**",
        f"- Latest assignment rows: **{metrics['assignment_rows']:,}**",
        f"- Unique cleaned OCIDs: **{metrics['unique_cleaned_ocids']:,}**",
        f"- Duplicate cleaned OCID rows: **{metrics['duplicate_cleaned_ocid_rows']:,}**",
        f"- Unmatched assignment OCIDs: **{metrics['unmatched_assignment_ocids']:,}**",
        f"- Current niche review flags: **{metrics['current_review_flags']:,}**",
        "",
        "## Report consistency results",
        "",
        "| Check | Status | Mismatched keys |",
        "|---|---|---:|",
    ]
    for check in checks:
        lines.append(f"| {check['name']} | {check['status']} | {check['mismatch_keys']} |")
    lines.extend(["", "## Interpretation", ""])
    if mismatch_files:
        lines.append("Some business-analysis report files do not match the latest generated niche assignments or source records.")
        lines.append("Regenerate the business-analysis reports with `src/analyze_procurement_business.py` and rerun this validation script before building dashboard views that depend on those outputs.")
        lines.append("")
        lines.append("Mismatch detail files:")
        for name in mismatch_files:
            lines.append(f"- `{name}`")
    else:
        lines.append("The checked category, niche, fiscal-year, stage, buyer, and source-classification crosswalk outputs match the latest files for the checks implemented in this script.")
    lines.extend([
        "",
        "## Important caveats",
        "",
        "- Niche labels remain provisional until reviewed; distribution is not classification accuracy.",
        "- Historical Assam records are not current, India-wide opportunities.",
        "- Tender value is not supplier profit; verify currency/unit and the source definitions before commercial interpretation.",
        "- Counts of historical stages must not be interpreted as current tender availability.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    required = [CLEANED_FILE, ASSIGNMENTS_FILE, *REQUIRED_REPORTS.values()]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("Validation cannot run; required files are missing:")
        for path in missing:
            print(f"- {path}")
        return 2

    cleaned = pd.read_csv(CLEANED_FILE, low_memory=False)
    assignments = pd.read_csv(ASSIGNMENTS_FILE, low_memory=False)
    if "ocid" not in cleaned or "ocid" not in assignments:
        raise KeyError("Both cleaned data and assignments must include 'ocid'.")

    cleaned_ocids = _normalise(cleaned["ocid"], "")
    assignment_ocids = _normalise(assignments["ocid"], "")
    cleaned_unique = set(cleaned_ocids[cleaned_ocids != ""])
    assignment_unique = set(assignment_ocids[assignment_ocids != ""])
    matched_ids = cleaned_unique & assignment_unique
    review_col = "manual_review_required"
    if review_col in assignments.columns:
        current_review_flags = assignments[review_col].astype(str).str.strip().str.upper().isin({"YES", "TRUE", "1", "Y"}).sum()
    else:
        current_review_flags = -1

    metrics = {
        "cleaned_rows": len(cleaned),
        "assignment_rows": len(assignments),
        "unique_cleaned_ocids": cleaned["ocid"].nunique(dropna=True),
        "duplicate_cleaned_ocid_rows": int(cleaned["ocid"].duplicated().sum()),
        "unmatched_assignment_ocids": len(assignment_unique - cleaned_unique),
        "current_review_flags": int(current_review_flags),
    }

    checks: list[dict] = []
    mismatch_files: list[str] = []

    # Overall input/assignment alignment.
    alignment_status = "PASS" if (
        len(cleaned) == len(assignments)
        and metrics["duplicate_cleaned_ocid_rows"] == 0
        and len(cleaned_unique - assignment_unique) == 0
        and len(assignment_unique - cleaned_unique) == 0
    ) else "MISMATCH"
    checks.append({"name": "Source/assignment OCID alignment", "status": alignment_status, "mismatch_keys": 0 if alignment_status == "PASS" else 1})

    # Broad category counts.
    broad_report = pd.read_csv(REQUIRED_REPORTS["broad_category_profile"])
    broad_current = _group_count(cleaned, "tender/mainProcurementCategory", "main_category")
    broad_cmp, broad_ok = _compare_counts(broad_report, "main_category", "records", broad_current, "main_category", "02_broad_category_profile_validation.csv")
    checks.append({"name": "Broad category profile", "status": "PASS" if broad_ok else "MISMATCH", "mismatch_keys": int((broad_cmp["status"] == "MISMATCH").sum())})
    if not broad_ok: mismatch_files.append("02_broad_category_profile_validation.csv")

    # Provisional niche counts, checked against the latest assignments.
    niche_report = pd.read_csv(REQUIRED_REPORTS["provisional_niche_profile"])
    niche_current = _group_count(assignments, "suggested_analytical_niche", "suggested_niche")
    niche_cmp, niche_ok = _compare_counts(niche_report, "suggested_niche", "records", niche_current, "suggested_niche", "03_provisional_niche_profile_validation.csv")
    checks.append({"name": "Provisional niche profile", "status": "PASS" if niche_ok else "MISMATCH", "mismatch_keys": int((niche_cmp["status"] == "MISMATCH").sum())})
    if not niche_ok: mismatch_files.append("03_provisional_niche_profile_validation.csv")

    # Fiscal year counts.
    if "fiscal_year" in cleaned.columns:
        year_report = pd.read_csv(REQUIRED_REPORTS["fiscal_year_profile"])
        year_current = _group_count(cleaned, "fiscal_year", "fiscal_year")
        year_cmp, year_ok = _compare_counts(year_report, "fiscal_year", "records", year_current, "fiscal_year", "04_fiscal_year_profile_validation.csv")
        checks.append({"name": "Fiscal-year record counts", "status": "PASS" if year_ok else "MISMATCH", "mismatch_keys": int((year_cmp["status"] == "MISMATCH").sum())})
        if not year_ok: mismatch_files.append("04_fiscal_year_profile_validation.csv")

    # Tender-stage counts from latest assignments (includes normalised missing values).
    stage_report = pd.read_csv(REQUIRED_REPORTS["tender_stage_profile"])
    stage_current = _group_count(assignments, "tender/stage", "tender_stage")
    stage_cmp, stage_ok = _compare_counts(stage_report, "tender_stage", "records", stage_current, "tender_stage", "06_tender_stage_profile_validation.csv")
    checks.append({"name": "Tender-stage record counts", "status": "PASS" if stage_ok else "MISMATCH", "mismatch_keys": int((stage_cmp["status"] == "MISMATCH").sum())})
    if not stage_ok: mismatch_files.append("06_tender_stage_profile_validation.csv")

    # Top-buyer record counts for the buyers included in the report.
    buyers_report = pd.read_csv(REQUIRED_REPORTS["top_buyers"])
    buyer_current = _group_count(assignments, "buyer/name", "buyer")
    buyers_cmp, buyers_ok = _compare_reported_subset(buyers_report, "buyer", "records", buyer_current, "buyer", "05_top_buyers_validation.csv")
    checks.append({"name": "Reported top-buyer counts", "status": "PASS" if buyers_ok else "MISMATCH", "mismatch_keys": int((buyers_cmp["status"] == "MISMATCH").sum())})
    if not buyers_ok: mismatch_files.append("05_top_buyers_validation.csv")

    # Full crosswalk counts.
    crosswalk_report = pd.read_csv(REQUIRED_REPORTS["source_classification_vs_niche"])
    crosswalk_current = _crosswalk_counts(assignments)
    crosswalk_cmp, crosswalk_ok = _compare_crosswalk(crosswalk_report, crosswalk_current)
    checks.append({"name": "Source-classification/niche crosswalk", "status": "PASS" if crosswalk_ok else "MISMATCH", "mismatch_keys": int((crosswalk_cmp["status"] == "MISMATCH").sum())})
    if not crosswalk_ok: mismatch_files.append("07_source_classification_vs_niche_validation.csv")

    json_overview = json.loads(REQUIRED_REPORTS["market_overview"].read_text(encoding="utf-8"))
    json_rows_ok = int(json_overview.get("cleaned_rows", -1)) == len(cleaned) and int(json_overview.get("assignment_rows", -1)) == len(assignments)
    checks.append({"name": "Market overview row counts", "status": "PASS" if json_rows_ok else "MISMATCH", "mismatch_keys": 0 if json_rows_ok else 1})
    if not json_rows_ok:
        mismatch_file = OUTPUT_DIR / "01_market_overview_validation.json"
        mismatch_file.write_text(json.dumps({"report": json_overview, "latest_cleaned_rows": len(cleaned), "latest_assignment_rows": len(assignments)}, indent=2), encoding="utf-8")
        mismatch_files.append(mismatch_file.name)

    summary = _markdown_report(checks, metrics, mismatch_files)
    (OUTPUT_DIR / "BUSINESS_ANALYSIS_VALIDATION_SUMMARY.md").write_text(summary, encoding="utf-8")
    pd.DataFrame(checks).to_csv(OUTPUT_DIR / "validation_check_results.csv", index=False, encoding="utf-8-sig")

    print("Business-analysis output validation complete.")
    print(f"Cleaned rows: {metrics['cleaned_rows']:,} | assignment rows: {metrics['assignment_rows']:,}")
    print(f"Duplicate cleaned OCID rows: {metrics['duplicate_cleaned_ocid_rows']:,}")
    print("\nCHECK RESULTS")
    for check in checks:
        print(f"- {check['status']}: {check['name']} (mismatched keys: {check['mismatch_keys']})")
    print(f"\nSummary: {OUTPUT_DIR / 'BUSINESS_ANALYSIS_VALIDATION_SUMMARY.md'}")
    print(f"Check table: {OUTPUT_DIR / 'validation_check_results.csv'}")
    if mismatch_files:
        print("\nMismatch detail files:")
        for name in mismatch_files:
            print(f"- {OUTPUT_DIR / name}")
        print("\nRecommended next step: rerun src/analyze_procurement_business.py, then rerun this validation script.")
        return 1
    print("\nAll implemented comparisons passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
