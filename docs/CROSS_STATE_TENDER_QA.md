# Cross-state tender Q&A improvements

## Goal

Tender question answering must work from the uploaded document rather than relying on the Assam/AGCL notice, a named state e-procurement portal, or vendor-specific terminology. The question expansion vocabulary now covers common India-wide procurement concepts such as bid security/EMD, tender-document fee, bid submission deadline, annual turnover, net worth, past/similar work experience, performance security, bid validity, delivery/completion period, payment terms, estimated tender value, required documents, scope/specifications, warranty, work/delivery location, and submission method.

## How it works

1. PDF/document text and source page/block locations are extracted as before.
2. Generic question synonyms expand lexical retrieval. This does not insert answers or assume the tender belongs to a particular state.
3. Question-specific scoring favours directly labelled clauses over generic process paragraphs.
4. When an LLM provider is unavailable, the local fallback attempts a direct, labelled answer for common money fields and deadline fields using only retrieved evidence. The amount must occur close to a relevant label. It distinguishes tender fee from EMD, and refuses to infer a closing date from the notice issue date when the notice delegates the date to an online portal.
5. Supporting snippets remain visible so users can inspect the original evidence. No live portal/corrigendum status is implied.

## Limitations

- State-agnostic does not mean all tender formats are guaranteed to parse. Scanned PDFs, non-standard tables, image-only annexures, and ambiguous wording may still require OCR or manual review.
- The local fallback uses deterministic rules for common fields, not generative comprehension. Complex conditions, alternatives, contradictory clauses, and legal conclusions still require an LLM or manual review.
- Only extracted/retrieved document text is used. The app does not scrape the referenced portal or verify current tender status.
- API-provider rate limits are separate from local retrieval. A quota error should not prevent users from inspecting the retrieved evidence.

## Regression test

`tests/test_cross_state_tender_qa.py` uses synthetic examples with generic portal wording, alternative labels, a tender fee next to an EMD value, a delegated deadline, and Hinglish phrasing. These examples do not use the Assam tender language as a required template.
