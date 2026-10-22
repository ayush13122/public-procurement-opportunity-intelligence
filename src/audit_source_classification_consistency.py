"""Record-level source-classification consistency audit.

This script DOES NOT change classifications. It compares the original source ZIP
against the generated niche-assignment file, exports suspicious source labels and
a representative sample of generic labels for review.

Run from the project root:
    python src/audit_source_classification_consistency.py
"""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd

DEFAULT_RAW_ZIP = Path("data/raw/datasets_of_assam_public_procurement_data_7259310.zip")
DEFAULT_ASSIGNMENTS = Path("reports/assam_record_niche_assignments.csv")
DEFAULT_OUTPUT = Path("reports/taxonomy_review/source_consistency_audit")

# These low-frequency source labels were flagged by the workbook audit because
# the associated examples appeared inconsistent with the label. All records with
# these labels are exported for record-level verification, not auto-reclassified.
HIGH_RISK_SOURCE_LABELS = {
    "Chemicals/Minerals",
    "Coal",
    "Entertainment/Musical Instruments",
    "Explosive",
    "Multi-crop Thresher",
    "Paddy Transplanter",
    "Security System",
    "Photostat Services",
    "Allotment of Space",
}

# Generic labels can legitimately contain many different deliverables. We take a
# deterministic sample to keep human review manageable.
GENERIC_LABEL_SAMPLE_SIZES = {
    "Miscellaneous Goods": 20,
    "Miscellaneous Services": 20,
    "Miscellaneous Works": 20,
    "Supply of Materials": 20,
}


def normalize_text(value: object) -> str:
    """Normalize text for consistency comparisons without changing source values."""
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def load_raw_procurement_zip(zip_path: Path) -> pd.DataFrame:
    """Load all fiscal-year tender CSV files from the original ZIP."""
    if not zip_path.exists():
        raise FileNotFoundError(f"Raw procurement ZIP not found: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        names = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
            and "ocds_mapped_procurement_data_fiscal_year_" in name.lower()
        ]
        if not names:
            raise ValueError(f"No fiscal-year procurement CSVs found in {zip_path}")
        frames = [pd.read_csv(archive.open(name), dtype=str, low_memory=False) for name in sorted(names)]
    data = pd.concat(frames, ignore_index=True)
    if "ocid" not in data.columns:
        raise ValueError("Original data is missing the 'ocid' identifier.")
    return data


def build_joined_audit(raw: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    """Join generated mapping outputs to source records by OCID and compare key fields."""
    if "ocid" not in raw.columns or "ocid" not in assignments.columns:
        raise ValueError("Both raw records and assignments must contain 'ocid'.")
    if raw["ocid"].duplicated().any():
        raise ValueError("Original raw data has duplicate OCIDs; audit join stopped.")
    if assignments["ocid"].duplicated().any():
        raise ValueError("Niche assignment file has duplicate OCIDs; audit join stopped.")

    source_cols = [
        column for column in [
            "ocid", "fiscal_year", "tender/title", "tender/mainProcurementCategory",
            "tenderclassification/description", "buyer/name", "tender/value/amount",
            "tender/datePublished", "tender/stage", "tender/numberOfTenderers",
        ] if column in raw.columns
    ]
    assignment_cols = [
        column for column in [
            "ocid", "suggested_analytical_niche", "mapping_method",
            "mapping_rationale", "manual_review_required",
        ] if column in assignments.columns
    ]
    merged = raw[source_cols].merge(
        assignments[assignment_cols], on="ocid", how="left", validate="one_to_one"
    )

    if "suggested_analytical_niche" not in merged.columns:
        merged["suggested_analytical_niche"] = ""
    if "mapping_method" not in merged.columns:
        merged["mapping_method"] = ""
    merged["source_label_review_flag"] = merged[
        "tenderclassification/description"
    ].fillna("").isin(HIGH_RISK_SOURCE_LABELS)

    # Generic records receive a separate sample-review flag; no label is changed.
    merged["generic_label_sample_flag"] = False
    for label in GENERIC_LABEL_SAMPLE_SIZES:
        mask = merged["tenderclassification/description"].fillna("").eq(label)
        merged.loc[mask, "generic_label_sample_flag"] = True

    # Compare source fields with assignment fields where the assignment file retains them.
    # Since assignments were generated from the same source this should usually be zero.
    merged["source_consistency_issue"] = ""
    title_col = "tender/title"
    class_col = "tenderclassification/description"
    if title_col in assignments.columns:
        source_title = raw[["ocid", title_col]].copy()
        source_title["title_norm"] = source_title[title_col].map(normalize_text)
        assigned_title = assignments[["ocid", title_col]].copy()
        assigned_title["assigned_title_norm"] = assigned_title[title_col].map(normalize_text)
        title_compare = source_title[["ocid", "title_norm"]].merge(
            assigned_title[["ocid", "assigned_title_norm"]], on="ocid", validate="one_to_one"
        )
        mismatches = set(title_compare.loc[
            title_compare["title_norm"] != title_compare["assigned_title_norm"], "ocid"
        ])
        merged.loc[merged["ocid"].isin(mismatches), "source_consistency_issue"] += "ASSIGNMENT_TITLE_DIFFERS_FROM_SOURCE;"

    if class_col in assignments.columns:
        source_class = raw[["ocid", class_col]].copy()
        source_class["class_norm"] = source_class[class_col].map(normalize_text)
        assigned_class = assignments[["ocid", class_col]].copy()
        assigned_class["assigned_class_norm"] = assigned_class[class_col].map(normalize_text)
        class_compare = source_class[["ocid", "class_norm"]].merge(
            assigned_class[["ocid", "assigned_class_norm"]], on="ocid", validate="one_to_one"
        )
        mismatches = set(class_compare.loc[
            class_compare["class_norm"] != class_compare["assigned_class_norm"], "ocid"
        ])
        merged.loc[merged["ocid"].isin(mismatches), "source_consistency_issue"] += "ASSIGNMENT_CLASS_DIFFERS_FROM_SOURCE;"

    return merged


def create_review_queue(joined: pd.DataFrame, random_state: int = 42) -> pd.DataFrame:
    """Return all high-risk-label records plus a reproducible sample of generic labels."""
    high_risk = joined[joined["source_label_review_flag"]].copy()
    high_risk["review_trigger"] = "HIGH_RISK_SOURCE_LABEL"
    samples = []
    for label, sample_size in GENERIC_LABEL_SAMPLE_SIZES.items():
        subset = joined[joined["tenderclassification/description"].fillna("").eq(label)]
        if not subset.empty:
            samples.append(subset.sample(n=min(sample_size, len(subset)), random_state=random_state).copy())
    generic = pd.concat(samples, ignore_index=True) if samples else joined.iloc[0:0].copy()
    if not generic.empty:
        generic["review_trigger"] = "GENERIC_LABEL_STRATIFIED_SAMPLE"
    queue = pd.concat([high_risk, generic], ignore_index=True)
    if not queue.empty:
        queue = queue.drop_duplicates(subset=["ocid"], keep="first")
        queue["review_status"] = "NOT_REVIEWED"
        queue["reviewer_approved_niche"] = ""
        queue["reviewer_notes"] = ""
        queue = queue.sort_values(
            ["review_trigger", "tenderclassification/description", "ocid"],
            kind="stable"
        )
    return queue


def write_markdown_summary(
    output_path: Path, raw: pd.DataFrame, assignments: pd.DataFrame,
    joined: pd.DataFrame, queue: pd.DataFrame
) -> None:
    source_counts = (
        joined.groupby("tenderclassification/description", dropna=False)
        .agg(
            records=("ocid", "size"),
            unique_buyers=("buyer/name", "nunique") if "buyer/name" in joined.columns else ("ocid", "size"),
        )
        .reset_index()
        .sort_values("records", ascending=False)
    )
    high = joined[joined["source_label_review_flag"]]
    generic = joined[joined["generic_label_sample_flag"]]
    unmatched = int(joined["suggested_analytical_niche"].isna().sum())
    mismatch_count = int(joined["source_consistency_issue"].ne("").sum())
    lines = [
        "# Record-Level Source Classification Consistency Audit",
        "",
        "This audit compares original tender records with generated niche assignments. ",
        "It does not approve, modify, or overwrite any classification.",
        "",
        "## Counts",
        f"- Raw source rows: **{len(raw):,}**",
        f"- Assignment rows: **{len(assignments):,}**",
        f"- Joined rows: **{len(joined):,}**",
        f"- Unique source OCIDs: **{raw['ocid'].nunique():,}**",
        f"- Records without a matched suggested niche: **{unmatched:,}**",
        f"- High-risk source-label records exported: **{len(high):,}**",
        f"- Generic-label records eligible for sample review: **{len(generic):,}**",
        f"- Assignment/source field disagreements detected: **{mismatch_count:,}**",
        f"- Final review queue rows: **{len(queue):,}**",
        "",
        "## High-risk source labels",
        "",
        "| Original classification | Records |",
        "|---|---:|",
    ]
    for label, count in high["tenderclassification/description"].value_counts().items():
        lines.append(f"| {label} | {count:,} |")
    lines += [
        "",
        "## Generic labels sampled",
        "",
        "| Original classification | Total source records | Sample size |",
        "|---|---:|---:|",
    ]
    sample_counts = queue[queue["review_trigger"].eq("GENERIC_LABEL_STRATIFIED_SAMPLE")][
        "tenderclassification/description"
    ].value_counts()
    for label, sample_size in sample_counts.items():
        total = int((joined["tenderclassification/description"] == label).sum())
        lines.append(f"| {label} | {total:,} | {sample_size:,} |")
    lines += [
        "",
        "## Rules for interpretation",
        "1. Preserve the source's original category and classification.",
        "2. Treat niche suggestions as provisional.",
        "3. A source-label/title conflict is a data-quality signal, not an automatic proof that the title is wrong.",
        "4. Review the actual OCID and title before changing a mapping rule.",
        "5. Do not infer eligibility, profitability, or win probability from category/title alone.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_audit(raw_zip: Path, assignments_path: Path, output_dir: Path) -> dict[str, int]:
    if not assignments_path.exists():
        raise FileNotFoundError(
            f"Niche assignment CSV not found: {assignments_path}. "
            "Run src/profile_procurement_categories.py first."
        )
    raw = load_raw_procurement_zip(raw_zip)
    assignments = pd.read_csv(assignments_path, dtype=str, low_memory=False)
    joined = build_joined_audit(raw, assignments)
    queue = create_review_queue(joined)

    output_dir.mkdir(parents=True, exist_ok=True)
    high = joined[joined["source_label_review_flag"]].copy()
    generic = queue[queue["review_trigger"].eq("GENERIC_LABEL_STRATIFIED_SAMPLE")].copy()
    summary_by_classification = (
        joined.groupby("tenderclassification/description", dropna=False)
        .agg(
            records=("ocid", "size"),
            unique_buyers=("buyer/name", "nunique") if "buyer/name" in joined.columns else ("ocid", "size"),
            suggested_niches=("suggested_analytical_niche", lambda s: " | ".join(sorted(set(s.dropna().astype(str))))),
        )
        .reset_index()
        .sort_values(["records", "tenderclassification/description"], ascending=[False, True])
    )
    field_mismatches = joined[joined["source_consistency_issue"].ne("")].copy()

    high.to_csv(output_dir / "high_risk_source_label_records.csv", index=False, encoding="utf-8-sig")
    generic.to_csv(output_dir / "generic_label_review_sample.csv", index=False, encoding="utf-8-sig")
    queue.to_csv(output_dir / "record_level_review_queue.csv", index=False, encoding="utf-8-sig")
    summary_by_classification.to_csv(output_dir / "source_classification_summary.csv", index=False, encoding="utf-8-sig")
    field_mismatches.to_csv(output_dir / "source_assignment_field_mismatches.csv", index=False, encoding="utf-8-sig")

    summary_path = output_dir / "SOURCE_CLASSIFICATION_CONSISTENCY_AUDIT.md"
    write_markdown_summary(summary_path, raw, assignments, joined, queue)
    return {
        "raw_rows": len(raw),
        "assignment_rows": len(assignments),
        "joined_rows": len(joined),
        "high_risk_source_label_records": len(high),
        "generic_label_review_sample": len(generic),
        "review_queue_rows": len(queue),
        "source_assignment_field_mismatches": len(field_mismatches),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-zip", type=Path, default=DEFAULT_RAW_ZIP)
    parser.add_argument("--assignments", type=Path, default=DEFAULT_ASSIGNMENTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    stats = run_audit(args.raw_zip, args.assignments, args.output_dir)
    print("Record-level source consistency audit complete.")
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value:,}")
    print(f"Reports: {args.output_dir.resolve()}")
    print(f"Summary: {(args.output_dir / 'SOURCE_CLASSIFICATION_CONSISTENCY_AUDIT.md').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
