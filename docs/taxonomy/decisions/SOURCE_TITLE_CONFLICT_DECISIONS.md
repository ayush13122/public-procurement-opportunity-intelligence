# Source-label/title conflict refinement

## Why this patch exists
The source-consistency audit successfully joined 34,232 source records to 34,232 assignments (zero field mismatches), but this only confirms source-field integrity. It does not mean the original classification label semantically matches every tender title.

The audit identified high-risk labels such as `Security System`, `Photostat Services`, `Entertainment/Musical Instruments`, `Chemicals/Minerals`, `Coal`, `Paddy Transplanter`, `Multi-crop Thresher`, and `Explosive`.

## What changes
- High-risk source labels are marked `REVIEW` at the label-summary level instead of being presented as trusted niche assignments.
- For records with those labels, clearer title evidence can generate a provisional `TITLE_KEYWORD_CANDIDATE`.
- Explicit cases based on the audit evidence get targeted title-first overrides (for example, road works under `Coal`, vaccine supply under `Paddy Transplanter`, and electrification under `Entertainment/Musical Instruments`).
- A vehicle/asset disposal auction under `Photostat Services` remains `Other / Needs Review` rather than being forced into printing or transport.
- Original source classifications and broad categories are never overwritten.
- Candidate overrides remain review-required; these rules are not verified ground truth.

## After copying
1. Replace the existing `src/profile_procurement_categories.py` with this version.
2. Copy `tests/test_source_title_conflict_rules.py` into `tests/`.
3. Run the full test suite.
4. Regenerate profile assignments and downstream review/EDA reports.
5. Re-run `src/audit_source_classification_consistency.py` and review the updated output.

## Limitations
Title text can be incomplete or ambiguous. Mixed-procurement contracts may need more than one supplier-capability tag. A final bid recommendation still needs the original notice/documents and the company's actual eligibility and commercial information.
