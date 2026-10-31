"""Regression tests based on wording found in the uploaded AGCL tender PDF.

The complete government tender is intentionally not bundled into this patch.
These small text fixtures exercise the exact formats that the extractor missed.
"""
from app.tender_requirements_extractor import extract_tender_requirements_draft


def test_agcl_tender_title_bid_security_turnover_and_delivery_are_candidates():
    pages = [
        {
            "page_number": 1,
            "text": (
                "TENDER DOCUMENT FOR SUPPLY OF Pressure Transmitter and Temperature Transmitter. "
                "INVITATION FOR e-BID UNDER SINGLE STAGE TWO BID SYSTEM. "
                "BID CLOSING DATE & TIME: As mentioned in online e-tender portal."
            ),
        },
        {
            "page_number": 2,
            "text": (
                "Tender Processing Fee Rs.1000/- (One Thousand only). "
                "Bid Security Amount* Rs.26000/- (Twenty Six Thousand) only deposited "
                "or Bank Guarantee of the same amount."
            ),
        },
        {
            "page_number": 32,
            "text": (
                "SCOPE OF WORK: Supply Pressure Transmitter, Qty:25 Nos and Temperature "
                "Transmitter, Qty:05 Nos. PRICE: FOR AGCL Stores, Duliajan, Assam basis. "
                "DELIVERY: materials are to be delivered at AGCL Stores, Duliajan, Assam."
            ),
        },
        {
            "page_number": 34,
            "text": (
                "Bidder must be a Manufacturer or Authorized Dealer having valid authorization "
                "letter with backup Warranty and ATEX Certificate. "
                "Successfully executed the order(s) of same or higher specifications "
                "in last 3 years reckoned from original bid closing date."
            ),
        },
        {
            "page_number": 37,
            "text": (
                "2.1 The minimum annual turnover achieved by the bidder as per their audited "
                "financial results in any one of the 3 immediate preceding financial year "
                "shall be above Rs. 21,00,000.00 (Twenty One Lakh) only."
            ),
        },
    ]

    draft = extract_tender_requirements_draft(pages)

    assert draft["tender_title"]["value"] == "Supply of Pressure Transmitter and Temperature Transmitter"
    assert draft["tender_title"]["page_number"] == 1
    assert draft["emd_required_inr"]["value"] == "26000"
    assert draft["emd_required_inr"]["page_number"] == 2
    assert draft["min_annual_turnover_inr"]["value"] == "2100000"
    assert draft["min_annual_turnover_inr"]["page_number"] == 37
    assert draft["target_region"]["value"] == "AGCL Stores, Duliajan, Assam"
    assert draft["target_region"]["page_number"] == 32
    assert "pressure transmitter supply" in draft["required_capabilities"]["value"]
    assert "temperature transmitter supply" in draft["required_capabilities"]["value"]
    assert draft["required_certifications"]["value"] == "ATEX Certificate"
    assert draft["required_certifications"]["status"].startswith("Candidate extracted")

    # The tender says to use the portal for the deadline; do not invent one from this PDF.
    assert draft["closing_date"]["value"] == ""
    assert "Portal lookup required" in draft["closing_date"]["status"]
    assert draft["closing_date"]["page_number"] == 1

    # The table has alternative single-/two-/three-PO quantity routes, not one scalar project count.
    assert draft["min_similar_projects"]["value"] == ""
    assert draft["min_years_experience"]["value"] == ""


def test_toc_warranty_is_not_misclassified_as_tender_capability():
    pages = [
        {
            "page_number": 5,
            "text": (
                "LIST OF ANNEXURES & APPENDICES APPLICABLE PAGE NO. "
                "APPENDIX C2 FORMAT OF AUTHORIZATION & BACKUP WARRANTY BY MANUFACTURERS "
                "APPENDIX C3 FORMAT FOR CERTIFICATE OF ANNUAL TURNOVER & NET WORTH "
                "ANNEXURE-B SCOPE OF WORK AND SPECIAL CONDITIONS OF CONTRACT"
            ),
        },
        {
            "page_number": 32,
            "text": "SCOPE OF WORK: Supply Pressure Transmitter, Qty:25 Nos and Temperature Transmitter, Qty:05 Nos.",
        },
    ]
    draft = extract_tender_requirements_draft(pages)
    assert "warranty" not in draft["required_capabilities"]["value"].lower()
    assert "pressure transmitter supply" in draft["required_capabilities"]["value"]


def test_portal_details_date_in_day_monthname_year_format_is_supported():
    pages = [{
        "page_number": 1,
        # PDF text extraction can join adjacent table cells as `AMBid`.
        "text": "Bid Submission Start Date 12-Oct-2026 09:00 AMBid Submission End Date 29-Oct-2026 02:30 PM. Bid Opening Date 30-Oct-2026 03:00 PM.",
    }]
    draft = extract_tender_requirements_draft(pages)
    assert draft["closing_date"]["value"] == "2026-10-29"
    assert draft["closing_date"]["page_number"] == 1


def test_portal_summary_table_title_stops_before_work_description():
    pages = [{
        "page_number": 1,
        "text": (
            "Work /Item(s) Title Supply of Pressure Transmitter and Temperature Transmitter "
            "Work Description Supply of Pressure Transmitter and Temperature Transmitter "
            "Pre Qualification Details Please refer Tender documents."
        ),
    }]
    draft = extract_tender_requirements_draft(pages)
    assert draft["tender_title"]["value"] == "Supply of Pressure Transmitter and Temperature Transmitter"