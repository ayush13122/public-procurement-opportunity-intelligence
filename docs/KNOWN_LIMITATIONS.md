# Known Limitations

## Historical procurement analytics

- The historical analytical dataset is Assam procurement records; it is not a live all-India tender feed.
- Works dominates the source extract; that distribution must not be generalized to India as a whole.
- Tender-value records include zero and missing/non-numeric values. Currency/unit has not been independently verified; zero does not automatically mean “free”.
- The category taxonomy is provisional. Source/assignment field consistency does not prove semantic classification correctness.

## ML tender-category classifier

- It predicts only the broad source category (`Works`, `Goods`, `Services`) from tender title text.
- Labels come from the historical source dataset; source label noise can limit model performance.
- The temporal holdout may still contain repeated normalized tender-title templates, making some examples easier than truly unseen titles.
- Class scores are not calibrated and must not be interpreted as bid-win probability, eligibility, or profitability.

## AI Tender Document Copilot

- Scanned/image-only PDF pages can be OCR-processed locally when PyMuPDF and Tesseract with the required language data are installed. OCR may misread digits, dates, amounts and table structure; verify important clauses against page images.
- Retrieval uses local TF-IDF text matching, not embeddings or a semantic vector database. Lexical ranking can miss a semantically related clause or rank a nearby generic certificate clause too highly.
- Direct local answers are deterministic and source-backed for supported question intents, but they are not full legal interpretation. Alternative routes, work-wise schedules and conflicts are surfaced rather than silently collapsed into one value.
- LLM-generated answers can still be wrong. Page references are evidence to inspect, not a guarantee.
- If a provider API key is configured, the question and retrieved excerpts may be sent to that provider. The full PDF is not deliberately sent by this module; do not upload confidential documents unless authorised.
- Live status, corrigenda, live deadlines and official portal updates are not checked automatically.

## Company Bid-Fit Analysis

- Tender requirements may be drafted from the uploaded notice, but values remain candidates until a person reviews the evidence. Company profile/capability information is user-entered.
- A multi-work tender may contain different EMD, scope, work location, contractor class or eligibility requirements by work serial. The user must select the specific work before using those fields for a company assessment.
- Capability fit uses transparent rules and text matching; it does not fully understand synonyms, technical equivalence, JV share calculations, or all forms of contractual eligibility.
- `POTENTIAL BID` is a rule-based screening result from submitted fields and confirmations. It is not a legal opinion, award prediction, or profitability calculation.
- No live portal status or deadline is independently verified by the current engine.

## Not implemented

- Automatic multi-portal/current-tender ingestion or scheduled refresh.
- Automatic login, CAPTCHA solving, tender submission, or storing portal credentials.
- Fully semantic interpretation of every BOQ/financial table, scanned annexure or handwritten/correspondence document.
- Company-specific award outcome prediction or validated margin/profit prediction.
- Legal eligibility certification or automated corrigendum reconciliation.
