# Real Tender Extraction Fix — Hinglish Handover

## Why this patch exists

The uploaded 56-page Assam Gas Company Limited tender PDF was successfully read, but the previous rule-based extractor missed several fields that are present in the PDF. It also read “warranty” from the table-of-contents page as if it were a capability.

## Changes

- Extracts a title from headers such as `TENDER DOCUMENT FOR SUPPLY OF ...`.
- Treats `Bid Security Amount` as an EMD/bid-security label.
- Extracts delivery destination phrases such as `FOR AGCL Stores, Duliajan, Assam basis`.
- Recognizes pressure and temperature transmitter product terms as capability suggestions.
- Avoids using a table-of-contents/index page as scope evidence.
- Identifies ATEX Certificate from the BEC wording where available, while still marking it for human review.
- Supports dates such as `29-Oct-2026` in portal tender-details printouts.
- If the main tender PDF explicitly says that the closing date is on the online e-tender portal, leaves the date blank and displays a portal-lookup status instead of guessing.

## Confirmed extraction from the supplied Tendernotice_1.pdf

| Field | Draft result | Source page | Notes |
|---|---|---:|---|
| Tender title | Supply of Pressure Transmitter and Temperature Transmitter | 1 | Candidate; verify |
| EMD / Bid Security | INR 26,000 | 2 | Candidate; verify |
| Delivery destination | AGCL Stores, Duliajan, Assam | 32 | Candidate; verify |
| Capabilities | Pressure transmitter supply; temperature transmitter supply | 1 | Keyword suggestions, not legal conclusions |
| Annual turnover threshold | INR 2,100,000 | 37 | Wording says “above” INR 21,00,000; strict threshold semantics need review |
| Certification candidate | ATEX Certificate | 34 | Verify applicability and submission stage |
| Closing date | Blank / portal lookup required | 1 | Main PDF delegates the date/time to the live e-tender portal |
| Similar-project count | Blank | 34–37 | The BEC uses alternative PO/quantity routes; do not collapse this into one guessed count |
| Minimum years | Blank | 34–37 | The BEC refers to orders executed in the last 3 years, not a simple “company must have existed for 3 years” rule |

These values are extraction candidates only. Confirm against the official portal, all annexures, and any current corrigendum before relying on them.

## Apply

Copy `app/tender_requirements_extractor.py` into the project root, replacing the file at:

`app/tender_requirements_extractor.py`

Add `tests/test_real_tender_extraction_regression.py` under `tests/`.

Then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

This patch intentionally does not include or replace `app/tender_copilot.py`, page UI files, `.env`, `.venv`, datasets, or the Git repository.