# Copilot Q&A: structured evidence and Gemini recovery

## Why the earlier screen said that no LLM was configured
The Q&A code previously read only `OPENAI_API_KEY`; the separate tender-field extractor read `GEMINI_API_KEY`. As a result, a configured Gemini key could extract tender fields but could not power the question-answering section. This patch adds Gemini as the Q&A provider when no OpenAI key is set.

## Retrieval and display changes
- Chunks are split around likely sentence/numbered-clause boundaries and kept shorter, with page/location metadata preserved.
- Query terms are expanded with common public-procurement expressions (deadline/closing date, EMD/bid security, similar supply/purchase order, certification/certificate).
- Numeric amount questions give stronger rank weight to source clauses containing the relevant amount; the complete tender still has to be checked when an answer spans multiple pages.
- Retrieved evidence appears as smaller clauses/table cells. Direct query terms and recognized wording variants are highlighted after HTML escaping; the source text is not executed as HTML.
- When no model key is configured or a request fails, the UI presents a labelled local evidence summary. It is not presented as an AI-generated conclusion.

## Gemini outage behavior
Transient 503/UNAVAILABLE, 429 and common 500-style service errors receive bounded retries. Persistent provider errors are shown as provider unavailability and the UI retains the retrieved evidence. This helps with temporary spikes but cannot guarantee that Google's endpoint will recover. Local evidence search and rule-based field extraction remain available.

## Use
Keep `GEMINI_API_KEY` in the local `.env` only. By default, Gemini Q&A reuses `GEMINI_TENDER_EXTRACTION_MODEL`; set `GEMINI_TENDER_QA_MODEL` only when a different model is known to be available in the user's account. `GEMINI_TENDER_MAX_RETRIES` defaults to 2 retries and `GEMINI_TENDER_RETRY_BASE_SECONDS` defaults to 1 second.

All answers and extracted fields remain source-grounded candidates. Confirm deadlines, conflicting clauses and eligibility rules against the official portal and any corrigenda.
