from app.tender_answer_engine import answer_common_tender_question


BANBASA_PAGES = [
    {
        "page_number": 1,
        "location": "PDF page 1",
        "text": (
            "Estimated cost put to bid Rs. 3,68,60,53,798/- (Rupees Three Hundred Sixty-Eight Crore) "
            "Earnest Money Rs. 3,78,60,538/- (Rupees Three Crore Seventy-Eight Lakh). "
            "Last date & time of 14/11/2026 up to 15:00 Hrs. online submission of bid "
            "Time and date of opening 16/11/2026 at 15:00 Hrs. of eligibility bid."
        ),
    },
    {
        "page_number": 4,
        "location": "PDF page 4",
        "text": (
            "c. The bidder should have had average Annual Financial Turn Over (gross) "
            "of at Rs. 111.0 Cr. on construction works during the immediate last five "
            "financial years ending on 31st March 2025 (Scanned copy of Certificate "
            "from CA with Unique Document Identification Number (UDIN) to be uploaded). "
            "e. The bidder should have a Banker's Certificate from a commercial Bank for Rs. 148.0 crore "
            "OR the bidder should have Net Worth certificate from CA of minimum Rs. 37.0 Cr. "
            "f. Bidding capacity: A = Maximum turnover in construction works executed in any one year."
        ),
    },
    {
        "page_number": 6,
        "location": "PDF page 6",
        "text": (
            "10. Certificate of Financial Turn over: At the time of submission of bid, bidder may upload "
            "affidavit/certificate from CA mentioning Financial Turn Over of last 5 years."
        ),
    },
]


def test_turnover_question_answers_from_entire_pages_and_not_certificate_clause():
    answer = answer_common_tender_question("annual turnover?", BANBASA_PAGES)
    assert answer is not None
    assert answer.page_number == 4
    assert "111.0 crore" in answer.answer
    assert "1,11,00,00,000" in answer.answer
    assert "five financial years ending on 31 March 2025" in answer.answer
    assert "PDF page 4" in answer.answer
    assert "Certificate of Financial Turn over" not in answer.evidence


def test_bidfit_field_label_question_is_detected_without_gemini():
    answer = answer_common_tender_question("Min Annual Turnover Inr", BANBASA_PAGES)
    assert answer is not None
    assert answer.intent == "turnover"
    assert answer.value_inr == "1110000000"


def test_emd_answer_does_not_confuse_estimated_project_cost_with_emd():
    answer = answer_common_tender_question("EMD amount?", BANBASA_PAGES)
    assert answer is not None
    assert answer.page_number == 1
    assert "3,78,60,538" in answer.answer
    assert "3,68,60,53,798" not in answer.answer


def test_deadline_table_reading_order_is_supported():
    answer = answer_common_tender_question("submission deadline?", BANBASA_PAGES)
    assert answer is not None
    assert answer.page_number == 1
    assert "14/11/2026" in answer.answer
    assert "15:00" in answer.answer


def test_portal_only_deadline_does_not_invent_a_date():
    pages = [{
        "page_number": 1,
        "location": "PDF page 1",
        "text": "Bid Closing Date & Time: As mentioned in Online e-tender portal.",
    }]
    answer = answer_common_tender_question("submission deadline?", pages)
    assert answer is not None
    assert "not stated in the uploaded PDF" in answer.answer
    assert "official e-tender portal" in answer.answer


def test_ambiguous_multi_intent_amount_query_does_not_choose_arbitrarily():
    assert answer_common_tender_question("What is the EMD and tender fee?", BANBASA_PAGES) is None


def test_bid_validity_question_never_falls_through_to_submission_deadline_when_not_found():
    answer = answer_common_tender_question(
        "How many days does the bid remain valid after the submission deadline?", BANBASA_PAGES
    )
    assert answer is None


def test_bid_opening_question_recognises_time_and_date_of_opening_word_order():
    answer = answer_common_tender_question("When will bids be opened?", BANBASA_PAGES)
    assert answer is not None
    assert answer.intent == "bid_opening"
    assert answer.page_number == 1
    assert "16/11/2026" in answer.answer
    assert "15:00" in answer.answer


def test_warranty_question_does_not_misread_financial_loss_duration_after_performance_guarantee():
    pages = BANBASA_PAGES + [{
        "page_number": 5,
        "location": "PDF page 5",
        "text": (
            "Performance Guarantee. Should not have incurred any loss (profit after tax should be positive) "
            "in more than two years during the last five consecutive balance sheet ending financial year 2025-26."
        ),
    }]
    answer = answer_common_tender_question("What is the minimum warranty period after completion?", pages)
    assert answer is None


def test_defect_liability_is_reported_as_dlp_not_mislabelled_as_warranty():
    pages = [{
        "page_number": 1,
        "location": "PDF page 1",
        "text": (
            "Total Time Period 36 Months. Defect Liability Period of 36 months including "
            "Operations and Comprehensive Maintenance after record of completion of the said work."
        ),
    }]
    answer = answer_common_tender_question("What is the minimum warranty period after completion?", pages)
    assert answer is not None
    assert "Defect Liability Period stated: 36 months" in answer.answer
    assert "not expressly as a separate product/work warranty" in answer.answer


def test_assam_portal_deadline_does_not_misread_ifb_issue_date_as_closing_date():
    pages = [
        {
            "page_number": 1,
            "location": "PDF page 1",
            "text": (
                "BID CLOSING DATE & TIME: As mentioned in online e-tender portal "
                "TECHNICAL BID OPENING DATE & TIME: As mentioned in online e-tender portal"
            ),
        },
        {
            "page_number": 2,
            "location": "PDF page 2",
            "text": (
                "Ref No C&P/INST/13/2026-27/02 dtd: 09/10/2026. "
                "You are invited to submit your bid on or before the scheduled bid closing date and time "
                "through Assam Govt e-procurement portal. For your ready reference salient points: "
                "IFB No dtd 09/10/2026. Tender Processing Fee Rs.1000. "
                "Bid Closing Date & Time. As mentioned in Online e-tender portal. "
                "Bid Validity. 120 days from bid Closing date. Bid Security Amount Rs.26000/-"
            ),
        },
        {
            "page_number": 19,
            "location": "PDF page 19",
            "text": (
                "12.0 DEADLINE FOR SUBMISSION OF BIDS: No bid can be submitted after the submission "
                "deadline is reached. The system time displayed on e-procurement web page shall decide "
                "the submission deadline."
            ),
        },
    ]
    deadline = answer_common_tender_question("What is the submission deadline?", pages)
    assert deadline is not None
    assert "not stated in the uploaded PDF" in deadline.answer
    assert "09/10/2026" not in deadline.answer
    assert "PDF page 1" in deadline.answer or "PDF page 2" in deadline.answer


def test_assam_bid_validity_extracts_120_days_from_standalone_bid_validity_label():
    pages = [{
        "page_number": 2,
        "location": "PDF page 2",
        "text": "Bid Validity. 120 days from bid Closing date.",
    }]
    answer = answer_common_tender_question(
        "How many days does the bid remain valid after the submission deadline?", pages
    )
    assert answer is not None
    assert answer.intent == "bid_validity"
    assert "120 days" in answer.answer


def test_assam_bid_opening_portal_placeholder_is_reported_not_guessed():
    pages = [{
        "page_number": 1,
        "location": "PDF page 1",
        "text": "TECHNICAL BID OPENING DATE & TIME: As mentioned in online e-tender portal.",
    }]
    answer = answer_common_tender_question("When will the bids be opened?", pages)
    assert answer is not None
    assert "bid-opening date/time is not stated" in answer.answer
    assert "official e-tender portal" in answer.answer


def test_assam_warranty_answer_preserves_both_durations_and_whichever_earlier():
    pages = [{
        "page_number": 55,
        "location": "PDF page 55",
        "text": (
            "Datasheet for Pressure Transmitter. Warranty 18 years from date of receipt and "
            "acceptance of material or 12 months from the date of commissioning, whichever is earlier."
        ),
    }]
    answer = answer_common_tender_question(
        "What is the minimum warranty period after completion?", pages
    )
    assert answer is not None
    assert "18 years" in answer.answer
    assert "12 months" in answer.answer
    assert "whichever is earlier" in answer.answer
    assert "confirm the complete clause" in answer.answer


def test_deadline_parser_keeps_date_after_dctn_abbreviation_and_dotted_leader():
    # This mirrors the real Odisha PDF's selectable text on PDF page 16. The
    # deadline label and date are separated by line breaks, a DTCN abbreviation
    # and dotted leaders; the parser must not truncate before 09.11.2025.
    pages = [
        {
            "page_number": 16,
            "location": "PDF page 16",
            "text": (
                "7 Last Date & time of submission of online Bid (Clause No. 1 of DTCN.)\n"
                "Time: 5.30 PM………….\nDt. 09.11.2025\n"
                "8 Date of original bid documents submission\n"
                "Time : 10.30 AM to 5.30 PM (except holidays)\n"
                "Dt.29.10.2026 at 10.30 A.M. To 09.11.2026 up to 5.30 P.M."
            ),
        },
        {
            "page_number": 22,
            "location": "PDF page 22",
            "text": (
                "The last date and time of submission of Bid is from Dt.30.10.2026 "
                "at 10.30 AM to Dt. 10.11.2026 at 5.30 PM.\n\n"
                "2. The Technical Bid documents (Cover-I) will be opened on 11.11.2026."
            ),
        },
    ]
    answer = answer_common_tender_question("What is the submission deadline?", pages)
    assert answer is not None
    assert answer.intent == "deadline"
    assert "conflicting submission-date entries" in answer.answer
    assert "09.11.2025" in answer.answer
    assert "10.11.2026 up to 5.30 PM" in answer.answer
