# Procurement Business Analysis Summary

## Scope and audit checks

- Historical cleaned records: **34,232**
- Unique OCIDs: **34,232**
- Joined rows: **34,232**
- Unmatched niche assignments: **0**
- Duplicate OCIDs in cleaned data: **0**
- Parsed publication dates: **34,232/34,232**
- Positive tender values: **30,242**
- Zero tender values: **2,410**
- Missing/non-numeric tender values: **1,580**
- Records flagged for niche review: **2,974**

## Initial observations

- Largest original procurement category is **Works** with 28,647 records (83.68%).
- Largest provisional analytical niche is **Construction & Civil Infrastructure** with 26,781 records (78.23%). This is a provisional label, not a validated accuracy claim.
- Most frequent buyer in this dataset is **Public Works Roads Department** with 10,724 records. This measures record count, not spend or buyer quality.
- Median positive tender value is **9,998,955.00** across 30,242 records with positive numeric values. Currency/unit should be verified from source metadata before using commercially.

## Required interpretation caveats

- This is historical Assam procurement data, not a current India-wide market feed.
- `suggested_analytical_niche` is a provisional rule-based label. Do not treat record share as classification accuracy.
- Zero tender value is reported separately from missing value. A zero may be a source placeholder or a genuine value; inspect before interpreting commercially.
- Tender value is not supplier profit, and historical bidder counts or tender stage do not establish eligibility or chance of winning.
- Historical records may include cancelled, awarded, and other stages. Do not present these as currently open opportunities.
- No tender win-probability or profitability model is fitted in this analysis.

## Output files

- `01_market_overview.json`
- `02_broad_category_profile.csv`
- `03_provisional_niche_profile.csv`
- `04_fiscal_year_profile.csv`
- `05_top_buyers.csv`
- `06_tender_stage_profile.csv`
- `07_source_classification_vs_niche.csv`
- `charts/` contains interactive HTML charts when Plotly is installed.

## Charts

- `01_broad_category_counts.html`
- `02_provisional_niche_counts.html`
- `03_fiscal_year_record_counts.html`
