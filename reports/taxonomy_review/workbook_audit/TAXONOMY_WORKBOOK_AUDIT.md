# Taxonomy Workbook Audit

This report reviews candidate mapping risks visible in the workbook. It does not approve or overwrite any classifications.

## Workbook counts
- Source-label rows: 89
- Candidate sample rows: 118
- Unresolved sample rows: 21
- All flagged records: 2,974
- Niche-count rows: 19
- Mapping-method rows: 3

## Current mapping-method counts
| mapping_method          |   records |   unique_buyers |   flagged_records |   record_pct |
|:------------------------|----------:|----------------:|------------------:|-------------:|
| SOURCE_CLASSIFICATION   |     31258 |              97 |                 0 |        91.31 |
| TITLE_KEYWORD_CANDIDATE |       862 |              71 |               862 |         2.52 |
| UNRESOLVED              |      2112 |              68 |              2112 |         6.17 |

## Highest-count provisional niches
| suggested_analytical_niche          |   records |   unique_buyers |   source_classifications |   record_pct |   SOURCE_CLASSIFICATION |   TITLE_KEYWORD_CANDIDATE |   UNRESOLVED |
|:------------------------------------|----------:|----------------:|-------------------------:|-------------:|------------------------:|--------------------------:|-------------:|
| Construction & Civil Infrastructure |     26781 |              63 |                       15 |        78.23 |                   26777 |                         4 |            0 |
| Other / Needs Review                |      2113 |              68 |                        6 |         6.17 |                       0 |                         1 |         2112 |
| Electrical, Energy & Utilities      |      1356 |              43 |                       14 |         3.96 |                    1316 |                        40 |            0 |
| Healthcare & Laboratory             |       650 |              25 |                       17 |         1.9  |                     539 |                       111 |            0 |
| Professional & Business Services    |       589 |              57 |                        8 |         1.72 |                     552 |                        37 |            0 |
| Industrial Machinery & Equipment    |       537 |              37 |                       11 |         1.57 |                     448 |                        89 |            0 |
| Food & Catering                     |       391 |              17 |                        3 |         1.14 |                     390 |                         1 |            0 |
| Office & General Supplies           |       317 |              33 |                        8 |         0.93 |                     274 |                        43 |            0 |
| Computer, Network & Electronics     |       313 |              48 |                        9 |         0.91 |                     268 |                        45 |            0 |
| Media, Printing & Creative Services |       305 |              23 |                        8 |         0.89 |                     149 |                       156 |            0 |
| Agriculture & Forestry              |       263 |              19 |                        9 |         0.77 |                     204 |                        59 |            0 |
| Transport & Logistics               |       198 |              32 |                        8 |         0.58 |                     126 |                        72 |            0 |

## Manual review actions detected from sample evidence
- Action rows written: 45

See `taxonomy_manual_review_actions.csv` for the tender titles, current suggestions, issue type, and recommended review action.

## Recommendations
1. Keep the original broad category and original detailed classification unchanged.
2. Treat the suggested analytical niche as provisional until reviewed; mapping coverage is not classification accuracy.
3. Classify primarily from the actual deliverable/tender title and documents, not buyer name or accidental words in an organisation name.
4. Keep procurement type (Works/Goods/Services) as a separate axis from supplier/business niche.
5. Use `Other / Needs Review` for conflicting or insufficient evidence rather than forcing a category.
6. For mixed tenders (e.g., IT hardware + support), allow multiple tags or a primary niche plus a secondary capability tag.
7. Do not infer current bid availability, profit, or win probability from historical classification data alone.
