# Assam Procurement Cleaning Decisions

## Principle
The original source ZIP is immutable. Cleaning creates a separate analysis-ready table; it does not overwrite raw files.

## Fields excluded from the analytical table
- `initiationType`, `tag`: constant `tender` in every record.
- `id`: constant `1`; not the record's unique identifier.
- `date`: constant `2022-09-29`, representing export/download date, not the tender event date.
- `tender/status`: all records are `NA` in this extract, so no usable status signal exists in this column.
- `tender/milestones/title`, `tender/milestones/code`, `tender/milestones/type`: constant values for all records. The title says `Price Bid Opening Date`, while code says `PreBid Meeting Date`; treat as a data-quality/schema anomaly, not reliable record-level milestone data.
- `tender/milestones/dueDate`: all missing.
- Repeated `.1` milestone columns (`type.1`, `title.1`, `dueDate.1`): repeated constant/missing metadata, not useful as record-level features.
- Any additional column that the script empirically identifies as constant or all-missing is reported and excluded from the analytical table for this export.

## Fields not to discard
Keep fields that vary and support procurement analysis, including `ocid`, `fiscal_year`, `tender/title`, `tender/mainProcurementCategory`, `tenderclassification/description`, `tender/procurementMethod`, `tender/contractType`, `tender/value/amount`, `tender/datePublished`, `tender/tenderPeriod/durationInDays`, `Payment Mode`, `tender/stage`, `tender/numberOfTenderers`, `tender/bidOpening/date`, and `buyer/name` when present.

## Row handling
No rows are dropped by the cleaning script. It reports duplicate OCIDs, and keeps them in the output for a deliberate later decision. Current audit: 34,232 rows, 34 original columns, 0 duplicate OCIDs.

## Numeric handling
- Convert tender value to numeric when parseable.
- Preserve zero tender values as zero, but report them separately because zero may mean a non-disclosed/zero-coded value or a true zero; investigate before interpreting.
- Convert number of tenderers and tender-period duration to numeric where possible.

## Date handling
- Do not use `date` as tender date.
- Parse `tender/datePublished` and `tender/bidOpening/date` into date/time values, using formats encountered in this export.
- Keep `fiscal_year` as provided, and retain `source_csv_file` for provenance.

## Generated outputs
- `data/processed/assam_procurement_cleaned.csv`
- `reports/assam_field_quality_report.csv`
- `reports/assam_constant_and_excluded_columns.csv`
- `reports/assam_cleaning_summary.md`

The output has 34,232 rows and 21 columns on the tested source ZIP. Re-run the report when source data changes; decisions may differ on a future export.
