# Assam Procurement Category Profiling & Niche Mapping Audit

## Scope
- Source ZIP: `datasets_of_assam_public_procurement_data_7259310.zip`
- Fiscal-year CSV files read: 6
- Total records: 34,232
- Source columns (excluding temporary audit columns): 34
- Unique OCIDs: 34,232
- Original classification labels: 89
- Original broad categories: 3

## Original broad-category profile

| Original category | Records | Record % | Unique classification labels |
|---|---:|---:|---:|
| Works | 28,647 | 83.68% | 41 |
| Goods | 4,279 | 12.50% | 33 |
| Services | 1,306 | 3.82% | 16 |

## Highest-volume original classifications

| Original classification | Records | Record % | Suggested niche | Mapping status |
|---|---:|---:|---|---|
| Civil Works | 14,733 | 43.04% | Construction & Civil Infrastructure | PROVISIONAL |
| Civil Works – Roads | 6,020 | 17.59% | Construction & Civil Infrastructure | PROVISIONAL |
| Civil Works - Building | 3,697 | 10.80% | Construction & Civil Infrastructure | PROVISIONAL |
| Electrical Works | 1,108 | 3.24% | Electrical, Energy & Utilities | PROVISIONAL |
| Supply of Materials | 1,087 | 3.18% | Materials & General Supplies | REVIEW |
| Miscellaneous Goods | 904 | 2.64% | Other / Needs Review | REVIEW |
| Construction Works | 655 | 1.91% | Construction & Civil Infrastructure | PROVISIONAL |
| Civil Works - Water Works | 613 | 1.79% | Construction & Civil Infrastructure | PROVISIONAL |
| Miscellaneous Services | 500 | 1.46% | Other / Needs Review | REVIEW |
| Miscellaneous Works | 455 | 1.33% | Other / Needs Review | REVIEW |
| Civil Works - Bridges | 422 | 1.23% | Construction & Civil Infrastructure | PROVISIONAL |
| Machineries | 371 | 1.08% | Industrial Machinery & Equipment | PROVISIONAL |
| Medical Equipments/Waste | 325 | 0.95% | Healthcare & Laboratory | PROVISIONAL |
| Food Products | 317 | 0.93% | Food & Catering | PROVISIONAL |
| Consultancy | 316 | 0.92% | Professional & Business Services | PROVISIONAL |

## First-pass niche mapping status
- Labels provisionally mapped by explicit keyword rules: 74
- Records covered by provisional mappings: 31,258 (91.31%)
- Labels needing manual review: 15
- **Important:** provisional means suggested, not verified ground truth. Inspect `assam_niche_mapping_review.csv`, especially `Other / Needs Review`, miscellaneous labels, and the sample titles before finalizing a taxonomy.

## Record-level niche candidates
The script also creates `assam_record_niche_distribution.csv` and `assam_record_niche_assignments.csv`. For generic classification labels only, it uses a transparent title-keyword rule to suggest a candidate niche. Rows remain marked for review; these rule-based suggestions are not verified truth.

## Record-level niche candidates

| Suggested analytical niche | Records | Record % |
|---|---:|---:|
| Construction & Civil Infrastructure | 26,781 | 78.23% |
| Other / Needs Review | 2,113 | 6.17% |
| Electrical, Energy & Utilities | 1,356 | 3.96% |
| Healthcare & Laboratory | 650 | 1.90% |
| Professional & Business Services | 589 | 1.72% |
| Industrial Machinery & Equipment | 537 | 1.57% |
| Food & Catering | 391 | 1.14% |
| Office & General Supplies | 317 | 0.93% |
| Computer, Network & Electronics | 313 | 0.91% |
| Media, Printing & Creative Services | 305 | 0.89% |
| Agriculture & Forestry | 263 | 0.77% |
| Transport & Logistics | 198 | 0.58% |
| IT & Software Services | 166 | 0.48% |
| Water, Sanitation & Environmental Services | 138 | 0.40% |
| Architecture & Technical Design | 71 | 0.21% |
| Safety & Security Systems | 25 | 0.07% |
| Property, Space & Facilities | 13 | 0.04% |
| Housekeeping & Facilities Services | 4 | 0.01% |
| Chemicals & Industrial Materials | 2 | 0.01% |

Mapping method counts:
- Source classification candidate: 31,258
- Title-keyword candidate for generic/ambiguous source labels: 862
- Unresolved; inspect manually: 2,112

Title-keyword candidates are suggestions, not validated labels. `assam_record_niche_assignments.csv` retains all source fields and a rationale so a reviewer can inspect these suggestions before they power the app.

## Data availability notes
- Tender values are parsed for coverage reporting, but zero amounts and missing amounts must remain separate states.
- A tender stage is not the same as a tender status or proof of award/winning supplier.
- Detailed eligibility terms may be absent from listing-level fields; original tender documents are still needed for shortlisted current opportunities.
- `assam_field_coverage_by_category.csv` shows available fields by broad category. Use it to decide which metrics are defensible.

## Generated reports
- `assam_broad_category_profile.csv`
- `assam_classification_by_broad_category.csv`
- `assam_niche_mapping_review.csv`
- `assam_field_coverage_by_category.csv`
- `assam_year_profile.csv`
