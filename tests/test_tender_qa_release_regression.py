"""Cross-state regression tests for the Odisha Mayurbhanj tender Q&A paths."""
from app.tender_answer_engine import answer_common_tender_question
from app.tender_review_audit import build_tender_review_findings
from app.tender_question_intents import should_skip_provider_for_question


ODISHA_PAGES = [
    {
        "page_number": 2,
        "location": "PDF page 2",
        "text": (
            "Cost of Bid Documents (in Rs.) EMD in Rs Class of Contractor Period of Completion 1 2 3 4 5 6 7 "
            "1 Agro-Enterprise Model on Production of QPM of fruits, vegetables and flowers, at KVK, Mayurbhanj-I, Samakhunta "
            "1051436.00 6000.00 10514.00 C&D 3 (THREE) CALENDER MONTH "
            "2 Construction of road to different units inside at KVK, Mayurbhanj-II, Jashipur "
            "1934365.00 6000.00 19344.00 C&D 3 (TWO) CALENDER MONTH "
            "3 Construction of balance boundary wall adjacent to Biological Control Lab at Krushi Bhavan, Mayurbhanj, Baripada "
            "583440.00 4000.00 5834.00 C&D 3 (THREE) CALENDER MONTH "
            "4 Furnishing of FIAC Extension, Bahalda 446376.00 2000.00 4464.00 C&D 3 (THREE) CALENDER MONTH "
            "5 Upgradation of AEE Office, Baripada 306782.00 2000.00 3068.00 C&D 3 (THREE) CALENDER MONTH "
            "6 Upgradation and Furnishing of EE Office, Baripada 487558.00 2000.00 4876.00 C&D 3 (THREE) CALENDER MONTH "
            "7 Furnishing of FIAC extension & FIAC, Bijatala 358795.00 2000.00 3588.00 C&D 3 (THREE) CALENDER MONTH "
            "8 Furnishing of AAE Office, Bisoi 441793.00 2000.00 4418.00 C&D 3 (THREE) CALENDER MONTH "
            "9 Furnishing of FIAC extension, Bisoi 297265.00 2000.00 2973.00 C&D 3 (THREE) CALENDER MONTH "
            "10 Furnishing of FIAC Extension Jamda and repairing of FIAC building, Jamda 501966.00 4000.00 5020.00 C&D 3 (THREE) CALENDER MONTH "
            "11 Furnishing of FIAC extension, Karanjia 401029.00 2000.00 4010.00 C&D 3 (THREE) CALENDER MONTH"
        ),
        "layout_text": """Cost of Bid Documents (in Rs.) EMD in Rs Class of Contractor Period of Completion
1 2 3 4 5 6 7
1
Agro-Enterprise Model on Production of QPM of fruits, vegetables and flowers, at KVK, Mayurbhanj-I, Samakhunta
1051436.00
6000.00
10514.00
C&D
3 (THREE) CALENDER MONTH
2
Construction of road to different units inside at KVK, Mayurbhanj-II, Jashipur
1934365.00
6000.00
19344.00
C&D
3 (TWO) CALENDER MONTH
3
Construction of balance boundary wall adjacent to Biological Control Lab at Krushi Bhavan, Mayurbhanj, Baripada
583440.00
4000.00 5834.00
C&D
3 (THREE) CALENDER MONTH
4 Furnishing of FIAC Extension, Bahalda
446376.00
2000.00 4464.00
C&D
3 (THREE) CALENDER MONTH
5 Upgradation of AEE Office, Baripada
306782.00
2000.00 3068.00
C&D
3 (THREE) CALENDER MONTH
6 Upgradation and Furnishing of EE Office, Baripada
487558.00
2000.00 4876.00
C&D
3 (THREE) CALENDER MONTH
7 Furnishing of FIAC extension & FIAC, Bijatala
358795.00
2000.00 3588.00
C&D
3 (THREE) CALENDER MONTH
8
Furnishing of AAE Office, Bisoi
441793.00
2000.00 4418.00
C&D
3 (THREE) CALENDER MONTH
9 Furnishing of FIAC extension, Bisoi
297265.00
2000.00 2973.00
C&D
3 (THREE) CALENDER MONTH
10 Furnishing of FIAC Extension Jamda and repairing of FIAC building, Jamda
501966.00
4000.00 5020.00
C&D
3 (THREE) CALENDER MONTH
11 Furnishing of FIAC extension, Karanjia
401029.00
2000.00 4010.00
C&D
3 (THREE) CALENDER MONTH""",
    },
    {
        "page_number": 3,
        "location": "PDF page 3",
        "text": (
            "12 Furnishing of FIAC extension, Kusumi 372047.00 2000.00 3720.00 C&D 3 (THREE) CALENDER MONTH "
            "13 Construction of toilet and repair renovation of ADO office and training hall, Rairangpur 365693.00 2000.00 3657.00 C&D 3 (THREE) CALENDER MONTH "
            "14 Furnishing of FIAC extension, Rairangpur 381276.00 2000.00 3813.00 C&D 3 (THREE) CALENDER MONTH "
            "15 Furnishing of FIAC extension, Thakurmunda 484319.00 2000.00 4843.00 C&D 3 (THREE) CALENDER MONTH "
            "16 Repair and renovation of ADO, Udala 453528.00 2000.00 4535.00 C&D 3 (THREE) CALENDER MONTH "
            "The bidders have to participate in ONLINE bidding only."
        ),
        "layout_text": """12 Furnishing of FIAC extension, Kusumi
372047.00
2000.00 3720.00
C&D
3 (THREE) CALENDER MONTH
13 Construction of toilet and repair renovation of ADO office and training hall, Rairangpur
365693.00
2000.00 3657.00
C&D
3 (THREE) CALENDER MONTH
14 Furnishing of FIAC extension, Rairangpur
381276.00
2000.00 3813.00
C&D
3 (THREE) CALENDER MONTH
15 Furnishing of FIAC extension, Thakurmunda
484319.00
2000.00 4843.00
C&D
3 (THREE) CALENDER MONTH
16 Repair and renovation of ADO, Udala
453528.00
2000.00 4535.00
C&D
3 (THREE) CALENDER MONTH
The bidders have to participate in ONLINE bidding only.""",
    },
    {
        "page_number": 5,
        "location": "PDF page 5",
        "text": (
            "SPECIAL CLAUSES 2. Joint venture is required for the works having Sl. No. "
            "1,4,5,6,7,8,9,10,11,12,13,14,15&16. "
            "3. The bidder should have valid electrical license in his name or should have Registered Joint Venture Agreement/MOU "
            "with an electrical contractor having valid HT/LT/MV issued by the ELBO for the Composite Tender WORKS. "
            "6. The bidder must provide warranty of the works for minimum three years after completion of the works."
        ),
        "layout_text": (
            "SPECIAL CLAUSES\n2. Joint venture is required for the works having Sl. No. 1,4,5,6,7,8,9,10,11,12,13,14,15&16.\n"
            "3. The bidder should have valid electrical license in his name or should have Registered Joint Venture Agreement/MOU "
            "with an electrical contractor having valid HT/LT/MV issued by the ELBO for the Composite Tender WORKS.\n"
            "6. The bidder must provide warranty of the works for minimum three years after completion of the works."
        ),
    },
    {
        "page_number": 16,
        "location": "PDF page 16",
        "text": (
            "Last Date & time of submission of online Bid (Clause No. 1 of DTCN.) "
            "Time: 5.30 PM Dt. 09.11.2025 Date of original bid documents submission "
            "Dt.29.10.2026 at 10.30 A.M. To 09.11.2026 up to 5.30 P.M"
        ),
    },
    {
        "page_number": 17,
        "location": "PDF page 17",
        "text": "Bid validity period (Clause No. 8 of DTCN.) 90 days",
    },
    {
        "page_number": 21,
        "location": "PDF page 21",
        "text": (
            "Sealed percentage rate bids are invited on ONLINE in single cover system from “C” & “D”, "
            "and also the criteria mentioned in column 06 Class contractors registered with the State Governments."
        ),
    },
    {
        "page_number": 22,
        "location": "PDF page 22",
        "text": (
            "The last date and time of submission of Bid is from Dt.30.10.2026 at 10.30 AM to Dt. 10.11.2026 up to 5.30 PM. "
            "Bids shall be opened at 11.00 AM on Dt.11.11.2026."
        ),
    },
    {
        "page_number": 30,
        "location": "PDF page 30",
        "text": (
            "83. EIGIBILITY CRITERIA. To be eligible for qualification, applicants shall furnish the followings. "
            "Copy of valid Registration Certificate. Copy of PAN Card. Copy of G.S.T. Registration Certificate. "
            "Schedule-A regarding No Relation Certificate. Schedule-D regarding litigation debarring/expelling or abandonment of work. "
            "Schedule-E affidavit. The bidder must provide electrical contractor registration certificate, PAN, GST certificate."
        ),
    },
]


def test_bid_document_fee_question_returns_work_specific_schedule_not_one_arbitrary_amount():
    answer = answer_common_tender_question("What is the cost of bid documents?", ODISHA_PAGES)
    assert answer is not None
    assert answer.intent == "tender_fee"
    assert "work-specific" in answer.answer
    assert "Work 1" in answer.answer and "₹6,000" in answer.answer
    assert "Work 3" in answer.answer and "₹4,000" in answer.answer
    assert "Work 16" in answer.answer and "₹2,000" in answer.answer
    assert "1:6000" in answer.raw_value and "16:2000" in answer.raw_value


def test_bid_validity_question_does_not_get_misrouted_to_submission_deadline():
    answer = answer_common_tender_question(
        "How many days does the bid remain valid after the submission deadline?", ODISHA_PAGES
    )
    assert answer is not None
    assert answer.intent == "bid_validity"
    assert answer.page_number == 17
    assert "90 days" in answer.answer
    assert "09.11.2025" not in answer.answer


def test_bid_opening_question_returns_opening_event_not_submission_deadline():
    answer = answer_common_tender_question("When will the bids be opened?", ODISHA_PAGES)
    assert answer is not None
    assert answer.intent == "bid_opening"
    assert answer.page_number == 22
    assert "11.11.2026" in answer.answer
    assert "11.00 AM" in answer.answer
    assert "09.11.2025" not in answer.answer


def test_warranty_period_is_answered_locally_without_gemini():
    answer = answer_common_tender_question(
        "What is the minimum warranty period required after completion of the work?", ODISHA_PAGES
    )
    assert answer is not None
    assert answer.intent == "warranty"
    assert answer.raw_value == "3 years"
    assert answer.page_number == 5


def test_joint_venture_answer_parses_serial_number_alternatives():
    answer = answer_common_tender_question("Which work serial numbers require a Joint Venture agreement?", ODISHA_PAGES)
    assert answer is not None
    assert answer.intent == "joint_venture"
    assert answer.raw_value == "1, 4–16"
    assert "1, 4–16" in answer.answer


def test_contractor_class_question_returns_c_and_d_not_an_unrelated_initial():
    answer = answer_common_tender_question("What classes of contractors are eligible?", ODISHA_PAGES)
    assert answer is not None
    assert answer.intent == "contractor_class"
    assert answer.raw_value == "C & D"


def test_emd_question_returns_work_specific_schedule_not_one_arbitrary_amount():
    answer = answer_common_tender_question("What is the EMD amount?", ODISHA_PAGES)
    assert answer is not None
    assert answer.intent == "emd"
    assert "work-specific" in answer.answer
    assert "Work 1" in answer.answer and "₹10,514" in answer.answer
    assert "Work 16" in answer.answer and "₹4,535" in answer.answer
    assert "1:10514" in answer.raw_value and "16:4535" in answer.raw_value


def test_submission_deadline_conflict_is_reported_instead_of_silently_choosing_a_date():
    answer = answer_common_tender_question("What is the submission deadline?", ODISHA_PAGES)
    assert answer is not None
    assert answer.intent == "deadline"
    assert "conflicting submission-date entries" in answer.answer
    assert "09.11.2025" in answer.answer
    assert "10.11.2026 up to 5.30 PM" in answer.answer


def test_no_turnover_threshold_returns_careful_not_found_answer():
    answer = answer_common_tender_question("Does the tender specify a minimum annual turnover requirement?", ODISHA_PAGES)
    assert answer is not None
    assert answer.intent == "turnover"
    assert "No explicit minimum annual turnover amount was found" in answer.answer
    assert answer.page_number == 30
    assert "corrigenda" in answer.answer


def test_review_audit_flags_odisha_deadline_conflict_variable_emd_and_jv_scope():
    findings = build_tender_review_findings(ODISHA_PAGES)
    titles = {item["title"] for item in findings}
    assert "Conflicting bid submission date entries" in titles
    assert "EMD varies by work package" in titles
    assert "Joint Venture requirement applies only to specified work serials" in titles


def test_bidfit_multi_work_notice_uses_package_title_not_late_clause_text():
    from app.tender_requirements_extractor import extract_tender_requirements_draft

    cover = {
        "page_number": 1,
        "location": "PDF page 1",
        "text": (
            "GOVERNMENT OF ODISHA AGRICULTURE DEPARTMENT BID IDENTIFICATION NO.-03/2026-27 "
            "TECHNICAL BID DOCUMENTS / DETAILED TENDER CALL NOTICE FOR THE WORKS: "
            "1. Agro-Enterprise Model at KVK Samakhunta 2. Construction of road at KVK Jashipur "
            "3. Construction of boundary wall at Krushi Bhavan 4. Furnishing of FIAC Bahalda "
            "5. Upgradation of AEE Office 6. Upgradation of EE Office 7. Furnishing FIAC Bijatala "
            "8. Furnishing AAE Office Bisoi 9. Furnishing FIAC Bisoi 10. Furnishing FIAC Jamda "
            "11. Furnishing FIAC Karanjia 12. Furnishing FIAC Kusumi 13. Construction of toilet Rairangpur "
            "14. Furnishing FIAC Rairangpur 15. Furnishing FIAC Thakurmunda 16. Repair ADO Udala"
        ),
        "layout_text": "TECHNICAL BID DOCUMENTS / DETAILED TENDER CALL NOTICE FOR THE WORKS",
    }
    late_page = {
        "page_number": 50,
        "location": "PDF page 50",
        "text": "Name of work with job nature accepted Bid number date of completion total payment received",
    }
    fields = extract_tender_requirements_draft([cover, *ODISHA_PAGES[:2], late_page])
    title = fields["tender_title"]
    assert title["page_number"] == 1
    assert "Multiple works (16 listed packages)" in title["value"]
    assert "total payment received" not in title["value"].casefold()


def test_bidfit_emd_scalar_is_suppressed_when_notice_has_work_wise_schedule():
    from app.tender_requirements_extractor import extract_tender_requirements_draft

    fields = extract_tender_requirements_draft(ODISHA_PAGES)
    emd = fields["emd_required_inr"]
    assert emd["value"] == ""
    assert "Work-specific EMD schedule detected (16 work rows)" in emd["status"]
    assert emd["page_numbers"] == [2, 3]


def test_enrichment_does_not_let_ai_restore_a_single_emd_or_conflicting_deadline():
    from app.tender_requirements_extractor import extract_tender_requirements_draft
    from app.tender_review_audit import enrich_tender_fields

    fields = extract_tender_requirements_draft(ODISHA_PAGES)
    fields["emd_required_inr"]["value"] = "10514"  # Simulate a wrong Gemini scalar.
    fields["closing_date"]["value"] = "2026-11-10"  # Simulate one side of the conflict.
    enriched = enrich_tender_fields(ODISHA_PAGES, fields)
    assert enriched["emd_required_inr"]["value"] == ""
    assert "work-specific emd schedule" in enriched["emd_required_inr"]["status"].casefold()
    assert enriched["closing_date"]["value"] == ""
    assert "conflicting submission-date" in enriched["closing_date"]["status"].casefold()


def test_multi_work_bidfit_merge_preserves_blank_safety_status_over_ai_scalar():
    from app.tender_extraction_hybrid import merge_candidate_fields

    local = {
        "emd_required_inr": {
            "value": "", "page_number": 2, "page_numbers": [2, 3],
            "evidence": "EMD in Rs schedule across work rows", 
            "status": "Work-specific EMD schedule detected — select the work serial",
        }
    }
    ai = {
        "emd_required_inr": {
            "value": "10514", "page_number": 2, "page_numbers": [2],
            "evidence": "EMD in Rs 10514", "status": "AI candidate extracted",
        }
    }
    merged = merge_candidate_fields(local, ai)["emd_required_inr"]
    assert merged["value"] == ""
    assert "work-specific emd schedule" in merged["status"].casefold()
    assert merged["ai_candidate_value_for_review"] == "10514"


def test_eligibility_enrichment_captures_required_digital_signature_credential():
    from app.tender_requirements_extractor import extract_tender_requirements_draft
    from app.tender_review_audit import enrich_tender_fields

    pages = [
        {"page_number": 3, "text": "The bidder must possess matching class compatible Digital Signature Certificate (DSC)."},
        {"page_number": 17, "text": "The DSC used must be of appropriate class (Class II or Class III) issued from a registered Certifying Authority."},
    ]
    fields = enrich_tender_fields(pages, extract_tender_requirements_draft(pages))
    assert "Digital Signature Certificate (DSC)" in fields["required_certifications"]["value"]
    assert fields["required_certifications"]["page_number"] == 3


def test_structured_field_questions_stay_local_when_exact_answer_is_not_found():
    assert should_skip_provider_for_question(
        "How many days does the bid remain valid after the submission deadline?"
    )
    assert should_skip_provider_for_question("What is the minimum warranty period after completion?")
    assert should_skip_provider_for_question("What is the EMD amount?")


def test_general_eligibility_question_can_still_use_optional_llm_path():
    assert not should_skip_provider_for_question(
        "Explain the overall eligibility criteria and how they fit together."
    )
