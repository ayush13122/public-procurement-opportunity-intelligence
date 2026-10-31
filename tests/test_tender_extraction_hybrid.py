from app.tender_extraction_hybrid import merge_candidate_fields, with_local_fallback_status
from app.tender_requirements_extractor import extract_tender_requirements_draft


def _ocr_pages():
    return [{
        "page_number": 4,
        "location": "PDF page 4",
        "text": (
            "c. The bidder should have had average Annual Financial Turn Over (gross) "
            "of at Rs. 111.0 Cr. on construction works during the immediate last five "
            "financial years ending on 31st March 2025."
        ),
    }]


def test_empty_gemini_turnover_field_is_filled_from_local_evidence():
    local = extract_tender_requirements_draft(_ocr_pages())
    ai = {"min_annual_turnover_inr": {"value": "", "page_number": None, "page_numbers": [], "evidence": "", "status": "Not found"}}
    merged = merge_candidate_fields(local, ai)
    field = merged["min_annual_turnover_inr"]
    assert field["value"] == "1110000000"
    assert field["page_number"] == 4
    assert "Turn Over" in field["evidence"]
    assert field["source"] == "rule_based"


def test_direct_local_turnover_beats_conflicting_unverified_ai_number():
    local = extract_tender_requirements_draft(_ocr_pages())
    ai = {"min_annual_turnover_inr": {
        "value": "1480000000", "page_number": 4, "page_numbers": [4],
        "evidence": "average Annual Financial Turn Over (gross) of at Rs. 111.0 Cr.",
        "status": "AI candidate", "source": "gemini",
    }}
    merged = merge_candidate_fields(local, ai)
    field = merged["min_annual_turnover_inr"]
    assert field["value"] == "1110000000"
    assert field["ai_candidate_value_for_review"] == "1480000000"
    assert "Gemini differed" in field["status"]


def test_gemini_failure_keeps_local_field_and_truthfully_leaves_missing_fields_blank():
    local = extract_tender_requirements_draft(_ocr_pages())
    local["emd_required_inr"] = {"value": "", "page_number": None, "page_numbers": [], "evidence": "", "status": "Not found"}
    fallback = with_local_fallback_status(local, reason="quota exhausted")
    assert fallback["min_annual_turnover_inr"]["value"] == "1110000000"
    assert "quota exhausted" in fallback["min_annual_turnover_inr"]["status"]
    assert fallback["emd_required_inr"]["value"] == ""
