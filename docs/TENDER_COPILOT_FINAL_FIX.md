# Tender Copilot final hybrid OCR/Q&A fix

## Why the earlier screenshots still showed `Not found`

The app has three separate stages: (1) scanned-PDF OCR and page/chunk indexing, (2) question-answer retrieval, and (3) Bid-Fit draft extraction. Improving retrieval alone cannot populate the Bid-Fit turnover field. In addition, Streamlit keeps the processed document and draft in the current browser session; changing code does not rebuild an already-loaded draft until the document is cleared/reprocessed or the session is restarted.

The final patch changes all three relevant paths in one consistent snapshot.

## Behavior after this patch

- Local Tesseract OCR remains in the file-processing path for scanned pages. OCR text, physical page numbers and a per-page OCR marker are kept; it does not require a Gemini call.
- Common labelled questions (annual turnover, EMD/bid security, tender fee, estimated tender cost/value, net worth and submission deadline) are answered from the complete extracted page corpus before calling an LLM. A clear, source-supported answer does not spend Gemini quota.
- Open-ended questions keep TF-IDF retrieval, structured shorter evidence excerpts and query-term highlighting. If a provider request fails, the retrieved source passages remain available.
- Bid-Fit extraction always calculates a local evidence-backed baseline first. Valid Gemini fields can enrich it, but an empty or conflicting Gemini turnover/EMD/date candidate cannot silently erase the stronger labelled local value.
- If Gemini explicitly returns quota exhaustion, the code does not retry that same request multiple times; the UI also remembers the quota failure for the current browser session and skips further Gemini requests until the user explicitly permits one retry after checking the quota reset. Local extraction and common Q&A continue to work.
- Work title extraction prioritizes a first-page `Name of Work` / `Tender Title` label and stops at the next table-row label. This prevents an unrelated later phrase like “total payment received … TDS amount” from being mistaken for the tender title.
- A single scalar `Min Similar Projects` value is suppressed when the tender specifies multiple alternative work-count/value routes such as `3 OR 2 OR 1` completed works. The full clause is kept for review.
- Every output is still a draft candidate, not a final eligibility/legal conclusion. OCR can misread digits or tables; check the original page image and corrigenda.

## Prepared-snapshot smoke-test on the uploaded 8-page Banbasa scan

Local OCR reads all 8 pages. The latest prepared project snapshot produced:

| Question / field | Result | Source |
|---|---|---|
| Annual turnover | ₹111.0 crore = ₹1,11,00,00,000 full INR | PDF page 4 |
| EMD / earnest money | ₹3,78,60,538 | PDF page 1 |
| Submission deadline | 14/11/2026 up to 15:00 Hrs. | PDF page 1 |
| Tender title | Development of Integrated Check post at Banbasa, Uttarakhand on Indo-Nepal Border on EPC basis | PDF page 1 |
| Work location | Banbasa, Uttarakhand — candidate parsed from the named work | PDF page 1 |
| Similar-work count | Kept blank because three qualification routes are alternatives | PDF page 2 |

The assembled release candidate full project test suite passes 192 tests. These are tests run in the assembled development snapshot; the user's Windows repository must still be tested after patching.

## Apply on Windows / IntelliJ

1. Stop Streamlit with `Ctrl+C`.
2. Back up the files listed in `PATCH_README.txt`.
3. Extract the patch ZIP into `D:\Github\public-procurement-opportunity-intelligence` and allow folders to merge. Do not replace `.env`, `.venv`, `.git`, datasets, or model artifacts.
4. If OCR is already working, do not reinstall Tesseract. Ensure the Python dependency is installed with `\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt`.
5. Run the focused tests and then the full suite using the commands in `PATCH_README.txt`.
6. Restart Streamlit. On the Copilot page, click **Clear loaded document and its draft**, remove the selected PDF using the file chip's `×`, upload `Tendernotice_1 (3).pdf` again and click **Process selected document**. This forces a fresh OCR index instead of reusing an earlier session cache.
7. Ask `annual turnover?` in Q&A; expected local answer is ₹111 crore with PDF page 4. Then click **Extract candidate fields for Bid-Fit**. With Gemini selected, local extraction runs first; if the quota is exhausted, the local value remains in the field with source evidence.

Never share an API key or include `.env` in the patch/ZIP.


## Cross-state regression — Odisha Mayurbhanj (53-page document)

The release test suite also covers a second real tender from Odisha. Local answers include 90-day bid validity, three-year warranty, Joint Venture work serials 1 and 4–16, C & D contractor class, work-wise EMD and bid-document-cost schedules, no numeric turnover threshold found in readable eligibility text, bid-opening schedule, and conflicting submission-date entries. See `docs/FINAL_TESTING_GUIDE.md` for the tested pages and the local Windows commands.
