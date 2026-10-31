# Final Integration Changelog — Release Candidate

This release candidate consolidates the Market Explorer, ML category classifier, AI Tender Document Copilot, and Company Bid-Fit prototype. The Copilot reliability work is included as one consistent source snapshot rather than a stack of one-off patches.

## Final Copilot reliability changes

- Page-preserving PDF text extraction with optional local Tesseract OCR for scanned/image-only pages.
- Full-document deterministic Q&A for supported tender intents before an optional LLM call.
- Local handling for work-wise EMD and bid-document-fee schedules, bid validity, submission/opening schedules, turnover, warranty, JV scope and contractor class.
- Explicit handling of missing numeric turnover, work-package alternatives and conflicting closing dates without silently inventing or collapsing values.
- Local Bid-Fit baseline extraction with Gemini enrichment only when available; AI blanks/conflicts do not silently erase safer local candidates.
- Bounded provider retries; quota exhaustion skips repeated calls and preserves local/offline functionality.
- Local validation utility that runs OCR, Q&A, Bid-Fit extraction and source audit without API/provider calls.
- Updated README, test guide, status and known-limitations documentation.

## Verification on assembled snapshot

- `python -m pytest tests -q`: **192 passed**.
- Updated application and diagnostic modules compile successfully.
- The Odisha 53-page uploaded tender was processed locally: 10 OCR pages, 237 chunks, 16 EMD and fee schedule rows, 90-day bid validity, three-year warranty, JV serials 1 and 4–16, C & D contractor class, no numeric turnover threshold found in readable eligibility text, and submission-date conflict flagged.
- The Banbasa eight-page scan has prior prepared-snapshot smoke-test results documented in `docs/TENDER_COPILOT_FINAL_FIX.md`; run the Windows diagnostic to confirm the owner environment.

## Not part of this release

No current/live tender feed, portal login/CAPTCHA automation, automatic bid submission, guaranteed eligibility, tender-win prediction or profitability model is included. OCR/AI candidates still require human verification against original documents and corrigenda.

- Fixed an actual-PDF Odisha deadline parsing issue where a line break, `DTCN.)` abbreviation and dotted leaders truncated the stale page-16 date. Added a layout-specific regression; current Q&A/Bid-Fit correctly surface the page-16/page-22 conflict.
- Added an extraction processing-version guard so stale cached page indexes and Bid-Fit drafts are not silently reused after engine updates.
- Rule-based (offline) extraction is the default; optional Gemini errors/quota no longer block local candidate extraction or common deterministic Q&A.
