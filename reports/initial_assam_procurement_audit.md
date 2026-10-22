# Initial Data Feasibility Audit — Assam Public Procurement

## Executive verdict

This archive is sizeable and useful for historical procurement analysis, but **it is not sufficient as the only dataset for a narrowly IT/software-focused opportunity platform**. The records are dominated by `Works`. Keep it as a historical foundation while we check the official national procurement portal for a current opportunity sample. If current data cannot be collected efficiently, broaden the case study to public procurement across categories rather than pretending every record is IT-related.

## Source and coverage

- Source catalog: https://www.data.gov.in/catalog/assam-public-procurement-data
- Fiscal-year CSV files found: 6
- Combined dimensions: **34,232 rows × 34 source columns** (the audit adds one temporary source-file marker in memory).
- Unique `ocid`: 34,232; duplicate `ocid`: 0.
- Duplicate full rows (including source marker): 0.
- `tender/datePublished` date range: 2016-04-10 to 2022-03-31.
- `date` is constant in the provided extract and should not be used for tender trend analysis; prefer `tender/datePublished`.
- Records per fiscal year:

| Fiscal year | Records | Unique OCID | Services | Goods | Works | IT keyword candidates |
| --- | --- | --- | --- | --- | --- | --- |
| 2016-2017 | 1576 | 1576 | 56 | 236 | 1284 | 28 |
| 2017-2018 | 6128 | 6128 | 161 | 804 | 5163 | 105 |
| 2018-2019 | 9043 | 9043 | 198 | 802 | 8043 | 96 |
| 2019-2020 | 6205 | 6205 | 349 | 850 | 5006 | 90 |
| 2020-2021 | 6590 | 6590 | 229 | 771 | 5590 | 101 |
| 2021-2022 | 4690 | 4690 | 313 | 816 | 3561 | 81 |

## Procurement category mix

- **Works:** 28,647 records (83.7%).
- **Goods:** 4,279 records (12.5%).
- **Services:** 1,306 records (3.8%).

## IT/software relevance screen

- Broad keyword screen finds **501 candidate rows**. This is not a verified count: broad words such as `computer`, `network`, `mapping` or `automation` can create false positives.
- Classification containing `Information Technology` or `Computer`: 270 candidates.
- Manually validate relevance before filtering a final IT-only dataset.

## Data-quality findings

- Amounts after removing Indian-style commas: 32,652 parse as numeric; 1,580 are missing; 2,410 are recorded as zero. Do not assume that a zero means an actual zero-price tender without checking.
- `tender/externalReference` duplicates should not be used alone as a deduplication key. The `ocid` field is unique in this extract.
- No winning-supplier-name column is present in the 34 original source columns. `tender/stage` includes labels such as `AOC`, but stage alone does not identify the winning supplier.
- 100%-missing original source columns: `tender/submissionMethodDetails`, `tender/milestones/dueDate`, `tender/status`, `tender/milestones/dueDate.1`.
- Fields at >=99% missing:
- `tender/milestones/dueDate` — 34,232 missing (100.0%).
- `tender/milestones/dueDate.1` — 34,232 missing (100.0%).
- `tender/status` — 34,232 missing (100.0%).
- `tender/submissionMethodDetails` — 34,232 missing (100.0%).
- `tender/documents/id` — 33,894 missing (99.0%).
- Common stage labels:
- `AOC`: 10,381
- `To be Opened`: 7,094
- `Technical Evaluation`: 6,519
- `Financial Bid Opening`: 4,908
- `Financial Evaluation`: 2,289
- `Technical Bid Opening`: 1,348
- `Cancelled`: 913
- `nan`: 386
- `Retender`: 176
- `Bid Opening`: 156

## Recommended next decision

The Government of India's CPPP portal has current active tenders, archive, bid-award pages and advanced search filters for organisation, title, category, product category, form of contract, value and dates, but advanced searches require a CAPTCHA. We should test one narrow search and confirm the available download/export before choosing a full collection plan.

If usable current data is accessible, keep historical Assam records and current national opportunities as clearly separate datasets with separate time/geographic coverage. Otherwise, broaden the core analysis to historical public procurement across categories and use any current IT tenders as an illustrative subset.

Do not label the opportunity score as probability of winning or profitability unless the relevant outcome and company-cost data support that inference.
