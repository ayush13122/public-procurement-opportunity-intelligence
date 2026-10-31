# Public Procurement Market Intelligence â€” Power BI Project

This folder contains the editable Power BI Project (PBIP), using PBIR report definitions and a TMDL semantic model. A native PBIX export is also included separately in the repository.

## Choose how to open the report

### Ready-to-open native report

Open this file in Power BI Desktop:

`powerbi/exports/Public_Procurement_Market_Intelligence.pbix`

### Editable project source

Open this file in Power BI Desktop:

`powerbi/Public_Procurement_Market_Intelligence/Public Procurement Market Intelligence.pbip`

The PBIP source is the editable project. The PBIX export is the convenient native report file.

## Data source

The Power Query parameter `pCsvPath` references the cleaned analytical dataset:

`data/processed/assam_procurement_cleaned.csv`

If the repository is stored elsewhere, update `pCsvPath` in Power Query to the corresponding local CSV file, then select Close & Apply and refresh.

## Included report pages

1. **Executive Overview** â€” headline KPIs, fiscal-year trend, broad category mix and tender-stage distribution.
2. **Market & Category** â€” broad categories, procurement methods, original classifications and contract types.
3. **Buyer Intelligence** â€” all-years Top 10 buyer ranking and detail table.
4. **Tender Value Analysis** â€” total, average and median positive values, category comparison and Top 10 tender records.
5. **Data Quality & ML Insights** â€” positive, zero and missing values, value coverage, bidder counts by stage and held-out classifier metrics.

## Report model

- Based on the cleaned 21-column Assam procurement dataset.
- Includes DAX measures for tender counts, buyer counts, value coverage, positive/zero/missing values, median positive tender value and historical model metrics.
- Includes derived Top 10 buyers, Top 10 tenders and Top 15 detailed source-classification tables.
- Uses the registered navy/teal report theme.

## Data caveats

- Scope: Assam historical dataset, FY 2016-17 through FY 2021-22; 34,232 records.
- Tender-value currency and scale have not been independently verified in source metadata. Values are shown in source units.
- Tender value is not supplier revenue, profit, awarded amount or public expenditure.
- Classifier metrics are historical holdout metrics for broad Works/Goods/Services classification, not eligibility, bid-win or profit predictions.
- Provisional niche classifications require human review.
- Top 10 buyer and tender summary tables are all-years rankings and are not affected by fiscal-year slicers.

## Refresh and host verification

The PBIP was opened in Power BI Desktop on the target Windows PC. After refreshing the local CSV source, visuals that initially appeared blank became visible. This records an open/refresh smoke check; inspect all pages and slicer interactions after making changes.

The build-environment structural checks are in `VALIDATION_SUMMARY.md`. Machine-specific `.pbi` cache and local settings are excluded from version control.

## Source and attribution

Source dataset: Assam Public Procurement Data, Government of India Open Government Data Platform. Refer to the main project README for attribution and licence information.