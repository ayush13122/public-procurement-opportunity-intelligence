#!/usr/bin/env python
r"""Offline end-to-end diagnostic for Tender Document Copilot.

Examples (PowerShell, from repository root):
    .\.venv\Scripts\python.exe tools\validate_tender_copilot.py "D:\\path\\tender.pdf"
    .\.venv\Scripts\python.exe tools\validate_tender_copilot.py tender.pdf --question "What is the EMD?"

This script does not call Gemini/OpenAI and does not upload the PDF anywhere.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.tender_copilot import extract_pdf_pages, chunk_document_pages  # noqa: E402
from app.tender_answer_engine import answer_common_tender_question  # noqa: E402
from app.tender_extraction_hybrid import merge_candidate_fields  # noqa: E402
from app.tender_requirements_extractor import extract_tender_requirements_draft  # noqa: E402
from app.tender_review_audit import build_tender_review_findings, enrich_tender_fields  # noqa: E402

DEFAULT_QUESTIONS = (
    "What is the EMD amount?",
    "What is the cost of bid documents?",
    "What is the minimum annual turnover requirement?",
    "What is the submission deadline?",
    "When will the bids be opened?",
    "How many days does the bid remain valid after the submission deadline?",
    "What is the minimum warranty period after completion?",
    "Which work serial numbers require a Joint Venture?",
    "What class of contractor is eligible?",
)


def _field_summary(fields: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    item = fields.get(key, {})
    return {
        "value": item.get("value", ""),
        "status": item.get("status", ""),
        "source_location": item.get("source_location", ""),
        "evidence": item.get("evidence", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline OCR, Q&A and Bid-Fit diagnostic for one tender PDF.")
    parser.add_argument("pdf", type=Path, help="Path to a tender PDF")
    parser.add_argument(
        "--question", action="append", default=[],
        help="Question to test (repeat this option to test multiple custom questions)",
    )
    parser.add_argument("--skip-ocr", action="store_true", help="Do not OCR pages without embedded text")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of formatted text")
    args = parser.parse_args()

    pdf_path = args.pdf.expanduser().resolve()
    if not pdf_path.is_file():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 2
    if pdf_path.suffix.casefold() != ".pdf":
        print("ERROR: The selected file does not have a .pdf extension.", file=sys.stderr)
        return 2

    try:
        pdf_bytes = pdf_path.read_bytes()
        pages = extract_pdf_pages(pdf_bytes, ocr_scanned_pages=not args.skip_ocr)
        chunks = chunk_document_pages(pages, source_name=pdf_path.name)
        local_fields = extract_tender_requirements_draft(pages)
        # The no-AI run deliberately passes local fields through the same safety
        # enrichment used after Gemini merge in Streamlit.
        fields = enrich_tender_fields(pages, local_fields)
        findings = build_tender_review_findings(pages)
        questions = args.question or list(DEFAULT_QUESTIONS)
        answers = []
        for question in questions:
            answer = answer_common_tender_question(question, pages)
            answers.append({
                "question": question,
                "mode": "local structured answer" if answer else "no direct local answer; use retrieved evidence review",
                "answer": answer.answer if answer else None,
                "page": answer.page_number if answer else None,
                "source_location": answer.source_location if answer else None,
                "evidence": answer.evidence if answer else None,
            })

        payload = {
            "file": str(pdf_path),
            "file_size_mb": round(len(pdf_bytes) / (1024 * 1024), 2),
            "pdf_pages": len(pages),
            "ocr_pages": sum(1 for page in pages if page.get("ocr_used")),
            "readable_pages": sum(1 for page in pages if str(page.get("text", "")).strip()),
            "searchable_chunks": len(chunks),
            "bidfit_fields": {
                key: _field_summary(fields, key)
                for key in (
                    "tender_title", "required_capabilities", "target_region",
                    "min_years_experience", "experience_lookback_years", "min_similar_projects",
                    "min_annual_turnover_inr", "required_certifications",
                    "emd_required_inr", "closing_date",
                )
            },
            "local_answers": answers,
            "review_flags": findings,
            "provider_calls": 0,
        }
    except Exception as exc:  # Keep diagnostics user-readable; no swallowed failures.
        print(f"ERROR: Diagnostic failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("=" * 78)
    print("TENDER COPILOT — OFFLINE VALIDATION")
    print("=" * 78)
    print(f"File: {payload['file']}")
    print(f"Size: {payload['file_size_mb']} MB | PDF pages: {payload['pdf_pages']} | OCR pages: {payload['ocr_pages']}")
    print(f"Readable pages: {payload['readable_pages']} | Searchable chunks: {payload['searchable_chunks']}")
    print("Provider/API calls: 0 (this diagnostic is local-only)")
    print("\nBID-FIT FIELD CHECK")
    for key, value in payload["bidfit_fields"].items():
        print(f"\n[{key}] {value['value'] or '(blank / non-scalar)'}")
        print(f"  Status: {value['status']}")
        print(f"  Source: {value['source_location'] or 'not assigned'}")
        if value["evidence"]:
            print(f"  Evidence: {value['evidence'][:420]}")
    print("\nLOCAL Q&A CHECK")
    for item in answers:
        print(f"\nQ: {item['question']}")
        print(f"Mode: {item['mode']}")
        print(f"A: {item['answer'] or 'No direct answer. Review retrieved passages in the Copilot UI.'}")
        if item["source_location"]:
            print(f"Source: {item['source_location']}")
    print("\nTENDER REVIEW FLAGS")
    if not findings:
        print("No pattern-based review flags were triggered.")
    for finding in findings:
        print(f"- [{finding.get('severity')}] {finding.get('title')}: {finding.get('details')}")
    print("\nReminder: candidates and OCR output must be checked against original pages and live portal/corrigenda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
