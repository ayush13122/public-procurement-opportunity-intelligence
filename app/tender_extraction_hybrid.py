"""Merge deterministic evidence-backed candidates with optional Gemini extraction."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

_NUMERIC_EVIDENCE_FIELDS = {"min_annual_turnover_inr", "emd_required_inr", "closing_date"}


def _value(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("value", "") or "").strip()


def _has_page_evidence(item: Any) -> bool:
    if not isinstance(item, dict) or not _value(item) or not str(item.get("evidence", "") or "").strip():
        return False
    page_numbers = item.get("page_numbers") or ([item.get("page_number")] if item.get("page_number") else [])
    return any(str(n).strip() for n in page_numbers)


def merge_candidate_fields(
    local_fields: dict[str, dict[str, Any]],
    ai_fields: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Use local extraction as the non-silent baseline; never let empty AI fields erase it.

    For turnover, EMD and closing date, a local candidate wins when it is labelled,
    numeric/date-shaped, and page-evidenced. These are high-risk scalar values where
    a plausible but wrong AI value is more harmful than a reviewable deterministic one.
    Other fields prefer a valid Gemini candidate and use local candidates to fill gaps.
    """
    ai_fields = ai_fields or {}
    all_names = list(dict.fromkeys([*local_fields.keys(), *ai_fields.keys()]))
    merged: dict[str, dict[str, Any]] = {}

    for name in all_names:
        local = deepcopy(local_fields.get(name) or {})
        ai = deepcopy(ai_fields.get(name) or {})
        local_value = _value(local)
        ai_value = _value(ai)
        local_supported = _has_page_evidence(local)
        ai_supported = _has_page_evidence(ai)

        use_local = False
        local_status = str(local.get("status", "") or "")
        # Preserve local safety findings even though their scalar value is blank:
        # multi-work EMD, alternative project-count routes, and conflicting dates
        # must not be overwritten by a plausible-looking Gemini scalar.
        non_scalar_safety_status = any(marker in local_status.casefold() for marker in (
            "work-specific emd schedule",
            "multiple alternative similar-work routes",
            "multi-route po/quantity criteria",
            "conflicting submission-date entries",
            "no numeric minimum annual turnover threshold",
        ))
        if non_scalar_safety_status:
            use_local = True
        elif local_supported and local_value and not ai_supported:
            use_local = True
        elif name in _NUMERIC_EVIDENCE_FIELDS and local_supported and local_value:
            if name == "min_annual_turnover_inr":
                evidence = str(local.get("evidence", "")).casefold()
                use_local = ("turn over" in evidence or "turnover" in evidence) and any(
                    symbol in evidence for symbol in ("rs", "₹", "inr", "crore", " cr")
                )
            elif name == "emd_required_inr":
                evidence = str(local.get("evidence", "")).casefold()
                use_local = any(label in evidence for label in ("emd", "earnest money", "bid security"))
            elif name == "closing_date":
                evidence = str(local.get("evidence", "")).casefold()
                use_local = any(label in evidence for label in (
                    "submission", "closing date", "last date", "bid end", "bid closing"
                )) and local_value.count("-") == 2

        if use_local:
            chosen = local
            if non_scalar_safety_status:
                if ai_value:
                    chosen["ai_candidate_value_for_review"] = ai_value
                # Keep the precise safety status (e.g. work-wise schedule) intact.
            elif ai_value and ai_value != local_value:
                chosen["status"] = "Local labelled candidate — Gemini differed; verify against source"
                chosen["ai_candidate_value_for_review"] = ai_value
            else:
                chosen["status"] = "Local evidence-backed candidate — verify against source"
            chosen["source"] = "rule_based"
        elif ai_supported:
            chosen = ai
            chosen.setdefault("source", "gemini")
        elif local_supported:
            chosen = local
            chosen["status"] = "Local fallback candidate — Gemini value unavailable; verify against source"
            chosen["source"] = "rule_based"
        elif ai:
            chosen = ai
        else:
            chosen = local
        merged[name] = chosen
    return merged


def with_local_fallback_status(fields: dict[str, dict[str, Any]], *, reason: str = "Gemini unavailable") -> dict[str, dict[str, Any]]:
    """Mark local candidates clearly when the provider failed, leaving blanks honest."""
    result = deepcopy(fields)
    for item in result.values():
        if not isinstance(item, dict):
            continue
        if _value(item) and _has_page_evidence(item):
            item["source"] = "rule_based"
            item["status"] = f"Local fallback candidate — {reason}; verify against source"
        elif not _value(item):
            # Preserve specialized status such as portal lookup or multi-route ambiguity.
            previous = str(item.get("status", "") or "")
            if not previous or previous.lower().startswith("not found"):
                item["status"] = "Not found by local rules — verify the whole tender and annexures"
    return result
