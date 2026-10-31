"""Streamlit interface for transparent company-to-tender fit screening.

All form values are mirrored into non-widget session-state keys. This prevents
widget cleanup during Streamlit multipage navigation from wiping the user's input.
The latest result is also retained for the lifetime of the session.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.bid_fit_engine import CompanyProfile, TenderRequirements, evaluate_bid_fit  # noqa: E402

PREFILL_KEY_MAP = {
    "tender_title": "bidfit_tender_title",
    "required_capabilities": "bidfit_tender_capabilities_raw",
    "target_region": "bidfit_target_region",
    "min_years_experience": "bidfit_min_years_raw",
    "min_similar_projects": "bidfit_min_projects_raw",
    "min_annual_turnover_inr": "bidfit_min_turnover_raw",
    "required_certifications": "bidfit_required_certifications_raw",
    "emd_required_inr": "bidfit_emd_required_raw",
    "source_url": "bidfit_source_url",
}

DEFAULTS = {
    "bidfit_profile_company_name": "",
    "bidfit_profile_capabilities": "",
    "bidfit_profile_regions": "",
    "bidfit_profile_turnover": "",
    "bidfit_profile_experience": "",
    "bidfit_profile_projects": "",
    "bidfit_profile_certifications": "",
    "bidfit_profile_emd_capacity": "",
    "bidfit_profile_confirmed": False,
    "bidfit_tender_title": "",
    "bidfit_tender_capabilities_raw": "",
    "bidfit_target_region": "",
    "bidfit_min_years_raw": "",
    "bidfit_min_projects_raw": "",
    "bidfit_min_turnover_raw": "",
    "bidfit_required_certifications_raw": "",
    "bidfit_emd_required_raw": "",
    "bidfit_source_url": "",
    "bidfit_closing_date_known": False,
    "bidfit_closing_date": date.today(),
    "bidfit_requirements_reviewed": False,
    "bidfit_official_source_checked": False,
}


def _save_form_value(widget_key: str) -> None:
    """Mirror changing widget values to persistent-in-session non-widget state."""
    saved = dict(st.session_state.get("bidfit_saved_form_values", {}))
    saved[widget_key] = st.session_state.get(widget_key)
    st.session_state["bidfit_saved_form_values"] = saved
    # Any edited input makes an older evaluation stale; don't show it as current.
    st.session_state.pop("last_bid_fit_result", None)
    st.session_state.pop("last_bid_fit_title", None)


def _apply_reviewed_prefill(payload: dict) -> None:
    """Apply reviewed Copilot draft values before the corresponding widgets render."""
    draft_values = payload.get("values", {})
    saved = dict(st.session_state.get("bidfit_saved_form_values", {}))
    for draft_name, widget_key in PREFILL_KEY_MAP.items():
        if draft_name == "source_url":
            value = str(payload.get("official_source_url", "") or "")
        else:
            value = str(draft_values.get(draft_name, "") or "")
        st.session_state[widget_key] = value
        saved[widget_key] = value

    raw_closing_date = str(draft_values.get("closing_date", "") or "").strip()
    try:
        closing_date_value = date.fromisoformat(raw_closing_date) if raw_closing_date else date.today()
    except ValueError:
        closing_date_value = date.today()
    st.session_state["bidfit_closing_date"] = closing_date_value
    saved["bidfit_closing_date"] = closing_date_value

    # Import never proves official verification. Explicitly reset all confirmations.
    for key in ("bidfit_closing_date_known", "bidfit_requirements_reviewed", "bidfit_official_source_checked"):
        st.session_state[key] = False
        saved[key] = False

    st.session_state["bidfit_saved_form_values"] = saved
    values_snapshot = {key: str(value or "") for key, value in draft_values.items()}
    metadata = {
        "source_filename": payload.get("source_filename", "uploaded tender file"),
        "field_details": payload.get("field_details", {}),
        "values": values_snapshot,
    }
    st.session_state["bidfit_prefill_metadata"] = metadata
    st.session_state["bidfit_last_reviewed_import"] = {
        **metadata,
        "official_source_url": "",
    }
    st.session_state["bidfit_prefill_notice"] = True
    # A new tender import invalidates any earlier tender evaluation.
    st.session_state.pop("last_bid_fit_result", None)
    st.session_state.pop("last_bid_fit_title", None)


# Use non-widget keys as the durable session copy; widget keys may be cleaned up
# by Streamlit when the user navigates away from this page.
for key, default in DEFAULTS.items():
    if key not in st.session_state:
        saved = st.session_state.get("bidfit_saved_form_values", {})
        st.session_state[key] = saved.get(key, default)

pending_prefill = st.session_state.pop("bidfit_pending_prefill", None)
if pending_prefill:
    _apply_reviewed_prefill(pending_prefill)

# A recovery/refresh prefill request can arrive while this page is being rendered.
# This button is shown above the tender fields so keys are updated before widgets mount.
st.title("Company Bid-Fit Analysis")
st.caption("Explainable rule-based screening · not a bid-win prediction or profitability guarantee")
st.info(
    "Enter company details and the mandatory criteria from the official tender documents. "
    "The tool flags potential blockers and explains its score; it does not replace the official tender documents, "
    "legal review, or a commercial cost assessment. Current input/result data persists only in this browser session; "
    "it is not saved to a database."
)

if st.session_state.pop("bidfit_prefill_notice", False):
    st.success(
        f"Tender fields were prefilled from Copilot file: {st.session_state.get('bidfit_prefill_metadata', {}).get('source_filename', 'uploaded file')}. "
        "Please verify every value; source/status confirmations remain unchecked."
    )

_import_meta = st.session_state.get("bidfit_prefill_metadata")
if _import_meta:
    with st.expander("Review source evidence from the most recent Copilot import", expanded=False):
        st.caption(f"Imported from: {_import_meta.get('source_filename', 'uploaded tender file')}")
        _rows = []
        for _name, _details in _import_meta.get("field_details", {}).items():
            locations = _details.get("source_locations") or [f"Page {n}" for n in _details.get("page_numbers", [])]
            _rows.append({
                "Field": _name.replace("_", " ").title(),
                "Extracted value": _details.get("value", "") or "Not found",
                "Source location(s)": "; ".join(locations) or "—",
                "Evidence": _details.get("evidence", "") or "No evidence extracted",
            })
        if _rows:
            st.dataframe(_rows, width="stretch", hide_index=True)
        st.caption("Evidence points to the uploaded file; it does not verify the official source or latest corrigenda.")

    _saved_values = _import_meta.get("values", {})
    if _saved_values and st.button("Re-apply reviewed Copilot values to tender fields", key="bidfit_reapply_copilot_values"):
        _apply_reviewed_prefill({
            "values": _saved_values,
            "source_filename": _import_meta.get("source_filename", "uploaded tender file"),
            "field_details": _import_meta.get("field_details", {}),
            "official_source_url": "",
        })
        st.rerun()

with st.expander("Important assumptions and limitations", expanded=False):
    st.markdown(
        "- A **Potential Bid** means the entered information looks suitable for further review; it does not mean the company will win.\n"
        "- **No-Bid** is issued only when a listed hard blocker is present and the profile, requirements, and official source are confirmed.\n"
        "- Capability matching is simple text overlap. Synonyms, equivalent qualifications, consortium arrangements, and tender-specific legal nuances require human review.\n"
        "- Tender value is not treated as company profit. Profitability analysis is not included in this milestone.\n"
        "- Use the exact full INR amount in turnover and EMD fields. Do not mix rupees with lakhs/crores."
    )


def parse_optional_float(raw: str, label: str) -> tuple[float | None, str | None]:
    if not raw.strip():
        return None, None
    try:
        value = float(raw.replace(",", "").strip())
    except ValueError:
        return None, f"{label} must be numeric or left blank."
    if value < 0:
        return None, f"{label} cannot be negative."
    return value, None


def parse_optional_int(raw: str, label: str) -> tuple[int | None, str | None]:
    value, error = parse_optional_float(raw, label)
    if error or value is None:
        return None, error
    if not value.is_integer():
        return None, f"{label} must be a whole number."
    return int(value), None


def parse_list(raw: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;\n]", raw) if part.strip()]


def valid_url(raw: str) -> bool:
    parsed = urlparse(raw.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

st.subheader("A. Company profile")
c1, c2 = st.columns(2)
with c1:
    company_name = st.text_input("Company / supplier name", placeholder="e.g. ABC Technologies", key="bidfit_profile_company_name", on_change=_save_form_value, args=("bidfit_profile_company_name",))
    company_capabilities_raw = st.text_area("Capabilities / products / services (comma-separated)", placeholder="e.g. computer supply, network installation, IT maintenance", height=90, key="bidfit_profile_capabilities", on_change=_save_form_value, args=("bidfit_profile_capabilities",))
    company_regions_raw = st.text_input("Service regions (comma-separated)", placeholder="e.g. Assam, Meghalaya or Pan-India", key="bidfit_profile_regions", on_change=_save_form_value, args=("bidfit_profile_regions",))
    annual_turnover_raw = st.text_input("Annual turnover (INR, full rupee amount)", placeholder="e.g. 25000000", key="bidfit_profile_turnover", on_change=_save_form_value, args=("bidfit_profile_turnover",))
with c2:
    years_relevant_experience_raw = st.text_input("Years of relevant experience in this domain", placeholder="e.g. 8", key="bidfit_profile_experience", on_change=_save_form_value, args=("bidfit_profile_experience",))
    similar_projects_raw = st.text_input("Number of similar completed projects", placeholder="e.g. 5", key="bidfit_profile_projects", on_change=_save_form_value, args=("bidfit_profile_projects",))
    certifications_raw = st.text_area("Company certifications / registrations", placeholder="e.g. GST registration, ISO 9001 (comma-separated)", height=90, key="bidfit_profile_certifications", on_change=_save_form_value, args=("bidfit_profile_certifications",))
    emd_capacity_raw = st.text_input("Available EMD support capacity (INR)", placeholder="Cash / bank guarantee / approved limits; e.g. 500000", key="bidfit_profile_emd_capacity", on_change=_save_form_value, args=("bidfit_profile_emd_capacity",))
profile_confirmed = st.checkbox("I confirm the company information above is complete and accurate to my knowledge.", key="bidfit_profile_confirmed", on_change=_save_form_value, args=("bidfit_profile_confirmed",))

st.divider()
st.subheader("B. Tender requirements")
tender_title = st.text_input("Tender title *", placeholder="Exact title from the tender notice", key="bidfit_tender_title", on_change=_save_form_value, args=("bidfit_tender_title",))
tender_capabilities_raw = st.text_area("Required capability / scope keywords", placeholder="e.g. computer supply, installation, warranty", height=80, key="bidfit_tender_capabilities_raw", on_change=_save_form_value, args=("bidfit_tender_capabilities_raw",))
t1, t2 = st.columns(2)
with t1:
    target_region = st.text_input("Tender delivery / work region", placeholder="e.g. Assam", key="bidfit_target_region", on_change=_save_form_value, args=("bidfit_target_region",))
    min_years_raw = st.text_input("Minimum experience years, if specified", placeholder="leave blank if not applicable / not stated", key="bidfit_min_years_raw", on_change=_save_form_value, args=("bidfit_min_years_raw",))
    min_projects_raw = st.text_input("Minimum similar projects, if specified", placeholder="leave blank if not applicable / not stated", key="bidfit_min_projects_raw", on_change=_save_form_value, args=("bidfit_min_projects_raw",))
    min_turnover_raw = st.text_input("Minimum annual turnover in INR, if specified", placeholder="e.g. 10000000", key="bidfit_min_turnover_raw", on_change=_save_form_value, args=("bidfit_min_turnover_raw",))
with t2:
    required_certifications_raw = st.text_area("Mandatory certifications / registrations", placeholder="e.g. GST registration", height=78, key="bidfit_required_certifications_raw", on_change=_save_form_value, args=("bidfit_required_certifications_raw",))
    emd_required_raw = st.text_input("Required EMD in INR, if specified", placeholder="e.g. 250000", key="bidfit_emd_required_raw", on_change=_save_form_value, args=("bidfit_emd_required_raw",))
    source_url = st.text_input("Official tender source URL *", placeholder="https://...", key="bidfit_source_url", on_change=_save_form_value, args=("bidfit_source_url",))
    closing_date_known = st.checkbox("Closing date is stated in the official notice", key="bidfit_closing_date_known", on_change=_save_form_value, args=("bidfit_closing_date_known",))
    closing_date = st.date_input("Closing date", disabled=not closing_date_known, key="bidfit_closing_date", on_change=_save_form_value, args=("bidfit_closing_date",))
requirements_reviewed = st.checkbox("I checked the tender documents and entered all known mandatory eligibility requirements.", key="bidfit_requirements_reviewed", on_change=_save_form_value, args=("bidfit_requirements_reviewed",))
official_source_checked = st.checkbox("I checked the official tender page recently for current status / deadline / corrigenda.", key="bidfit_official_source_checked", on_change=_save_form_value, args=("bidfit_official_source_checked",))

if st.button("Evaluate Bid-Fit", type="primary", key="evaluate_bidfit"):
    errors: list[str] = []
    annual_turnover, e = parse_optional_float(annual_turnover_raw, "Annual turnover")
    if e: errors.append(e)
    emd_capacity, e = parse_optional_float(emd_capacity_raw, "EMD support capacity")
    if e: errors.append(e)
    years, e = parse_optional_int(years_relevant_experience_raw, "Years in business")
    if e: errors.append(e)
    projects, e = parse_optional_int(similar_projects_raw, "Similar projects")
    if e: errors.append(e)
    min_years, e = parse_optional_int(min_years_raw, "Minimum experience years")
    if e: errors.append(e)
    min_projects, e = parse_optional_int(min_projects_raw, "Minimum similar projects")
    if e: errors.append(e)
    min_turnover, e = parse_optional_float(min_turnover_raw, "Minimum annual turnover")
    if e: errors.append(e)
    emd_required, e = parse_optional_float(emd_required_raw, "Required EMD")
    if e: errors.append(e)

    if not tender_title.strip():
        errors.append("Tender title is required.")
    if not source_url.strip() or not valid_url(source_url):
        errors.append("Enter a valid official source URL starting with http:// or https://.")
    if any(v is not None and v < 0 for v in (years, projects, min_years, min_projects)):
        errors.append("Experience years and project counts cannot be negative.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        company = CompanyProfile(
            name=company_name.strip(),
            capabilities=parse_list(company_capabilities_raw),
            service_regions=parse_list(company_regions_raw),
            years_relevant_experience=years,
            similar_projects_completed=projects,
            annual_turnover_inr=annual_turnover,
            emd_support_capacity_inr=emd_capacity,
            certifications=parse_list(certifications_raw),
            profile_confirmed=profile_confirmed,
        )
        tender = TenderRequirements(
            title=tender_title.strip(),
            required_capabilities=parse_list(tender_capabilities_raw),
            target_region=target_region.strip(),
            min_years_experience=min_years,
            min_similar_projects=min_projects,
            min_annual_turnover_inr=min_turnover,
            required_certifications=parse_list(required_certifications_raw),
            emd_required_inr=emd_required,
            closing_date=closing_date if closing_date_known else None,
            official_source_url=source_url.strip(),
            requirements_reviewed=requirements_reviewed,
            official_source_checked=official_source_checked,
        )
        result = evaluate_bid_fit(company, tender)
        st.session_state["last_bid_fit_result"] = result.to_dict()
        st.session_state["last_bid_fit_title"] = tender.title

result_data = st.session_state.get("last_bid_fit_result")
if result_data:
    st.divider()
    st.subheader(f"Saved result: {st.session_state.get('last_bid_fit_title', 'Tender')}")
    st.caption("This result is retained across page navigation in the current session. Editing an input clears it as stale.")
    recommendation = result_data["recommendation"]
    if recommendation == "POTENTIAL BID":
        st.success("POTENTIAL BID — requirements appear suitable for further commercial and legal review.")
    elif recommendation == "NO-BID":
        st.error("NO-BID — a confirmed blocking criterion is present in the entered information.")
    else:
        st.warning("MANUAL REVIEW — verify the items below before making a decision.")

    score = result_data["fit_score"]
    if score is not None:
        st.metric("Rule-based fit score", f"{score:.1f}/100")
        st.caption("This score measures only the criteria entered into this form. It is not a probability of winning a tender.")
    else:
        st.info("No fit score could be calculated because no comparable criterion was supplied.")
    if result_data["hard_fail_reasons"]:
        st.markdown("**Potential blocking criteria**")
        for item in result_data["hard_fail_reasons"]:
            st.error(item)
    if result_data["review_reasons"]:
        st.markdown("**Items needing confirmation**")
        for item in result_data["review_reasons"]:
            st.warning(item)
    if result_data["factors"]:
        st.markdown("**Criterion-by-criterion breakdown**")
        st.dataframe(pd.DataFrame(result_data["factors"]), width="stretch", hide_index=True)
    with st.expander("Warnings and limitations", expanded=False):
        for item in result_data["warnings"]:
            st.write(f"- {item}")
    st.download_button("Download this evaluation as JSON", data=json.dumps(result_data, indent=2, ensure_ascii=False), file_name="bid_fit_evaluation.json", mime="application/json")

st.caption("Prototype only. Verify every mandatory term and the latest corrigendum on the official tender source before acting.")
