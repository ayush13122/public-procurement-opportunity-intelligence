# AI Tender Document Copilot — Release Candidate

## Purpose

The Copilot supports tender-document review. It extracts page text, indexes evidence, answers common tender questions from the whole readable document when a supported local rule applies, and prepares evidence-backed candidate fields for human review before Bid-Fit. Gemini/OpenAI are optional enrichers for broader questions; common supported questions do not need a provider call.

It does **not** verify live tender status, fetch corrigenda, guarantee eligibility, predict awards, or calculate profit from tender value alone.

## Start the application

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m streamlit run app\market_explorer.py
```

`requirements-ocr.txt` installs the Python-side PDF/OCR dependency. Tesseract OCR itself is a separate Windows program. On this machine, the confirmed location was `D:\app\Tesseract-OCR`; `tesseract --list-langs` should include `eng`. If the command is not found, add the Tesseract install directory to PATH or configure its full path in the local environment.

## Offline validation tool (recommended before opening the UI)

The diagnostic script processes a PDF locally, does not call Gemini/OpenAI, and reports OCR coverage, chunks, Bid-Fit draft fields, direct local Q&A answers, and review flags.

```powershell
.\.venv\Scripts\python.exe tools\validate_tender_copilot.py "D:\path\to\Tender.pdf"
```

Test selected questions:

```powershell
.\.venv\Scripts\python.exe tools\validate_tender_copilot.py "D:\path\to\Tender.pdf" --question "What is the EMD amount?" --question "What is the bid validity period?"
```

Machine-readable output:

```powershell
.\.venv\Scripts\python.exe tools\validate_tender_copilot.py "D:\path\to\Tender.pdf" --json
```

The diagnostic prints `Provider/API calls: 0`. It is intended to distinguish an OCR/extractor issue from a Streamlit session/cache/UI issue.

## Processing and answer flow

1. Validate the file and extract selectable text page-by-page.
2. OCR only pages with insufficient embedded text, when Tesseract and English language data are available.
3. Preserve physical page numbers and original line-layout text for table-aware parsing, then build local TF-IDF searchable chunks.
4. For supported intents, scan the **full extracted page corpus first**, not only the top-ranked chunks. Supported local answers currently include EMD/Bid Security (including work-wise schedules), bid-document fees (including work-wise schedules), turnover, net worth, estimated tender value, submission deadline/conflicts, bid-opening schedule, bid validity, warranty, Joint Venture work serials, and eligible contractor class.
5. If no deterministic answer is available, show retrieved passages. A configured Gemini/OpenAI provider may generate an answer from retrieved evidence, but provider calls are optional and may be blocked by quota/service availability.
6. Keep the evidence visible with source locations. Highlighted matching words aid navigation; they are not themselves proof of correctness.
7. Bid-Fit draft extraction runs local rules first. Gemini may enrich candidates, but safety findings such as work-specific EMD, alternative similar-work routes, and conflicting dates are not replaced by a misleading scalar.
8. A human must review every field and the source page before sending the draft into Company Bid-Fit Analysis.

## Gemini/OpenAI configuration (optional)

For Gemini, first install the optional SDK with `python -m pip install -r requirements-gemini.txt`, then configure `GEMINI_API_KEY` in the repository-root `.env`. Optionally set `GEMINI_TENDER_EXTRACTION_MODEL` to a model available to the Google AI Studio project. For OpenAI, configure `OPENAI_API_KEY` and a supported `TENDER_COPILOT_MODEL`.

Never commit or share `.env`. Restart Streamlit after editing it. Free-tier quota/service availability is controlled by the provider; this app cannot raise provider quotas. When quota is exhausted, common supported local Q&A and local Bid-Fit extraction continue without a new model request.

## Refreshing a document after code updates

Streamlit can retain a processed document and draft in the current browser session. After updating code:

1. Stop Streamlit with `Ctrl+C` and restart it.
2. Use **Clear loaded document and its draft** on the Copilot page.
3. Remove the selected PDF using the `x` on the upload chip.
4. Upload it again and click **Process selected document**.
5. Confirm the displayed PDF page count, searchable chunk count, and OCR page count before testing questions.

## Regression examples

### Banbasa, Uttarakhand (8-page scanned EPC notice)

The prepared release-candidate smoke-test read all 8 pages using local OCR and returned:

- Average annual gross turnover: ₹111.0 crore = ₹1,11,00,00,000, PDF page 4; five financial years ending 31 March 2025.
- EMD: ₹3,78,60,538, PDF page 1.
- Submission deadline: 14/11/2026 up to 15:00 Hrs., PDF page 1.
- Similar-work options: 3 OR 2 OR 1 completed works with different minimum values. The scalar Min Similar Projects field is cleared; the full alternatives remain as evidence/review flags.

### Mayurbhanj, Odisha (53-page multi-work tender)

The prepared release-candidate smoke-test read 53 pages, OCR'd 10 scanned pages, and returned:

- Bid validity: 90 days, PDF page 17.
- Warranty: 3 years, PDF page 5.
- JV required for work serials 1 and 4–16, PDF page 5.
- Contractor classes: C & D, PDF page 2.
- EMD varies by package; all 16 rows are displayed from PDF pages 2–3. No single EMD amount is put into Bid-Fit.
- No numeric annual turnover threshold was found in the readable eligibility text; Clause 83 is at PDF page 30. This is phrased as a search result, not a legal guarantee that no annexure/corrigendum has a threshold.
- Conflicting date entries were found: 09.11.2025 in Contract Data (PDF page 16) and 10.11.2026 up to 5:30 PM in the detailed notice (PDF page 22). The app does not silently choose one; it flags portal/corrigendum verification.

These are results from the prepared development snapshot. Run the same PDFs through the local diagnostic on your Windows project to verify your installation.

## Test suite

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

The assembled release candidate currently passes 192 automated tests. Tests do not call external model APIs. Your local test count may differ if the repository has additional tests or local modifications.

## Limitations

- OCR can misread digits, dates, tables, stamps and scanned low-resolution text. Check critical values against the original page image.
- TF-IDF retrieval is lexical, not a modern semantic vector database. Synonyms and complex cross-page clauses may still be missed.
- Local direct Q&A only covers supported question types; open-ended questions may show evidence-only summaries or optionally use an LLM.
- Multi-work tender notices require the bidder to identify the chosen work serial before using the EMD, delivery location, scope or package-specific condition in Bid-Fit.
- Live portal status, deadline updates and corrigenda are not fetched automatically.
- Company profile information remains user-entered. The app does not decide legal eligibility or tender award probability.
