# Copilot Draft Persistence Fix

## Problem fixed

The Copilot draft-review inputs could be blank after navigating to Company Bid-Fit Analysis and then returning to the Copilot page, even though the extracted evidence table remained visible.

## Root cause

The draft inputs were inside a Streamlit form. Form edits are batched until a form button is submitted. A user who navigated away before saving could lose the latest edits, and Streamlit can clean widget-bound state when that widget is not on the active page.

## Changes

- Draft review inputs now render outside the `st.form` container.
- Each input uses an `on_change` callback to mirror its value into the non-widget session key `copilot_bidfit_reviewed_values`.
- Returning to the page restores widget keys from that non-widget dictionary.
- The review checkbox is mirrored separately and also restored after navigation.
- A **Save draft edits** button remains as an explicit save action.
- Extracted values and source evidence remain separate from the user's editable values.
- The existing PDF/DOCX/TXT/CSV/XLSX/XLS document support is preserved.

## Apply

Merge these paths into the current project root:

- `app/pages/2_AI_Tender_Document_Copilot.py` — replace
- `app/copilot_review_state.py` — add
- `tests/test_copilot_review_state.py` — add
- `docs/COPILOT_DRAFT_PERSISTENCE_FIX.md` — add

No dependency change is required. Do not overwrite `.git`, `.venv`, `.env`, or data files.

## Verify

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m streamlit run app/market_explorer.py
```

Manual test:

1. Upload and process the demo tender file.
2. Click **Extract candidate fields for Bid-Fit** once.
3. Edit a draft field, for example the tender title, and do not click Save.
4. Navigate to Company Bid-Fit Analysis and return to AI Tender Document Copilot.
5. Confirm the field retains the edit and you do not need to extract again.
6. Check the review confirmation box, navigate away, then return and confirm that it remains checked for the session.

## Limitation

State persists within the active Streamlit session. It is not database-backed and is not guaranteed after a server restart, session expiration, or a new browser session.
