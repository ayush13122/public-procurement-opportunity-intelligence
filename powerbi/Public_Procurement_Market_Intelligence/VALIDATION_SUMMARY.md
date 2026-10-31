# Power BI Build and Data Validation Summary

## Package structure checks

The PBIP build validation recorded:

- PBIP entry file and paired Report / SemanticModel folders: present.
- PBIR JSON files parsed successfully: 59.
- Report pages: 5.
- Visual definitions: 49.
- All visual positions fit inside the 1280 x 720 page canvas.
- Report column/measure references resolve to semantic-model entities.
- Theme registered under `StaticResources/RegisteredResources`.
- Three fiscal-year slicers share the same sync group.

## Cleaned dataset audit

- Rows and columns: 34,232 x 21.
- Unique OCIDs: 34,232.
- Unique buyers: 101.
- Positive tender-value records: 30,242.
- Zero tender-value records: 2,410.
- Missing/non-numeric tender-value records: 1,580.
- Total recorded tender value (raw source units): 1,285,310,421,385.
- Average recorded tender value (zero included, blanks excluded): 39,363,910.98.
- Median positive tender value: 9,998,955.

### Broad category counts

| Category | Records |
|---|---:|
| Works | 28,647 |
| Goods | 4,279 |
| Services | 1,306 |

### Fiscal-year counts

| Fiscal year | Records |
|---|---:|
| 2016-2017 | 1,576 |
| 2017-2018 | 6,128 |
| 2018-2019 | 9,043 |
| 2019-2020 | 6,205 |
| 2020-2021 | 6,590 |
| 2021-2022 | 4,690 |

## Power BI Desktop verification

Power BI Desktop was not installed in the isolated build environment used for the structural PBIP checks.

Subsequently, the PBIP was opened and refreshed in Power BI Desktop on the target Windows PC. The user confirmed that visuals initially appearing blank became visible after refresh.

This is a host-specific open/refresh smoke check. It is not a claim that every page, slicer combination, measure or Power BI Desktop version has undergone exhaustive regression testing.

The repository also contains the native report export at:

`powerbi/exports/Public_Procurement_Market_Intelligence.pbix`

## Interpretation caveats

- The dataset is historical Assam procurement data, not a live tender feed.
- Currency and scale of tender-value fields have not been independently confirmed in source metadata; report values use source units.
- Tender value is not supplier profit, revenue, awarded amount or expenditure.
- ML metrics are historical broad-category holdout metrics, not award or eligibility predictions.
- Provisional taxonomy labels require human review.