"""Source-backed enrichment and review flags for tender extraction.

This module deliberately does not decide legal eligibility. It marks document
patterns that deserve human attention, and every finding carries its source page
and supporting quotation. It works with both Gemini and offline extractor output.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Iterable


def _text(page: dict[str, Any]) -> str:
    return " ".join(str(page.get("text", "") or "").replace("\x00", " ").split())


def _page_no(page: dict[str, Any], fallback: int) -> int:
    try:
        return int(page.get("page_number", fallback))
    except (TypeError, ValueError):
        return fallback


def _pages(pages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned = []
    for i, page in enumerate(pages, start=1):
        text = _text(page)
        if text:
            cleaned.append({
                "page_number": _page_no(page, i),
                "text": text,
                "layout_text": str(page.get("layout_text", "") or ""),
            })
    return cleaned


def _snippet(text: str, start: int, end: int, before: int = 90, after: int = 170) -> str:
    left = max(0, start - before)
    right = min(len(text), max(end, start + 1) + after)
    value = text[left:right].strip()
    if left:
        value = "…" + value
    if right < len(text):
        value += "…"
    return value


def _find_first(pages: list[dict[str, Any]], pattern: re.Pattern[str]) -> tuple[dict[str, Any], re.Match[str]] | None:
    for page in pages:
        match = pattern.search(page["text"])
        if match:
            return page, match
    return None


def _field_default() -> dict[str, Any]:
    return {
        "value": "",
        "page_number": None,
        "page_numbers": [],
        "evidence": "",
        "status": "Not confidently extracted — inspect the official document",
    }


def _apply_portal_deadline_status(pages: list[dict[str, Any]], fields: dict[str, dict[str, Any]]) -> None:
    """Distinguish an explicitly portal-delegated deadline from a generic miss."""
    current = fields.get("closing_date")
    if not isinstance(current, dict):
        return

    portal_pattern = re.compile(
        r"\b(?:bid\s+closing\s+date(?:\s*&\s*time)?|bid\s+submission\s+(?:end\s+)?date(?:\s*&\s*time)?)\b"
        r".{0,150}?\b(?:as\s+mentioned|as\s+specified|as\s+indicated|refer\s+to|will\s+be\s+available)\b"
        r".{0,100}?\b(?:online\s+)?e[- ]?tender\s+portal\b",
        re.I,
    )
    found = _find_first(pages, portal_pattern)
    if not found:
        return

    page, match = found
    # If a dated deadline is explicitly present elsewhere, preserve the model/rule result.
    dated_deadline = re.compile(
        r"\b(?:bid\s+submission\s+(?:end|closing)\s+date|bid\s+closing\s+date|"
        r"bid\s+submission\s+deadline|submission\s+deadline|closing\s+date|"
        r"last\s+date\s+for\s+(?:bid\s+)?submission)\b"
        r".{0,60}?\b\d{1,2}(?:\s+|[-/])(?:\d{1,2}|[A-Za-z]{3,9})(?:\s+|[-/])\d{4}\b",
        re.I,
    )
    if any(dated_deadline.search(item["text"]) for item in pages):
        return

    previous_value = str(current.get("value", "") or "").strip()
    previous_evidence = str(current.get("evidence", "") or "").strip()
    number = page["page_number"]
    current.update({
        "value": "",
        "page_number": number,
        "page_numbers": [number],
        "evidence": _snippet(page["text"], match.start(), match.end()),
        "status": (
            "Not stated in supplied document — portal lookup required; unsupported candidate cleared"
            if previous_value else "Not stated in supplied document — portal lookup required"
        ),
        "source_location": f"Page {number}",
        "source_locations": [f"Page {number}"],
    })
    if previous_value:
        current["suppressed_candidate"] = previous_value
        current["suppressed_candidate_evidence"] = previous_evidence


def _certification_matches(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gather common certificate/approval/report phrases from actual requirement context."""
    patterns = [
        ("ATEX/IECEx certification", re.compile(r"\bATEX\s*/\s*IECEx\s+Certification\b", re.I)),
        ("ATEX Certificate", re.compile(r"\bATEX\s+Certificate\b", re.I)),
        ("IECEx certification", re.compile(r"\bIECEx\s+Certification\b", re.I)),
        ("PESO/CCOE approval", re.compile(r"\bPESO\s*/\s*CCOE\s+approval\b", re.I)),
        ("Calibration report", re.compile(r"\bCalibration\s+Report\b", re.I)),
        ("Calibration certificate", re.compile(r"\bCalibration\s+Certificate\b", re.I)),
        ("Digital Signature Certificate (DSC)", re.compile(r"\bDigital\s+Signature\s+Certificate\s*\(\s*DSC\s*\)", re.I)),
    ]
    collected: list[dict[str, Any]] = []
    for page in pages:
        text = page["text"]
        for label, pattern in patterns:
            for match in pattern.finditer(text):
                # Keep only terms which occur in requirement-like context, a datasheet,
                # BEC/eligibility clause, or an explicit submission checklist.
                context = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
                context_lower = context.lower()
                if not any(term in context_lower for term in (
                    "required", "must submit", "must possess", "bidder must", "documents to be submitted", "along with", "certificate",
                )):
                    continue
                collected.append({
                    "label": label,
                    "page_number": page["page_number"],
                    "quote": _snippet(text, match.start(), match.end(), before=45, after=75),
                    "start": match.start(),
                })

    # Prefer the explicit datasheet formulation where available; otherwise preserve
    # the wording found in BEC/checklists. Never imply that ATEX and IECEx are both
    # mandatory unless the source literally states the combined requirement.
    has_combined_atex_iecex = any(x["label"] == "ATEX/IECEx certification" for x in collected)
    if has_combined_atex_iecex:
        # Normalize the display label but keep every source occurrence, including
        # the separate BEC mention of an ATEX Certificate on page 34.
        collected = [
            {**x, "label": "ATEX/IECEx certification"}
            if x["label"] in {"ATEX Certificate", "IECEx certification"} else x
            for x in collected
        ]
    # Calibration Report and Calibration Certificate are separate source wordings
    # for the same document family; retain both quotations but show one review label.
    has_calibration = any(x["label"] in {"Calibration report", "Calibration certificate"} for x in collected)
    if has_calibration:
        collected = [
            {**x, "label": "Calibration report/certificate"}
            if x["label"] in {"Calibration report", "Calibration certificate"} else x
            for x in collected
        ]
    seen: set[tuple[str, int, str]] = set()
    result = []
    for item in collected:
        key = (item["label"].casefold(), item["page_number"], item["quote"].casefold())
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _enrich_certifications(pages: list[dict[str, Any]], fields: dict[str, dict[str, Any]]) -> None:
    matches = _certification_matches(pages)
    if not matches:
        return

    labels: list[str] = []
    for item in matches:
        if item["label"] not in labels:
            labels.append(item["label"])
    label_order = {
        "ATEX/IECEx certification": 0,
        "ATEX Certificate": 0,
        "IECEx certification": 0,
        "PESO/CCOE approval": 1,
        "Calibration report/certificate": 2,
        "Digital Signature Certificate (DSC)": 3,
        "Calibration report": 2,
        "Calibration certificate": 2,
    }
    labels.sort(key=lambda label: label_order.get(label, 99))
    field = fields.get("required_certifications")
    if not isinstance(field, dict):
        field = _field_default()
        fields["required_certifications"] = field

    # Keep any additional valid model candidates but deduplicate them against the
    # source-derived list. The explicit phrases are still shown in evidence below.
    existing = str(field.get("value", "") or "").strip()
    merged_labels = list(labels)
    if existing:
        for item in re.split(r"[;,\n]+", existing):
            item = item.strip()
            normalized = item.casefold()
            covered_by_source_candidate = (
                ("atex certificate" in normalized and any("atex/iecex certification" in x.casefold() for x in merged_labels))
                or ("iecex certification" in normalized and any("atex/iecex certification" in x.casefold() for x in merged_labels))
                or ("calibration report" in normalized or "calibration certificate" in normalized)
                and any("calibration report/certificate" in x.casefold() for x in merged_labels)
                or ("peso/ccoe approval" in normalized and any("peso/ccoe approval" in x.casefold() for x in merged_labels))
            )
            if item and not covered_by_source_candidate and not any(item.casefold() in label.casefold() or label.casefold() in item.casefold() for label in merged_labels):
                merged_labels.append(item)

    page_numbers = sorted({int(item["page_number"]) for item in matches})
    evidence_lines = []
    for item in matches:
        line = f"Page {item['page_number']}: {item['quote']}"
        if line not in evidence_lines:
            evidence_lines.append(line)
    field.update({
        "value": "; ".join(merged_labels),
        "page_number": page_numbers[0] if page_numbers else field.get("page_number"),
        "page_numbers": page_numbers,
        "evidence": "\n".join(evidence_lines),
        "status": "Source-backed candidates merged across BEC, submission checklist and datasheets — verify applicability and submission stage",
        "source_location": "; ".join(f"Page {n}" for n in page_numbers),
        "source_locations": [f"Page {n}" for n in page_numbers],
        "source_supplemented": True,
    })


def enrich_tender_fields(pages: list[dict[str, Any]], fields: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Apply evidence-only cross-checks common to Gemini and offline extraction."""
    cleaned = _pages(pages)
    result = deepcopy(fields)
    _apply_portal_deadline_status(cleaned, result)
    _enrich_certifications(cleaned, result)

    # Re-apply high-risk, multi-value/contradiction checks after Gemini/local merge.
    # A single scalar field must never collapse a work-wise schedule or a conflict.
    from app.tender_answer_engine import answer_common_tender_question

    turnover_answer = answer_common_tender_question("minimum annual turnover", cleaned)
    if turnover_answer and "no explicit minimum annual turnover amount was found" in turnover_answer.answer.casefold():
        field = result.get("min_annual_turnover_inr")
        if isinstance(field, dict):
            field.update({
                "value": "",
                "page_number": turnover_answer.page_number,
                "page_numbers": [turnover_answer.page_number],
                "evidence": turnover_answer.evidence,
                "status": "No numeric minimum annual turnover threshold located in readable text — check schedules/annexures and corrigenda",
                "source_location": turnover_answer.source_location,
                "source_locations": [turnover_answer.source_location],
            })

    emd_answer = answer_common_tender_question("EMD amount", cleaned)
    if emd_answer and ";" in emd_answer.raw_value:
        field = result.get("emd_required_inr")
        if isinstance(field, dict):
            field.update({
                "value": "",
                "page_number": emd_answer.page_number,
                "page_numbers": [emd_answer.page_number],
                "evidence": emd_answer.evidence,
                "status": "Work-specific EMD schedule detected — select the work serial; no single amount applies to all packages",
                "source_location": emd_answer.source_location,
                "source_locations": [emd_answer.source_location],
            })

    deadline_answer = answer_common_tender_question("submission deadline", cleaned)
    if deadline_answer and "conflicting submission-date entries" in deadline_answer.answer.casefold():
        field = result.get("closing_date")
        if isinstance(field, dict):
            conflict_pages = sorted({int(value) for value in re.findall(r"PDF page (\d+)", deadline_answer.raw_value)})
            field.update({
                "value": "",
                "page_number": deadline_answer.page_number,
                "page_numbers": conflict_pages or [deadline_answer.page_number],
                "evidence": deadline_answer.evidence,
                "status": "Conflicting submission-date entries — verify official portal/corrigendum; no date selected",
                "source_location": deadline_answer.source_location,
                "source_locations": [f"PDF page {n}" for n in (conflict_pages or [deadline_answer.page_number])],
            })

    # In a package-level NIT, the first page may list many unrelated works. Do not
    # invent one delivery location or scope and carry it into a company Bid-Fit score.
    multi_work_page = next((page for page in cleaned if re.search(
        r"detailed\s+tender\s+call\s+notice\s+for\s+the\s+works|works\s+as\s+detailed\s+in\s+table\s+below",
        page["text"], re.I,
    )), None)
    if multi_work_page:
        for field_name, message in (
            ("target_region", "Multiple work sites are listed — select the work serial before confirming the delivery/work location"),
            ("required_capabilities", "Multiple different work scopes are listed — select the work serial before transferring scope keywords to Bid-Fit"),
        ):
            field = result.get(field_name)
            if isinstance(field, dict) and not str(field.get("value", "") or "").strip():
                field["status"] = message
                field["page_number"] = multi_work_page["page_number"]
                field["page_numbers"] = [multi_work_page["page_number"]]
                field["source_location"] = f"Page {multi_work_page['page_number']}"
                field["source_locations"] = [f"Page {multi_work_page['page_number']}"]
                field["evidence"] = _snippet(multi_work_page["text"], 0, min(len(multi_work_page["text"]), 500))

    route_heading_patterns = (
        r"single\s+P\.?O\.?\s+Quantity",
        r"two\s+similar\s+completed\s+P\.?O\.?(?:\s+each)?",
        r"three\s+similar\s+completed\s+P\.?O\.?(?:\s+each)?",
    )
    route_page = next((
        page for page in cleaned
        if all(re.search(term, page["text"], re.I) for term in route_heading_patterns)
        and re.search(r"pressure\s+transmitter.{0,180}?\b25\s+20\s+12\s+10\b", page["text"], re.I)
        and re.search(r"temperature\s+transmitter.{0,180}?\b5\s+4\s+2\s+1\b", page["text"], re.I)
    ), None)
    if route_page:
        page_numbers = [route_page["page_number"]]
        route_evidence = ""
        heading_match = re.search(r"single\s+P\.?O\.?\s+Quantity", route_page["text"], re.I)
        pressure_match = re.search(r"pressure\s+transmitter.{0,180}?\b25\s+20\s+12\s+10\b", route_page["text"], re.I)
        temperature_match = re.search(r"temperature\s+transmitter.{0,180}?\b5\s+4\s+2\s+1\b", route_page["text"], re.I)
        table_match = heading_match or pressure_match or temperature_match
        if table_match:
            route_evidence = _snippet(route_page["text"], table_match.start(), table_match.end(), before=210, after=470)
        explicit_min_years_patterns = (
            re.compile(r"\bminimum(?:\s+of)?\s+\d+\s+years?\s+(?:of\s+)?(?:(?:relevant|professional|industry|business|company)\s+)?experience\b", re.I),
            re.compile(r"\b(?:minimum|at\s+least|not\s+less\s+than)\s+experience\s+(?:of\s+)?\d+\s+years?\b", re.I),
        )
        has_explicit_minimum_years = any(
            pattern.search(page["text"])
            for page in cleaned
            for pattern in explicit_min_years_patterns
        )
        for field_name, status, clear_value in (
            ("min_similar_projects", "Multi-route PO/quantity criteria found — the scalar candidate was cleared because no single project count represents the alternative routes; inspect Tender review flags", True),
            ("min_years_experience", "No separate minimum company/business-experience duration identified. The 'last 3 years' phrase is a supply-order lookback, not company age; verify the BEC's 03-year/05-year wording", not has_explicit_minimum_years),
        ):
            field = result.get(field_name)
            if isinstance(field, dict):
                previous_value = str(field.get("value", "") or "").strip()
                if clear_value and previous_value:
                    field["suppressed_candidate"] = previous_value
                    field["suppressed_candidate_evidence"] = str(field.get("evidence", "") or "")
                    field["value"] = ""
                field["status"] = status if clear_value else str(field.get("status", "Candidate extracted — verify"))
                field["page_numbers"] = page_numbers or field.get("page_numbers", [])
                field["page_number"] = page_numbers[0] if page_numbers else field.get("page_number")
                field["source_location"] = "; ".join(f"Page {n}" for n in page_numbers)
                field["source_locations"] = [f"Page {n}" for n in page_numbers]
                if route_evidence:
                    field["evidence"] = route_evidence
    # Generic EPC/works tenders sometimes offer alternatives (e.g. 3 OR 2 OR 1
    # completed similar works, each subject to a different minimum value). A flat
    # scalar extractor can incorrectly retain the final "one similar work" route.
    # Suppress that scalar when multiple distinct routes are explicitly present.
    alternative_route_page = None
    alternative_route_evidence = ""
    for page in cleaned:
        text = page["text"]
        route_matches = list(re.finditer(
            r"\b(?P<count>one|two|three|four|\d+)\s+(?:similar\s+)?completed\s+works?\b",
            text, re.I,
        ))
        distinct_counts = {match.group("count").casefold() for match in route_matches}
        if len(distinct_counts) >= 2 and len(re.findall(r"\bor\b", text, re.I)) >= 1:
            # Require cost/amount wording nearby so ordinary prose listing several works
            # is not mistaken for alternative qualification routes.
            if re.search(r"(?:each\s+costing|costing\s+not\s+less|similar\s+completed\s+work).{0,120}(?:Rs\.?|₹|INR|=\s*\d)", text, re.I):
                alternative_route_page = page
                match = route_matches[0]
                alternative_route_evidence = _snippet(text, match.start(), match.end(), before=80, after=620)
                break
    if alternative_route_page:
        field = result.get("min_similar_projects")
        if isinstance(field, dict):
            previous_value = str(field.get("value", "") or "").strip()
            if previous_value:
                field["suppressed_candidate"] = previous_value
                field["suppressed_candidate_evidence"] = str(field.get("evidence", "") or "")
            field["value"] = ""
            page_number = int(alternative_route_page["page_number"])
            field["page_number"] = page_number
            field["page_numbers"] = [page_number]
            field["source_location"] = f"PDF page {page_number}"
            field["source_locations"] = [f"PDF page {page_number}"]
            field["evidence"] = alternative_route_evidence
            field["status"] = (
                "Multiple alternative similar-work routes detected — the single project-count field was cleared; "
                "review the full qualification clause and required values"
            )
    return result


def build_tender_review_findings(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flag high-value document structure/consistency issues without resolving them."""
    cleaned = _pages(pages)
    findings: list[dict[str, Any]] = []

    def add(title: str, severity: str, details: str, action: str, evidence_items: list[tuple[int, str]]) -> None:
        # De-duplicate exact same evidence lines, preserving order.
        evidence_lines: list[str] = []
        source_pages: list[int] = []
        for number, quote in evidence_items:
            if number not in source_pages:
                source_pages.append(number)
            line = f"Page {number}: {quote}"
            if line not in evidence_lines:
                evidence_lines.append(line)
        if not evidence_lines:
            return
        findings.append({
            "title": title,
            "severity": severity,
            "details": details,
            "recommended_action": action,
            "source_locations": [f"Page {n}" for n in source_pages],
            "page_numbers": source_pages,
            "evidence": "\n".join(evidence_lines),
        })

    # State-neutral checks powered by the local answer engine. These reuse the
    # same full-document clauses shown to the user in Q&A and do not call Gemini.
    from app.tender_answer_engine import answer_common_tender_question

    deadline_answer = answer_common_tender_question("submission deadline", cleaned)
    if deadline_answer and "conflicting submission-date entries" in deadline_answer.answer.casefold():
        add(
            "Conflicting bid submission date entries",
            "Critical review",
            deadline_answer.answer,
            "Do not rely on either date until the live tender portal and latest corrigendum/addendum are checked. Record the verified portal date and timestamp separately.",
            [(deadline_answer.page_number, deadline_answer.evidence)],
        )

    emd_answer = answer_common_tender_question("EMD amount", cleaned)
    if emd_answer and ";" in emd_answer.raw_value:
        add(
            "EMD varies by work package",
            "High",
            "The tender's schedule contains different EMD amounts for different work serial numbers. A single EMD value would be misleading.",
            "Ask the bidder to identify the selected work serial number and verify that row's EMD against the original schedule before transferring it into Bid-Fit.",
            [(emd_answer.page_number, emd_answer.evidence)],
        )

    joint_venture_answer = answer_common_tender_question("which works require a joint venture", cleaned)
    if joint_venture_answer:
        add(
            "Joint Venture requirement applies only to specified work serials",
            "High",
            joint_venture_answer.answer,
            "Confirm the selected work serial number and check the applicable JV/electrical/PH contractor agreement schedule before assessing eligibility.",
            [(joint_venture_answer.page_number, joint_venture_answer.evidence)],
        )

    # 1) Closing deadline is intentionally delegated to the tender portal.
    portal_pattern = re.compile(
        r"\b(?:bid\s+closing\s+date(?:\s*&\s*time)?|bid\s+submission\s+(?:end\s+)?date(?:\s*&\s*time)?)\b"
        r".{0,150}?\b(?:as\s+mentioned|as\s+specified|as\s+indicated|refer\s+to|will\s+be\s+available)\b"
        r".{0,100}?\b(?:online\s+)?e[- ]?tender\s+portal\b",
        re.I,
    )
    portal = _find_first(cleaned, portal_pattern)
    if portal:
        page, match = portal
        explicit_date_pattern = re.compile(
            r"\b(?:bid\s+submission\s+(?:end|closing)\s+date|bid\s+closing\s+date|"
            r"bid\s+submission\s+deadline|submission\s+deadline|closing\s+date|"
            r"last\s+date\s+for\s+(?:bid\s+)?submission)\b.{0,65}?"
            r"\b\d{1,2}(?:\s+|[-/])(?:\d{1,2}|[A-Za-z]{3,9})(?:\s+|[-/])\d{4}\b",
            re.I,
        )
        if not any(explicit_date_pattern.search(p["text"]) for p in cleaned):
            add(
                "Closing deadline is not stated in this PDF",
                "Deadline",
                "The document points to the online e-tender portal rather than supplying an exact closing date/time. Do not populate a guessed date.",
                "Check the live official portal and latest corrigenda/addenda; record the checked timestamp and official URL separately.",
                [(page["page_number"], _snippet(page["text"], match.start(), match.end()))],
            )

    # 2) Eligibility uses different quantity routes for each item; a scalar count is misleading.
    route_heading_patterns = (
        r"single\s+P\.?O\.?\s+Quantity",
        r"two\s+similar\s+completed\s+P\.?O\.?(?:\s+each)?",
        r"three\s+similar\s+completed\s+P\.?O\.?(?:\s+each)?",
    )
    route_page = next((
        page for page in cleaned
        if all(re.search(term, page["text"], re.I) for term in route_heading_patterns)
        and re.search(r"pressure\s+transmitter.{0,180}?\b25\s+20\s+12\s+10\b", page["text"], re.I)
        and re.search(r"temperature\s+transmitter.{0,180}?\b5\s+4\s+2\s+1\b", page["text"], re.I)
    ), None)
    if route_page:
        evidence = []
        pressure = re.search(r"pressure\s+transmitter.{0,180}?\b25\s+20\s+12\s+10\b", route_page["text"], re.I)
        temperature = re.search(r"temperature\s+transmitter.{0,180}?\b5\s+4\s+2\s+1\b", route_page["text"], re.I)
        if pressure:
            evidence.append((route_page["page_number"], _snippet(route_page["text"], pressure.start(), pressure.end())))
        if temperature:
            evidence.append((route_page["page_number"], _snippet(route_page["text"], temperature.start(), temperature.end())))
        criteria_page = _find_first(cleaned, re.compile(r"successfully\s+executed\s+the\s+order\(s\).{0,150}?last\s+3\s+years", re.I))
        if criteria_page:
            page, match = criteria_page
            evidence.append((page["page_number"], _snippet(page["text"], match.start(), match.end())))
        add(
            "Experience criteria contain alternative PO/quantity routes",
            "High",
            "The BEC does not define one universal minimum number of projects. Pressure Transmitter: one PO for 20 units, or two similar completed POs of 12 units each, or three of 10 each. Temperature Transmitter: one PO for 4 units, or two POs of 2 units each, or three of 1 each. The BEC says the qualifying orders must be for same/higher specifications and completed within the last 3 years reckoned from the original bid closing date; industry and bidder-type conditions also matter.",
            "Keep these routes item-wise in review. Compare the bidder's evidence against a qualifying route; do not convert the table to a single min_similar_projects value. Verify the detailed OEM-versus-dealer rules and the period wording in the complete BEC.",
            evidence,
        )

    # 3) The BEC itself contains both a 05-year phrase and several 03-year instructions.
    lookback_five = _find_first(cleaned, re.compile(r"prescribed\s+period\s+of\s+05\s+years", re.I))
    lookback_three = _find_first(cleaned, re.compile(r"(?:last\s+3\s+years|prescribed\s+period\s+of\s+03\s*\(three\)\s+years|prescribed\s+03\s*\(three\)\s+years)", re.I))
    if lookback_five and lookback_three:
        p5, m5 = lookback_five
        p3, m3 = lookback_three
        add(
            "Experience lookback period contains 05-year and 03-year wording",
            "Critical review",
            "The experience section includes the phrase 'prescribed period of 05 years', but adjacent instructions describe the applicable period as 03 (three) years. The source text does not reconcile these statements.",
            "Do not choose a lookback period automatically. Check the latest official corrigendum or request clarification from AGCL before marking experience eligibility as met.",
            [
                (p5["page_number"], _snippet(p5["text"], m5.start(), m5.end())),
                (p3["page_number"], _snippet(p3["text"], m3.start(), m3.end())),
            ],
        )

    # 4) Annual turnover and net worth are separate hard eligibility conditions.
    net_worth_pattern = re.compile(r"net\s+worth.{0,120}?\bpositive\b.{0,100}?(?:preceding\s+financial|accounting\s+year)", re.I)
    net_worth = _find_first(cleaned, net_worth_pattern)
    if net_worth:
        page, match = net_worth
        add(
            "Positive net worth is a separate eligibility criterion",
            "High",
            "The financial criteria include positive net worth for the preceding financial/accounting year in addition to the annual turnover threshold. Net worth is not one of the current nine Bid-Fit draft fields.",
            "Manually verify the audited balance sheet/eligible accountant certificate and add a separate positive-net-worth check before making a Bid/No-Bid decision.",
            [(page["page_number"], _snippet(page["text"], match.start(), match.end()))],
        )

    # 4) Delivery lead time is a real obligation, but not currently a Bid-Fit score input.
    delivery_pattern = re.compile(r"\bDELIVERY\b.{0,240}?(?:within\s+(?:two|2)\s+months?.{0,100}?(?:receipt\s+of\s+PO|purchase\s+order)|receipt\s+of\s+PO.{0,100}?within\s+(?:two|2)\s+months?)", re.I)
    delivery = _find_first(cleaned, delivery_pattern)
    if delivery:
        page, match = delivery
        add(
            "Delivery lead time should be reviewed against supplier capacity",
            "Operational risk",
            "The order requires delivery within two months of receiving the purchase order by email (the notice also says the delivery schedule will be intimated with the PO). This condition is not currently represented by the simple Bid-Fit eligibility fields.",
            "Check sourcing lead time, OEM availability, logistics and delivery capacity before treating a high capability/eligibility match as bid-ready.",
            [(page["page_number"], _snippet(page["text"], match.start(), match.end()))],
        )

    # 5) Certificate naming and submission stages differ across the BEC/checklist/datasheets.
    cert_matches = _certification_matches(cleaned)
    if any(x["label"] in {"ATEX/IECEx certification", "PESO/CCOE approval", "Calibration report", "Calibration certificate"} for x in cert_matches):
        evidence = []
        for x in cert_matches:
            if x["label"] in {"ATEX/IECEx certification", "PESO/CCOE approval", "Calibration report", "Calibration certificate"}:
                evidence.append((x["page_number"], x["quote"]))
        add(
            "Multiple product compliance documents appear in the datasheets",
            "High",
            "Beyond an ATEX Certificate mention in the BEC/dispatch checklist, the datasheets explicitly mention ATEX/IECEx certification, PESO/CCOE approval and a Calibration Report. Treat these as separate candidates, not one generic certificate.",
            "Review the exact item datasheets and whether each document is required with the technical bid, before dispatch, or at another contract stage. Do not treat an equipment certificate as proof that the bidder itself is authorised.",
            evidence,
        )

    # 6) Main warranty clause says months, datasheets literally say years; preserve, don't fix.
    warranty_general = _find_first(cleaned, re.compile(r"warranty\s+shall\s+remain\s+valid\s+for\s+twelve\s*\(12\)\s*months?.{0,200}?eighteen\s*\(18\)\s*months?.{0,100}?whichever\s+occurs\s+earlier", re.I))
    warranty_datasheets = []
    for page in cleaned:
        match = re.search(r"warranty.{0,100}?18\s+years?\s+from\s+date\s+of\s+receipt.{0,180}?12\s+months?.{0,100}?whichever\s+is\s+earlier", page["text"], re.I)
        if match:
            warranty_datasheets.append((page["page_number"], _snippet(page["text"], match.start(), match.end())))
    if warranty_general and warranty_datasheets:
        page, match = warranty_general
        evidence = [(page["page_number"], _snippet(page["text"], match.start(), match.end()))]
        evidence.extend(warranty_datasheets)
        add(
            "Potential warranty wording inconsistency: months versus years",
            "Critical review",
            "The general warranty clause refers to twelve (12) months after operation or eighteen (18) months after delivery, whichever occurs earlier. The item datasheets literally state '18 years' from receipt and acceptance or 12 months from commissioning. The extractor must not silently change 'years' to 'months'; this may be a drafting error but the source does not resolve it.",
            "Verify against an official corrigendum or written clarification from the procuring entity before relying on the warranty duration or submitting a bid.",
            evidence,
        )

    # 7) Technical unit/value should be verified rather than silently corrected.
    temp_bec = _find_first(cleaned, re.compile(r"temperature\s+transmitter.{0,120}?range\s*:?\s*30\s*PSI", re.I))
    temp_datasheet = _find_first(cleaned, re.compile(r"measurement\s+range\s*[-:]?\s*-?10\s+to\s+100\s+degree\s+C", re.I))
    if temp_bec and temp_datasheet:
        p1, m1 = temp_bec
        p2, m2 = temp_datasheet
        add(
            "Temperature transmitter range wording needs technical confirmation",
            "Technical review",
            "The BEC table describes the Temperature Transmitter range as '30PSI', while the datasheet gives a measurement range of -10 to 100 Degree C. These are not obviously equivalent specifications; this audit flags the wording without deciding which is correct.",
            "Confirm the intended range/unit with the technical specification or official clarification before technical compliance is assessed.",
            [
                (p1["page_number"], _snippet(p1["text"], m1.start(), m1.end())),
                (p2["page_number"], _snippet(p2["text"], m2.start(), m2.end())),
            ],
        )

    # 8) Cover and IFB reference dates are different; flag only when the same base
    # tender identifier appears with different dates in the opening pages.
    opening_pages = [p for p in cleaned if p["page_number"] <= 3]
    reference_records: list[tuple[str, str, int, str]] = []
    ref_pattern = re.compile(
        r"(?:tender\s*/?\s*ifb\s+no\.?|ifb\s+no\.?|tender\s+no\.?|ref\s+no\.?)\s*[:.]?\s*"
        r"(?P<ref>[A-Z0-9&./_-]{6,60}?).{0,75}?\b(?:dtd|dated)\s*[:.]?\s*"
        r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        re.I,
    )
    for page in opening_pages:
        for match in ref_pattern.finditer(page["text"]):
            ref = re.sub(r"/\d{1,3}$", "", match.group("ref").strip(" /"))
            date = match.group("date")
            reference_records.append((ref.casefold(), date, page["page_number"], _snippet(page["text"], match.start(), match.end())))
    different_dates = None
    for i, first in enumerate(reference_records):
        for second in reference_records[i + 1:]:
            if first[0] == second[0] and first[1] != second[1]:
                different_dates = (first, second)
                break
        if different_dates:
            break
    if different_dates:
        first, second = different_dates
        add(
            "Tender reference dates differ across opening pages",
            "Reference check",
            f"Related tender reference text appears with dates {first[1]} and {second[1]} in the opening pages. They may represent different document-reference dates, but the PDF alone does not explain the difference.",
            "Verify the active tender number/date on the official portal and check any corrigendum; do not decide the applicable date from this automated flag alone.",
            [(first[2], first[3]), (second[2], second[3])],
        )

    return findings
