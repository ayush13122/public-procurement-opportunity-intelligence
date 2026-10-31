# DAX Measure Inventory

| Measure | Purpose |
|---|---|
| Total Tenders (Numeric) / Total Tenders | Distinct OCID count and card display. |
| Unique Buyers (Numeric) / Unique Buyers | Distinct buyer count and card display. |
| Positive / Zero / Missing Value Records | Distinct value-quality states. |
| Recorded Tender Value (Numeric) | Sum of nonblank amounts; source units unverified. |
| Average Recorded Tender Value (Numeric) | Mean across nonblank values; includes zero-valued records. |
| Median Positive Tender Value (Numeric) | Median excluding zero and blank values. |
| Tender Value Coverage % | Positive + zero amounts divided by all records. |
| Positive Value Share % | Positive values divided by all records. |
| Average Tenderers / Average Tender Period Days | Simple procurement metrics. |
| Holdout Accuracy / Macro F1 / Weighted F1 / Balanced Accuracy | Stored historical classifier baseline metrics. |
