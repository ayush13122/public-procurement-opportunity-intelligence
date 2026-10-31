from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.tender_copilot import (  # noqa: E402
    DocumentChunk,
    LLMNotConfiguredError,
    PDFProcessingError,
    answer_with_llm,
    build_llm_input,
    build_retrieval_index,
    chunk_pdf_pages,
    answer_with_gemini,
    extract_pdf_pages,
    file_sha256,
    get_configured_provider,
    retrieve_relevant_chunks,
)


def test_file_sha256_is_stable_and_changes_for_different_content():
    assert file_sha256(b"abc") == file_sha256(b"abc")
    assert file_sha256(b"abc") != file_sha256(b"abcd")


def test_extract_pdf_pages_rejects_empty_bytes():
    with pytest.raises(PDFProcessingError, match="empty"):
        extract_pdf_pages(b"")


def test_extract_pdf_pages_rejects_non_pdf_bytes():
    with pytest.raises(PDFProcessingError, match="could not be read as a PDF"):
        extract_pdf_pages(b"not really a pdf")


def test_chunk_pdf_pages_preserves_page_and_source_metadata():
    text = "eligibility turnover experience tender requirement " * 25
    chunks = chunk_pdf_pages(
        [{"page_number": 7, "text": text}],
        source_name="notice.pdf",
        chunk_size=220,
        overlap=30,
    )
    assert len(chunks) > 1
    assert all(chunk.page_number == 7 for chunk in chunks)
    assert all(chunk.source_name == "notice.pdf" for chunk in chunks)
    assert chunks[0].chunk_index == 0


def test_chunk_pdf_pages_skips_empty_page_text():
    chunks = chunk_pdf_pages([
        {"page_number": 1, "text": "  "},
        {"page_number": 2, "text": "minimum turnover requirement is fifty lakh rupees"},
    ])
    assert len(chunks) == 1
    assert chunks[0].page_number == 2


def test_chunk_pdf_pages_rejects_invalid_overlap():
    with pytest.raises(ValueError, match="overlap"):
        chunk_pdf_pages([{"page_number": 1, "text": "some text"}], chunk_size=200, overlap=200)


def make_chunks():
    return [
        DocumentChunk(1, 0, "The earnest money deposit EMD is INR 50000 and must be submitted with the bid.", "notice.pdf"),
        DocumentChunk(3, 0, "The bidder must demonstrate three completed similar works during the last five years.", "notice.pdf"),
        DocumentChunk(5, 0, "The bid submission deadline is 30 November 2026 at 3 PM.", "notice.pdf"),
    ]


def test_retrieval_returns_emd_passage_with_correct_page():
    chunks = make_chunks()
    vectorizer, matrix = build_retrieval_index(chunks)
    results = retrieve_relevant_chunks("What is the EMD amount?", chunks, vectorizer, matrix)
    assert results
    assert results[0].page_number == 1
    assert "50000" in results[0].text


def test_retrieval_returns_no_evidence_for_unrelated_question():
    chunks = make_chunks()
    vectorizer, matrix = build_retrieval_index(chunks)
    results = retrieve_relevant_chunks(
        "Who won the cricket tournament?", chunks, vectorizer, matrix
    )
    assert results == []


def test_build_llm_input_includes_page_citation_and_question():
    hit = make_chunks()[0]
    prompt = build_llm_input(
        "What is the EMD?",
        [type("Hit", (), {"page_number": hit.page_number, "text": hit.text})()],
    )
    assert "What is the EMD?" in prompt
    assert "PDF page 1" in prompt
    assert "50000" in prompt
    assert "untrusted reference text" in prompt


def test_answer_with_llm_requires_api_key():
    with pytest.raises(LLMNotConfiguredError, match="OPENAI_API_KEY"):
        answer_with_llm("What is EMD?", make_chunks()[:1], api_key="")


def test_answer_with_llm_without_evidence_does_not_call_provider():
    answer = answer_with_llm("What is EMD?", [], api_key="not-empty")
    assert "could not find enough relevant evidence" in answer


def test_gemini_key_is_recognized_as_q_and_a_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    assert get_configured_provider() == "gemini"


def test_gemini_is_preferred_when_both_provider_keys_are_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    assert get_configured_provider() == "gemini"


def test_gemini_q_and_a_uses_retrieved_evidence_and_returns_text(monkeypatch):
    monkeypatch.setenv("GEMINI_TENDER_MAX_RETRIES", "0")
    class FakeResponse:
        text = "The exact deadline is not stated in this excerpt. The notice refers bidders to the online portal [PDF page 1]."
    class FakeModels:
        def __init__(self):
            self.kwargs = None
        def generate_content(self, **kwargs):
            self.kwargs = kwargs
            return FakeResponse()
    class FakeClient:
        def __init__(self):
            self.models = FakeModels()
    client = FakeClient()
    answer = answer_with_gemini(
        "submission deadline?", make_chunks()[:1], api_key="fake-key", model="test-model", client=client
    )
    assert "deadline is not stated" in answer
    assert client.models.kwargs["model"] == "test-model"
    assert "User question" in client.models.kwargs["contents"]
    assert "50000" in client.models.kwargs["contents"]


def test_extract_synthetic_demo_pdf_returns_page_text_and_page_numbers():
    demo_pdf = PROJECT_ROOT / "assets" / "demo_synthetic_tender_notice.pdf"
    pages = extract_pdf_pages(demo_pdf.read_bytes())
    assert len(pages) == 3
    assert [page["page_number"] for page in pages] == [1, 2, 3]
    extracted = " ".join(page["text"] for page in pages)
    assert "EMD" in extracted
    assert "INR 10,000" in extracted
    assert "SYNTHETIC DEMO" in extracted
