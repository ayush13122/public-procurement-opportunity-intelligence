"""Replace previous ad-hoc PowerShell inspection of taxonomy outputs.

Run from project root: python src/inspect_taxonomy_outputs.py
Creates repeatable reports for mapping-method counts, niche counts, review queue,
review examples, and title-keyword candidate reconciliation.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TAX = REPORTS / "taxonomy_review"
OUT = REPORTS / "terminal_checks"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required report not found: {path.relative_to(ROOT)}")
    return pd.read_csv(path, low_memory=False)


def s(df: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    if column not in df.columns:
        return pd.Series([default] * len(df), index=df.index, dtype="string")
    return df[column].astype("string").fillna("").str.strip()


def main() -> int:
    assignments = read_csv_required(REPORTS / "assam_record_niche_assignments.csv")
    queue = read_csv_required(TAX / "00_classification_review_queue.csv")
    review = read_csv_required(TAX / "01_records_requiring_review.csv")
    method_summary_path = TAX / "03_mapping_method_summary.csv"
    method_summary = pd.read_csv(method_summary_path) if method_summary_path.exists() else pd.DataFrame()
    summary_path = TAX / "TAXONOMY_REVIEW_SUMMARY.md"
    summary_text = summary_path.read_text(encoding="utf-8", errors="replace") if summary_path.exists() else "(Summary markdown not found.)"

    assignment_niche_col = "suggested_analytical_niche"
    assignment_counts = assignments[assignment_niche_col].fillna("(BLANK / NO NICHE)").replace("", "(BLANK / NO NICHE)").value_counts(dropna=False).rename_axis("niche").reset_index(name="records")
    assignment_counts["record_pct"] = (assignment_counts["records"] / max(len(assignments), 1) * 100).round(2)
    assignment_counts.to_csv(OUT / "taxonomy_all_niche_counts.csv", index=False)
    queue.to_csv(OUT / "taxonomy_classification_review_queue_copy.csv", index=False)

    method_col = s(review, "mapping_method")
    candidate_mask = method_col.eq("TITLE_KEYWORD_CANDIDATE")
    candidates = review.loc[candidate_mask].copy()
    candidates["suggested_analytical_niche"] = s(candidates, "suggested_analytical_niche").replace("", "(BLANK / NO NICHE SUGGESTED)")
    candidate_counts = candidates["suggested_analytical_niche"].value_counts(dropna=False).rename_axis("suggested_niche").reset_index(name="records")
    candidate_counts["candidate_pct"] = (candidate_counts["records"] / max(len(candidates), 1) * 100).round(2)
    candidate_counts.to_csv(OUT / "taxonomy_title_keyword_candidate_counts_including_blank.csv", index=False)

    blank_candidates = int(s(review.loc[candidate_mask], "suggested_analytical_niche").eq("").sum())
    candidate_count = int(candidate_mask.sum())
    candidate_group_sum = int(candidate_counts["records"].sum())
    niche_suggestion_counts = (s(assignments, assignment_niche_col).replace("", "(BLANK / NO NICHE)")
                               .value_counts(dropna=False).rename_axis("niche").reset_index(name="records"))
    niche_suggestion_counts.to_csv(OUT / "taxonomy_assignment_niche_counts.csv", index=False)

    # Same equivalent of Select-Object -First 15 and review sample - but repeatable.
    queue.head(15).to_csv(OUT / "taxonomy_first_15_classifications.csv", index=False)
    review.head(10).to_csv(OUT / "taxonomy_first_10_review_records.csv", index=False)
    method_col_assign = s(assignments, "mapping_method")
    method_distribution = method_col_assign.value_counts(dropna=False).rename_axis("mapping_method").reset_index(name="records")
    method_distribution["record_pct"] = (method_distribution["records"] / max(len(assignments), 1) * 100).round(2)
    method_distribution.to_csv(OUT / "taxonomy_assignment_method_counts.csv", index=False)

    lines = ["# Taxonomy Output Inspection", "", f"- Assignment records: {len(assignments):,}",
             f"- Classification review queue rows: {len(queue):,}", f"- Review records: {len(review):,}",
             f"- Title-keyword candidate rows in review file: {candidate_count:,}",
             f"- Candidate rows with blank niche: {blank_candidates:,}",
             f"- Candidate grouped count total (blank category included): {candidate_group_sum:,}",
             f"- Candidate reconciliation: {'PASS' if candidate_count == candidate_group_sum else 'CHECK'}", "",
             "## Assignment Method Counts", "", method_distribution.to_markdown(index=False),
             "", "## Candidate Counts by Suggested Niche (including blank) ", "", candidate_counts.to_markdown(index=False),
             "", "## All Assignment Niche Counts", "", assignment_counts.to_markdown(index=False),
             "", "## First 15 Classification Queue Rows", "", queue.head(15).to_markdown(index=False),
             "", "## First 10 Review Records", "", review.head(10).to_markdown(index=False),
             "", "## Existing Taxonomy Summary", "", summary_text, ""]
    out_summary = OUT / "taxonomy_output_inspection.md"
    out_summary.write_text("\n".join(lines), encoding="utf-8")
    print("=== TAXONOMY COUNTS ===")
    print("Assignment records:", len(assignments))
    print("Review records:", len(review))
    print("Title-keyword candidates:", candidate_count)
    print("Candidates with blank niche:", blank_candidates)
    print("Grouped candidate count (blank included):", candidate_group_sum)
    print("Candidate count reconciliation:", "PASS" if candidate_count == candidate_group_sum else "CHECK")
    print("\n=== TOP NICHES (all assignments) ===\n", assignment_counts.head(20).to_string(index=False))
    print("\n=== TITLE-KEYWORD CANDIDATE COUNTS (including blanks) ===\n", candidate_counts.to_string(index=False))
    print("\nReports saved to:", OUT)
    print("Summary:", out_summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
