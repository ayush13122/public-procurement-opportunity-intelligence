from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.tender_evidence_presentation import (  # noqa: E402
    highlight_evidence_html,
    local_evidence_summary,
    matched_query_terms,
    structure_evidence_text,
)
from app.tender_copilot import (  # noqa: E402
    DocumentChunk,
    build_retrieval_index,
    chunk_document_pages,
    retrieve_relevant_chunks,
)


def test_question_aliases_retrieve_deadline_clause_from_procurement_wording():
    pages = [
        {"page_number": 1, "text": "BID CLOSING DATE & TIME: As mentioned in online e-tender portal."},
        {"page_number": 19, "text": "12.0 DEADLINE FOR SUBMISSION OF BIDS: No bid can be submitted after the submission dead line is reached. The system time displayed on e-procurement web page shall decide the submission dead line."},
        {"page_number": 34, "text": "The bidder must submit a valid certificate with the offer."},
    ]
    chunks = chunk_document_pages(pages, chunk_size=360, overlap=30)
    vectorizer, matrix = build_retrieval_index(chunks)
    hits = retrieve_relevant_chunks("submission deadline?", chunks, vectorizer, matrix, top_k=5)
    assert hits
    assert any(hit.page_number in {1, 19} for hit in hits[:2])
    assert any("submission" in hit.text.casefold() for hit in hits[:3])


def test_chunking_breaks_long_flattened_clauses_into_shorter_evidence_units():
    text = "1.0 ELIGIBILITY: Original equipment manufacturer required. 2.0 EMD: Bid security is INR 26,000. 3.0 DEADLINE: As mentioned on the portal."
    chunks = chunk_document_pages([{"page_number": 3, "text": text}], chunk_size=100, overlap=10)
    assert len(chunks) >= 2
    assert all(len(chunk.text) <= 100 for chunk in chunks)
    assert all(chunk.page_number == 3 for chunk in chunks)


def test_highlight_terms_are_safe_and_highlight_aliases():
    html_text = highlight_evidence_html("Bid Closing Date: As mentioned in the online portal. <script>alert(1)</script>", "submission deadline?")
    assert "<mark class=\"tender-hit\">Closing Date</mark>" in html_text or "<mark class=\"tender-hit\">Bid Closing Date</mark>" in html_text
    assert "&lt;script&gt;" in html_text
    assert "<script>" not in html_text


def test_structured_evidence_splits_table_cells_and_sentences():
    lines = structure_evidence_text("Item: Pressure Transmitter | Quantity: 25 | 1 purchase order: 20. Two similar orders each: 12.")
    assert len(lines) >= 3
    assert any("Quantity: 25" in line for line in lines)


def test_local_answer_is_explicitly_labelled_not_ai_generated():
    hit = DocumentChunk(1, 0, "Bid closing date: As mentioned in e-tender portal.", "notice.pdf")
    summary = local_evidence_summary("submission deadline?", [hit])
    assert "not an AI-generated conclusion" in summary
    assert "PDF page 1" in summary


def test_numeric_emd_question_prefers_the_clause_with_amount_not_general_process_text():
    pages = [
        {"page_number": 2, "text": "Bid Security Amount* Rs.26000/- (Twenty Six Thousand) only."},
        {"page_number": 16, "text": "EMD should be paid online through the Assam e-tendering website."},
    ]
    chunks = chunk_document_pages(pages, chunk_size=300, overlap=20)
    vectorizer, matrix = build_retrieval_index(chunks)
    hits = retrieve_relevant_chunks("EMD amount?", chunks, vectorizer, matrix, top_k=2)
    assert hits
    assert hits[0].page_number == 2
    assert "26000" in hits[0].text
