# Copilot-to-Bid-Fit integration (first version)

## What changed

The Copilot page now includes a local, rule-based extraction step for common tender fields. Users can review/edit the draft and transfer it into the Company Bid-Fit Analysis form through Streamlit session state.

Extracted candidates include tender title, scope keyword suggestions, work region, minimum experience, similar projects, turnover, certifications/registrations, EMD and closing date. Every extracted candidate keeps page evidence. Unfound fields stay blank.

## Important safety behaviour

- This first extractor uses local regular expressions and a small vocabulary; it is not an LLM and will not understand every tender format.
- No official tender source URL is inferred from arbitrary PDF links. The user must enter it on the Bid-Fit page.
- The final requirements-reviewed, official-source-checked and closing-date-known checkboxes remain unchecked after transfer.
- The user must review the draft and evidence before the transfer button becomes effective.
- The Bid-Fit page shows evidence from the imported PDF, but this does not verify authenticity, current status, or corrigenda.
- A blank field means the rule-based parser did not confidently find it; it does not mean the tender has no such requirement.
- The fit score remains rule-based suitability screening, not bid-win probability or profit prediction.

## How to use

1. Open **AI Tender Document Copilot** and upload a selectable-text tender PDF.
2. Click **Process PDF**.
3. Under **Prepare a Bid-Fit draft from this PDF**, click **Extract candidate fields for Bid-Fit**.
4. Inspect each extracted value and its page evidence. Correct fields as needed; leave unspecified requirements blank.
5. Tick the review confirmation and click **Send reviewed draft to Bid-Fit**.
6. Open **Company Bid-Fit Analysis**. The tender fields will be prefilled; the company profile remains separate.
7. Add the actual official tender URL, verify the complete notice and current corrigenda, and tick the confirmation boxes only after doing those checks.

## Current limitations

This version does not call Gemini or OpenAI for requirement extraction, cannot OCR scanned PDFs, cannot determine the current live status of a tender, and cannot establish profitability. The extracted data are suggestions and require user review.
