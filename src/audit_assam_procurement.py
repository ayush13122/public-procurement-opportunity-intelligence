"""
Initial data feasibility audit for the Assam Public Procurement ZIP.
Place the downloaded ZIP in <project_root>/data/raw/ and run this script.
Outputs are written to <project_root>/reports/.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORT_DIR = PROJECT_ROOT / "reports"

IT_PATTERN = re.compile(
    r"\b(software|information technology|information system|it services|"
    r"web portal|website|application development|computer|computing|programming|"
    r"digital solution|digitization|digitisation|e-governance|e governance|erp|"
    r"database|data centre|data center|server|network|networking|cyber|cloud|ict|"
    r"computerisation|computerization|automation)\b",
    flags=re.IGNORECASE,
)


def find_source_zip() -> Path:
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser()
        if candidate.is_file() and candidate.suffix.lower() == ".zip":
            return candidate
        raise FileNotFoundError(f"ZIP path not found: {candidate}")

    candidates = sorted(RAW_DIR.glob("*.zip")) if RAW_DIR.exists() else []
    for candidate in candidates:
        try:
            with zipfile.ZipFile(candidate) as archive:
                names = archive.namelist()
            if any("ocds_mapped_procurement_data_fiscal_year_2016_2017.csv" in n for n in names):
                return candidate
        except (OSError, zipfile.BadZipFile):
            continue

    raise FileNotFoundError(
        "Source ZIP not found. Save the downloaded ZIP in data/raw/, "
        "or run: python src/audit_assam_procurement.py <full-path-to-zip>"
    )


def fmt_table(headers: list[str], rows: list[list[object]]) -> str:
    def clean(value: object) -> str:
        return str(value).replace("|", r"\|").replace("\n", " ").strip()

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(clean(v) for v in row) + " |")
    return "\n".join(lines)


def main() -> None:
    source_zip = find_source_zip()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip) as archive:
        members = [
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
            and "ocds_mapped_procurement_data_fiscal_year_" in name
        ]
        if not members:
            raise ValueError("No expected fiscal-year CSV files found in the ZIP.")

        frames = []
        for member in sorted(members):
            with archive.open(member) as file:
                frame = pd.read_csv(file, low_memory=False)
            frame["_source_file"] = Path(member).name
            frames.append(frame)

        df = pd.concat(frames, ignore_index=True, sort=False)

    required = [
        "ocid", "fiscal_year", "tender/title",
        "tenderclassification/description", "tender/mainProcurementCategory",
        "tender/value/amount", "tender/datePublished", "tender/stage",
        "buyer/name", "tender/numberOfTenderers",
    ]
    missing_required = [col for col in required if col not in df.columns]
    if missing_required:
        raise ValueError(f"Expected columns missing from source: {missing_required}")

    # Amounts use both plain digits and Indian-style comma grouping (e.g. 60,00,000).
    amount = pd.to_numeric(
        df["tender/value/amount"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    pub_date = pd.to_datetime(df["tender/datePublished"], errors="coerce")
    search_text = (
        df["tender/title"].fillna("").astype(str)
        + " "
        + df["tenderclassification/description"].fillna("").astype(str)
    )
    it_match = search_text.str.contains(IT_PATTERN, na=False)

    year = (
        df.groupby("fiscal_year", dropna=False)
        .agg(
            records=("ocid", "size"),
            unique_ocid=("ocid", "nunique"),
            services=("tender/mainProcurementCategory", lambda s: int((s == "Services").sum())),
            goods=("tender/mainProcurementCategory", lambda s: int((s == "Goods").sum())),
            works=("tender/mainProcurementCategory", lambda s: int((s == "Works").sum())),
        )
        .reset_index()
        .sort_values("fiscal_year")
    )
    it_by_year = pd.DataFrame({"fiscal_year": df.loc[it_match, "fiscal_year"].value_counts().index,
                               "it_keyword_matches": df.loc[it_match, "fiscal_year"].value_counts().values})
    year = year.merge(it_by_year, on="fiscal_year", how="left").fillna({"it_keyword_matches": 0})
    year["it_keyword_matches"] = year["it_keyword_matches"].astype(int)
    year.to_csv(REPORT_DIR / "assam_procurement_year_summary.csv", index=False)

    quality = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        "missing_percent": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
        "unique_values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    }).sort_values(["missing_percent", "column"], ascending=[False, True])
    quality.to_csv(REPORT_DIR / "assam_procurement_column_quality.csv", index=False)

    category_counts = df["tender/mainProcurementCategory"].value_counts(dropna=False)
    keyword_counts = pd.DataFrame([
        {
            "keyword_group": "Broad IT/software/computer/network/digital keywords in title + classification",
            "matched_records": int(it_match.sum()),
            "interpretation": "Candidate matches only; manually validate false positives.",
        },
        {
            "keyword_group": "Classification contains Information Technology or Computer",
            "matched_records": int(df["tenderclassification/description"].str.contains(
                r"Information Technology|Computer", case=False, na=False
            ).sum()),
            "interpretation": "Classification screen; still needs relevance review.",
        },
        {
            "keyword_group": "Main category = Services",
            "matched_records": int((df["tender/mainProcurementCategory"] == "Services").sum()),
            "interpretation": "All services, not necessarily IT-related.",
        },
    ])
    keyword_counts.to_csv(REPORT_DIR / "assam_procurement_keyword_summary.csv", index=False)

    rows = [[r.fiscal_year, int(r.records), int(r.unique_ocid), int(r.services),
             int(r.goods), int(r.works), int(r.it_keyword_matches)]
            for r in year.itertuples(index=False)]
    year_table = fmt_table(
        ["Fiscal year", "Records", "Unique OCID", "Services", "Goods", "Works", "IT keyword candidates"],
        rows,
    )

    category_lines = [
        f"- **{cat}:** {int(count):,} records ({count / len(df) * 100:.1f}%)."
        for cat, count in category_counts.items()
    ]
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    top_missing = quality[quality["missing_percent"] >= 99]
    missing_lines = [
        f"- `{r.column}` — {int(r.missing_count):,} missing ({r.missing_percent:.1f}%)."
        for r in top_missing.itertuples(index=False)
    ] or ["- No columns with at least 99% missing values."]

    stage_counts = df["tender/stage"].value_counts(dropna=False).head(10)
    stage_lines = [f"- `{stage}`: {int(count):,}" for stage, count in stage_counts.items()]
    pub_min = pub_date.min().strftime("%Y-%m-%d") if pub_date.notna().any() else "unavailable"
    pub_max = pub_date.max().strftime("%Y-%m-%d") if pub_date.notna().any() else "unavailable"

    report = f"""# Initial Data Feasibility Audit — Assam Public Procurement

## Executive verdict

This archive is sizeable and useful for historical procurement analysis, but **it is not sufficient as the only dataset for a narrowly IT/software-focused opportunity platform**. The records are dominated by `Works`. Keep it as a historical foundation while we check the official national procurement portal for a current opportunity sample. If current data cannot be collected efficiently, broaden the case study to public procurement across categories rather than pretending every record is IT-related.

## Source and coverage

- Source catalog: https://www.data.gov.in/catalog/assam-public-procurement-data
- Fiscal-year CSV files found: {len(members)}
- Combined dimensions: **{len(df):,} rows × {len(df.columns) - 1} source columns** (the audit adds one temporary source-file marker in memory).
- Unique `ocid`: {df["ocid"].nunique():,}; duplicate `ocid`: {int(df["ocid"].duplicated().sum()):,}.
- Duplicate full rows (including source marker): {int(df.duplicated().sum()):,}.
- `tender/datePublished` date range: {pub_min} to {pub_max}.
- `date` is constant in the provided extract and should not be used for tender trend analysis; prefer `tender/datePublished`.
- Records per fiscal year:

{year_table}

## Procurement category mix

{chr(10).join(category_lines)}

## IT/software relevance screen

- Broad keyword screen finds **{int(it_match.sum()):,} candidate rows**. This is not a verified count: broad words such as `computer`, `network`, `mapping` or `automation` can create false positives.
- Classification containing `Information Technology` or `Computer`: {int(df["tenderclassification/description"].str.contains(r"Information Technology|Computer", case=False, na=False).sum()):,} candidates.
- Manually validate relevance before filtering a final IT-only dataset.

## Data-quality findings

- Amounts after removing Indian-style commas: {int(amount.notna().sum()):,} parse as numeric; {int(amount.isna().sum()):,} are missing; {int((amount == 0).sum()):,} are recorded as zero. Do not assume that a zero means an actual zero-price tender without checking.
- `tender/externalReference` duplicates should not be used alone as a deduplication key. The `ocid` field is unique in this extract.
- No winning-supplier-name column is present in the 34 original source columns. `tender/stage` includes labels such as `AOC`, but stage alone does not identify the winning supplier.
- 100%-missing original source columns: {", ".join(f"`{c}`" for c in empty_cols) if empty_cols else "None"}.
- Fields at >=99% missing:
{chr(10).join(missing_lines)}
- Common stage labels:
{chr(10).join(stage_lines)}

## Recommended next decision

The Government of India's CPPP portal has current active tenders, archive, bid-award pages and advanced search filters for organisation, title, category, product category, form of contract, value and dates, but advanced searches require a CAPTCHA. We should test one narrow search and confirm the available download/export before choosing a full collection plan.

If usable current data is accessible, keep historical Assam records and current national opportunities as clearly separate datasets with separate time/geographic coverage. Otherwise, broaden the core analysis to historical public procurement across categories and use any current IT tenders as an illustrative subset.

Do not label the opportunity score as probability of winning or profitability unless the relevant outcome and company-cost data support that inference.
"""
    (REPORT_DIR / "initial_assam_procurement_audit.md").write_text(report, encoding="utf-8")
    print(f"Audit complete: {source_zip}")
    print(f"Rows: {len(df):,} | Original source columns: {len(df.columns) - 1}")
    print(f"Unique OCIDs: {df['ocid'].nunique():,}")
    print(f"IT keyword candidates (unvalidated): {int(it_match.sum()):,}")
    print(f"Reports written to: {REPORT_DIR}")


if __name__ == "__main__":
    main()
