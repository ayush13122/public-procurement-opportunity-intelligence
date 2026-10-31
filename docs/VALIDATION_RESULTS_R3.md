# Tender Copilot Offline Extraction Fix r3 — validation

Date: 30 October 2026

## Automated checks

- Copilot-focused regression suite: **108 passed**.
- Python compile checks passed for the updated extractor, answer engine, Streamlit page and validation utility.
- A repo-wide test run was not claimed: this incremental patch workspace does not contain unrelated project modules under `src/` and other `app/` modules.

## New regression coverage

1. OCR rupee glyph `k` directly before `3,78,60,538/-` after the `Earnest Money` label, confirmed by the following amount-in-words clause:
   - Bid-Fit field extracts `37860538` with an OCR-specific review status.
   - Local Q&A returns `₹3,78,60,538` with page evidence.
2. Banbasa `work experience during the last Seven years` is exposed as an **experience lookback** field. It is not transferred into the minimum bidder/company-age field.
3. Conflicting 3-year and 5-year experience lookback wording remains a conflict; no single scalar is chosen.
4. Experience lookback metadata is excluded from `build_bidfit_prefill_payload`.

## Actual tender diagnostics

### Banbasa Integrated Check Post — `Tendernotice_1 (3).pdf`

Full offline diagnostic including OCR:

- 8 PDF pages; OCR ran on 8 pages; 30 searchable chunks.
- EMD ₹3,78,60,538 — page 1.
- Annual turnover ₹111 crore / ₹1,110,000,000 full INR — page 4.
- Experience lookback 7 years — page 2; explicitly not minimum company age.
- Similar completed works: alternative 3 / 2 / 1 routes; scalar project-count field remains blank.
- Deadline 14/11/2026 at 15:00 — page 1.
- Local EMD Q&A returns the amount with source page evidence.

### Odisha Agriculture — `Tendernotice_1 (4).pdf`

Embedded-text diagnostic (OCR skipped in this r3 run):

- 53 pages; 219 searchable chunks.
- 16 package-specific EMD rows remain a schedule, not a universal EMD scalar.
- No numeric annual turnover threshold found in the extracted eligibility section.
- Conflicting dates remain flagged instead of selecting one scalar date.

### Assam Gas Company — `Tendernotice_1(1).pdf`

Embedded-text diagnostic (OCR skipped in this r3 run):

- 56 pages; 192 searchable chunks.
- EMD ₹26,000 — page 2.
- Minimum annual turnover ₹21 lakh — page 37.
- Experience lookback wording conflicts between 3 and 5 years; new field shows the conflict and leaves its scalar blank.
- Closing date remains portal-only; it is not inferred from the tender issue date.

## Important limit

The OCR-glyph regression fixture reproduces the exact `k3,78,60,538` OCR text visible in the user's Streamlit evidence. The container's Tesseract run on the supplied Banbasa PDF read the currency glyph as `Rs.` on page 1, so the synthetic OCR variant test is what verifies the `k`-specific fallback.
