# Assam Procurement Cleaning Summary

- Source ZIP: `datasets_of_assam_public_procurement_data_7259310.zip`
- CSV members loaded: 6
- Original rows: 34,232
- Original source columns (excluding script-added provenance): 34
- Rows in analytical output: 34,232
- Columns in analytical output: 21
- Duplicate OCID rows (reported, not silently removed): 0
- Missing OCID rows: 0
- Zero tender-value rows (preserved and flagged): 2410
- Missing tender-value rows after normalization: 1580

## Handling decisions

- The original ZIP is never modified.
- No tender rows are removed by this script.
- Constant, all-missing, export-metadata and non-record-specific milestone columns are excluded from the analytical CSV and documented in `assam_constant_and_excluded_columns.csv`.
- The `date` field is treated as the source export date, not a tender event date.
- The source event dates `tender/datePublished` and `tender/bidOpening/date` are parsed to datetimes where parseable.
- Tender amount, tenderer count and tender-period duration are converted to numeric where parseable.
- Zero tender values are retained as zero and reported separately; they are not automatically converted to missing.
- Source filenames are retained in `source_csv_file` for traceability.
- A constant field is not proof of a universal truth; these exclusions apply to this specific export and should be revisited if new source data is added.

## Files written

- Cleaned analytical table: `data/processed/assam_procurement_cleaned.csv`
- Field quality report: `reports/assam_field_quality_report.csv`
- Constant/excluded columns review: `reports/assam_constant_and_excluded_columns.csv`
