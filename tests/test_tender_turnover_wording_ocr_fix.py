"""Regression test for the real OCR wording used in the Banbasa tender."""
from app.tender_requirements_extractor import extract_tender_requirements_draft


def test_ocr_spaced_turn_over_extracts_111_crore_annual_turnover_on_page_4():
    # This mirrors Tesseract's text from page 4, including the unusual
    # "Turn Over" spelling and the "Rs. 111.0 Cr." amount format.
    pages = [
        {
            "page_number": 1,
            "text": (
                "Development of Integrated Check post at Banbasa Uttarakhand. "
                "Earnest Money Rs. 3,78,60,538/- Last date and time of online submission "
                "of bid 14/11/2026 up to 15:00 Hrs."
            ),
        },
        {
            "page_number": 4,
            "text": (
                "c. The bidder should have had average Annual Financial Turn Over (gross) "
                "of at Rs. 111.0 Cr. on construction works during the immediate last five "
                "financial years ending on 31st March 2025 (Scanned copy of Certificate "
                "from CA with Unique Document Identification Number (UDIN) to be uploaded). "
                "There is no need to upload entire voluminous balance sheet. "
                "d. The bidder should not have incurred any loss. "
                "e. The bidder should have a Banker's Certificate from a commercial Bank "
                "for Rs. 148.0 crore or Net Worth certificate of minimum Rs. 37.0 Cr."
            ),
        },
        {
            "page_number": 6,
            "text": (
                "10. Certificate of Financial Turn over: At the time of submission of bid, "
                "bidder may upload affidavit/certificate from CA mentioning Financial Turn "
                "Over of last 5 years. There is no need to upload entire voluminous balance sheet."
            ),
        },
    ]

    draft = extract_tender_requirements_draft(pages)
    turnover = draft["min_annual_turnover_inr"]
    assert turnover["value"] == "1110000000"  # full INR, not 111 crore text
    assert turnover["page_number"] == 4
    assert "111.0 Cr" in turnover["evidence"]
    assert "last five financial years" in turnover["evidence"]


def test_turnover_parser_keeps_existing_compact_turnover_wording_compatibility():
    pages = [{
        "page_number": 7,
        "text": (
            "The minimum annual turnover achieved by the bidder shall be above "
            "Rs. 21,00,000.00 in any one of the preceding financial years."
        ),
    }]
    draft = extract_tender_requirements_draft(pages)
    assert draft["min_annual_turnover_inr"]["value"] == "2100000"
    assert draft["min_annual_turnover_inr"]["page_number"] == 7
