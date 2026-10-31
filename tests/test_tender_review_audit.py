from app.tender_requirements_extractor import extract_tender_requirements_draft
from app.tender_review_audit import build_tender_review_findings, enrich_tender_fields


def _agcl_fixture_pages():
    return [
        {"page_number": 1, "text": "TENDER DOCUMENT FOR SUPPLY OF Pressure Transmitter and Temperature Transmitter. BID CLOSING DATE & TIME: As mentioned in online e-tender portal. TENDER/IFB NO.: C&P/INST/13/2026-27 dtd:09/08/2026"},
        {"page_number": 2, "text": "Ref No: C&P/INST/13/2026-27/02 dtd: 09/10/2026. Tender No C&P/INST/13/2026-27 dtd: 09/10/2026. Bid Security Amount Rs.26000/-"},
        {"page_number": 32, "text": "SCOPE OF WORK: Supply Pressure Transmitter, Qty:25 Nos and Temperature Transmitter, Qty:05 Nos. PRICE: The Price quoted should be FOR AGCL Stores, Duliajan, Assam basis. DELIVERY: The ordered materials are to be delivered within Two months from the receipt of PO by email. Documents to be submitted along with dispatch of materials: Authorization Certificate from the manufacturer/OEM; Catalogue and literature; Guaranty/Warranty Certificate; ATEX Certificate; Calibration Certificate."},
        {"page_number": 33, "text": "GUARANTY/WARRANTY: The warranty shall remain valid for twelve (12) months after the Goods have been put into operation or for eighteen (18) Months after the date of delivery, whichever occurs earlier."},
        {"page_number": 34, "text": "ANNEXURE-C BID EVALUATION CRITERIA. 1.1 EXPERIENCE: Bidder must be a Manufacturer of tendered items or Authorized Dealer/Channel Partner/Distributor/Agent. Bidder must have successfully executed the order(s) of same or higher specifications having minimum value/quantities as indicated in the table in last 3 years reckoned from original bid closing date. Description of Items Unit Required Quantity Single P.O Quantity Two similar Completed P.O each Order Quantity Three similar Completed P.O each Order Quantity Pressure Transmitter Range 0-25 bar No 25 20 12 10 Temperature Transmitter Range: 30PSI NO 5 4 2 1. Valid Authorization Letter with backup Warranty and ATEX Certificate."},
        {"page_number": 35, "text": "The OEM and bidder shall fulfil experience criteria. Successfully completed orders are required; LOI/LOA alone are not acceptable."},
        {"page_number": 36, "text": "The experience section says prescribed period of 05 years. Bidder must submit breakup of similar work/supply executed within the prescribed period of 03 years reckoned from the original bid closing date."},
        {"page_number": 37, "text": "The minimum annual turnover achieved by the bidder as per their audited financial results in any one of the 3 immediate preceding financial year shall be above Rs. 21,00,000.00. Net worth of the bidder must be Positive for the preceding financial/accounting year."},
        {"page_number": 55, "text": "DATASHEET FOR PRESSURE TRANSMITTER. ATEX/IECEx Certification Required. PESO/CCOE approval Required. Calibration Report Required. Warranty 18 years from date of receipt and acceptance of material or 12 months from the date of commissioning, whichever is earlier."},
        {"page_number": 56, "text": "DATASHEET FOR TEMPERATURE TRANSMITTER. Measurement range -10 to 100 Degree C. ATEX/IECEx Certification Required. PESO/CCOE approval Required. Calibration Report Required. Warranty 18 years from date of receipt and acceptance of material or 12 months from the date of commissioning, whichever is earlier."},
    ]


def test_portal_deadline_is_classified_as_not_stated_not_generic_not_found():
    pages = _agcl_fixture_pages()
    fields = enrich_tender_fields(pages, extract_tender_requirements_draft(pages))
    assert fields["closing_date"]["value"] == ""
    assert fields["closing_date"]["status"] == "Not stated in supplied document — portal lookup required"
    assert fields["closing_date"]["page_number"] == 1


def test_certifications_are_supplemented_from_multiple_source_pages():
    pages = _agcl_fixture_pages()
    fields = enrich_tender_fields(pages, extract_tender_requirements_draft(pages))
    value = fields["required_certifications"]["value"].lower()
    assert "atex/iecex certification" in value
    assert "peso/ccoe approval" in value
    assert "calibration report" in value
    assert 34 in fields["required_certifications"]["page_numbers"]
    assert 55 in fields["required_certifications"]["page_numbers"]
    assert 56 in fields["required_certifications"]["page_numbers"]
    assert "source-backed candidates" in fields["required_certifications"]["status"].lower()


def test_complex_experience_routes_do_not_become_a_scalar_project_count():
    pages = _agcl_fixture_pages()
    fields = enrich_tender_fields(pages, extract_tender_requirements_draft(pages))
    findings = build_tender_review_findings(pages)
    experience = next(x for x in findings if "alternative PO/quantity routes" in x["title"])
    assert fields["min_similar_projects"]["value"] == ""
    assert fields["min_years_experience"]["value"] == ""
    assert "20 units" in experience["details"]
    assert "12 units each" in experience["details"]
    assert "10 each" in experience["details"]
    assert "4 units" in experience["details"]
    assert "last 3 years" in experience["details"]
    titles = [x["title"] for x in findings]
    assert "Experience lookback period contains 05-year and 03-year wording" in titles


def test_net_worth_and_delivery_period_are_flagged_as_additional_requirements():
    findings = build_tender_review_findings(_agcl_fixture_pages())
    titles = [x["title"] for x in findings]
    assert "Positive net worth is a separate eligibility criterion" in titles
    assert "Delivery lead time should be reviewed against supplier capacity" in titles


def test_warranty_years_vs_months_is_flagged_without_silently_correcting_it():
    findings = build_tender_review_findings(_agcl_fixture_pages())
    warranty = next(x for x in findings if "warranty wording inconsistency" in x["title"].lower())
    assert "eighteen (18) months" in warranty["details"].lower()
    assert "18 years" in warranty["details"].lower()
    assert "official corrigendum" in warranty["recommended_action"].lower()
    assert "Page 33:" in warranty["evidence"]
    assert "Page 55:" in warranty["evidence"]
    assert "Page 56:" in warranty["evidence"]


def test_temperature_range_and_reference_date_inconsistencies_are_flagged():
    findings = build_tender_review_findings(_agcl_fixture_pages())
    titles = [x["title"] for x in findings]
    assert "Temperature transmitter range wording needs technical confirmation" in titles
    assert "Tender reference dates differ across opening pages" in titles


def test_enrichment_is_model_agnostic_for_gemini_candidate_output():
    pages = _agcl_fixture_pages()
    # Mirrors the shape returned by the Gemini adapter, without making a network call.
    fields = {
        "required_certifications": {
            "value": "ATEX Certificate",
            "page_number": 34,
            "page_numbers": [34],
            "evidence": "valid authorization letter with backup Warranty and ATEX Certificate",
            "status": "AI candidate extracted — human verification required",
            "source": "gemini",
        },
        "closing_date": {
            "value": "2026-09-08",
            "page_number": 1,
            "page_numbers": [1],
            "evidence": "TENDER/IFB NO.: C&P/INST/13/2026-27 dtd:09/08/2026",
            "status": "AI candidate extracted — human verification required",
            "source": "gemini",
        },
        "min_similar_projects": {
            "value": "3", "page_number": 34, "page_numbers": [34],
            "evidence": "Three similar Completed P.O each Order Quantity", "status": "AI candidate extracted — human verification required", "source": "gemini",
        },
        "min_years_experience": {
            "value": "3", "page_number": 34, "page_numbers": [34],
            "evidence": "in last 3 years reckoned from original bid closing date", "status": "AI candidate extracted — human verification required", "source": "gemini",
        },
    }
    enriched = enrich_tender_fields(pages, fields)
    assert enriched["closing_date"]["value"] == ""
    assert "unsupported candidate cleared" in enriched["closing_date"]["status"]
    assert enriched["closing_date"]["suppressed_candidate"] == "2026-09-08"
    assert enriched["min_similar_projects"]["value"] == ""
    assert enriched["min_similar_projects"]["suppressed_candidate"] == "3"
    assert enriched["min_years_experience"]["value"] == ""
    assert "ATEX/IECEx certification" in enriched["required_certifications"]["value"]
    assert "PESO/CCOE approval" in enriched["required_certifications"]["value"]
    assert "Calibration report/certificate" in enriched["required_certifications"]["value"]
    assert enriched["required_certifications"]["source"] == "gemini"
    assert fields["required_certifications"]["value"] == "ATEX Certificate"  # input not mutated


def test_explicit_dated_portal_summary_is_not_overridden_as_missing():
    pages = [{"page_number": 1, "text": "Bid Submission End Date 29-Oct-2026 02:30 PM. The bid closing date is as mentioned on e-tender portal."}]
    fields = {"closing_date": {"value": "2026-10-29", "page_number": 1, "page_numbers": [1], "evidence": "Bid Submission End Date 29-Oct-2026", "status": "Candidate extracted — verify"}}
    enriched = enrich_tender_fields(pages, fields)
    assert enriched["closing_date"]["value"] == "2026-10-29"


def test_audit_finding_carries_source_pages_and_verbatim_support():
    findings = build_tender_review_findings(_agcl_fixture_pages())
    for finding in findings:
        assert finding["source_locations"]
        assert finding["page_numbers"]
        assert "Page " in finding["evidence"]
        assert finding["recommended_action"]
