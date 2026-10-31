from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.tender_copilot import (  # noqa: E402
    DocumentChunk,
    build_retrieval_index,
    chunk_document_pages,
    retrieve_relevant_chunks,
)
from app.tender_evidence_presentation import local_evidence_summary  # noqa: E402


def test_ocr_decimal_is_not_split_into_a_fake_clause_number():
    # Faithful OCR-shaped text from page 4 of the uploaded Banbasa tender.
    pages = [{
        "page_number": 4,
        "location": "PDF page 4",
        "text": (
            "c. The bidder should have had average Annual Financial Turn Over (gross) "
            "of at Rs. 111.0 Cr. on construction works during the immediate last five "
            "financial years ending on 31st March 2025 (Scanned copy of Certificate "
            "from CA with Unique Document Identification Number (UDIN) to be uploaded). "
            "There is no need to upload entire voluminous balance sheet. "
            "d. The bidder should not have incurred any loss during the available last five years."
        ),
    }, {
        "page_number": 6,
        "location": "PDF page 6",
        "text": (
            "10. Certificate of Financial Turn over: At the time of submission of bid, "
            "bidder may upload affidavit/certificate from CA mentioning Financial Turn Over "
            "of last 5 years or for the period as specified in the bid document."
        ),
    }]
    chunks = chunk_document_pages(pages, source_name="Tendernotice_1 (3).pdf")
    turnover_chunks = [chunk for chunk in chunks if chunk.page_number == 4]
    assert any("111.0 Cr." in chunk.text for chunk in turnover_chunks)
    assert not any("111.\n0 Cr." in chunk.text for chunk in turnover_chunks)


def test_annual_turnover_question_returns_answer_not_only_certificate_evidence():
    # Use the same amount formatting seen in the scanned PDF's OCR output.
    chunks = [
        DocumentChunk(
            page_number=6,
            chunk_index=0,
            text=(
                "10. Certificate of Financial Turn over: At the time of submission of bid, "
                "bidder may upload affidavit/certificate from CA mentioning Financial Turn Over "
                "of last 5 years or for the period as specified in the bid document."
            ),
            source_name="Tendernotice_1 (3).pdf",
        ),
        DocumentChunk(
            page_number=4,
            chunk_index=0,
            text=(
                "c. The bidder should have had average Annual Financial Turn Over (gross) "
                "of at Rs. 111. 0 Cr. on construction works during the immediate last five "
                "financial years ending on 31st March 2025 (Scanned copy of Certificate "
                "from CA with Unique Document Identification Number (UDIN) to be uploaded)."
            ),
            source_name="Tendernotice_1 (3).pdf",
        ),
        DocumentChunk(
            page_number=4,
            chunk_index=1,
            text=(
                "e. The bidder should have a Banker's Certificate from a commercial Bank for "
                "Rs. 148.0 crore OR Net Worth certificate of minimum Rs. 37.0 Cr."
            ),
            source_name="Tendernotice_1 (3).pdf",
        ),
    ]
    vectorizer, matrix = build_retrieval_index(chunks)
    hits = retrieve_relevant_chunks("annual turnover?", chunks, vectorizer, matrix, top_k=5)
    assert hits[0].page_number == 4
    assert "average Annual Financial Turn Over" in hits[0].text
    answer = local_evidence_summary("annual turnover?", hits)
    assert "Turnover criterion: Rs. 111.0 Cr." in answer
    assert "PDF page 4" in answer
    assert "last five financial years ending on 31st March 2025" in answer
    assert "Rs. 148.0 crore" not in answer.split("Supporting evidence")[0]
    assert "Rs. 37.0 Cr." not in answer.split("Supporting evidence")[0]
