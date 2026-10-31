# Windows Setup and Testing Guide

This guide applies to the current repository. It does not require applying an older patch ZIP or merging files from a separate patch folder.

## A. Requirements

- Windows 10/11.
- Python 3.11.
- Git.
- Power BI Desktop for opening the Power BI files.
- Tesseract OCR only if scanned-PDF OCR is required.

## B. Create a clean Python environment

Run from the repository root. Do not recreate `.venv` while its Python executable is in use. Open a fresh terminal and deactivate the environment first if you intentionally need to rebuild it.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Check the environment:

```powershell
python -m pip check
python --version
```

## C. Optional integrations

### Gemini

Install only when using Gemini-backed workflows:

```powershell
python -m pip install -r requirements-gemini.txt
```

### OCR

Install the Python OCR dependency:

```powershell
python -m pip install -r requirements-ocr.txt
```

Tesseract is a separate desktop application and must be installed separately. Verify that PowerShell can find it:

```powershell
tesseract --version
tesseract --list-langs
```

The language list should include `eng` for English OCR.

OCR may misread digits, dates, amounts and tables. Check important extracted fields against the original PDF page.

## D. Configure API credentials

Create `.env` from the template **only if `.env` does not already exist**:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Add provider credentials to the local `.env` file only when required by the workflow. Do not commit `.env`, paste API keys into source files or publish credentials in logs or screenshots.

Local retrieval and supported rule-based answers can operate without an LLM provider. Provider-backed workflows may send relevant prompts and document excerpts to the configured provider. Do not upload confidential documents unless authorised.

## E. Run automated tests

Run the complete suite:

```powershell
python -m pytest tests -q
```

The recorded Windows release snapshot passed 210 tests. The actual test count may change as tests are added or modified; use the current command output as the authoritative result.

Check dependency consistency:

```powershell
python -m pip check
```

## F. Run the Streamlit application

```powershell
python -m streamlit run app/market_explorer.py
```

Check the four application areas:

1. Historical Procurement Market Explorer.
2. ML Tender Category Classifier.
3. AI Tender Document Copilot.
4. Company Bid-Fit Analysis.

For the Copilot, test a selectable-text PDF and, when OCR is installed, a scanned PDF. Verify extracted amounts, dates and eligibility clauses against the original page and inspect the evidence page references.

## G. Offline tender diagnostic

The diagnostic utility makes no Gemini/OpenAI provider calls:

```powershell
python tools/validate_tender_copilot.py "C:\path\to\your\local-test-tender.pdf"
```

Use PDFs that you are authorised to process. Keep private tender PDFs outside the public repository. Do not commit customer, company-confidential or third-party tender documents without permission.

Detailed historical diagnostic observations are documented in `docs/VALIDATION_RESULTS.md`. They are not a guarantee that every tender format will be parsed correctly.

## H. Open the Power BI report

### Native PBIX

Open `powerbi/exports/Public_Procurement_Market_Intelligence.pbix` in Power BI Desktop, refresh if needed and inspect the report pages.

### Editable PBIP source

Open `powerbi/Public_Procurement_Market_Intelligence/Public Procurement Market Intelligence.pbip` in Power BI Desktop.

The Power Query parameter `pCsvPath` references the cleaned dataset. If the repository is stored in a different location, update the parameter to the local `data/processed/assam_procurement_cleaned.csv` path, then refresh.

Inspect the five report pages and test slicers before relying on a result. Save any further report changes from Power BI Desktop.

## I. Before publishing

Check:

```powershell
git status --short --branch
git diff --check
```

Confirm that local `.env`, `.venv`, backups, `.pbi` cache folders and original private tender PDFs are excluded from version control.

Never publish API keys, private tender files, local cache files or machine-specific credentials.