# Scanned PDF OCR support for Tender Copilot

## Why this is needed

Some procurement portals publish image-only/scanned PDFs. `pypdf` can read their page count but returns no text, so the current retrieval index has no searchable chunks. The uploaded Banbasa integrated check post notice has 8 pages and no selectable text layer.

## What the patch changes

- `app/tender_copilot.py`: first extracts embedded text; only pages with fewer than 40 characters are OCR'd locally.
- Keeps physical PDF page numbers and adds `ocr_used` / `text_extraction_method` metadata to each page record.
- Uses PyMuPDF's Tesseract-backed OCR, in English by default. It does not upload the PDF to Gemini or another API for OCR.
- Keeps already-searchable PDFs on the fast text extraction path.
- Provides a helpful error when the optional OCR package or Tesseract engine/language data is missing.

## Windows setup (IntelliJ)

1. Install Tesseract OCR from the Windows installer linked by the Tesseract documentation: https://github.com/UB-Mannheim/tesseract/wiki
2. During setup, include English language data and add Tesseract to PATH if the installer offers that option.
3. Restart the IntelliJ terminal; run `tesseract --version` to confirm Windows can find it.
4. From the repository root, run:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
   .\.venv\Scripts\python.exe -m pytest tests\test_tender_ocr.py tests\test_tender_copilot.py -q
   .\.venv\Scripts\python.exe -m streamlit run app\market_explorer.py
   ```

5. Re-select the scanned PDF and click **Process selected document** once again. The OCR is performed at processing time, so an already-processed cached file must be reprocessed in a fresh Streamlit session or after changing the file selection.

## Language

Default OCR language is English (`eng`). Set `TENDER_OCR_LANGUAGE` to a Tesseract language code that is installed, for example `eng+hin` only if both language data files are installed.

## Accuracy and privacy

OCR can misread numbers, punctuation, table cells and low-quality scans. Treat all extracted tender amounts, dates and eligibility clauses as candidates and verify against the original page. OCR is local; it does not make the PDF searchable to the cloud provider or remove the need to verify source page images.
