"""Business-focused exploratory analysis for Assam procurement records.

Reads the cleaned historical dataset and the provisional niche assignments,
checks the join, produces CSV summaries/HTML charts/Markdown findings, and does
not modify source data or make bid-win/profit predictions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    import plotly.express as px
except ImportError:  # chart generation should be optional
    px = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# If script lives in a copied project src/ folder, parents[1] is the project root.
CLEANED_PATH = PROJECT_ROOT / "data" / "processed" / "assam_procurement_cleaned.csv"
ASSIGNMENTS_PATH = PROJECT_ROOT / "reports" / "assam_record_niche_assignments.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "business_analysis"

REQUIRED_CLEANED_COLUMNS = [
    "ocid",
    "fiscal_year",
    "tender/mainProcurementCategory",
    "tenderclassification/description",
    "tender/title",
    "buyer/name",
    "tender/value/amount",
    "tender/datePublished",
    "tender/stage",
    "tender/numberOfTenderers",
]
ASSIGNMENT_COLUMNS = [
    "ocid",
    "suggested_analytical_niche",
    "mapping_method",
    "manual_review_required",
]


def normalize_missing(series: pd.Series) -> pd.Series:
    """Convert common text placeholders into pandas NA without altering source files."""
    result = series.copy()
    text = result.astype("string").str.strip()
    missing_tokens = {"", "NA", "N/A", "NIL", "NULL", "NONE", "NAN", "-"}
    result = result.mask(text.str.upper().isin(missing_tokens))
    return result


def parse_amount(series: pd.Series) -> pd.Series:
    """Parse tender values including Indian comma grouping, preserving true zeros."""
    cleaned = normalize_missing(series).astype("string")
    cleaned = cleaned.str.replace(",", "", regex=False)
    cleaned = cleaned.str.replace(r"[₹$\s]", "", regex=True)
    cleaned = cleaned.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def parse_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(normalize_missing(series), errors="coerce")


def share(count: int | float, total: int | float) -> float:
    return round((float(count) / float(total) * 100.0), 2) if total else 0.0


def require_columns(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def load_and_join(cleaned_path: Path, assignments_path: Path) -> tuple[pd.DataFrame, dict]:
    if not cleaned_path.exists():
        raise FileNotFoundError(f"Cleaned dataset not found: {cleaned_path}")
    if not assignments_path.exists():
        raise FileNotFoundError(f"Niche assignment file not found: {assignments_path}")
    cleaned = pd.read_csv(cleaned_path, low_memory=False)
    assignments = pd.read_csv(assignments_path, low_memory=False)
    return load_and_join_from_frames(cleaned, assignments)


def load_and_join_from_frames(cleaned: pd.DataFrame, assignments: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cleaned = cleaned.copy()
    assignments = assignments.copy()
    require_columns(cleaned, REQUIRED_CLEANED_COLUMNS, "Cleaned dataset")
    require_columns(assignments, ASSIGNMENT_COLUMNS, "Niche assignments")

    source_duplicate_ocids = int(cleaned["ocid"].duplicated().sum())
    assignment_duplicate_ocids = int(assignments["ocid"].duplicated().sum())
    if source_duplicate_ocids or assignment_duplicate_ocids:
        raise ValueError(
            "OCID must be unique in both inputs; "
            f"cleaned duplicates={source_duplicate_ocids}, assignments duplicates={assignment_duplicate_ocids}"
        )

    selected = assignments[ASSIGNMENT_COLUMNS].copy()
    joined = cleaned.merge(selected, on="ocid", how="left", validate="one_to_one", indicator=True)
    unmatched = int((joined["_merge"] != "both").sum())
    joined = joined.drop(columns=["_merge"])

    joined["tender_value_numeric"] = parse_amount(joined["tender/value/amount"])
    joined["tenderers_numeric"] = parse_numeric(joined["tender/numberOfTenderers"])
    joined["publication_date_parsed"] = pd.to_datetime(
        normalize_missing(joined["tender/datePublished"]), errors="coerce"
    )
    joined["main_category_clean"] = normalize_missing(joined["tender/mainProcurementCategory"]).fillna("Unknown")
    joined["source_classification_clean"] = normalize_missing(
        joined["tenderclassification/description"]
    ).fillna("Unknown")
    joined["niche_clean"] = normalize_missing(joined["suggested_analytical_niche"]).fillna("Other / Needs Review")
    joined["buyer_clean"] = normalize_missing(joined["buyer/name"]).fillna("Unknown buyer")
    joined["stage_clean"] = normalize_missing(joined["tender/stage"]).fillna("Unknown / Missing")
    joined["fiscal_year_clean"] = normalize_missing(joined["fiscal_year"]).fillna("Unknown")

    # Conservative flags: zero is not treated as missing, but is separately reported.
    joined["value_status"] = "positive"
    joined.loc[joined["tender_value_numeric"].isna(), "value_status"] = "missing_or_non_numeric"
    joined.loc[joined["tender_value_numeric"].eq(0), "value_status"] = "zero"
    joined.loc[joined["tender_value_numeric"].lt(0), "value_status"] = "negative"

    review_text = joined["manual_review_required"].astype("string").str.strip().str.upper()
    joined["needs_niche_review"] = review_text.isin({"YES", "TRUE", "1", "Y"})

    diagnostics = {
        "cleaned_rows": int(len(cleaned)),
        "assignment_rows": int(len(assignments)),
        "joined_rows": int(len(joined)),
        "cleaned_columns": int(len(cleaned.columns)),
        "source_duplicate_ocids": source_duplicate_ocids,
        "assignment_duplicate_ocids": assignment_duplicate_ocids,
        "unmatched_assignments": unmatched,
        "unique_ocids": int(joined["ocid"].nunique(dropna=True)),
        "parsed_publication_dates": int(joined["publication_date_parsed"].notna().sum()),
        "positive_values": int(joined["value_status"].eq("positive").sum()),
        "zero_values": int(joined["value_status"].eq("zero").sum()),
        "missing_values": int(joined["value_status"].eq("missing_or_non_numeric").sum()),
        "negative_values": int(joined["value_status"].eq("negative").sum()),
        "records_needing_niche_review": int(joined["needs_niche_review"].sum()),
    }
    return joined, diagnostics


def _value_stats(group: pd.DataFrame) -> dict:
    vals = group.loc[group["tender_value_numeric"] > 0, "tender_value_numeric"].dropna()
    return {
        "positive_value_records": int(len(vals)),
        "zero_value_records": int(group["value_status"].eq("zero").sum()),
        "missing_value_records": int(group["value_status"].eq("missing_or_non_numeric").sum()),
        "median_positive_value": round(float(vals.median()), 2) if len(vals) else None,
        "mean_positive_value": round(float(vals.mean()), 2) if len(vals) else None,
        # Sum is deliberately omitted: mixed missing/zero values make total tender value easy to misinterpret.
    }


def category_profile(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    rows = []
    for category, group in df.groupby("main_category_clean", dropna=False):
        rows.append({
            "main_category": category,
            "records": int(len(group)),
            "record_share_pct": share(len(group), total),
            "unique_buyers": int(group["buyer_clean"].nunique()),
            "unique_classifications": int(group["source_classification_clean"].nunique()),
            **_value_stats(group),
        })
    return pd.DataFrame(rows).sort_values("records", ascending=False)


def niche_profile(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    rows = []
    for niche, group in df.groupby("niche_clean", dropna=False):
        rows.append({
            "suggested_niche": niche,
            "records": int(len(group)),
            "record_share_pct": share(len(group), total),
            "unique_buyers": int(group["buyer_clean"].nunique()),
            "unique_source_classifications": int(group["source_classification_clean"].nunique()),
            "records_needing_review": int(group["needs_niche_review"].sum()),
            "review_share_pct_within_niche": share(group["needs_niche_review"].sum(), len(group)),
            **_value_stats(group),
        })
    return pd.DataFrame(rows).sort_values("records", ascending=False)


def fiscal_year_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, group in df.groupby("fiscal_year_clean", dropna=False):
        rows.append({
            "fiscal_year": year,
            "records": int(len(group)),
            "unique_buyers": int(group["buyer_clean"].nunique()),
            "unique_classifications": int(group["source_classification_clean"].nunique()),
            "publication_dates_parsed": int(group["publication_date_parsed"].notna().sum()),
            **_value_stats(group),
        })
    result = pd.DataFrame(rows)
    # Fiscal year strings are presented lexically; values here are of the form YYYY-YYYY.
    return result.sort_values("fiscal_year")


def buyer_profile(df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    rows = []
    for buyer, group in df.groupby("buyer_clean", dropna=False):
        rows.append({
            "buyer": buyer,
            "records": int(len(group)),
            "record_share_pct": share(len(group), len(df)),
            "broad_categories": int(group["main_category_clean"].nunique()),
            "suggested_niches": int(group["niche_clean"].nunique()),
            "median_positive_value": _value_stats(group)["median_positive_value"],
            "positive_value_records": _value_stats(group)["positive_value_records"],
        })
    return pd.DataFrame(rows).sort_values(["records", "buyer"], ascending=[False, True]).head(top_n)


def stage_profile(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby("stage_clean", dropna=False)
        .agg(records=("ocid", "size"), unique_buyers=("buyer_clean", "nunique"))
        .reset_index()
        .rename(columns={"stage_clean": "tender_stage"})
        .sort_values("records", ascending=False)
    )
    result["record_share_pct"] = result["records"].apply(lambda count: share(count, len(df)))
    return result


def source_vs_niche_profile(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["main_category_clean", "source_classification_clean", "niche_clean"], dropna=False)
        .agg(records=("ocid", "size"), unique_buyers=("buyer_clean", "nunique"),
             review_records=("needs_niche_review", "sum"))
        .reset_index()
        .sort_values("records", ascending=False)
    )


def create_charts(category: pd.DataFrame, niche: pd.DataFrame, years: pd.DataFrame, output_dir: Path) -> list[str]:
    if px is None:
        return ["Plotly is not installed; CSV reports were still generated."]
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    top_cat = category.head(10).sort_values("records")
    fig = px.bar(top_cat, x="records", y="main_category", orientation="h", title="Historical tenders by original broad category")
    p = charts_dir / "01_broad_category_counts.html"
    fig.write_html(p, include_plotlyjs="cdn")
    outputs.append(str(p))

    top_niche = niche.head(15).sort_values("records")
    fig = px.bar(top_niche, x="records", y="suggested_niche", orientation="h", title="Historical records by provisional analytical niche")
    p = charts_dir / "02_provisional_niche_counts.html"
    fig.write_html(p, include_plotlyjs="cdn")
    outputs.append(str(p))

    if not years.empty:
        fig = px.line(years, x="fiscal_year", y="records", markers=True, title="Historical tender records by fiscal year")
        p = charts_dir / "03_fiscal_year_record_counts.html"
        fig.write_html(p, include_plotlyjs="cdn")
        outputs.append(str(p))
    return outputs


def write_summary(df: pd.DataFrame, diagnostics: dict, category: pd.DataFrame, niche: pd.DataFrame,
                  years: pd.DataFrame, buyers: pd.DataFrame, stages: pd.DataFrame,
                  charts: list[str], output_dir: Path) -> Path:
    total = len(df)
    top_buyer = buyers.iloc[0] if len(buyers) else None
    top_niche = niche.iloc[0] if len(niche) else None
    top_category = category.iloc[0] if len(category) else None
    positive_values = df.loc[df["tender_value_numeric"] > 0, "tender_value_numeric"].dropna()
    lines = [
        "# Procurement Business Analysis Summary", "",
        "## Scope and audit checks", "",
        f"- Historical cleaned records: **{total:,}**",
        f"- Unique OCIDs: **{diagnostics['unique_ocids']:,}**",
        f"- Joined rows: **{diagnostics['joined_rows']:,}**",
        f"- Unmatched niche assignments: **{diagnostics['unmatched_assignments']:,}**",
        f"- Duplicate OCIDs in cleaned data: **{diagnostics['source_duplicate_ocids']:,}**",
        f"- Parsed publication dates: **{diagnostics['parsed_publication_dates']:,}/{total:,}**",
        f"- Positive tender values: **{diagnostics['positive_values']:,}**",
        f"- Zero tender values: **{diagnostics['zero_values']:,}**",
        f"- Missing/non-numeric tender values: **{diagnostics['missing_values']:,}**",
        f"- Records flagged for niche review: **{diagnostics['records_needing_niche_review']:,}**",
        "", "## Initial observations", "",
    ]
    if top_category is not None:
        lines.append(f"- Largest original procurement category is **{top_category['main_category']}** with {int(top_category['records']):,} records ({top_category['record_share_pct']:.2f}%).")
    if top_niche is not None:
        lines.append(f"- Largest provisional analytical niche is **{top_niche['suggested_niche']}** with {int(top_niche['records']):,} records ({top_niche['record_share_pct']:.2f}%). This is a provisional label, not a validated accuracy claim.")
    if top_buyer is not None:
        lines.append(f"- Most frequent buyer in this dataset is **{top_buyer['buyer']}** with {int(top_buyer['records']):,} records. This measures record count, not spend or buyer quality.")
    if len(positive_values):
        lines.append(f"- Median positive tender value is **{positive_values.median():,.2f}** across {len(positive_values):,} records with positive numeric values. Currency/unit should be verified from source metadata before using commercially.")
    lines.extend([
        "", "## Required interpretation caveats", "",
        "- This is historical Assam procurement data, not a current India-wide market feed.",
        "- `suggested_analytical_niche` is a provisional rule-based label. Do not treat record share as classification accuracy.",
        "- Zero tender value is reported separately from missing value. A zero may be a source placeholder or a genuine value; inspect before interpreting commercially.",
        "- Tender value is not supplier profit, and historical bidder counts or tender stage do not establish eligibility or chance of winning.",
        "- Historical records may include cancelled, awarded, and other stages. Do not present these as currently open opportunities.",
        "- No tender win-probability or profitability model is fitted in this analysis.",
        "", "## Output files", "",
        "- `01_market_overview.json`",
        "- `02_broad_category_profile.csv`",
        "- `03_provisional_niche_profile.csv`",
        "- `04_fiscal_year_profile.csv`",
        "- `05_top_buyers.csv`",
        "- `06_tender_stage_profile.csv`",
        "- `07_source_classification_vs_niche.csv`",
        "- `charts/` contains interactive HTML charts when Plotly is installed.",
        "", "## Charts", "",
    ])
    lines.extend([f"- `{Path(p).name}`" for p in charts])
    lines.append("")
    output_path = output_dir / "PROCUREMENT_BUSINESS_ANALYSIS_SUMMARY.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_analysis(cleaned_path: Path = CLEANED_PATH, assignments_path: Path = ASSIGNMENTS_PATH,
                 output_dir: Path = OUTPUT_DIR) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    df, diagnostics = load_and_join(cleaned_path, assignments_path)
    category = category_profile(df)
    niche = niche_profile(df)
    years = fiscal_year_profile(df)
    buyers = buyer_profile(df)
    stages = stage_profile(df)
    crosswalk = source_vs_niche_profile(df)

    reports = {
        "02_broad_category_profile.csv": category,
        "03_provisional_niche_profile.csv": niche,
        "04_fiscal_year_profile.csv": years,
        "05_top_buyers.csv": buyers,
        "06_tender_stage_profile.csv": stages,
        "07_source_classification_vs_niche.csv": crosswalk,
    }
    for filename, report in reports.items():
        report.to_csv(output_dir / filename, index=False, encoding="utf-8-sig")

    overview = {
        **diagnostics,
        "broad_category_count": int(df["main_category_clean"].nunique()),
        "source_classification_count": int(df["source_classification_clean"].nunique()),
        "provisional_niche_count": int(df["niche_clean"].nunique()),
        "buyers_count": int(df["buyer_clean"].nunique()),
        "median_positive_tender_value": float(df.loc[df["tender_value_numeric"] > 0, "tender_value_numeric"].median()),
    }
    (output_dir / "01_market_overview.json").write_text(json.dumps(overview, indent=2), encoding="utf-8")
    charts = create_charts(category, niche, years, output_dir)
    summary = write_summary(df, diagnostics, category, niche, years, buyers, stages, charts, output_dir)

    print("Procurement business analysis complete.")
    print(f"Historical records: {diagnostics['joined_rows']:,}")
    print(f"Broad categories: {overview['broad_category_count']} | source classifications: {overview['source_classification_count']} | provisional niches: {overview['provisional_niche_count']}")
    print(f"Buyers: {overview['buyers_count']:,} | records needing niche review: {diagnostics['records_needing_niche_review']:,}")
    print(f"Positive values: {diagnostics['positive_values']:,} | zero: {diagnostics['zero_values']:,} | missing: {diagnostics['missing_values']:,}")
    print(f"Reports: {output_dir}")
    print(f"Summary: {summary}")
    return {"data": df, "diagnostics": diagnostics, "category_profile": category,
            "niche_profile": niche, "fiscal_year_profile": years, "summary_path": summary}


def main() -> int:
    run_analysis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
