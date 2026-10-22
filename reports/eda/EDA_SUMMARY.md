# Assam Procurement EDA Summary

## Run metadata
- Input: `data/processed/assam_procurement_cleaned.csv`
- Rows loaded: **34,232**
- Columns in cleaned input: **21**
- Unique OCIDs: **34,232**
- Duplicate OCID rows: **0**
- Rows preserved by the EDA join: **34,232 / 34,232**
- Publication date parsed: **34,232 / 34,232** (100.00%)
- Publication-date range: **2016-04-10 13:00:00** to **2022-03-31 18:50:00**
- Positive tender values: **30,242**
- Zero tender values: **2,410**
- Missing tender values: **1,580**
- Median positive tender value (all categories): **9,998,955.00**

## Original broad category profile

| Original category | Records | Record share | Unique buyers | Value coverage |
|---|---:|---:|---:|---:|
| Works | 28,647 | 83.68% | 76 | 97.60% |
| Goods | 4,279 | 12.50% | 83 | 84.48% |
| Services | 1,306 | 3.82% | 76 | 82.54% |

## Top original classifications

| Classification | Records | Record share |
|---|---:|---:|
| Civil Works | 14,733 | 43.04% |
| Civil Works – Roads | 6,020 | 17.59% |
| Civil Works - Building | 3,697 | 10.80% |
| Electrical Works | 1,108 | 3.24% |
| Supply of Materials | 1,087 | 3.18% |
| Miscellaneous Goods | 904 | 2.64% |
| Construction Works | 655 | 1.91% |
| Civil Works - Water Works | 613 | 1.79% |
| Miscellaneous Services | 500 | 1.46% |
| Miscellaneous Works | 455 | 1.33% |

## Most common recorded tender stages

- AOC: 10,381 (30.33%)
- To be Opened: 7,094 (20.72%)
- Technical Evaluation: 6,519 (19.04%)
- Financial Bid Opening: 4,908 (14.34%)
- Financial Evaluation: 2,289 (6.69%)

## Candidate niche mapping

Provisional niche assignments merged by OCID; duplicate assignment IDs removed before merge: 0. Treat these as candidate labels pending review.

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
