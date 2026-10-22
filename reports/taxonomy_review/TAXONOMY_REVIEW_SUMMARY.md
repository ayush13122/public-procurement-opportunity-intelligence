# Niche Taxonomy Review Summary

## Purpose

This review pack separates rule-based candidate labels from human-verified taxonomy decisions.
Do not use a suggested niche as ground truth until its classification or sample records have been reviewed.

## Data volume

- Source classifications in review queue: **89**
- Records flagged for manual review or unresolved mapping: **2,974**
- Stratified record sample for first-pass spot-check: **560**

## Priority guide

- **HIGH**: source label is already marked REVIEW or represents at least 1,000 records.
- **MEDIUM**: 100–999 records.
- **LOW**: fewer than 100 records.

## Current mapping methods

| mapping_method          |   record_count |   unique_buyers |   suggested_niches |   review_flagged |   record_pct |   review_flag_pct_within_method |
|:------------------------|---------------:|----------------:|-------------------:|-----------------:|-------------:|--------------------------------:|
| SOURCE_CLASSIFICATION   |          31258 |              97 |                 14 |                0 |        91.31 |                               0 |
| UNRESOLVED              |           2112 |              68 |                  1 |             2112 |         6.17 |                             100 |
| TITLE_KEYWORD_CANDIDATE |            862 |              71 |                 19 |              862 |         2.52 |                             100 |

## Largest candidate niches

| suggested_analytical_niche                 |   record_count |   unique_buyers |   unique_source_classifications |   title_keyword_candidates |   unresolved_records |   manual_review_flagged |   record_pct |   manual_review_pct |
|:-------------------------------------------|---------------:|----------------:|--------------------------------:|---------------------------:|---------------------:|------------------------:|-------------:|--------------------:|
| Construction & Civil Infrastructure        |          26781 |              63 |                              15 |                          4 |                    0 |                       4 |        78.23 |                0.01 |
| Other / Needs Review                       |           2113 |              68 |                               6 |                          1 |                 2112 |                    2113 |         6.17 |              100    |
| Electrical, Energy & Utilities             |           1356 |              43 |                              14 |                         40 |                    0 |                      40 |         3.96 |                2.95 |
| Healthcare & Laboratory                    |            650 |              25 |                              17 |                        111 |                    0 |                     111 |         1.9  |               17.08 |
| Professional & Business Services           |            589 |              57 |                               8 |                         37 |                    0 |                      37 |         1.72 |                6.28 |
| Industrial Machinery & Equipment           |            537 |              37 |                              11 |                         89 |                    0 |                      89 |         1.57 |               16.57 |
| Food & Catering                            |            391 |              17 |                               3 |                          1 |                    0 |                       1 |         1.14 |                0.26 |
| Office & General Supplies                  |            317 |              33 |                               8 |                         43 |                    0 |                      43 |         0.93 |               13.56 |
| Computer, Network & Electronics            |            313 |              48 |                               9 |                         45 |                    0 |                      45 |         0.91 |               14.38 |
| Media, Printing & Creative Services        |            305 |              23 |                               8 |                        156 |                    0 |                     156 |         0.89 |               51.15 |
| Agriculture & Forestry                     |            263 |              19 |                               9 |                         59 |                    0 |                      59 |         0.77 |               22.43 |
| Transport & Logistics                      |            198 |              32 |                               8 |                         72 |                    0 |                      72 |         0.58 |               36.36 |
| IT & Software Services                     |            166 |              34 |                               9 |                         22 |                    0 |                      22 |         0.48 |               13.25 |
| Water, Sanitation & Environmental Services |            138 |               4 |                               3 |                        138 |                    0 |                     138 |         0.4  |              100    |
| Architecture & Technical Design            |             71 |              10 |                               3 |                          2 |                    0 |                       2 |         0.21 |                2.82 |

## Files

- `00_classification_review_queue.csv`: editable decisions for the 89 source classifications.
- `01_records_requiring_review.csv`: all records flagged for review or unresolved mapping.
- `02_stratified_record_sample.csv`: compact sample across methods/niches/classifications.
- `03_mapping_method_summary.csv`: records and review burden by mapping method.
- `04_niche_risk_summary.csv`: counts and review risks by proposed niche.

## Review rule

Approve or change the niche based on source classification and sampled tender titles. Preserve the original classification. For ambiguous titles, keep `Other / Needs Review` or use a more general category; do not force a precise niche.
