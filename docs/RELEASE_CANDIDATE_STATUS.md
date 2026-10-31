# Public Procurement Opportunity Intelligence — Release Candidate Status

## Included modules

1. Historical Procurement Market Explorer for the supplied Assam public procurement dataset.
2. Broad tender-category classifier (`Works`, `Goods`, `Services`).
3. AI Tender Document Copilot with selectable PDF text extraction, optional local scanned-page OCR, source-grounded local Q&A, optional Gemini/OpenAI enrichment, and evidence-backed Bid-Fit candidate extraction.
4. Company Bid-Fit Analysis with transparent rule-based screening and manual-review gates.

## Verification performed on the assembled release candidate

- Full automated test suite: **192 passed** in the assembled development snapshot.
- Python compile checks: passed for updated application modules and the diagnostic tool.
- Actual Banbasa 8-page scanned PDF smoke-test: local OCR read all 8 pages at 150 DPI in about 30 seconds. Bid-Fit extracted annual turnover INR 1,110,000,000 (page 4), EMD INR 37,860,538 (page 1), and closing date 2026-11-14 (page 1); local Q&A returned the ₹111 crore turnover, ₹3,78,60,538 EMD and 14/11/2026 15:00 deadline with source pages.
- Actual Odisha 53-page tender smoke-test: 53 pages parsed, 10 pages OCR'd; common local answers covered 90-day bid validity, 3-year warranty, JV work serials 1 and 4–16, C&D contractor class, all 16 work-specific EMD rows and all 16 bid-document-fee rows, no numeric turnover threshold found in readable eligibility text, and conflicting submission-date entries flagged; the opening schedule is also returned locally.
- Local diagnostic tool added: `tools/validate_tender_copilot.py`. It makes zero provider/API calls.

These results were obtained in the assembled development container. They do **not** prove the user's Windows checkout is updated or that every possible tender format will be parsed correctly. The final Windows test commands are in `docs/FINAL_TESTING_GUIDE.md`.

## Release scope and claims

The app is a functional academic/portfolio prototype for procurement analysis and tender-document decision support. It is not a production procurement platform. It does not ingest all Indian tender portals live, verify corrigenda, log into portals, submit bids, certify eligibility, predict wins, or calculate margins.

## Release checklist for the project owner

- [ ] Apply the consolidated patch to the existing Windows repository; keep `.env`, `.venv`, `.git`, data and model artifacts untouched.
- [ ] Install/update `requirements-ocr.txt` in the existing virtual environment.
- [ ] Run the full test suite locally and record the actual result.
- [ ] Run `tools/validate_tender_copilot.py` on the Banbasa and Odisha sample PDFs.
- [ ] Start Streamlit and smoke-test all four pages.
- [ ] Verify one selectable-text PDF and one scanned PDF.
- [ ] Review all amounts/dates and confirm the portal/corrigendum separately.
- [ ] Check Git status and remove temporary files, secrets, uploads and generated caches before publishing.
- [ ] Verify README setup, dataset attribution and model artifact instructions.

## Model baseline recorded in project history

The existing broad-category classifier baseline recorded in the project history was accuracy 93.35%, macro F1 86.73%, weighted F1 93.66%, and balanced accuracy 91.55% on the recorded temporal holdout. These are historical model results, not a newly re-run metric in this final Copilot validation pass.

Detailed current real-PDF results, including the Odisha layout-specific deadline conflict regression, are in `docs/VALIDATION_RESULTS.md`.
