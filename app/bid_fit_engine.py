"""Explainable rule-based bid-fit screening for public procurement opportunities.

This module is decision support, not a bid-win model, legal eligibility opinion,
or profitability prediction. It evaluates only fields explicitly supplied by a
user and keeps missing/unverified information visible.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from urllib.parse import urlparse
from typing import Any


@dataclass(frozen=True)
class CompanyProfile:
    name: str = ""
    capabilities: list[str] = field(default_factory=list)
    service_regions: list[str] = field(default_factory=list)
    years_relevant_experience: int | None = None
    similar_projects_completed: int | None = None
    annual_turnover_inr: float | None = None
    emd_support_capacity_inr: float | None = None
    certifications: list[str] = field(default_factory=list)
    profile_confirmed: bool = False


@dataclass(frozen=True)
class TenderRequirements:
    title: str
    required_capabilities: list[str] = field(default_factory=list)
    target_region: str = ""
    min_years_experience: int | None = None
    min_similar_projects: int | None = None
    min_annual_turnover_inr: float | None = None
    required_certifications: list[str] = field(default_factory=list)
    emd_required_inr: float | None = None
    closing_date: date | None = None
    official_source_url: str = ""
    requirements_reviewed: bool = False
    official_source_checked: bool = False


@dataclass(frozen=True)
class FactorResult:
    criterion: str
    weight: float
    points_awarded: float | None
    status: str
    explanation: str


@dataclass(frozen=True)
class BidFitResult:
    recommendation: str
    fit_score: float | None
    factors: list[FactorResult]
    hard_fail_reasons: list[str]
    review_reasons: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.fit_score is not None:
            result["fit_score"] = round(self.fit_score, 2)
        return result


def _norm(value: str) -> str:
    """Lowercase and normalize punctuation/whitespace for simple comparisons."""
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _norm_set(values: list[str]) -> set[str]:
    return {_norm(value) for value in values if _norm(value)}


def _term_matches(required: str, available_terms: list[str]) -> bool:
    """Conservative lexical match; this is not semantic NLP or synonym matching."""
    req = _norm(required)
    if not req:
        return False
    req_tokens = set(req.split())
    for item in available_terms:
        candidate = _norm(item)
        if not candidate:
            continue
        candidate_tokens = set(candidate.split())
        if req == candidate or req in candidate or candidate in req:
            return True
        union = req_tokens | candidate_tokens
        if union and len(req_tokens & candidate_tokens) / len(union) >= 0.5:
            return True
    return False


def _valid_http_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _compare_minimum(
    *,
    label: str,
    company_value: float | int | None,
    required_value: float | int | None,
    weight: float,
    hard_fail_reasons: list[str],
    review_reasons: list[str],
    factors: list[FactorResult],
    display: str,
) -> None:
    if required_value is None:
        return
    if company_value is None:
        review_reasons.append(f"Company {label.lower()} is missing; cannot compare with the tender requirement.")
        factors.append(FactorResult(label, weight, None, "Not assessed", "Company value is missing."))
        return
    if company_value < required_value:
        message = f"Company {label.lower()} ({company_value:,.0f}) is below the stated minimum ({required_value:,.0f})."
        hard_fail_reasons.append(message)
        factors.append(FactorResult(label, weight, 0.0, "Fail", message))
    else:
        message = f"Company value ({company_value:,.0f}) meets the stated minimum ({required_value:,.0f})."
        factors.append(FactorResult(label, weight, weight, "Pass", message))


def evaluate_bid_fit(
    company: CompanyProfile,
    tender: TenderRequirements,
    *,
    today: date | None = None,
    potential_bid_threshold: float = 70.0,
) -> BidFitResult:
    """Evaluate a company against user-entered tender criteria transparently.

    ``NO-BID`` is returned only for an evidenced hard blocker when the user has
    confirmed the profile, reviewed the requirements, and checked the official
    source. Otherwise unverified blockers lead to ``MANUAL REVIEW``.
    """
    if not _norm(tender.title):
        raise ValueError("Tender title is required.")
    if not 0 <= potential_bid_threshold <= 100:
        raise ValueError("potential_bid_threshold must be between 0 and 100.")
    for label, value in (
        ("minimum years of experience", tender.min_years_experience),
        ("minimum similar projects", tender.min_similar_projects),
    ):
        if value is not None and value < 0:
            raise ValueError(f"{label} cannot be negative.")

    for label, value in (
        ("years of relevant experience", company.years_relevant_experience),
        ("similar completed projects", company.similar_projects_completed),
    ):
        if value is not None and value < 0:
            raise ValueError(f"Company {label} cannot be negative.")

    for label, value in (
        ("minimum annual turnover", tender.min_annual_turnover_inr),
        ("required EMD", tender.emd_required_inr),
        ("company annual turnover", company.annual_turnover_inr),
        ("company EMD support capacity", company.emd_support_capacity_inr),
    ):
        if value is not None and value < 0:
            raise ValueError(f"{label} cannot be negative.")

    current_date = today or date.today()
    hard_fail_reasons: list[str] = []
    review_reasons: list[str] = []
    warnings: list[str] = [
        "This is a rule-based fit screen, not a prediction of tender-win probability or guaranteed profitability.",
        "Capability matching uses simple text overlap; it does not understand every synonym or technical equivalence.",
    ]
    factors: list[FactorResult] = []

    if not company.profile_confirmed:
        review_reasons.append("Confirm that the company profile is complete and accurate.")
    if not tender.requirements_reviewed:
        review_reasons.append("Confirm that mandatory requirements were checked against the official tender documents.")
    if not tender.official_source_checked:
        review_reasons.append("Check the official source for current status, deadline, and corrigenda.")
    if not _valid_http_url(tender.official_source_url):
        review_reasons.append("A valid official tender source URL is required for traceability.")

    if tender.closing_date is not None and tender.closing_date < current_date:
        if tender.official_source_checked:
            hard_fail_reasons.append(
                f"The entered closing date ({tender.closing_date.isoformat()}) has passed; do not proceed unless the official source confirms an extension or new tender."
            )
        else:
            review_reasons.append(
                f"The entered closing date ({tender.closing_date.isoformat()}) is in the past; recheck status/extension on the official source."
            )

    # Capability fit is informative, not an automatic legal disqualification.
    required_capabilities = [x.strip() for x in tender.required_capabilities if _norm(x)]
    if required_capabilities:
        matched = [x for x in required_capabilities if _term_matches(x, company.capabilities)]
        ratio = len(matched) / len(required_capabilities)
        weight = 35.0
        points = weight * ratio
        missing = [x for x in required_capabilities if x not in matched]
        status = "Pass" if ratio == 1 else ("Partial" if ratio > 0 else "Mismatch")
        explanation = f"Matched {len(matched)} of {len(required_capabilities)} listed capability terms."
        if missing:
            explanation += " Check manually: " + ", ".join(missing) + "."
            warnings.append("Capability mismatch is not treated as a legal disqualification because terminology may differ.")
        factors.append(FactorResult("Capability match", weight, points, status, explanation))

    # Geographic fit is a soft signal because companies may operate outside their usual region.
    target_region = _norm(tender.target_region)
    company_regions = _norm_set(company.service_regions)
    if target_region:
        weight = 10.0
        pan_india = {"pan india", "india", "all india", "nationwide"} & company_regions
        if pan_india or target_region in company_regions:
            factors.append(FactorResult("Geographic fit", weight, weight, "Pass", "Company profile includes the target region or pan-India coverage."))
        else:
            factors.append(FactorResult("Geographic fit", weight, 0.0, "Review", "Target region is not listed in the company's service regions; confirm whether the company can serve it."))
            warnings.append("Geographic mismatch is a review flag, not an automatic no-bid decision.")

    # Mandatory objective checks. A failed criterion is definitive only once the
    # user has confirmed both the company profile and the official requirements/source.
    _compare_minimum(
        label="Years of relevant experience",
        company_value=company.years_relevant_experience,
        required_value=tender.min_years_experience,
        weight=15.0,
        hard_fail_reasons=hard_fail_reasons,
        review_reasons=review_reasons,
        factors=factors,
        display="years",
    )
    _compare_minimum(
        label="Similar completed projects",
        company_value=company.similar_projects_completed,
        required_value=tender.min_similar_projects,
        weight=15.0,
        hard_fail_reasons=hard_fail_reasons,
        review_reasons=review_reasons,
        factors=factors,
        display="projects",
    )
    _compare_minimum(
        label="Annual turnover (INR)",
        company_value=company.annual_turnover_inr,
        required_value=tender.min_annual_turnover_inr,
        weight=15.0,
        hard_fail_reasons=hard_fail_reasons,
        review_reasons=review_reasons,
        factors=factors,
        display="INR",
    )

    required_certs = _norm_set(tender.required_certifications)
    if required_certs:
        available_certs = _norm_set(company.certifications)
        missing_certs = sorted(required_certs - available_certs)
        weight = 10.0
        if missing_certs:
            reason = "Missing listed mandatory certification(s): " + ", ".join(missing_certs) + "."
            hard_fail_reasons.append(reason)
            factors.append(FactorResult("Required certifications", weight, 0.0, "Fail", reason))
        else:
            factors.append(FactorResult("Required certifications", weight, weight, "Pass", "All listed required certifications appear in the company profile; verify document validity."))

    if tender.emd_required_inr is not None:
        weight = 10.0
        if company.emd_support_capacity_inr is None:
            review_reasons.append("Company EMD support capacity is missing; cannot compare it with the stated EMD.")
            factors.append(FactorResult("EMD support capacity (INR)", weight, None, "Not assessed", "Company capacity is missing."))
        elif company.emd_support_capacity_inr < tender.emd_required_inr:
            reason = f"Company EMD support capacity ({company.emd_support_capacity_inr:,.0f}) is below the stated EMD ({tender.emd_required_inr:,.0f})."
            hard_fail_reasons.append(reason)
            factors.append(FactorResult("EMD support capacity (INR)", weight, 0.0, "Fail", reason))
        else:
            factors.append(FactorResult("EMD support capacity (INR)", weight, weight, "Pass", "Available EMD support capacity meets the entered EMD amount; confirm accepted payment/guarantee method."))

    assessed = [f for f in factors if f.points_awarded is not None and f.weight > 0]
    total_weight = sum(f.weight for f in assessed)
    fit_score = (sum(float(f.points_awarded) for f in assessed) / total_weight * 100.0) if total_weight else None
    if not assessed:
        review_reasons.append("At least one concrete capability, region, or eligibility criterion is needed to calculate a fit score.")

    verified_for_decision = (
        company.profile_confirmed
        and tender.requirements_reviewed
        and tender.official_source_checked
        and _valid_http_url(tender.official_source_url)
    )
    if hard_fail_reasons and verified_for_decision:
        recommendation = "NO-BID"
    elif hard_fail_reasons or review_reasons or not verified_for_decision:
        recommendation = "MANUAL REVIEW"
    elif fit_score is not None and fit_score >= potential_bid_threshold:
        recommendation = "POTENTIAL BID"
    else:
        recommendation = "MANUAL REVIEW"
        review_reasons.append(
            f"The fit score is below the configurable {potential_bid_threshold:.0f}-point Potential Bid threshold; review the opportunity manually."
        )

    return BidFitResult(
        recommendation=recommendation,
        fit_score=fit_score,
        factors=factors,
        hard_fail_reasons=hard_fail_reasons,
        review_reasons=review_reasons,
        warnings=warnings,
    )
