from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PdfWriter

from app.tender_copilot import PDFProcessingError, _normalize_ocr_currency_tokens, extract_pdf_pages


def make_one_page_pdf(text: str | None = None) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_ocr_normalizes_common_rupee_symbol_misread_before_amount():
    assert _normalize_ocr_currency_tokens("Earnest Money %50,000/-") == "Earnest Money Rs. 50,000/-"
    assert _normalize_ocr_currency_tokens("7% per annum") == "7% per annum"


def test_ocr_normalizes_less_than_symbol_misread_as_rupee_after_earnest_money_label():
    assert _normalize_ocr_currency_tokens("Earnest Money <3,78,60,538/-") == "Earnest Money Rs. 3,78,60,538/-"
    assert _normalize_ocr_currency_tokens("The result must be < 10 for this test") == "The result must be < 10 for this test"


def test_pdf_extraction_keeps_embedded_text_mode_when_ocr_disabled():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # A simple blank PDF exercises the no-OCR path by overriding OCR explicitly.
    out = io.BytesIO()
    writer.write(out)
    pages = extract_pdf_pages(out.getvalue(), ocr_scanned_pages=False)
    assert pages[0]["page_number"] == 1
    assert pages[0]["text_extraction_method"] == "embedded"


def test_image_only_pdf_raises_actionable_error_when_optional_pymupdf_missing(monkeypatch):
    pdf_bytes = make_one_page_pdf()
    import builtins
    real_import = builtins.__import__

    def selective_import(name, *args, **kwargs):
        if name == "pymupdf":
            raise ImportError("mocked missing PyMuPDF")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", selective_import)
    with pytest.raises(PDFProcessingError, match="install OCR support"):
        extract_pdf_pages(pdf_bytes, ocr_scanned_pages=True)


def test_ocr_fallback_extracts_a_scanned_page_and_marks_method(monkeypatch):
    pdf_bytes = make_one_page_pdf()

    class FakeOCRPage:
        def get_textpage_ocr(self, **kwargs):
            assert kwargs["language"] == "eng"
            assert kwargs["dpi"] == 220
            return "fake-textpage"
        def get_text(self, kind, textpage=None):
            assert textpage == "fake-textpage"
            return "Earnest Money Deposit EMD %50,000"

    class FakeOCRDoc:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def load_page(self, index):
            assert index == 0
            return FakeOCRPage()

    class FakePyMuPDF:
        @staticmethod
        def open(**kwargs):
            assert kwargs["stream"] == pdf_bytes
            assert kwargs["filetype"] == "pdf"
            return FakeOCRDoc()

    import sys
    monkeypatch.setitem(sys.modules, "pymupdf", FakePyMuPDF)
    pages = extract_pdf_pages(pdf_bytes)
    assert "EMD" in pages[0]["text"]
    assert pages[0]["ocr_used"] is True
    assert pages[0]["text_extraction_method"] == "ocr"
    assert pages[0]["page_number"] == 1


def test_ocr_can_be_disabled_for_privacy_or_speed():
    pdf_bytes = make_one_page_pdf()
    pages = extract_pdf_pages(pdf_bytes, ocr_scanned_pages=False)
    assert pages[0]["ocr_used"] is False


def test_zero_minimum_embedded_threshold_skips_ocr(monkeypatch):
    # A zero threshold yields no low-text OCR candidates, so the OCR dependency
    # must not be imported even when the PDF page itself is blank.
    pdf_bytes = make_one_page_pdf()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    # Blank test pages are not candidates when the threshold is zero.
    pages = extract_pdf_pages(out.getvalue(), ocr_min_embedded_chars=0)
    assert pages[0]["ocr_used"] is False
