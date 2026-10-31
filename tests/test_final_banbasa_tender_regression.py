"""End-to-end regression coverage for the scanned Banbasa tender's OCR text.

These tests use OCR-style text fixtures; the actual uploaded 8-page scanned PDF is
also smoke-tested during patch preparation, but is not bundled into the repository.
"""
from app.tender_answer_engine import answer_common_tender_question
from app.tender_extraction_hybrid import merge_candidate_fields, with_local_fallback_status
from app.tender_requirements_extractor import extract_tender_requirements_draft
from app.tender_review_audit import enrich_tender_fields


BANBASA_OCR_PAGES = [
    {
        "page_number": 1,
        "location": "PDF page 1",
        "text": (
            '"INFORMATION & INSTRUCTIONS To BIDDERS" for E-Tendering The Director (Project), LPAI '
            "invites bids for Development of Land Port at Banbasa, District Champawat Uttarakhand. "
            "NIT No 17/EE/LPAI/NEW DELHI/2026-27 Name of Work Development of Integrated Check post "
            "at Banbasa, Uttarakhand on Indo-Nepal Border on EPC Basis-Mode | / (Engineering Procurement & Construction) "
            "Estimated cost put to bid Rs. 3,68,60,53,798/- Earnest Money Rs. 3,78,60,538/- "
            "Total Time Period 36 Months Period of Completion 06 Month planning and 30 Months execution. "
            "Last date & time of 14/11/2026 up to 15:00 Hrs. online submission of bid "
            "Time and date of opening 16/11/2026 at 15:00 Hrs. of eligibility bid."
        ),
    },
    {
        "page_number": 2,
        "location": "PDF page 2",
        "text": (
            "Bidders eligibility criteria for work experience during the last Seven years. "
            "Three similar completed works each costing not less than Rs. 148.00 Crores including GST. OR "
            "Two similar completed works each costing not less than Rs. 221.00 Crores including GST. OR "
            "One similar completed work costing not less than Rs. 295.00 Crores including GST. "
            "Works of Similar nature shall mean Construction for infrastructure including allied works."
        ),
    },
    {
        "page_number": 4,
        "location": "PDF page 4",
        "text": (
            "c. The bidder should have had average Annual Financial Turn Over (gross) of at Rs. 111.0 Cr. "
            "on construction works during the immediate last five financial years ending on 318tmarch 2025 "
            "(Scanned copy of Certificate from CA with Unique Document Identification Number (UDIN) to be uploaded). "
            "d. The bidder should not have incurred any loss in more than two years. "
            "e. The bidder should have a Banker's Certificate from a commercial Bank for Rs. 148.0 crore "
            "OR Net Worth certificate of minimum Rs. 37.0 Cr. "
            "f. Bidding capacity: A = Maximum turnover in construction works executed in any one year."
        ),
    },
    {
        "page_number": 6,
        "location": "PDF page 6",
        "text": (
            "10. Certificate of Financial Turn over: At the time of submission of bid, bidder may upload "
            "affidavit/certificate from CA mentioning Financial Turn Over of last 5 years. "
            "There is no need to upload entire voluminous balance sheet."
        ),
    },
]


def test_full_local_extractor_uses_labelled_work_title_not_later_tds_sentence():
    pages = BANBASA_OCR_PAGES + [{
        "page_number": 3,
        "location": "PDF page 3",
        "text": "certificate clearly specifying the name of work, total payment received against the work and TDS amount for the work.",
    }]
    fields = enrich_tender_fields(pages, extract_tender_requirements_draft(pages))
    assert fields["tender_title"]["value"].startswith("Development of Integrated Check post at Banbasa")
    assert "total payment received" not in fields["tender_title"]["value"].casefold()
    assert fields["tender_title"]["page_number"] == 1


def test_offline_bidfit_extracts_turnover_emd_deadline_and_work_region_together():
    fields = enrich_tender_fields(BANBASA_OCR_PAGES, extract_tender_requirements_draft(BANBASA_OCR_PAGES))
    assert fields["min_annual_turnover_inr"]["value"] == "1110000000"
    assert fields["min_annual_turnover_inr"]["page_number"] == 4
    assert "111.0 Cr" in fields["min_annual_turnover_inr"]["evidence"]
    assert fields["emd_required_inr"]["value"] == "37860538"
    assert fields["emd_required_inr"]["page_number"] == 1
    assert fields["closing_date"]["value"] == "2026-11-14"
    assert "15:00" in fields["closing_date"]["evidence"]
    assert fields["target_region"]["value"] == "Banbasa, Uttarakhand"
    assert "EPC / infrastructure construction" in fields["required_capabilities"]["value"]
    # The 3/2/1 completed-work options are alternatives, not a single project-count field.
    assert fields["min_similar_projects"]["value"] == ""
    assert "alternative similar-work routes" in fields["min_similar_projects"]["status"]
    assert fields["min_years_experience"]["value"] == ""
    assert fields["experience_lookback_years"]["value"] == "7"
    assert "not a minimum company age" in fields["experience_lookback_years"]["status"]


def test_annual_turnover_question_answers_without_gemini_from_full_ocr_pages():
    answer = answer_common_tender_question("Min Annual Turnover Inr", BANBASA_OCR_PAGES)
    assert answer is not None
    assert answer.page_number == 4
    assert "₹111.0 crore" in answer.answer
    assert "₹1,11,00,00,000 full INR" in answer.answer
    assert "31 March 2025" in answer.answer
    assert "Certificate of Financial Turn over" not in answer.evidence


def test_local_turnover_survives_blank_or_wrong_gemini_field():
    local = extract_tender_requirements_draft(BANBASA_OCR_PAGES)
    blank_ai = {key: {"value": "", "page_numbers": [], "evidence": "", "status": "Not found"} for key in local}
    merged = merge_candidate_fields(local, blank_ai)
    assert merged["min_annual_turnover_inr"]["value"] == "1110000000"
    assert merged["min_annual_turnover_inr"]["source"] == "rule_based"

    wrong_ai = {key: {"value": "", "page_numbers": [], "evidence": "", "status": "Not found"} for key in local}
    wrong_ai["min_annual_turnover_inr"] = {
        "value": "1480000000", "page_number": 4, "page_numbers": [4],
        "evidence": "The bidder should have a Banker's Certificate from a commercial Bank for Rs. 148.0 crore",
        "status": "AI candidate extracted — human verification required", "source": "gemini",
    }
    merged_wrong = merge_candidate_fields(local, wrong_ai)
    assert merged_wrong["min_annual_turnover_inr"]["value"] == "1110000000"
    assert merged_wrong["min_annual_turnover_inr"]["ai_candidate_value_for_review"] == "1480000000"


def test_failed_gemini_still_has_local_candidate_fields():
    local = extract_tender_requirements_draft(BANBASA_OCR_PAGES)
    fallback = with_local_fallback_status(local, reason="daily quota exhausted")
    assert fallback["min_annual_turnover_inr"]["value"] == "1110000000"
    assert "daily quota exhausted" in fallback["min_annual_turnover_inr"]["status"]


def test_emd_ocr_rupee_glyph_k_is_parsed_only_after_emd_label_and_amount_words():
    pages = [{
        "page_number": 1,
        "location": "PDF page 1",
        "text": (
            "Earnest Money k3,78,60,538/- "
            "(Rupees Three Crore Seventy-Eight Lakh Sixty Thousand Five Hundred Thirty-Eight only)."
        ),
    }]
    fields = extract_tender_requirements_draft(pages)
    assert fields["emd_required_inr"]["value"] == "37860538"
    assert fields["emd_required_inr"]["page_number"] == 1
    assert "OCR-tolerant" in fields["emd_required_inr"]["status"]

    answer = answer_common_tender_question("What is the EMD amount?", pages)
    assert answer is not None
    assert "₹3,78,60,538" in answer.answer
    assert answer.value_inr == "37860538"
    assert answer.page_number == 1


def test_lookback_window_is_not_misreported_as_minimum_company_age():
    pages = [{
        "page_number": 2,
        "location": "PDF page 2",
        "text": (
            "Bidders eligibility criteria for work experience during the last Seven years. "
            "Three similar completed works each costing not less than Rs. 148.00 Crores including GST."
        ),
    }]
    fields = extract_tender_requirements_draft(pages)
    assert fields["min_years_experience"]["value"] == ""
    assert fields["experience_lookback_years"]["value"] == "7"
    assert "not a minimum company age" in fields["experience_lookback_years"]["status"]
    assert fields["experience_lookback_years"]["page_number"] == 2


def test_conflicting_experience_lookback_periods_are_not_collapsed_to_one_value():
    pages = [
        {"page_number": 34, "text": "EXPERIENCE: Bidder must have completed similar supply orders in last 3 years reckoned from original bid closing date."},
        {"page_number": 36, "text": "The experience section says prescribed period of 05 years. Bidder must submit breakup of similar work/supply executed within the prescribed period of 03 years reckoned from the original bid closing date."},
    ]
    fields = extract_tender_requirements_draft(pages)
    assert fields["experience_lookback_years"]["value"] == ""
    assert "3 years / 5 years" in fields["experience_lookback_years"]["status"]
    assert fields["experience_lookback_years"]["page_numbers"] == [34, 36]


def test_experience_lookback_is_display_only_and_not_transferred_to_bidfit():
    from app.tender_requirements_extractor import build_bidfit_prefill_payload

    fields = extract_tender_requirements_draft(BANBASA_OCR_PAGES)
    reviewed = {name: info["value"] for name, info in fields.items()}
    payload = build_bidfit_prefill_payload(
        reviewed, source_filename="banbasa.pdf", field_details=fields
    )
    assert "experience_lookback_years" not in payload["values"]
    assert payload["values"]["min_years_experience"] == ""
