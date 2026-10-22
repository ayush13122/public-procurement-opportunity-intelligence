# Known Limitations

- The data is an Assam historical snapshot for FY 2016-17 through FY 2021-22, not a current all-India tender feed.
- A high share of records are in `Works`; this reflects this dataset's composition and is not an India-wide market estimate.
- `tender/documents/id` is missing for nearly all records, which limits programmatic access to detailed tender documents from this extract.
- Tender-value values include zero and missing entries; zero must not automatically be interpreted as free or a confirmed value.
- Taxonomy is still provisional; 2,974 records were flagged for review in one refined run (counts may vary after rule updates).
- Source classification/title mismatches need evidence-based review. Source/assignment field alignment passing does not verify semantic accuracy.
- Active tender portal searches were manual feasibility tests only; a repeatable current-data pipeline was not yet built.
- No Streamlit dashboard, automated live refresh, bid recommendation engine, or ML win model is included in this release.
