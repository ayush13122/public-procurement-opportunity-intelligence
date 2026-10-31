from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.tender_copilot import build_retrieval_index, chunk_document_pages, retrieve_relevant_chunks
from app.tender_evidence_presentation import local_evidence_summary, matched_query_terms
from app.tender_question_intents import expand_tender_question, question_intents


def _search(question: str, pages: list[dict], top_k: int = 5):
    chunks = chunk_document_pages(pages, source_name="other-state-tender.pdf", chunk_size=500, overlap=60)
    vectorizer, matrix = build_retrieval_index(chunks)
    hits = retrieve_relevant_chunks(question, chunks, vectorizer, matrix, top_k=top_k)
    return chunks, hits


def test_other_state_wording_finds_bid_security_amount_without_state_specific_terms():
    pages = [{
        "page_number": 1,
        "text": "Tender Document Cost: Rs. 1,500/-. Bid Security (EMD): Rs. 1,25,000/- shall be submitted online with the technical bid."
    }]
    _chunks, hits = _search("How much is the EMD?", pages)
    answer = local_evidence_summary("How much is the EMD?", hits)
    assert hits and hits[0].page_number == 1
    assert "Rs. 1,25,000/-" in answer
    assert "1,500" not in answer.split("Relevant wording:")[0]
    assert "PDF page 1" in answer


def test_another_portal_label_for_closing_date_returns_the_actual_date_when_stated():
    pages = [{
        "page_number": 2,
        "text": "Last Date and Time for Submission of Bids: 14-11-2026 15:00 hours. Technical bids open on 16-11-2026."
    }]
    _chunks, hits = _search("When do I have to submit the bid?", pages)
    answer = local_evidence_summary("When do I have to submit the bid?", hits)
    assert hits
    assert "14-11-2026" in answer
    assert "15:00" in answer


def test_portal_delegated_deadline_is_not_guessed_from_issue_date():
    pages = [{
        "page_number": 1,
        "text": "Notice issued 08-10-2026. Bid Submission End Date & Time: As available on the online procurement portal."
    }]
    _chunks, hits = _search("submission deadline?", pages)
    answer = local_evidence_summary("submission deadline?", hits)
    assert "not stated" in answer.casefold()
    assert "portal" in answer.casefold()
    assert "08-10-2026" not in answer.split("Supporting evidence")[0]


def test_tender_fee_is_not_confused_with_bid_security():
    pages = [{
        "page_number": 1,
        "text": "Fee for Tender Document: INR 2,000 non-refundable. Earnest Money Deposit: INR 80,000."
    }]
    _chunks, fee_hits = _search("What is the tender document fee?", pages)
    _chunks, emd_hits = _search("earnest money deposit amount", pages)
    fee_answer = local_evidence_summary("What is the tender document fee?", fee_hits)
    emd_answer = local_evidence_summary("earnest money deposit amount", emd_hits)
    assert "INR 2,000" in fee_answer
    assert "INR 80,000" not in fee_answer.split("Relevant wording:")[0]
    assert "INR 80,000" in emd_answer


def test_generic_expansion_is_state_agnostic_and_contains_no_state_name_assumption():
    expanded = expand_tender_question("minimum average annual turnover")
    assert "audited financial statements" in expanded
    assert "preceding financial years" in expanded
    assert "assam" not in expanded.casefold()
    assert "turnover" in question_intents("minimum average annual turnover")


def test_hinglish_question_variants_recognize_deadline_intent():
    assert "deadline" in question_intents("bid submit karne ki last date kab tak hai?")
    expanded = expand_tender_question("bid submit karne ki last date kab tak hai?")
    assert "bid closing date" in expanded


def test_retrieval_supports_location_delivery_and_required_document_questions():
    pages = [
        {"page_number": 3, "text": "Delivery shall be made at the district hospital store within 45 days from issue of the purchase order."},
        {"page_number": 4, "text": "Bidders must submit GST registration, PAN, signed declaration, and proof of similar completed supply."},
    ]
    _chunks, delivery_hits = _search("What is the delivery period and location?", pages)
    _chunks, document_hits = _search("Which documents are required to submit?", pages)
    assert delivery_hits and delivery_hits[0].page_number == 3
    assert document_hits and document_hits[0].page_number == 4
    assert any("GST registration" in hit.text for hit in document_hits)


def test_highlight_match_terms_work_for_portal_neutral_synonyms():
    terms = matched_query_terms("last date for submission?", "Bid Submission End Date: 14-11-2026")
    assert any("submission" in term.casefold() or "closing date" in term.casefold() for term in terms)
