from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.tender_copilot import DocumentChunk, build_retrieval_index, retrieve_relevant_chunks  # noqa: E402
from app.tender_evidence_presentation import local_evidence_summary  # noqa: E402
from app.tender_question_intents import expand_tender_question, question_intents  # noqa: E402


def _chunks():
    # OCR-style wording extracted from the uploaded Banbasa tender's page 4.
    return [
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
            chunk_index=1,
            text=(
                "c. The bidder should have had average Annual Financial Turn Over (gross) "
                "at Rs. 111.0 Cr. on construction works during the immediate last five "
                "financial years ending on 31st March 2025 (Scanned copy of Certificate "
                "from CA with UDIN to be uploaded). There is no need to upload entire "
                "voluminous balance sheet."
            ),
            source_name="Tendernotice_1 (3).pdf",
        ),
        DocumentChunk(
            page_number=1,
            chunk_index=2,
            text=(
                "Estimated cost put to bid Rs. 3,68,60,53,798/- and Earnest Money Rs. 3,78,60,538/-. "
                "Last date and time of online submission of bid 14/11/2026 up to 15:00 Hrs."
            ),
            source_name="Tendernotice_1 (3).pdf",
        ),
    ]


def test_turn_over_spelling_is_recognized_as_turnover_intent():
    assert "turnover" in question_intents("turn over?")
    expanded = expand_tender_question("turn over?").casefold()
    assert "average annual financial turn over" in expanded
    assert "preceding financial years" in expanded


def test_turnover_amount_with_crore_suffix_is_not_truncated():
    chunks = _chunks()
    vectorizer, matrix = build_retrieval_index(chunks)
    hits = retrieve_relevant_chunks("turn over?", chunks, vectorizer, matrix, top_k=5)
    assert hits
    assert hits[0].page_number == 4
    answer = local_evidence_summary("turn over?", hits)
    assert "Rs. 111.0 Cr." in answer
    assert "PDF page 4" in answer
    assert "Certificate of Financial Turn over" not in answer.split("Supporting evidence")[0]


def test_turnover_query_finds_annual_financial_turn_over_label_even_with_ocr_spacing():
    chunks = _chunks()
    vectorizer, matrix = build_retrieval_index(chunks)
    hits = retrieve_relevant_chunks("minimum annual financial turnover", chunks, vectorizer, matrix, top_k=5)
    assert hits
    assert hits[0].page_number == 4
    answer = local_evidence_summary("minimum annual financial turnover", hits)
    assert "111.0 Cr." in answer
    assert "31st March 2025" in answer


def test_turnover_result_does_not_confuse_emd_or_project_cost_with_turnover():
    chunks = _chunks()
    vectorizer, matrix = build_retrieval_index(chunks)
    hits = retrieve_relevant_chunks("turnover requirement", chunks, vectorizer, matrix, top_k=5)
    answer = local_evidence_summary("turnover requirement", hits)
    assert "111.0 Cr." in answer
    assert "3,78,60,538" not in answer.split("Relevant wording:")[0]
    assert "3,68,60,53,798" not in answer.split("Relevant wording:")[0]
