# Project Status â€” Windows Release Snapshot

**Status date:** 31 October 2026  
**Repository:** Public Procurement Opportunity Intelligence & Bid Strategy Platform

## Implemented modules

1. Historical Assam Procurement Market Explorer.
2. Broad tender-category classifier using TF-IDF and Logistic Regression.
3. AI Tender Document Copilot with page-preserving PDF extraction, local retrieval, supported deterministic answers, optional local OCR, and optional Gemini/OpenAI enrichment.
4. Copilot-to-Bid-Fit draft handoff with evidence-backed candidate fields.
5. Company Bid-Fit Analysis with transparent rules and manual-review gates.
6. Power BI Market Intelligence report with an editable PBIP source project.

## Current Windows verification snapshot

The following results were recorded from the working Windows repository:

- Full automated suite: **210 passed**.
- Test command: `python -m pytest tests -q`.
- Dependency consistency: `python -m pip check` reported no broken requirements.
- `app.gemini_runtime` imported successfully.
- README Markdown code fences were balanced.
- Business-analysis validation reported all eight implemented consistency checks as PASS.
- The cleaned historical dataset contains 34,232 records, 21 analytical columns, 34,232 unique OCIDs and zero duplicate OCID rows.
- Tesseract OCR 5.5.3 was available on the Windows machine, with `eng` and `osd` language data listed.

These are local verification results from the recorded working snapshot. Re-run the commands after changing dependencies, code, data or reports.

## Power BI release

The repository contains both:

- Native report: `powerbi/exports/Public_Procurement_Market_Intelligence.pbix`
- Editable project: `powerbi/Public_Procurement_Market_Intelligence/`

The PBIP package build checks recorded 59 parsed PBIR JSON files, five report pages and 49 visual definitions. The report was opened and refreshed in Power BI Desktop on the target Windows PC; visuals that were initially blank became visible after refresh.

This records a successful open/refresh check, not exhaustive testing of every visual interaction, slicer combination or every Power BI Desktop version.

## Recorded ML baseline

The historical broad-category classifier baseline:

| Metric | Result |
|---|---:|
| Accuracy | 93.35% |
| Macro F1 | 86.73% |
| Weighted F1 | 93.66% |
| Balanced accuracy | 91.55% |

Evaluation used a chronological holdout with FY 2021-22 held out. The metrics describe the historical Assam dataset and its source labels. They are not eligibility, bid-win or profit predictions.

## Tender-document validation notes

Earlier offline tender smoke-test results are recorded in `docs/VALIDATION_RESULTS.md`. Those diagnostic cases are separate from the 210 automated tests.

The original real tender PDFs used during private testing are not included in the public repository. Diagnostic findings must be verified against the original documents and current official tender portal/corrigenda before any commercial or legal decision.

The synthetic PDF under `assets/` is a fictional demonstration document.

## Release scope and limitations

This is a functional academic/portfolio decision-support prototype. It does not:

- Ingest all Indian tender portals as a live feed.
- Automatically verify tender status, deadlines or corrigenda.
- Log in to portals, solve CAPTCHAs or submit bids.
- Certify legal eligibility.
- Predict tender awards or supplier profit.
- Fully parse every BOQ, table, scanned annexure or tender-document format.

Niche taxonomy labels remain provisional. Copilot-extracted tender fields are candidates requiring human review. Bid-Fit results are rule-based screening outputs, not legal opinions or award predictions.

## Release readiness checklist

- [x] Main application modules integrated in the working repository.
- [x] Gemini and OCR dependencies separated from the base requirements.
- [x] Full local automated suite passed: 210 tests.
- [x] Business-analysis consistency checks passed.
- [x] Native PBIX export and editable PBIP source present.
- [x] API template uses placeholders.
- [ ] Final Git staging review.
- [ ] Final public-repository secret and file audit.
- [ ] Commit and push after owner approval.