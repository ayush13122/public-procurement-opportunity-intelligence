"""Build a transparent review pack for the Assam procurement niche taxonomy.

Run from the project root:
    python src/review_niche_taxonomy.py

Reads existing outputs from:
    reports/assam_niche_mapping_review.csv
    reports/assam_record_niche_assignments.csv
    data/processed/assam_procurement_cleaned.csv

Writes non-destructive review files under reports/taxonomy_review/.
No raw or cleaned data is changed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_DIR = REPORTS_DIR / "taxonomy_review"
CLASS_REVIEW_FILE = REPORTS_DIR / "assam_niche_mapping_review.csv"
RECORD_ASSIGNMENTS_FILE = REPORTS_DIR / "assam_record_niche_assignments.csv"
CLEANED_DATA_FILE = PROJECT_ROOT / "data" / "processed" / "assam_procurement_cleaned.csv"

CLASS_REQUIRED = {
    "original_classification", "record_count", "record_pct", "dominant_main_category",
    "dominant_category_pct_within_label", "suggested_analytical_niche", "mapping_rationale",
    "mapping_status", "sample_titles_for_review",
}
RECORD_REQUIRED = {
    "ocid", "tender/title", "tender/mainProcurementCategory", "tenderclassification/description",
    "buyer/name", "tender/value/amount", "tender/datePublished", "suggested_analytical_niche",
    "mapping_method", "mapping_rationale", "manual_review_required",
}


def _require_columns(df: pd.DataFrame, expected: set[str], label: str) -> None:
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {sorted(missing)}")


def priority_for_mapping(status: object, records: object) -> str:
    status_text = str(status).strip().upper()
    try:
        count = int(float(records))
    except (ValueError, TypeError):
        count = 0
    if status_text == "REVIEW" or count >= 1000:
        return "HIGH"
    if count >= 100:
        return "MEDIUM"
    return "LOW"


def build_taxonomy_review_frames(
    class_df: pd.DataFrame, record_df: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """Prepare editable taxonomy queue, record queue, method stats, and stratified sample."""
    _require_columns(class_df, CLASS_REQUIRED, "Classification mapping report")
    _require_columns(record_df, RECORD_REQUIRED, "Record assignment report")

    classes = class_df.copy()
    classes["review_priority"] = classes.apply(
        lambda row: priority_for_mapping(row["mapping_status"], row["record_count"]), axis=1
    )
    # Explicitly leave final approval empty: a rule-based suggestion is not verified truth.
    classes["reviewer_decision"] = ""
    classes["approved_analytical_niche"] = ""
    classes["reviewer_notes"] = ""
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    classes["_priority_sort"] = classes["review_priority"].map(priority_order)
    classes = classes.sort_values(
        ["_priority_sort", "record_count", "original_classification"],
        ascending=[True, False, True],
    ).drop(columns="_priority_sort")

    records = record_df.copy()
    flag = records["manual_review_required"].astype("string").fillna("").str.upper().str.strip()
    method = records["mapping_method"].astype("string").fillna("").str.upper().str.strip()
    needs_review = flag.eq("YES") | method.eq("UNRESOLVED")
    review_records = records.loc[needs_review].copy()
    review_records["review_reason"] = review_records.apply(
        lambda row: (
            "UNRESOLVED: classification/title did not produce a reliable niche"
            if str(row.get("mapping_method", "")).upper() == "UNRESOLVED"
            else "TITLE_KEYWORD_CANDIDATE: verify title-based match against notice"
            if str(row.get("mapping_method", "")).upper() == "TITLE_KEYWORD_CANDIDATE"
            else "MANUAL_REVIEW_FLAGGED",
        )[0],
        axis=1,
    )
    review_records["reviewer_decision"] = ""
    review_records["approved_analytical_niche"] = ""
    review_records["reviewer_notes"] = ""
    keep = [
        "ocid", "fiscal_year", "tender/title", "tender/mainProcurementCategory",
        "tenderclassification/description", "buyer/name", "tender/value/amount",
        "tender/datePublished", "tender/stage", "tender/numberOfTenderers",
        "suggested_analytical_niche", "mapping_method", "mapping_rationale",
        "manual_review_required", "review_reason", "reviewer_decision",
        "approved_analytical_niche", "reviewer_notes",
    ]
    review_records = review_records[[c for c in keep if c in review_records.columns]]
    review_records = review_records.sort_values(
        ["mapping_method", "tenderclassification/description", "ocid"], na_position="last"
    )

    # A reviewable, deterministic sample across mapping methods and suggested niches.
    sample_source = records.copy()
    sample_source["_method"] = sample_source["mapping_method"].astype("string").fillna("[MISSING]")
    sample_source["_niche"] = sample_source["suggested_analytical_niche"].astype("string").fillna("[MISSING]")
    sample_source["_class"] = sample_source["tenderclassification/description"].astype("string").fillna("[MISSING]")
    sample_source = sample_source.sort_values("ocid", kind="stable")
    sample = (
        sample_source.groupby(["_method", "_niche", "_class"], dropna=False, group_keys=False)
        .head(5)
        .copy()
    )
    sample["reviewer_decision"] = ""
    sample["approved_analytical_niche"] = ""
    sample["reviewer_notes"] = ""
    sample_cols = [
        "ocid", "tender/title", "tender/mainProcurementCategory",
        "tenderclassification/description", "suggested_analytical_niche", "mapping_method",
        "mapping_rationale", "manual_review_required", "reviewer_decision",
        "approved_analytical_niche", "reviewer_notes",
    ]
    sample = sample[[c for c in sample_cols if c in sample.columns]].reset_index(drop=True)

    method_summary = (
        records.groupby("mapping_method", dropna=False)
        .agg(
            record_count=("ocid", "size"),
            unique_buyers=("buyer/name", "nunique"),
            suggested_niches=("suggested_analytical_niche", "nunique"),
            review_flagged=("manual_review_required", lambda s: int(s.astype("string").fillna("").str.upper().eq("YES").sum())),
        )
        .reset_index()
    )
    method_summary["record_pct"] = (method_summary["record_count"] / max(len(records), 1) * 100).round(2)
    method_summary["review_flag_pct_within_method"] = (
        method_summary["review_flagged"] / method_summary["record_count"].replace(0, pd.NA) * 100
    ).round(2)
    method_summary = method_summary.sort_values("record_count", ascending=False)

    niche_summary = (
        records.groupby("suggested_analytical_niche", dropna=False)
        .agg(
            record_count=("ocid", "size"),
            unique_buyers=("buyer/name", "nunique"),
            unique_source_classifications=("tenderclassification/description", "nunique"),
            title_keyword_candidates=("mapping_method", lambda s: int(s.astype("string").eq("TITLE_KEYWORD_CANDIDATE").sum())),
            unresolved_records=("mapping_method", lambda s: int(s.astype("string").eq("UNRESOLVED").sum())),
            manual_review_flagged=("manual_review_required", lambda s: int(s.astype("string").fillna("").str.upper().eq("YES").sum())),
        )
        .reset_index()
    )
    niche_summary["record_pct"] = (niche_summary["record_count"] / max(len(records), 1) * 100).round(2)
    niche_summary["manual_review_pct"] = (
        niche_summary["manual_review_flagged"] / niche_summary["record_count"].replace(0, pd.NA) * 100
    ).round(2)
    niche_summary = niche_summary.sort_values("record_count", ascending=False)

    return {
        "classification_review_queue": classes,
        "records_requiring_review": review_records,
        "mapping_method_summary": method_summary,
        "niche_risk_summary": niche_summary,
        "stratified_sample": sample,
    }


def write_summary(outputs: Dict[str, pd.DataFrame], output_dir: Path) -> None:
    classes = outputs["classification_review_queue"]
    reviews = outputs["records_requiring_review"]
    methods = outputs["mapping_method_summary"]
    niches = outputs["niche_risk_summary"]
    lines = [
        "# Niche Taxonomy Review Summary", "",
        "## Purpose", "",
        "This review pack separates rule-based candidate labels from human-verified taxonomy decisions.",
        "Do not use a suggested niche as ground truth until its classification or sample records have been reviewed.", "",
        "## Data volume", "",
        f"- Source classifications in review queue: **{len(classes):,}**",
        f"- Records flagged for manual review or unresolved mapping: **{len(reviews):,}**",
        f"- Stratified record sample for first-pass spot-check: **{len(outputs['stratified_sample']):,}**",
        "", "## Priority guide", "",
        "- **HIGH**: source label is already marked REVIEW or represents at least 1,000 records.",
        "- **MEDIUM**: 100–999 records.",
        "- **LOW**: fewer than 100 records.",
        "", "## Current mapping methods", "",
        methods.to_markdown(index=False), "", "## Largest candidate niches", "",
        niches.head(15).to_markdown(index=False), "", "## Files", "",
        "- `00_classification_review_queue.csv`: editable decisions for the 89 source classifications.",
        "- `01_records_requiring_review.csv`: all records flagged for review or unresolved mapping.",
        "- `02_stratified_record_sample.csv`: compact sample across methods/niches/classifications.",
        "- `03_mapping_method_summary.csv`: records and review burden by mapping method.",
        "- `04_niche_risk_summary.csv`: counts and review risks by proposed niche.",
        "", "## Review rule", "",
        "Approve or change the niche based on source classification and sampled tender titles. Preserve the original classification. "
        "For ambiguous titles, keep `Other / Needs Review` or use a more general category; do not force a precise niche.", "",
    ]
    (output_dir / "TAXONOMY_REVIEW_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    missing_files = [p for p in [CLASS_REVIEW_FILE, RECORD_ASSIGNMENTS_FILE, CLEANED_DATA_FILE] if not p.exists()]
    if missing_files:
        paths = "\n".join(f"- {p}" for p in missing_files)
        raise FileNotFoundError(
            "Required inputs are missing. Run category profiling and cleaning first:\n" + paths
        )
    class_df = pd.read_csv(CLASS_REVIEW_FILE, low_memory=False)
    record_df = pd.read_csv(RECORD_ASSIGNMENTS_FILE, low_memory=False)
    cleaned_df = pd.read_csv(CLEANED_DATA_FILE, low_memory=False)
    if len(record_df) != len(cleaned_df):
        raise ValueError(
            f"Record assignments ({len(record_df):,}) do not match cleaned rows ({len(cleaned_df):,}). "
            "Stop and reconcile record IDs before proceeding."
        )
    if "ocid" in record_df and "ocid" in cleaned_df and not record_df["ocid"].equals(cleaned_df["ocid"]):
        # Order can differ between files; compare sets and uniqueness before proceeding.
        if set(record_df["ocid"].astype(str)) != set(cleaned_df["ocid"].astype(str)):
            raise ValueError("OCID sets differ between assignment report and cleaned dataset.")
    outputs = build_taxonomy_review_frames(class_df, record_df)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filenames = {
        "classification_review_queue": "00_classification_review_queue.csv",
        "records_requiring_review": "01_records_requiring_review.csv",
        "stratified_sample": "02_stratified_record_sample.csv",
        "mapping_method_summary": "03_mapping_method_summary.csv",
        "niche_risk_summary": "04_niche_risk_summary.csv",
    }
    for key, filename in filenames.items():
        outputs[key].to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")
    write_summary(outputs, OUTPUT_DIR)
    print("Niche taxonomy review pack generated.")
    print(f"Source classifications: {len(class_df):,}")
    print(f"Assignment records: {len(record_df):,}")
    print(f"Records to review: {len(outputs['records_requiring_review']):,}")
    print(f"Stratified sample rows: {len(outputs['stratified_sample']):,}")
    print(f"Outputs: {OUTPUT_DIR}")
    print(f"Summary: {OUTPUT_DIR / 'TAXONOMY_REVIEW_SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
