# Project Methodology

## 1. Source and raw-data preservation
The source archive is kept unchanged in `data/raw/`. Audit/cleaning scripts read its six year-wise CSV files and write outputs to separate folders.

## 2. Data quality and cleaning
The cleaning pipeline preserves the original row count, uses the OCID as a procurement-record identifier, converts known missing markers, standardizes numeric values, and removes columns that are constant or unsuitable for event-level analysis. The source download/export date is not used as the tender publication date.

## 3. Category and niche profiling
Original broad category and original detailed classification remain unchanged. Analytical niches are provisional suggestions based on source classification and a restricted set of title rules. Conflicts and low-confidence cases remain flagged for review instead of being forced into a specific niche.

## 4. Exploratory and business analysis
The scripts report category/niche counts, fiscal-year activity, buyer counts, tender stage, tender-value quality, and crosswalks between source classifications and proposed niches. Outputs are reproducible CSV/Markdown files and interactive Plotly HTML charts.

## 5. Validation
Unit tests cover key helper functions and representative title-classification cases. The report-validation script compares generated aggregates with cleaned data and current assignments. Passing tests and aggregate reconciliation demonstrate software consistency; they do not prove all niche labels are semantically correct.

## 6. Decision boundaries
This release supports historical market exploration only. It does not recommend an actual bid, estimate profit or predict winning probability. A future fit engine must separately evaluate mandatory eligibility, capability match, geography, value constraints, deadline readiness, and evidence completeness.
