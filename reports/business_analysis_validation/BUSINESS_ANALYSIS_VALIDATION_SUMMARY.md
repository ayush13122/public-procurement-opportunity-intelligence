# Business Analysis Output Validation

This report compares previously generated business-analysis reports with the latest cleaned dataset and niche assignments.
It does not change or overwrite source data or analytical reports.

## Source integrity checks

- Latest cleaned rows: **34,232**
- Latest assignment rows: **34,232**
- Unique cleaned OCIDs: **34,232**
- Duplicate cleaned OCID rows: **0**
- Unmatched assignment OCIDs: **0**
- Current niche review flags: **2,974**

## Report consistency results

| Check | Status | Mismatched keys |
|---|---|---:|
| Source/assignment OCID alignment | PASS | 0 |
| Broad category profile | PASS | 0 |
| Provisional niche profile | PASS | 0 |
| Fiscal-year record counts | PASS | 0 |
| Tender-stage record counts | PASS | 0 |
| Reported top-buyer counts | PASS | 0 |
| Source-classification/niche crosswalk | PASS | 0 |
| Market overview row counts | PASS | 0 |

## Interpretation

The checked category, niche, fiscal-year, stage, buyer, and source-classification crosswalk outputs match the latest files for the checks implemented in this script.

## Important caveats

- Niche labels remain provisional until reviewed; distribution is not classification accuracy.
- Historical Assam records are not current, India-wide opportunities.
- Tender value is not supplier profit; verify currency/unit and the source definitions before commercial interpretation.
- Counts of historical stages must not be interpreted as current tender availability.
