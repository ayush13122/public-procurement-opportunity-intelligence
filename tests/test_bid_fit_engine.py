from datetime import date
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.bid_fit_engine import (  # noqa: E402
    CompanyProfile,
    TenderRequirements,
    evaluate_bid_fit,
)


TODAY = date(2026, 10, 24)
SOURCE_URL = "https://example.gov.in/tender/123"


@pytest.fixture
def eligible_company():
    return CompanyProfile(
        name="Example IT Supplier",
        capabilities=["computer supply", "network installation", "IT maintenance"],
        service_regions=["Assam", "Meghalaya"],
        years_relevant_experience=8,
        similar_projects_completed=5,
        annual_turnover_inr=25_000_000,
        emd_support_capacity_inr=700_000,
        certifications=["GST registration", "ISO 9001"],
        profile_confirmed=True,
    )


@pytest.fixture
def suitable_tender():
    return TenderRequirements(
        title="Supply and installation of computer systems",
        required_capabilities=["computer supply", "network installation"],
        target_region="Assam",
        min_years_experience=3,
        min_similar_projects=2,
        min_annual_turnover_inr=10_000_000,
        required_certifications=["GST registration"],
        emd_required_inr=500_000,
        closing_date=date(2026, 11, 30),
        official_source_url=SOURCE_URL,
        requirements_reviewed=True,
        official_source_checked=True,
    )


def test_complete_eligible_profile_returns_potential_bid(eligible_company, suitable_tender):
    result = evaluate_bid_fit(eligible_company, suitable_tender, today=TODAY)
    assert result.recommendation == "POTENTIAL BID"
    assert result.fit_score == pytest.approx(100.0)
    assert not result.hard_fail_reasons
    assert result.review_reasons == []


def test_turnover_below_mandatory_minimum_returns_no_bid(eligible_company, suitable_tender):
    company = CompanyProfile(**{**eligible_company.__dict__, "annual_turnover_inr": 2_000_000})
    result = evaluate_bid_fit(company, suitable_tender, today=TODAY)
    assert result.recommendation == "NO-BID"
    assert any("turnover" in reason.lower() for reason in result.hard_fail_reasons)


def test_missing_required_certification_returns_no_bid(eligible_company, suitable_tender):
    company = CompanyProfile(**{**eligible_company.__dict__, "certifications": ["GST registration"]})
    tender = TenderRequirements(**{**suitable_tender.__dict__, "required_certifications": ["ISO 9001"]})
    result = evaluate_bid_fit(company, tender, today=TODAY)
    assert result.recommendation == "NO-BID"
    assert any("certification" in reason.lower() for reason in result.hard_fail_reasons)


def test_insufficient_emd_support_returns_no_bid(eligible_company, suitable_tender):
    company = CompanyProfile(**{**eligible_company.__dict__, "emd_support_capacity_inr": 100_000})
    result = evaluate_bid_fit(company, suitable_tender, today=TODAY)
    assert result.recommendation == "NO-BID"
    assert any("emd" in reason.lower() for reason in result.hard_fail_reasons)


def test_expired_deadline_after_source_check_returns_no_bid(eligible_company, suitable_tender):
    tender = TenderRequirements(**{**suitable_tender.__dict__, "closing_date": date(2026, 10, 20)})
    result = evaluate_bid_fit(eligible_company, tender, today=TODAY)
    assert result.recommendation == "NO-BID"
    assert any("closing date" in reason.lower() for reason in result.hard_fail_reasons)


def test_expired_deadline_without_source_check_requires_review(eligible_company, suitable_tender):
    tender = TenderRequirements(**{
        **suitable_tender.__dict__,
        "closing_date": date(2026, 10, 20),
        "official_source_checked": False,
    })
    result = evaluate_bid_fit(eligible_company, tender, today=TODAY)
    assert result.recommendation == "MANUAL REVIEW"
    assert any("past" in reason.lower() or "source" in reason.lower() for reason in result.review_reasons)


def test_unconfirmed_profile_never_returns_potential_bid(eligible_company, suitable_tender):
    company = CompanyProfile(**{**eligible_company.__dict__, "profile_confirmed": False})
    result = evaluate_bid_fit(company, suitable_tender, today=TODAY)
    assert result.recommendation == "MANUAL REVIEW"
    assert any("company profile" in reason.lower() for reason in result.review_reasons)


def test_unreviewed_tender_requirements_never_returns_potential_bid(eligible_company, suitable_tender):
    tender = TenderRequirements(**{**suitable_tender.__dict__, "requirements_reviewed": False})
    result = evaluate_bid_fit(eligible_company, tender, today=TODAY)
    assert result.recommendation == "MANUAL REVIEW"


def test_missing_company_turnover_when_required_needs_review(eligible_company, suitable_tender):
    company = CompanyProfile(**{**eligible_company.__dict__, "annual_turnover_inr": None})
    result = evaluate_bid_fit(company, suitable_tender, today=TODAY)
    assert result.recommendation == "MANUAL REVIEW"
    assert any("turnover" in reason.lower() for reason in result.review_reasons)


def test_missing_official_url_needs_review(eligible_company, suitable_tender):
    tender = TenderRequirements(**{**suitable_tender.__dict__, "official_source_url": ""})
    result = evaluate_bid_fit(eligible_company, tender, today=TODAY)
    assert result.recommendation == "MANUAL REVIEW"
    assert any("url" in reason.lower() for reason in result.review_reasons)


def test_capability_mismatch_is_review_not_automatic_no_bid(eligible_company, suitable_tender):
    tender = TenderRequirements(**{
        **suitable_tender.__dict__,
        "required_capabilities": ["heavy civil construction", "bridge engineering"],
    })
    result = evaluate_bid_fit(eligible_company, tender, today=TODAY)
    assert result.recommendation == "MANUAL REVIEW"
    assert not result.hard_fail_reasons
    capability_factor = next(f for f in result.factors if f.criterion == "Capability match")
    assert capability_factor.status == "Mismatch"


def test_no_comparable_criteria_returns_manual_review(eligible_company):
    tender = TenderRequirements(
        title="General tender notice",
        official_source_url=SOURCE_URL,
        requirements_reviewed=True,
        official_source_checked=True,
    )
    result = evaluate_bid_fit(eligible_company, tender, today=TODAY)
    assert result.recommendation == "MANUAL REVIEW"
    assert result.fit_score is None


def test_empty_title_raises_value_error(eligible_company, suitable_tender):
    tender = TenderRequirements(**{**suitable_tender.__dict__, "title": " "})
    with pytest.raises(ValueError, match="Tender title is required"):
        evaluate_bid_fit(eligible_company, tender, today=TODAY)


def test_negative_mandatory_threshold_raises_value_error(eligible_company, suitable_tender):
    tender = TenderRequirements(**{**suitable_tender.__dict__, "min_annual_turnover_inr": -1})
    with pytest.raises(ValueError, match="cannot be negative"):
        evaluate_bid_fit(eligible_company, tender, today=TODAY)


def test_negative_company_experience_raises_value_error(eligible_company, suitable_tender):
    company = CompanyProfile(**{**eligible_company.__dict__, "years_relevant_experience": -1})
    with pytest.raises(ValueError, match="Company years of relevant experience cannot be negative"):
        evaluate_bid_fit(company, suitable_tender, today=TODAY)
