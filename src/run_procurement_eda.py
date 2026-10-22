"""Reproducible exploratory data analysis for the Assam procurement dataset.

Run from the project root:
    python src/run_procurement_eda.py

Input:
    data/processed/assam_procurement_cleaned.csv

Optional input:
    reports/assam_record_niche_assignments.csv (provisional niche mapping)

Outputs:
    reports/eda/*.csv  - analysis tables
    reports/eda/charts/*.html - interactive Plotly charts
    reports/eda/EDA_SUMMARY.md - generated findings and limitations

The script never edits raw or cleaned data. Niche labels are treated as provisional,
not as verified ground truth. Tender value summaries separate zero values from
positive values and never interpret tender value as profit.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "assam_procurement_cleaned.csv"
REPORT_DIR = PROJECT_ROOT / "reports" / "eda"
CHART_DIR = REPORT_DIR / "charts"
NICHE_FILE = PROJECT_ROOT / "reports" / "assam_record_niche_assignments.csv"

COL = {
    "ocid": "ocid",
    "broad_category": "tender/mainProcurementCategory",
    "classification": "tenderclassification/description",
    "title": "tender/title",
    "amount": "tender/value/amount",
    "published": "tender/datePublished",
    "opening_date": "tender/bidOpening/date",
    "duration": "tender/tenderPeriod/durationInDays",
    "buyer": "buyer/name",
    "stage": "tender/stage",
    "tenderers": "tender/numberOfTenderers",
    "method": "tender/procurementMethod",
    "contract_type": "tender/contractType",
    "fiscal_year": "fiscal_year",
}
REQUIRED = [COL[k] for k in ("ocid", "broad_category", "classification", "title", "amount", "published", "buyer", "stage", "fiscal_year")]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def display_missing(s: pd.Series) -> pd.Series:
    """Return a reporting copy with null and blank values labelled clearly."""
    return s.astype("string").str.strip().replace({"": pd.NA, "<NA>": pd.NA}).fillna("[MISSING]")


def as_numeric(s: pd.Series) -> pd.Series:
    """Parse a numeric-looking column without converting true zeros to missing."""
    text = s.astype("string").str.strip()
    text = text.str.replace(",", "", regex=False).str.replace("₹", "", regex=False)
    return pd.to_numeric(text, errors="coerce")


def parse_dates(s: pd.Series) -> pd.Series:
    """Handle the mixed ISO and day-first date formats in the source export."""
    return pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")


def fiscal_sort_key(value: object) -> tuple[int, str]:
    text = str(value)
    m = re.search(r"(19|20)\d{2}", text)
    return (int(m.group(0)) if m else 9999, text)


def numeric_group_summary(df: pd.DataFrame, group_cols: list[str], amount_col: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for key, group in df.groupby(group_cols, dropna=False, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        vals = group[amount_col].dropna()
        positive = vals[vals > 0]
        row: dict[str, object] = dict(zip(group_cols, ["[MISSING]" if pd.isna(x) else x for x in key]))
        row.update({
            "record_count": int(len(group)),
            "amount_present_count": int(vals.size),
            "amount_missing_count": int(group[amount_col].isna().sum()),
            "amount_coverage_pct": round(float(vals.size / len(group) * 100), 2) if len(group) else 0.0,
            "zero_amount_count": int((vals == 0).sum()),
            "negative_amount_count": int((vals < 0).sum()),
            "positive_amount_count": int(positive.size),
            "positive_amount_median": float(positive.median()) if positive.size else pd.NA,
            "positive_amount_mean": float(positive.mean()) if positive.size else pd.NA,
            "positive_amount_p25": float(positive.quantile(.25)) if positive.size else pd.NA,
            "positive_amount_p75": float(positive.quantile(.75)) if positive.size else pd.NA,
            "positive_amount_p90": float(positive.quantile(.90)) if positive.size else pd.NA,
            "positive_amount_max": float(positive.max()) if positive.size else pd.NA,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def try_load_niche_mapping(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    if not NICHE_FILE.exists():
        return df, "No provisional niche assignments found; run src/profile_procurement_categories.py first."
    niche = pd.read_csv(NICHE_FILE, dtype={"ocid": "string"}, low_memory=False)
    if "ocid" not in niche.columns or "suggested_analytical_niche" not in niche.columns:
        return df, "Niche assignments file exists but required columns were not found; niche EDA skipped."
    dupes = int(niche["ocid"].duplicated().sum())
    if dupes:
        niche = niche.drop_duplicates("ocid", keep="first")
    add_cols = [c for c in ["ocid", "suggested_analytical_niche", "mapping_method", "manual_review_required"] if c in niche.columns]
    base = df.copy()
    base["ocid"] = base["ocid"].astype("string")
    niche["ocid"] = niche["ocid"].astype("string")
    base = base.merge(niche[add_cols], on="ocid", how="left", validate="one_to_one")
    note = f"Provisional niche assignments merged by OCID; duplicate assignment IDs removed before merge: {dupes}. Treat these as candidate labels pending review."
    return base, note


def make_field_quality(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for col in df.columns:
        s = df[col]
        nonmissing = s.dropna()
        vc = nonmissing.astype(str).value_counts().head(3)
        out.append({
            "column": col,
            "dtype": str(s.dtype),
            "row_count": int(len(df)),
            "missing_count": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 2),
            "unique_non_missing": int(nonmissing.nunique()),
            "top_values": " | ".join(f"{k} ({v})" for k, v in vc.items()),
        })
    return pd.DataFrame(out).sort_values(["missing_pct", "unique_non_missing"], ascending=[False, True])


def make_profile(df: pd.DataFrame, group_col: str, amount_col: str, broad_col: str, buyer_col: str, class_col: str) -> pd.DataFrame:
    x = df.copy()
    x[group_col] = display_missing(x[group_col])
    rows = []
    for name, group in x.groupby(group_col, dropna=False, sort=False):
        values = group[amount_col].dropna()
        positives = values[values > 0]
        rows.append({
            group_col: name,
            "records": int(len(group)),
            "record_pct": round(len(group) / len(x) * 100, 2) if len(x) else 0,
            "unique_buyers": int(group[buyer_col].nunique(dropna=True)),
            "unique_classifications": int(group[class_col].nunique(dropna=True)),
            "amount_present": int(values.size),
            "amount_coverage_pct": round(values.size / len(group) * 100, 2) if len(group) else 0,
            "zero_amount_count": int((values == 0).sum()),
            "positive_amount_median": float(positives.median()) if positives.size else pd.NA,
            "positive_amount_mean": float(positives.mean()) if positives.size else pd.NA,
            "positive_amount_max": float(positives.max()) if positives.size else pd.NA,
        })
    return pd.DataFrame(rows).sort_values("records", ascending=False)


def save_chart(fig: go.Figure, filename: str) -> None:
    fig.update_layout(template="plotly_white", margin=dict(l=50, r=25, t=70, b=90), title_x=0.02)
    fig.write_html(CHART_DIR / filename, include_plotlyjs="cdn", full_html=True)


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found: {INPUT_FILE}\nRun python src/clean_assam_procurement.py first."
        )

    df = pd.read_csv(INPUT_FILE, low_memory=False)
    missing_required = [c for c in REQUIRED if c not in df.columns]
    if missing_required:
        raise ValueError(f"Cleaned dataset is missing required columns: {missing_required}")
    original_rows = len(df)
    out, niche_note = try_load_niche_mapping(df)

    # Convert measures and event dates in memory only; the cleaned source CSV remains untouched.
    out[COL["amount"]] = as_numeric(out[COL["amount"]])
    out[COL["tenderers"]] = as_numeric(out[COL["tenderers"]]) if COL["tenderers"] in out.columns else pd.NA
    out[COL["duration"]] = as_numeric(out[COL["duration"]]) if COL["duration"] in out.columns else pd.NA
    out["_published_date"] = parse_dates(out[COL["published"]])
    out["_opening_date"] = parse_dates(out[COL["opening_date"]]) if COL["opening_date"] in out.columns else pd.NaT
    out["_amount"] = out[COL["amount"]]

    # 00 - overview and integrity metrics.
    overview_rows = [
        {"metric": "input_file", "value": str(INPUT_FILE.relative_to(PROJECT_ROOT))},
        {"metric": "records_loaded", "value": int(len(out))},
        {"metric": "columns_loaded_before_eda_helpers", "value": int(len(df.columns))},
        {"metric": "unique_ocids", "value": int(out[COL["ocid"]].nunique(dropna=True))},
        {"metric": "duplicate_ocid_rows", "value": int(out[COL["ocid"]].duplicated().sum())},
        {"metric": "rows_preserved_by_eda_merge", "value": int(len(out))},
        {"metric": "tender_value_missing", "value": int(out["_amount"].isna().sum())},
        {"metric": "tender_value_zero", "value": int((out["_amount"] == 0).sum())},
        {"metric": "tender_value_positive", "value": int((out["_amount"] > 0).sum())},
        {"metric": "publication_dates_parsed", "value": int(out["_published_date"].notna().sum())},
        {"metric": "opening_dates_parsed", "value": int(out["_opening_date"].notna().sum())},
        {"metric": "niche_mapping_note", "value": niche_note},
    ]
    write_csv(pd.DataFrame(overview_rows), REPORT_DIR / "00_eda_data_overview.csv")

    # 01 - quality and missingness.
    quality = make_field_quality(df)
    write_csv(quality, REPORT_DIR / "01_field_quality.csv")

    # 02 - high-level categories and original classifications.
    broad_col, class_col, buyer_col = COL["broad_category"], COL["classification"], COL["buyer"]
    broad_profile = make_profile(out, broad_col, "_amount", broad_col, buyer_col, class_col)
    write_csv(broad_profile, REPORT_DIR / "02_broad_category_profile.csv")

    class_copy = out.copy()
    class_copy[class_col] = display_missing(class_copy[class_col])
    class_rows = []
    for label, group in class_copy.groupby(class_col, dropna=False, sort=False):
        amounts = group["_amount"].dropna()
        positive = amounts[amounts > 0]
        sample_titles = group[COL["title"]].dropna().astype(str).str.strip()
        sample_titles = sample_titles[sample_titles.ne("")].drop_duplicates().head(3).tolist()
        broad_dist = group[broad_col].astype("string").fillna("[MISSING]").value_counts()
        class_rows.append({
            "original_classification": label,
            "records": int(len(group)),
            "record_pct": round(len(group) / len(out) * 100, 2),
            "dominant_broad_category": str(broad_dist.index[0]) if len(broad_dist) else "[MISSING]",
            "dominant_broad_category_records": int(broad_dist.iloc[0]) if len(broad_dist) else 0,
            "unique_buyers": int(group[buyer_col].nunique(dropna=True)),
            "amount_coverage_pct": round(amounts.size / len(group) * 100, 2) if len(group) else 0,
            "zero_amount_count": int((amounts == 0).sum()),
            "positive_amount_median": float(positive.median()) if positive.size else pd.NA,
            "sample_titles_for_review": " || ".join(sample_titles),
        })
    classification_profile = pd.DataFrame(class_rows).sort_values("records", ascending=False)
    write_csv(classification_profile, REPORT_DIR / "03_classification_profile.csv")

    # 04 - candidate analytical niches, if the mapping file is available.
    niche_col = "suggested_analytical_niche"
    if niche_col in out.columns:
        niche_summary = make_profile(out, niche_col, "_amount", broad_col, buyer_col, class_col)
        if "mapping_method" in out.columns:
            methods = out.groupby(niche_col, dropna=False)["mapping_method"].apply(lambda s: "; ".join(sorted(s.dropna().astype(str).unique()))).rename("mapping_methods").reset_index()
            niche_summary = niche_summary.merge(methods, on=niche_col, how="left")
        if "manual_review_required" in out.columns:
            review = out.groupby(niche_col, dropna=False)["manual_review_required"].apply(lambda s: int(s.astype(str).str.upper().isin(["YES", "TRUE", "1"]).sum())).rename("records_flagged_for_review").reset_index()
            niche_summary = niche_summary.merge(review, on=niche_col, how="left")
            niche_summary["review_flag_pct"] = (niche_summary["records_flagged_for_review"] / niche_summary["records"] * 100).round(2)
        write_csv(niche_summary, REPORT_DIR / "04_niche_profile.csv")

    # 05 - fiscal year, explicitly descriptive rather than causal.
    fy = out.groupby(COL["fiscal_year"], dropna=False).agg(
        records=(COL["ocid"], "size"),
        unique_buyers=(buyer_col, "nunique"),
        unique_classifications=(class_col, "nunique"),
        tender_value_records=("_amount", "count"),
        zero_tender_values=("_amount", lambda s: int((s == 0).sum())),
        positive_tender_values=("_amount", lambda s: int((s > 0).sum())),
        publication_dates_parsed=("_published_date", "count"),
    ).reset_index()
    fy["record_pct"] = (fy["records"] / len(out) * 100).round(2)
    fy = fy.sort_values(COL["fiscal_year"], key=lambda s: s.map(fiscal_sort_key))
    write_csv(fy, REPORT_DIR / "05_fiscal_year_profile.csv")

    # 06 - publication-month volume.
    pub = out[out["_published_date"].notna()].copy()
    pub["publication_month"] = pub["_published_date"].dt.to_period("M").astype(str)
    monthly = pub.groupby("publication_month").agg(
        records=(COL["ocid"], "size"),
        unique_buyers=(buyer_col, "nunique"),
        tender_value_records=("_amount", "count"),
    ).reset_index().sort_values("publication_month")
    write_csv(monthly, REPORT_DIR / "06_publication_month_profile.csv")

    # 07/08 - buyer profiles.
    buyer_work = out.copy()
    buyer_work[buyer_col] = display_missing(buyer_work[buyer_col])
    top_buyer = buyer_work.groupby(buyer_col, dropna=False).agg(
        tender_records=(COL["ocid"], "size"),
        unique_classifications=(class_col, "nunique"),
        broad_categories=(broad_col, "nunique"),
        values_available=("_amount", "count"),
        positive_value_median=("_amount", lambda s: float(s[s > 0].median()) if (s > 0).any() else pd.NA),
    ).reset_index().sort_values("tender_records", ascending=False).head(50)
    write_csv(top_buyer, REPORT_DIR / "07_top_buyers.csv")
    buyer_cat = buyer_work.groupby([broad_col, buyer_col], dropna=False).agg(
        tender_records=(COL["ocid"], "size"),
        values_available=("_amount", "count"),
        positive_value_median=("_amount", lambda s: float(s[s > 0].median()) if (s > 0).any() else pd.NA),
    ).reset_index().sort_values([broad_col, "tender_records"], ascending=[True, False])
    buyer_cat = buyer_cat.groupby(broad_col, dropna=False, group_keys=False).head(10)
    write_csv(buyer_cat, REPORT_DIR / "08_top_buyers_by_category.csv")

    # 09/10 - stage and procurement method profiles.
    for field_key, filename in [("stage", "09_stage_profile.csv"), ("method", "10_procurement_method_profile.csv"), ("contract_type", "11_contract_type_profile.csv")]:
        field = COL[field_key]
        if field in out.columns:
            temp = out.copy()
            temp[field] = display_missing(temp[field])
            prof = temp.groupby(field, dropna=False).agg(
                records=(COL["ocid"], "size"),
                unique_buyers=(buyer_col, "nunique"),
                unique_classifications=(class_col, "nunique"),
                amount_records=("_amount", "count"),
                zero_amount_count=("_amount", lambda s: int((s == 0).sum())),
                positive_amount_median=("_amount", lambda s: float(s[s > 0].median()) if (s > 0).any() else pd.NA),
            ).reset_index().sort_values("records", ascending=False)
            prof["record_pct"] = (prof["records"] / len(temp) * 100).round(2)
            write_csv(prof, REPORT_DIR / filename)

    # 12 - amount distribution separated into missing, zero and positive values.
    amount_summary = numeric_group_summary(out, [broad_col], "_amount")
    amount_summary = amount_summary.sort_values("record_count", ascending=False)
    write_csv(amount_summary, REPORT_DIR / "12_tender_value_by_broad_category.csv")
    niche_amount = None
    if niche_col in out.columns:
        niche_amount = numeric_group_summary(out, [niche_col], "_amount").sort_values("record_count", ascending=False)
        write_csv(niche_amount, REPORT_DIR / "13_tender_value_by_niche.csv")

    # 14 - focus rows for a human review list, not an automatic deletion list.
    review_mask = out["_amount"].isna() | (out["_amount"] == 0)
    review_cols = [COL["ocid"], COL["title"], buyer_col, broad_col, class_col, COL["amount"], COL["published"], COL["stage"], COL["fiscal_year"]]
    if niche_col in out.columns:
        review_cols += [niche_col]
    review_rows = out.loc[review_mask, [c for c in review_cols if c in out.columns]].copy()
    review_rows["review_reason"] = out.loc[review_mask, "_amount"].map(lambda x: "MISSING_VALUE" if pd.isna(x) else "ZERO_VALUE")
    write_csv(review_rows, REPORT_DIR / "14_missing_or_zero_tender_values_for_review.csv")

    # Charts: Plotly HTML keeps them interactive and avoids an image-renderer dependency.
    broad_plot = broad_profile.sort_values("records", ascending=True)
    fig = px.bar(broad_plot, x="records", y=broad_col, orientation="h", text="records", title="Historical procurement records by original broad category", labels={"records": "Tender records", broad_col: "Original procurement category"})
    save_chart(fig, "01_broad_category_distribution.html")

    top_class = classification_profile.head(15).sort_values("records", ascending=True)
    fig = px.bar(top_class, x="records", y="original_classification", orientation="h", text="records", title="Top 15 original tender classifications", labels={"records": "Tender records", "original_classification": "Original classification"})
    save_chart(fig, "02_top_classifications.html")

    fy_plot = fy.copy()
    fig = px.bar(fy_plot, x=COL["fiscal_year"], y="records", text="records", title="Historical records by fiscal year", labels={COL["fiscal_year"]: "Fiscal year", "records": "Tender records"})
    save_chart(fig, "03_records_by_fiscal_year.html")

    if not monthly.empty:
        fig = px.line(monthly, x="publication_month", y="records", markers=True, title="Tender publication volume by month", labels={"publication_month": "Publication month", "records": "Tender records"})
        fig.update_xaxes(tickangle=-45)
        save_chart(fig, "04_monthly_publication_volume.html")

    value_chart = broad_profile[broad_profile["positive_amount_median"].notna()].copy()
    if not value_chart.empty:
        fig = px.bar(value_chart.sort_values("positive_amount_median"), x="positive_amount_median", y=broad_col, orientation="h", title="Median positive tender value by broad category", labels={"positive_amount_median": "Median positive tender value (source currency units)", broad_col: "Original category"})
        save_chart(fig, "05_median_positive_value_by_category.html")

    if niche_col in out.columns:
        niche_plot = out.groupby(niche_col, dropna=False).size().rename("records").reset_index().sort_values("records", ascending=False).head(20).sort_values("records", ascending=True)
        niche_plot[niche_col] = niche_plot[niche_col].fillna("[MISSING]")
        fig = px.bar(niche_plot, x="records", y=niche_col, orientation="h", text="records", title="Top candidate analytical niches (provisional mapping)", labels={"records": "Tender records", niche_col: "Candidate niche"})
        save_chart(fig, "06_candidate_niche_distribution.html")

    # Human-readable summary with caveats and reproducibility facts.
    category_lines = "\n".join(
        f"| {row.iloc[0]} | {int(row['records']):,} | {row['record_pct']:.2f}% | {int(row['unique_buyers']):,} | {row['amount_coverage_pct']:.2f}% |"
        for _, row in broad_profile.iterrows()
    )
    top_class_lines = "\n".join(
        f"| {row['original_classification']} | {int(row['records']):,} | {row['record_pct']:.2f}% |"
        for _, row in classification_profile.head(10).iterrows()
    )
    positive = out.loc[out["_amount"] > 0, "_amount"].dropna()
    publish_min = out["_published_date"].min()
    publish_max = out["_published_date"].max()
    stage_series = display_missing(out[COL["stage"]]) if COL["stage"] in out.columns else pd.Series(dtype=str)
    top_stages = stage_series.value_counts().head(5)
    stage_lines = "\n".join(f"- {name}: {int(count):,} ({count / len(out) * 100:.2f}%)" for name, count in top_stages.items())
    summary = f"""# Assam Procurement EDA Summary

## Run metadata
- Input: `{INPUT_FILE.relative_to(PROJECT_ROOT)}`
- Rows loaded: **{len(out):,}**
- Columns in cleaned input: **{len(df.columns)}**
- Unique OCIDs: **{out[COL['ocid']].nunique(dropna=True):,}**
- Duplicate OCID rows: **{int(out[COL['ocid']].duplicated().sum()):,}**
- Rows preserved by the EDA join: **{len(out):,} / {original_rows:,}**
- Publication date parsed: **{int(out['_published_date'].notna().sum()):,} / {len(out):,}** ({out['_published_date'].notna().mean() * 100:.2f}%)
- Publication-date range: **{publish_min}** to **{publish_max}**
- Positive tender values: **{int((out['_amount'] > 0).sum()):,}**
- Zero tender values: **{int((out['_amount'] == 0).sum()):,}**
- Missing tender values: **{int(out['_amount'].isna().sum()):,}**
- Median positive tender value (all categories): **{positive.median():,.2f}**""" if positive.size else "# Assam Procurement EDA Summary\n\nNo positive tender values were parsed; inspect the field-quality report."
    summary += f"""

## Original broad category profile

| Original category | Records | Record share | Unique buyers | Value coverage |
|---|---:|---:|---:|---:|
{category_lines}

## Top original classifications

| Classification | Records | Record share |
|---|---:|---:|
{top_class_lines}

## Most common recorded tender stages

{stage_lines}

## Candidate niche mapping

{niche_note}

Candidate analytical niche labels are rule-based suggestions from the earlier profiling script, not verified source truth. Review `04_niche_profile.csv`, `assam_niche_mapping_review.csv`, and `assam_record_niche_assignments.csv` before using the mapping for company recommendations.

## Important limitations

1. This is a historical Assam procurement extract split across six fiscal-year source files; it does not represent all of India's procurement market.
2. The original `date` export stamp was excluded during cleaning. Temporal analysis here uses `tender/datePublished` and `fiscal_year` only.
3. Tender value is not supplier profit, final contract revenue, or a win probability.
4. A missing or zero tender value needs case-specific interpretation; both are reported separately and neither is silently replaced.
5. Current live tenders must be collected and verified separately before the app can make current-opportunity suggestions.
6. The EDA describes associations and distributions; it does not establish causal drivers of awards or supplier success.

## Generated artifacts

- `00_eda_data_overview.csv`
- `01_field_quality.csv`
- `02_broad_category_profile.csv`
- `03_classification_profile.csv`
- `04_niche_profile.csv` (if candidate mapping exists)
- `05_fiscal_year_profile.csv`
- `06_publication_month_profile.csv`
- `07_top_buyers.csv`
- `08_top_buyers_by_category.csv`
- `09_stage_profile.csv`
- `10_procurement_method_profile.csv` and `11_contract_type_profile.csv` (when fields exist)
- `12_tender_value_by_broad_category.csv`
- `13_tender_value_by_niche.csv` (if candidate mapping exists)
- `14_missing_or_zero_tender_values_for_review.csv`
- Interactive HTML charts in `charts/`
"""
    (REPORT_DIR / "EDA_SUMMARY.md").write_text(summary, encoding="utf-8")

    print("\nEDA complete.")
    print(f"Input records: {len(df):,} | columns: {len(df.columns)}")
    print(f"Unique OCIDs: {out[COL['ocid']].nunique(dropna=True):,} | duplicate OCID rows: {int(out[COL['ocid']].duplicated().sum()):,}")
    print(f"Publication dates parsed: {int(out['_published_date'].notna().sum()):,}/{len(out):,}")
    print(f"Tender values: positive={int((out['_amount'] > 0).sum()):,}, zero={int((out['_amount'] == 0).sum()):,}, missing={int(out['_amount'].isna().sum()):,}")
    print(f"Reports: {REPORT_DIR}")
    print(f"Charts: {CHART_DIR}")
    print(f"Summary: {REPORT_DIR / 'EDA_SUMMARY.md'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"EDA failed: {exc}", file=sys.stderr)
        raise
