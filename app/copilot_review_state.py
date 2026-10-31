"""Small pure helpers for persisting Copilot draft edits across Streamlit pages."""
from __future__ import annotations

from typing import Mapping, Any

REVIEW_FIELD_NAMES = (
    "tender_title",
    "required_capabilities",
    "target_region",
    "min_years_experience",
    "min_similar_projects",
    "min_annual_turnover_inr",
    "required_certifications",
    "emd_required_inr",
    "closing_date",
)

REVIEW_WIDGET_KEYS = {name: f"copilot_review_widget_{name}" for name in REVIEW_FIELD_NAMES}
REVIEW_CONFIRMATION_WIDGET_KEY = "copilot_review_widget_confirmation"
REVIEW_CONFIRMATION_SAVED_KEY = "copilot_draft_review_confirmation_saved"
REVIEW_VALUES_STATE_KEY = "copilot_bidfit_reviewed_values"


def initial_review_values(field_details: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    """Build the first editable value set from extracted field details."""
    return {
        name: str((field_details.get(name) or {}).get("value", "") or "")
        for name in REVIEW_FIELD_NAMES
    }


def merge_saved_review_values(
    field_details: Mapping[str, Mapping[str, Any]],
    saved_values: Mapping[str, Any] | None,
) -> dict[str, str]:
    """Restore user edits over extraction defaults, preserving intentional blanks."""
    values = initial_review_values(field_details)
    saved_values = saved_values or {}
    for name in REVIEW_FIELD_NAMES:
        if name in saved_values:
            values[name] = str(saved_values[name] or "")
    return values


def update_review_value(
    saved_values: Mapping[str, Any] | None,
    field_name: str,
    value: Any,
) -> dict[str, str]:
    """Return a copied persistence mapping with one field updated."""
    if field_name not in REVIEW_FIELD_NAMES:
        raise KeyError(f"Unknown Copilot review field: {field_name}")
    values = {name: str(item or "") for name, item in (saved_values or {}).items() if name in REVIEW_FIELD_NAMES}
    values[field_name] = str(value or "").strip()
    return values


def collect_widget_values(
    saved_values: Mapping[str, Any] | None,
    widget_values: Mapping[str, Any],
) -> dict[str, str]:
    """Snapshot current widget values while retaining any unchanged saved fields."""
    values = {name: str(value or "") for name, value in (saved_values or {}).items() if name in REVIEW_FIELD_NAMES}
    for name in REVIEW_FIELD_NAMES:
        if name in widget_values:
            values[name] = str(widget_values[name] or "").strip()
        else:
            values.setdefault(name, "")
    return values
