# Taxonomy Review Guide

## Why this step comes next

The project has completed source auditing, data cleaning, category profiling and first-pass EDA. Before the niche labels drive company-specific tender recommendations, we must assess the classification rules. The existing labels are candidate mappings, not ground truth.

## Outputs

- `00_classification_review_queue.csv`: all source classification labels, ranked by review priority. Fill in `reviewer_decision` (for example `APPROVE` or `CHANGE`), `approved_analytical_niche`, and `reviewer_notes` after reviewing the sample titles.
- `01_records_requiring_review.csv`: records flagged by the first-pass classifier or unresolved. It is deliberately separate from the main cleaned data.
- `02_stratified_record_sample.csv`: deterministic spot-check sample across mapping method, proposed niche and source classification.
- `03_mapping_method_summary.csv`: how many records were assigned by source classification, title keyword candidate, or left unresolved.
- `04_niche_risk_summary.csv`: category sizes, unresolved/title-only counts and manual review flag counts.

## How to review efficiently

1. Start with HIGH-priority source labels and all labels whose status is `REVIEW`.
2. Use the sample titles and original classification to confirm the suggested niche.
3. Pay extra attention to `TITLE_KEYWORD_CANDIDATE` rows: keyword matches can be false positives.
4. Keep uncertain entries under `Other / Needs Review` rather than forcing a niche.
5. Do not infer tender win probability or profit from historical tender value alone.
6. Preserve the original classification for auditability; the analytical niche is an additional field.

## Current limitations

This is a rule-based first-pass mapping over a historical Assam procurement extract, not a model validated against human-labelled ground truth. The suggested niches need review before production-style recommendations are made.
