# Tender Extraction Audit & Evidence Patch

## Why this patch

The Gemini integration can return the original nine Bid-Fit fields, but several tender clauses cannot safely be represented as one scalar. The supplied 56-page AGCL PDF is a regression benchmark: the deadline is delegated to the portal, experience uses item-wise alternative PO/quantity routes, net worth is a separate financial criterion, more than one product compliance document appears in datasheets, and two potentially material wording inconsistencies should be escalated instead of silently resolved.

## What changes

- Adds `app/tender_review_audit.py` and runs it after **both** Gemini and offline extraction.
- Explicitly labels the closing date as `Not stated in supplied document — portal lookup required` when the PDF says the online portal contains the date and no dated closing deadline is present in the supplied document.
- Supplement-merges certification candidates evidenced in the BEC, dispatch checklist and datasheets (for this notice: ATEX/IECEx certification, PESO/CCOE approval, calibration report/certificate). Original pages and quotes are retained for manual review.
- Leaves `min_similar_projects` and `min_years_experience` blank when the document contains alternate PO/quantity routes. Their statuses point to review flags instead of inventing one project count or treating a supply lookback as company age.
- Adds a separate **Tender review flags** panel for alternatives in experience tables, the BEC's conflicting 05-year / 03-year lookback wording, positive net worth, delivery period, compliance documents/submission stage, warranty wording (months versus literal years), temperature range wording and differing opening-page reference dates.
- No flag is automatically converted into a legal conclusion, verified field, live portal status or automatic Bid-Fit score. The user must check the original notice and portal/corrigenda.
- Keeps the existing nine editable Bid-Fit fields and human-review gate unchanged. Supplemental review findings are displayed but are not silently transferred into the fit score.

## Files in this ZIP

- `app/tender_requirements_extractor.py` — real-tender-compatible offline extractor, including the earlier fixes for title, bid security, delivery destination and portal-delegated closing date.
- `app/tender_review_audit.py` — new shared source-backed enrichment / review flags.
- `app/pages/2_AI_Tender_Document_Copilot.py` — calls the shared checks for Gemini and offline mode and displays the flags.
- `tests/test_real_tender_extraction_regression.py` — baseline regression tests for tender-specific wording.
- `tests/test_tender_review_audit.py` — tests for additional source-backed flags and field statuses.
- `docs/TENDER_EXTRACTION_AUDIT_AND_SCHEMA_PATCH.md` — this handover.

## Apply in IntelliJ IDEA

Project root:

`D:\Github\public-procurement-opportunity-intelligence`

1. Stop Streamlit with `Ctrl+C`.
2. Extract this ZIP into the **existing project root** and merge the `app`, `tests`, and `docs` folders.
3. Replace only `app/tender_requirements_extractor.py` and `app/pages/2_AI_Tender_Document_Copilot.py`; add `app/tender_review_audit.py`, the two test files, and this doc.
4. Do **not** replace `.env`, `.venv`, `.git`, datasets, model artifacts or company-profile data. Keep your Gemini key only in your local `.env`; never paste it into chat.
5. Run targeted checks first:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_real_tender_extraction_regression.py tests/test_tender_review_audit.py tests/test_gemini_tender_extractor.py -q
```

6. Then run the full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

7. Restart the app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/market_explorer.py
```

8. In AI Tender Document Copilot, reprocess `Tendernotice_1(1).pdf`, choose Gemini AI or Rule-based, and click **Extract candidate fields for Bid-Fit**. Scroll to **Tender review flags**. Read each source quote before confirming/transferring any draft.

## Acceptance criteria

- EMD remains INR 26,000 and turnover remains INR 2,100,000 as candidate values.
- The main PDF does not yield a guessed closing date; the UI says portal lookup is required.
- The extracted certification text contains separate ATEX/IECEx, PESO/CCOE and calibration candidates, with page evidence.
- The similar-project field stays blank instead of collapsing the item-wise 1-/2-/3-PO alternatives to one count.
- Warranty wording and temperature-range wording are visibly flagged for official/technical clarification.
- Transfer to Bid-Fit still requires the existing user-review checkbox; flags do not act as approval.

## Important limitations

- This is source-text auditing, not OCR; image-only text can still be missed.
- The current Bid-Fit rule engine does not yet score delivery capacity, positive net worth, item-wise experience alternatives or warranty/specification conflicts automatically. This patch shows the evidence and asks for review; it does not pretend those are already integrated into scoring.
- Current tender status, latest deadline and corrigenda must be checked on the official e-tender portal.
