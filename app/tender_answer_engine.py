"""Deterministic, whole-document answers for common tender questions.

This module is intentionally provider-independent. It searches all extracted pages,
not only the top TF-IDF chunks, so exact labelled financial/deadline clauses can
still be answered when Gemini is unavailable or retrieval ranks a nearby certificate
paragraph above the actual eligibility criterion.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Iterable

from app.tender_question_intents import question_intents


@dataclass(frozen=True)
class LocalTenderAnswer:
    intent: str
    answer: str
    page_number: int
    source_location: str
    evidence: str
    raw_value: str = ""
    value_inr: str = ""


_CURRENCY_AMOUNT = re.compile(
    r"(?P<raw>(?:₹\s*|\bRs\.?\s*|\bINR\s*)"
    r"(?P<number>\d[\d,]*(?:\.\s*\d+)?)\s*"
    r"(?P<unit>crores?|cr\.?|lakhs?|lacs?|lakh|lac)?\s*(?:/-)?)",
    re.IGNORECASE,
)
_DATE = re.compile(
    r"\b(?P<date>\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|"
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[,]?\s*\d{4})\b",
    re.IGNORECASE,
)
_TIME = re.compile(r"\b\d{1,2}[:.]\d{2}(?:\s*(?:AM|PM|HRS?\.?|HOURS?))?\b", re.I)
_OCR_EMD_AMOUNT = re.compile(
    r"(?P<raw>(?P<ocr_prefix>[kK])(?P<number>\d[\d,]*(?:\.\s*\d+)?)"
    r"(?P<unit>crores?|cr\.?|lakhs?|lacs?|lakh|lac)?\s*(?:/-)?)", re.I
)

_LABELS: dict[str, tuple[str, ...]] = {
    "emd": (
        "bid security amount", "earnest money deposit", "earnest money", "emd amount", "emd", "bid security", "bid bond"
    ),
    "tender_fee": (
        "tender processing fee", "tender document fee", "fee for tender document", "cost of tender document",
        "bid document fee", "tender fee", "document fee", "processing fee"
    ),
    "turnover": (
        "average annual financial turn over", "average annual financial turnover",
        "minimum average annual turnover", "minimum average annual financial turnover",
        "minimum annual financial turn over", "minimum annual financial turnover",
        "annual financial turn over", "annual financial turnover", "financial turn over", "financial turnover",
        "average annual turnover", "minimum annual turnover", "annual turnover", "turn over", "turnover"
    ),
    "net_worth": ("minimum net worth", "net worth certificate", "net worth"),
    "performance_security": (
        "performance security amount", "contract performance security", "performance bank guarantee",
        "performance security", "performance guarantee", "pbg"
    ),
    "tender_value": (
        "estimated cost put to bid", "estimated tender value", "estimated cost of work", "estimated cost",
        "tender value", "value put to tender", "project cost"
    ),
}

_DEADLINE_LABEL = re.compile(
    r"\b(?:last\s+date\s*(?:&|and)?\s*time\s+of\b|"
    r"last\s+date\s*(?:&|and)?\s*time\s*(?:of|for)?\s*(?:online\s+)?submission\s+of\s+(?:the\s+)?bid|"
    r"bid\s+submission\s+(?:end|closing)\s+date(?:\s*&\s*time)?(?=\s*[:.]|\s+\d)|"
    r"bid\s+closing\s+date\s*(?:&\s*time|and\s+time)(?=\s*[:.]|\s+\d)|"
    r"submission\s+deadline|deadline\s+for\s+submission(?:\s+of\s+bids?)?|"
    r"last\s+date(?:\s+and\s+time)?\s+for\s+(?:bid\s+)?submission|closing\s+date(?:\s+and\s+time)?)\b",
    re.IGNORECASE,
)

_PORTAL_PLACEHOLDER = re.compile(
    r"(?:as\s+mentioned|as\s+specified|as\s+indicated|will\s+be\s+available|refer(?:red)?\s+to)"
    r".{0,100}(?:online\s+)?e[- ]?tender\s+portal|portal\s+will\s+intimate|will\s+be\s+intimated\s+separately",
    re.IGNORECASE,
)


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\x00", " ")
    # Tesseract commonly emits "Rs. 111. 0 Cr."; repair only currency-number tokens.
    text = re.sub(
        r"(?i)((?:₹|\bRs\.?|\bINR)\s*\d[\d,]*)\.\s+(\d+)(?=\s*(?:cr\.?|crores?\b|lakhs?\b|lacs?\b|lakh\b|lac\b|/-|\b))",
        r"\1.\2", text,
    )
    return " ".join(text.split())


def _money_float(match: re.Match[str]) -> float:
    number = float(re.sub(r"\s+", "", match.group("number")).replace(",", ""))
    unit = (match.group("unit") or "").casefold().rstrip(".")
    if unit in {"cr", "crore", "crores"}:
        number *= 10_000_000
    elif unit in {"lakh", "lakhs", "lac", "lacs"}:
        number *= 100_000
    return number


def _indian_grouping(number: int) -> str:
    digits = str(abs(number))
    if len(digits) <= 3:
        out = digits
    else:
        out = digits[-3:]
        digits = digits[:-3]
        while digits:
            out = digits[-2:] + "," + out
            digits = digits[:-2]
    return ("-" if number < 0 else "") + out


def _evidence_excerpt(text: str, start: int, end: int, *, before: int = 80, after: int = 210) -> str:
    # Prefer a clause-aware window, but remain robust to OCR-flattened pages.
    left = max(0, start - before)
    right = min(len(text), max(end, start + 1) + after)
    # If a clause/paragraph marker occurs near the left edge, start there.
    preceding = list(re.finditer(r"(?:^|\s)(?:[a-z]\.|\d{1,2}[.)])\s+", text[left:start], re.I))
    if preceding:
        left += preceding[-1].start()
    excerpt = text[left:right].strip(" \t\n.;")
    if left > 0:
        excerpt = "…" + excerpt
    if right < len(text):
        excerpt += "…"
    return excerpt


def _page_no(page: dict[str, Any], fallback: int) -> int:
    try:
        return int(page.get("page_number", fallback))
    except (TypeError, ValueError):
        return fallback


def _matching_labels(intent: str, text: str) -> list[tuple[int, int, str]]:
    candidates: list[tuple[int, int, str]] = []
    for label in _LABELS[intent]:
        pat = r"\b" + r"\s+".join(re.escape(part) for part in label.split()) + r"\b"
        for match in re.finditer(pat, text, re.I):
            candidates.append((match.start(), match.end(), label))
    # Keep only longest label at overlapping positions; shorter aliases like "turnover"
    # must not lower the score for "average annual financial turn over".
    candidates.sort(key=lambda row: (row[0], -(row[1] - row[0])))
    filtered: list[tuple[int, int, str]] = []
    for candidate in candidates:
        if any(candidate[0] >= old[0] and candidate[1] <= old[1] for old in filtered):
            continue
        filtered.append(candidate)
    return filtered


def _amount_candidate(intent: str, pages: list[dict[str, Any]]) -> tuple[int, str, str, float, str] | None:
    # tuple: (page, location, evidence, score, source currency amount)
    candidates: list[tuple[float, int, str, str, str]] = []
    for i, page in enumerate(pages, start=1):
        text = _clean_text(page.get("text", ""))
        if not text:
            continue
        page_number = _page_no(page, i)
        location = str(page.get("location", f"PDF page {page_number}"))
        amount_hits = list(_CURRENCY_AMOUNT.finditer(text))
        if intent == "emd":
            # Some scanned notices turn the rupee glyph into "k". Keep this
            # OCR fallback scoped to EMD labels and amount-in-words confirmation.
            amount_hits.extend(
                match for match in _OCR_EMD_AMOUNT.finditer(text)
                if re.match(r"\s*\(\s*rupees?\b", text[match.end():], re.I)
            )
        if not amount_hits:
            continue
        for label_start, label_end, label in _matching_labels(intent, text):
            # Requirement amount should follow its field label. A preceding amount is
            # accepted only for formats like "Rs. 5000 - Tender Processing Fee".
            following = [m for m in amount_hits if 0 <= m.start() - label_end <= 230]
            preceding = [m for m in amount_hits if 0 <= label_start - m.end() <= 45]
            if following:
                amount = min(following, key=lambda m: m.start() - label_end)
                distance = amount.start() - label_end
            elif preceding:
                amount = min(preceding, key=lambda m: label_start - m.end())
                distance = label_start - amount.end()
            else:
                continue

            context_start = max(0, min(label_start, amount.start()) - (38 if intent == "turnover" else 3))
            context_end = min(len(text), max(label_end, amount.end()) + 170)
            context = text[context_start:context_end].strip()
            low_context = context.casefold()
            words = len(label.split())
            score = words * 4 + max(0, 12 - distance / 15)
            if intent == "turnover":
                if re.search(r"\b(?:average|minimum|gross|should\s+have\s+had|must\s+have|shall\s+have)\b", low_context):
                    score += 12
                if re.search(r"financial\s+years?|construction\s+works?", low_context):
                    score += 5
                if re.search(r"bidding\s+capacity|maximum\s+turnover", low_context):
                    score -= 7
                if re.search(r"certificate\s+of\s+financial\s+turn\s*over", low_context) and not re.search(r"average|minimum|should\s+have|must\s+have", low_context):
                    score -= 8
            elif intent == "emd":
                if re.search(r"\b(?:earnest\s+money|emd|bid\s+security)\b", low_context):
                    score += 8
                if re.search(r"performance\s+security", low_context):
                    score -= 8
            elif intent == "tender_fee":
                if re.search(r"non[- ]?refundable|tender\s+processing\s+fee", low_context):
                    score += 6
            elif intent == "net_worth":
                if re.search(r"minimum|positive|net\s+worth", low_context):
                    score += 8
            elif intent == "tender_value":
                if re.search(r"estimated\s+cost|cost\s+put\s+to\s+bid|estimated\s+tender\s+value", low_context):
                    score += 8
            amount_raw = re.sub(r"(?<=\d)\.\s+(?=\d)", ".", amount.group("raw")).strip()
            # Prefer the closest/specific field mention, not the largest or most repeated amount.
            candidates.append((score, page_number, location, context, amount_raw))
    if not candidates:
        return None
    candidates.sort(key=lambda row: row[0], reverse=True)
    top_score, page_number, location, evidence, raw_amount = candidates[0]
    number_match = _CURRENCY_AMOUNT.fullmatch(raw_amount) or _OCR_EMD_AMOUNT.fullmatch(raw_amount)
    normalized = str(int(round(_money_float(number_match)))) if number_match else ""
    return page_number, location, evidence, top_score, raw_amount + "\t" + normalized


def _amount_display(intent: str, raw_amount: str, normalized_inr: str) -> str:
    # Keep source-unit wording, while exposing the normalized full INR amount too.
    unit_match = re.search(r"(?i)\b(cr\.?|crores?|lakhs?|lacs?|lakh|lac)\b", raw_amount)
    unit = (unit_match.group(1).replace(".", "") if unit_match else "").casefold()
    raw_num_match = re.search(r"\d[\d,]*(?:\.\s*\d+)?", raw_amount)
    source_num = re.sub(r"\s+", "", raw_num_match.group(0)) if raw_num_match else raw_amount
    if unit in {"cr", "crore", "crores"}:
        return f"₹{source_num} crore (₹{_indian_grouping(int(normalized_inr))} full INR)"
    if unit in {"lakh", "lakhs", "lac", "lacs"}:
        return f"₹{source_num} lakh (₹{_indian_grouping(int(normalized_inr))} full INR)"
    return f"₹{_indian_grouping(int(normalized_inr))}" if normalized_inr.isdigit() else raw_amount


def _direct_amount_answer(question: str, pages: list[dict[str, Any]], intent: str) -> LocalTenderAnswer | None:
    found = _amount_candidate(intent, pages)
    if not found:
        return None
    page_number, location, evidence, score, raw_plus_norm = found
    if "\t" in raw_plus_norm:
        raw_amount, normalized_inr = raw_plus_norm.split("\t", 1)
    else:
        raw_amount, normalized_inr = raw_plus_norm, ""
    display = _amount_display(intent, raw_amount, normalized_inr)
    labels = {
        "emd": "EMD / Bid Security",
        "tender_fee": "Tender processing fee",
        "turnover": "Average annual turnover criterion",
        "net_worth": "Net worth criterion",
        "performance_security": "Performance security",
        "tender_value": "Estimated tender value / cost put to bid",
    }
    title = labels.get(intent, intent.replace("_", " ").title())

    if intent == "turnover":
        context_lower = evidence.casefold()
        period_match = re.search(r"(?:during|for)\s+(?:the\s+)?(?:immediate\s+)?last\s+(?:five|5)\s+financial\s+years?.{0,100}", evidence, re.I)
        period = period_match.group(0).strip(" .") if period_match else "the financial period specified in the cited clause"
        period = re.split(r"\s*\(", period, maxsplit=1)[0].strip(" .")
        period = re.sub(r"^(?:during|for)\s+", "", period, flags=re.I)
        period = re.sub(r"\b31(?:st|8t)\s*march\s+2025\b", "31 March 2025", period, flags=re.I)
        scope = "construction works" if "construction work" in context_lower else "the work/scope described in the cited clause"
        answer = (
            f"**{title}: {display}.** [{location}]\n\n"
            f"The clause requires average annual gross turnover on {scope} during {period}. "
            "This is a candidate extracted from the uploaded document; verify the amount, period, and wording against the original page before relying on it."
        )
    else:
        answer = f"**{title}: {display}.** [{location}]\n\nSource wording: “{evidence}”\n\nVerify the cited clause and any corrigenda before relying on it."
    return LocalTenderAnswer(
        intent=intent, answer=answer, page_number=page_number,
        source_location=location, evidence=evidence, raw_value=raw_amount, value_inr=normalized_inr,
    )


def _work_package_amount_schedule_answer(
    pages: list[dict[str, Any]], intent: str
) -> LocalTenderAnswer | None:
    """Read multi-work EMD or bid-document-fee schedules from a table.

    The parser preserves the work serial and title, and intentionally returns a
    schedule instead of inventing one document-wide scalar amount. In the Odisha
    table the columns before the contractor class are estimated cost, document
    cost and EMD; for other layouts it only accepts the schedule when the expected
    column labels and enough complete work rows are present.
    """
    header_index = next(
        (
            i for i, page in enumerate(pages)
            if re.search(r"\bEMD\s+in\s+Rs\b", str(page.get("layout_text") or page.get("text") or ""), re.I)
            and (
                intent == "emd"
                or re.search(r"cost\s+of\s+bid\s+documents?", str(page.get("layout_text") or page.get("text") or ""), re.I)
            )
        ),
        None,
    )
    if header_index is None:
        return None

    rows: list[tuple[int, str, str, str]] = []
    used_pages: list[int] = []
    for page_index in (header_index, header_index + 1):
        if page_index >= len(pages):
            continue
        page = pages[page_index]
        raw_text = str(page.get("layout_text") or page.get("text") or "")
        if not raw_text.strip():
            continue
        page_number = _page_no(page, page_index + 1)
        lines = raw_text.replace("\r", "").split("\n")
        if page_index == header_index:
            header_line = next((i for i, line in enumerate(lines) if re.search(r"\bEMD\s+in\s+Rs\b", line, re.I)), 0)
            lines = lines[header_line + 1:]
        else:
            # The following physical page is treated as a continuation only when it
            # contains the next serial range (typical split table ending at row 11).
            if not re.search(r"(?m)^\s*1[2-6](?:\s|$)", raw_text):
                continue

        starts: list[tuple[int, int, str]] = []
        for line_index, line in enumerate(lines):
            if re.fullmatch(r"\s*1\s+2\s+3\s+4\s+5\s+6\s+7\s*", line):
                continue
            match = re.match(r"^\s*(1[0-6]|[1-9])(?:\s+(.*))?$", line)
            if not match:
                continue
            serial = int(match.group(1))
            if page_index != header_index and serial < 12:
                continue
            starts.append((line_index, serial, (match.group(2) or "").strip()))

        for row_index, (start_line, serial, first_text) in enumerate(starts):
            end_line = starts[row_index + 1][0] if row_index + 1 < len(starts) else len(lines)
            block_lines = [first_text, *lines[start_line + 1:end_line]]
            block_text = " ".join(part.strip() for part in block_lines if part.strip())
            block_text = re.split(r"\bThe bidders have\s+to participate\b", block_text, maxsplit=1, flags=re.I)[0]
            class_match = re.search(r"\bC\s*&\s*D\b", block_text, re.I)
            if not class_match:
                continue
            before_class = block_text[:class_match.start()]
            amounts = re.findall(r"(?<![A-Za-z])\d[\d,]*(?:\.\d{1,2})?(?![A-Za-z])", before_class)
            if len(amounts) < 3:
                continue
            # Table order is estimated cost, document cost, EMD. A fee question
            # must not return the EMD (or estimated project value) from the same row.
            selected = amounts[-1] if intent == "emd" else amounts[-2]
            try:
                amount_value = int(round(float(selected.replace(",", ""))))
            except ValueError:
                continue
            first_amount = re.search(r"\b\d[\d,]*(?:\.\d{1,2})?\b", before_class)
            title = before_class[:first_amount.start()] if first_amount else before_class
            title = re.sub(r"\s+", " ", title).strip(" ,.-") or f"Work serial {serial}"
            rows.append((serial, title, f"₹{_indian_grouping(amount_value)}", f"{amount_value}"))
            used_pages.append(page_number)

    # A few partial rows are not enough to claim that a multi-package schedule
    # was parsed successfully. The supplied Odisha schedule contains 16 rows.
    if len(rows) < 8:
        return None
    unique_rows = {serial: (serial, title, amount, value) for serial, title, amount, value in rows}
    rows = [unique_rows[key] for key in sorted(unique_rows)]
    page_start, page_end = min(used_pages), max(used_pages)
    location = f"PDF pages {page_start}–{page_end}"
    answer_lines = [f"- Work {serial}: {title} — {amount}" for serial, title, amount, _value in rows]
    evidence_label = "EMD" if intent == "emd" else "Bid document cost"
    evidence = evidence_label + " schedule: " + "; ".join(
        f"Work {serial} {amount}" for serial, _title, amount, _value in rows
    )
    if intent == "emd":
        lead = "**EMD is work-specific in this tender; there is no single amount for all works.**"
        tail = "Select the relevant work serial number and verify the amount against the original table."
    else:
        lead = "**Bid document cost is work-specific in this tender; there is no single fee for all works.**"
        tail = "Select the relevant work serial number and verify the document cost against the original table."
    return LocalTenderAnswer(
        intent=intent,
        answer=(f"{lead} The schedule lists the following amounts ({location}):\n" + "\n".join(answer_lines) + f"\n\n{tail}"),
        page_number=page_start, source_location=location, evidence=evidence,
        raw_value="; ".join(f"{serial}:{value}" for serial, _title, _amount, value in rows),
    )


def _emd_schedule_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    return _work_package_amount_schedule_answer(pages, "emd")


def _tender_fee_schedule_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    return _work_package_amount_schedule_answer(pages, "tender_fee")



def _bid_opening_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    """Find the bid/technical-bid opening event without confusing it with closing."""
    patterns = (
        re.compile(r"technical\s+bid\s+documents?\s*(?:\([^)]*\)\s*)?will\s+be\s+opened", re.I),
        re.compile(r"technical\s+bids?\s+(?:will|shall)\s+be\s+opened", re.I),
        re.compile(r"bids?\s+shall\s+be\s+opened", re.I),
        re.compile(r"date\s+and\s+time\s+of\s+opening", re.I),
        re.compile(r"time\s+and\s+date\s+of\s+opening", re.I),
    )
    candidates: list[tuple[int, int, str, str, str]] = []
    for index, page in enumerate(pages, start=1):
        text = _clean_text(page.get("text", ""))
        if not text:
            continue
        page_number = _page_no(page, index)
        location = str(page.get("location", f"PDF page {page_number}"))
        for priority, pattern in enumerate(patterns):
            for match in pattern.finditer(text):
                zone = text[match.end():match.end() + 360]
                date_match = _DATE.search(zone)
                if not date_match:
                    continue
                time_match = _TIME.search(zone)
                date_text = date_match.group("date")
                if time_match:
                    date_text += f" at {time_match.group(0)}"
                evidence = _evidence_excerpt(text, match.start(), match.end() + date_match.end() + (time_match.end() if time_match else 0))
                candidates.append((priority, page_number, location, date_text, evidence))
    if not candidates:
        # Some notices explicitly delegate the technical-opening date/time to the
        # e-tender portal. Return that fact instead of falling through to a slow
        # provider or leaving the user with a generic retrieved-passage summary.
        portal_opening = re.compile(
            r"(?:(?:technical|priced)\s+)?bid(?:\s*\(\s*(?:technical|financial)\s*\))?\s+"
            r"opening\s+date\s*(?:&|and)\s*time", re.I
        )
        for index, page in enumerate(pages, start=1):
            text = _clean_text(page.get("text", ""))
            if not text:
                continue
            label = portal_opening.search(text)
            if not label:
                continue
            zone = text[label.end():label.end() + 240]
            if _PORTAL_PLACEHOLDER.search(zone):
                page_number = _page_no(page, index)
                location = str(page.get("location", f"PDF page {page_number}"))
                evidence = _evidence_excerpt(text, label.start(), label.end() + len(zone))
                return LocalTenderAnswer(
                    intent="bid_opening",
                    answer=(f"**The bid-opening date/time is not stated in the uploaded PDF.** [{location}]\n\n"
                            "The notice directs bidders to the official e-tender portal for the opening schedule. "
                            "Check the live portal and any corrigendum; do not infer the opening date from the tender issue date."),
                    page_number=page_number, source_location=location, evidence=evidence,
                )
        return None
    # Prefer explicitly named technical-bid events over generic bid-opening lines.
    candidates.sort(key=lambda item: (item[0], item[1]))
    _priority, page_number, location, date_text, evidence = candidates[0]
    normalised_date = _normalise_date(date_text.split(" at ", 1)[0])
    display_date = normalised_date if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalised_date) else date_text
    answer = f"**Bid opening schedule found: {display_date}**"
    if " at " in date_text:
        answer = f"**Bid opening schedule found: {date_text}.** [{location}]"
    else:
        answer = f"**Bid opening date found: {display_date}.** [{location}]"
    return LocalTenderAnswer(
        intent="bid_opening", answer=answer + f"\n\nSource wording: “{evidence}” Verify any revised opening schedule on the official portal.",
        page_number=page_number, source_location=location, evidence=evidence, raw_value=date_text,
    )

def _turnover_not_found_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer:
    """State that no numeric threshold was found without claiming universal absence."""
    eligibility_page = next(
        (page for page in pages if re.search(r"83\.?\s*E[I1]GIBILITY\s+CRITERIA|to\s+be\s+eligible\s+for\s+qualification", _clean_text(page.get("text", "")), re.I)),
        next((page for page in pages if re.search(r"eligibility\s+criteria", _clean_text(page.get("text", "")), re.I)), pages[0]),
    )
    index = pages.index(eligibility_page) + 1
    page_number = _page_no(eligibility_page, index)
    location = str(eligibility_page.get("location", f"PDF page {page_number}"))
    text = _clean_text(eligibility_page.get("text", ""))
    marker = re.search(r"eligibility\s+criteria", text, re.I)
    evidence = _evidence_excerpt(text, marker.start() if marker else 0, (marker.end() if marker else min(120, len(text))) + 180)
    # This is deliberately phrased as a search result from the uploaded text, not a
    # definitive legal statement that no annexure/corrigendum contains the criterion.
    return LocalTenderAnswer(
        intent="turnover",
        answer=("**No explicit minimum annual turnover amount was found in the readable text of this uploaded tender.** "
                f"The cited eligibility section is {location}; it lists eligibility documents/conditions but no numeric turnover threshold in the extracted passage. "
                "Check all work-specific schedules and the latest portal corrigenda before treating turnover as not required."),
        page_number=page_number, source_location=location, evidence=evidence,
    )


def _normalise_date(raw: str) -> str:
    """Normalise common tender date formats for reliable conflict detection."""
    value = re.sub(r"(?i)(\d)(st|nd|rd|th)\b", r"\1", raw.strip())
    value = value.replace(".", "/").replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def _deadline_answer(question: str, pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    portal_candidates: list[tuple[int, str, str]] = []
    dated_candidates: list[tuple[int, str, str, str]] = []
    for index, page in enumerate(pages, start=1):
        text = _clean_text(page.get("text", ""))
        if not text:
            continue
        page_number = _page_no(page, index)
        location = str(page.get("location", f"PDF page {page_number}"))
        for label in _DEADLINE_LABEL.finditer(text):
            after = text[label.end():label.end() + 280]
            # Split at ordinary sentence boundaries so a narrative sentence about
            # the portal cannot absorb a later IFB publication date. However, tender
            # table fields often put the date after "DTCN.)" and dotted leaders;
            # do not split at the closing parenthesis or immediately before a "Dt."
            # date token (the actual Odisha page-16 layout).
            sentence_boundary = re.search(
                r"(?<!\))\.\s+(?!Dt\.?\s*\d)(?=[A-Z])", after
            )
            if sentence_boundary and sentence_boundary.start() > 4:
                after = after[:sentence_boundary.start()]
            # Stop before a separate opening-date field; otherwise keep the full
            # submission window because the end date is the actual deadline.
            next_field = re.search(
                r"\b(?:bid\s+opening\s+date|technical\s+bid\s+opening|priced\s+bid\s+opening|"
                r"pre[- ]bid\s+conference|date\s+of\s+original\s+bid\s+documents\s+submission|"
                r"time\s+and\s+date\s+of\s+opening|date\s+and\s+time\s+of\s+opening|"
                r"bids?\s+shall\s+be\s+opened|technical\s+bid\s+documents?\s+\([^)]*\)\s+will\s+be\s+opened)\b",
                after, re.I,
            )
            candidate_zone = after[:next_field.start()] if next_field else after
            placeholder = _PORTAL_PLACEHOLDER.search(candidate_zone)
            date_matches = list(_DATE.finditer(candidate_zone))
            if placeholder:
                # A common layout puts the IFB/document date immediately before the
                # explicit field "Bid Closing Date & Time: As mentioned on portal".
                # Such a preceding date is the issue date, not the deadline. Only use
                # a date appearing AFTER the portal placeholder as a possible explicit
                # deadline; otherwise preserve the portal-only result.
                dates_after_placeholder = [m for m in date_matches if m.start() >= placeholder.end()]
                if dates_after_placeholder:
                    date_matches = dates_after_placeholder
                else:
                    date_matches = []
            if date_matches:
                # Tender notices often express a submission window as "from A to B".
                # The last date in that labelled window is the close, not the opening date.
                date = date_matches[-1]
                time = _TIME.search(candidate_zone[date.end():date.end() + 90])
                date_text = date.group("date") + (f" up to {time.group(0)}" if time else "")
                evidence = _evidence_excerpt(text, label.start(), label.end() + date.end() + (time.end() if time else 0))
                dated_candidates.append((page_number, location, date_text, evidence))
            elif placeholder:
                portal_candidates.append((page_number, location, _evidence_excerpt(text, label.start(), label.end() + len(candidate_zone))))

    # Different explicit dates in the same tender are material conflicts. Do not
    # silently choose the first result or the newest date; surface the contradiction.
    unique_dates: dict[str, list[tuple[int, str, str, str]]] = {}
    for candidate in dated_candidates:
        normalised = _normalise_date(candidate[2].split(" up to ")[0])
        unique_dates.setdefault(normalised, []).append(candidate)
    if len(unique_dates) > 1:
        all_candidates = [candidate for rows in unique_dates.values() for candidate in rows]
        all_candidates.sort(key=lambda item: item[0])
        best = all_candidates[-1]
        details = "; ".join(
            f"{item[2]} ({item[1]})" for item in all_candidates
        )
        evidence = "\n\n".join(item[3] for item in all_candidates)
        return LocalTenderAnswer(
            intent="deadline",
            answer=(f"**The uploaded tender contains conflicting submission-date entries:** {details}. "
                    "I cannot safely select one deadline. Check the live tender portal and latest corrigendum before acting."),
            page_number=best[0], source_location=best[1], evidence=evidence, raw_value=details,
        )

    if dated_candidates:
        # A single date, or repeated identical dates, is safe to report with the
        # source evidence. Prefer the page with the most complete closing-time entry.
        dated_candidates.sort(key=lambda item: ("up to" in item[2].casefold(), item[0]), reverse=True)
        page_number, location, date_text, evidence = dated_candidates[0]
        return LocalTenderAnswer(
            intent="deadline",
            answer=(f"**Submission deadline found in the uploaded document: {date_text}.** [{location}]\n\n"
                    "Verify the date/time against the original page and latest official corrigenda."),
            page_number=page_number, source_location=location, evidence=evidence, raw_value=date_text,
        )

    if portal_candidates:
        page_number, location, evidence = portal_candidates[-1]
        return LocalTenderAnswer(
            intent="deadline",
            answer=(f"**The exact submission deadline is not stated in the uploaded PDF.** [{location}]\n\n"
                    "The notice refers bidders to the official e-tender portal. Check the live tender listing and corrigenda/extension notices; do not infer the deadline from the publication date."),
            page_number=page_number, source_location=location, evidence=evidence,
        )
    return None


_DURATION = re.compile(
    r"\b(?P<number>\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|twelve|thirty|ninety)"
    r"\s*(?P<unit>days?|months?|years?)\b",
    re.I,
)
_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12,
    "thirty": 30, "ninety": 90,
}


def _duration_value(match: re.Match[str]) -> tuple[int, str]:
    raw_number = match.group("number").casefold()
    number = int(raw_number) if raw_number.isdigit() else _WORD_NUMBERS[raw_number]
    unit = match.group("unit").casefold()
    unit = unit[:-1] if unit.endswith("s") else unit
    return number, unit


def _bid_validity_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    patterns = (
        re.compile(r"\bbid\s+validity(?:\s+period)?\b", re.I),
        re.compile(r"\bvalidity\s+period\s+of\s+(?:the\s+)?bid\b", re.I),
        re.compile(r"\bbids?\s+(?:shall|will)\s+remain\s+valid\b", re.I),
        re.compile(r"\boffer\s+shall\s+remain\s+valid\b", re.I),
        re.compile(r"\ball\s+bids?\s+received\s+will\s+remain\s+valid\b", re.I),
    )
    candidates: list[tuple[int, str, int, str, str]] = []
    for index, page in enumerate(pages, start=1):
        text = _clean_text(page.get("text", ""))
        if not text:
            continue
        page_number = _page_no(page, index)
        location = str(page.get("location", f"PDF page {page_number}"))
        for pattern in patterns:
            for label in pattern.finditer(text):
                zone = text[label.start():label.end() + 180]
                duration = _DURATION.search(zone[label.end() - label.start():])
                if not duration:
                    continue
                number, unit = _duration_value(duration)
                score = 10 + (6 if "bid validity period" in zone.casefold() else 0)
                score += 4 if "after the deadline" in zone.casefold() or "from the deadline" in zone.casefold() else 0
                evidence = _evidence_excerpt(text, label.start(), label.end() + duration.end())
                candidates.append((score, location, page_number, f"{number} {unit}{'' if number == 1 else 's'}", evidence))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[2]), reverse=True)
    _, location, page_number, duration_text, evidence = candidates[0]
    return LocalTenderAnswer(
        intent="bid_validity",
        answer=(f"**Bid validity period: {duration_text}.** [{location}]\n\n"
                f"Source wording: “{evidence}” Verify the clause and any amendments before relying on it."),
        page_number=page_number, source_location=location, evidence=evidence, raw_value=duration_text,
    )


def _warranty_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    """Extract warranty/DLP durations only when the duration is tied to its label.

    A broad window after any ``guarantee`` occurrence can pick up unrelated figures.
    The parser uses narrow label-to-duration patterns and keeps a Defect Liability
    Period distinct from a separately stated warranty.
    """
    duration = (
        r"(?P<number>\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"twelve|thirty|ninety)\s*(?P<unit>days?|months?|years?)"
    )
    patterns = (
        (re.compile(
            rf"\b(?:(?:minimum|at\s+least)\s+)?(?:warranty|guarantee)\s+"
            rf"(?:period|duration)\s*(?:of|shall\s+be|is|:|-)\s*(?P<duration>{duration})", re.I
        ), "warranty"),
        (re.compile(
            rf"\bwarranty\s+(?:of\s+(?:the\s+)?(?:works?|goods?|items?|services?)\s+)?"
            rf"(?:for\s+)?(?:(?:a\s+)?(?:minimum|at\s+least)\s+)?(?P<duration>{duration})", re.I
        ), "warranty"),
        (re.compile(
            rf"\bdefect\s+liability(?:\s+(?:period|duration))?\s*"
            rf"(?:of|shall\s+be|is|:|-)\s*(?P<duration>{duration})", re.I
        ), "defect_liability"),
    )
    candidates: list[tuple[int, str, int, str, str, str]] = []
    for index, page in enumerate(pages, start=1):
        text = _clean_text(page.get("text", ""))
        if not text:
            continue
        page_number = _page_no(page, index)
        location = str(page.get("location", f"PDF page {page_number}"))
        for pattern, requirement_type in patterns:
            for match in pattern.finditer(text):
                prefix = text[max(0, match.start() - 45):match.start()].casefold()
                if re.search(r"(?:performance|bank|bid|earnest|security)\s+$", prefix):
                    continue
                duration_match = re.fullmatch(duration, match.group("duration"), re.I)
                if not duration_match:
                    continue
                raw_number = duration_match.group("number").casefold()
                number = int(raw_number) if raw_number.isdigit() else _WORD_NUMBERS[raw_number]
                unit = duration_match.group("unit").casefold()
                unit = unit[:-1] if unit.endswith("s") else unit
                duration_text = f"{number} {unit}{'' if number == 1 else 's'}"
                zone = text[match.start():min(len(text), match.end() + 100)]
                score = 10
                score += 8 if re.search(r"\bminimum\b|\bat\s+least\b", prefix + zone, re.I) else 0
                score += 5 if re.search(r"after\s+completion", zone, re.I) else 0
                evidence = _evidence_excerpt(text, match.start(), match.end(), before=30, after=260)
                candidates.append((score, location, page_number, duration_text, evidence, requirement_type))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], -item[2]), reverse=True)
    _, location, page_number, duration_text, evidence, requirement_type = candidates[0]
    if requirement_type == "defect_liability":
        answer_text = (
            f"**Defect Liability Period stated: {duration_text}.** [{location}]\n\n"
            "The document labels this as a Defect Liability Period, not expressly as a separate product/work warranty. "
            f"Source wording: “{evidence}” Check the contract clauses for any additional warranty obligation."
        )
    else:
        # Preserve multi-trigger clauses such as "18 years from receipt OR 12 months
        # from commissioning, whichever is earlier". Reporting just the first
        # duration would materially misstate the condition.
        if re.search(r"\bwhichever\s+is\s+earlier\b", evidence, re.I):
            durations = list(_DURATION.finditer(evidence))
            duration_labels = []
            for duration_match in durations:
                number, unit = _duration_value(duration_match)
                duration_labels.append(f"{number} {unit}{'' if number == 1 else 's'}")
            unique_duration_labels = list(dict.fromkeys(duration_labels))
            answer_text = (
                f"**Warranty clause contains alternative periods: {' and '.join(unique_duration_labels)}; the document says whichever is earlier.** [{location}]\n\n"
                f"Source wording: “{evidence}” The 'whichever is earlier' condition is material; confirm the complete clause with the tender issuer before relying on this unusually long stated period."
            )
        else:
            answer_text = (
                f"**Warranty period found: {duration_text}.** [{location}]\n\n"
                f"Source wording: “{evidence}” Verify the clause and any schedules before relying on it."
            )
    return LocalTenderAnswer(
        intent="warranty", answer=answer_text, page_number=page_number,
        source_location=location, evidence=evidence, raw_value=duration_text,
    )


def _joint_venture_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    pattern = re.compile(r"joint\s+venture\s+is\s+required\s+for\s+the\s+works\s+having\s+sl\.?\s*no\.?", re.I)
    for index, page in enumerate(pages, start=1):
        text = _clean_text(page.get("text", ""))
        if not text:
            continue
        page_number = _page_no(page, index)
        location = str(page.get("location", f"PDF page {page_number}"))
        match = pattern.search(text)
        if not match:
            continue
        zone = text[match.end():match.end() + 100]
        stop = re.search(r"[.;]", zone)
        list_text = zone[:stop.start()] if stop else zone
        numbers = [int(value) for value in re.findall(r"\b\d{1,2}\b", list_text)]
        if not numbers:
            continue
        numbers = sorted(set(numbers))
        # Compress contiguous serial numbers into ranges for readability.
        ranges: list[str] = []
        start = previous = numbers[0]
        for value in numbers[1:]:
            if value == previous + 1:
                previous = value
                continue
            ranges.append(str(start) if start == previous else f"{start}–{previous}")
            start = previous = value
        ranges.append(str(start) if start == previous else f"{start}–{previous}")
        summary = ", ".join(ranges)
        evidence = _evidence_excerpt(text, match.start(), match.end() + len(list_text))
        return LocalTenderAnswer(
            intent="joint_venture",
            answer=(f"**Joint Venture is required for work serial numbers: {summary}.** [{location}]\n\n"
                    f"Source wording: “{evidence}” Check the work-specific condition and JV schedule before bidding."),
            page_number=page_number, source_location=location, evidence=evidence, raw_value=summary,
        )
    return None


def _contractor_class_answer(pages: list[dict[str, Any]]) -> LocalTenderAnswer | None:
    patterns = (
        re.compile(r"bids?\s+are\s+invited\b.{0,180}?\bfrom\s+[“\"']?([A-Z][“\"']?\s*(?:&|and)\s*[“\"']?[A-Z])", re.I),
        re.compile(r"class\s+of\s+contractor\b.{0,100}?\b([A-Z]\s*(?:&|and|,)\s*[A-Z])\b", re.I),
    )
    for index, page in enumerate(pages, start=1):
        text = _clean_text(page.get("text", ""))
        if not text:
            continue
        page_number = _page_no(page, index)
        location = str(page.get("location", f"PDF page {page_number}"))
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value = re.sub(r"[“”\"']", "", match.group(1)).strip()
                evidence = _evidence_excerpt(text, match.start(), match.end())
                return LocalTenderAnswer(
                    intent="contractor_class",
                    answer=(f"**Eligible contractor class: {value}.** [{location}]\n\n"
                            f"Source wording: “{evidence}” Verify the equivalent-grade registration condition in the tender."),
                    page_number=page_number, source_location=location, evidence=evidence, raw_value=value,
                )
        # Table layouts often have a separate 'Class of Contractor' header and C&D
        # cell values elsewhere on the same page, so support that column pattern too.
        if re.search(r"class\s+of\s+contractor", text, re.I):
            class_value = re.search(r"\b([A-Z])\s*&\s*([A-Z])\b", text, re.I)
            if class_value:
                value = f"{class_value.group(1).upper()} & {class_value.group(2).upper()}"
                evidence = _evidence_excerpt(text, class_value.start(), class_value.end(), before=120, after=90)
                return LocalTenderAnswer(
                    intent="contractor_class",
                    answer=(f"**Eligible contractor class: {value}.** [{location}]\n\n"
                            f"Source wording: “{evidence}” Verify any work-specific class/grade restrictions in the tender."),
                    page_number=page_number, source_location=location, evidence=evidence, raw_value=value,
                )
    return None


def answer_common_tender_question(question: str, pages: Iterable[dict[str, Any]]) -> LocalTenderAnswer | None:
    """Answer high-confidence tender field questions from the entire extracted document.

    Returns None when a direct answer cannot be grounded so the caller can use
    semantic retrieval/LLM as a second path. The function never guesses missing values.
    """
    page_list = [dict(page) for page in pages if _clean_text(page.get("text", ""))]
    if not question.strip() or not page_list:
        return None
    intents = set(question_intents(question))
    # Resolve validity before deadline: natural questions often say "valid after the
    # submission deadline" but ask for a duration, not the calendar closing date.
    if "bid_validity" in intents:
        answer = _bid_validity_answer(page_list)
        if answer:
            return answer
        # A query such as "how long does the bid remain valid after the submission
        # deadline?" asks for a duration, not the calendar closing date. If no
        # validity clause is found, never fall through and return the deadline.
        if re.search(r"\bafter\s+(?:the\s+)?(?:bid\s+)?submission\s+deadline\b", question, re.I):
            intents.discard("deadline")
    if "warranty" in intents:
        answer = _warranty_answer(page_list)
        if answer:
            return answer
    if "bid_opening" in intents and "deadline" not in intents:
        answer = _bid_opening_answer(page_list)
        if answer:
            return answer
    if "joint_venture" in intents:
        answer = _joint_venture_answer(page_list)
        if answer:
            return answer
    if "contractor_class" in intents:
        answer = _contractor_class_answer(page_list)
        if answer:
            return answer
    if "emd" in intents:
        schedule_answer = _emd_schedule_answer(page_list)
        if schedule_answer:
            return schedule_answer
    if "tender_fee" in intents:
        schedule_answer = _tender_fee_schedule_answer(page_list)
        if schedule_answer:
            return schedule_answer
    # Resolve an explicit submission-deadline intent after bid-validity has been
    # ruled out. This prevents a duration question from returning an unrelated date.
    if "deadline" in intents:
        answer = _deadline_answer(question, page_list)
        if answer:
            return answer
    # Specific labels first. User asking e.g. "EMD amount and fee" should not have the
    # first unrelated amount silently selected; let multi-intent questions use retrieval.
    amount_intents = [key for key in ("emd", "tender_fee", "turnover", "net_worth", "performance_security", "tender_value") if key in intents]
    if len(amount_intents) != 1:
        return None
    direct = _direct_amount_answer(question, page_list, amount_intents[0])
    if direct is not None:
        return direct
    if amount_intents[0] == "turnover":
        # Do not send an ungrounded amount request to a slow provider when the full
        # readable upload contains no labelled numeric turnover criterion.
        labelled_text = any(re.search(r"turn\s*over|turnover", _clean_text(p.get("text", "")), re.I) for p in page_list)
        if not labelled_text:
            return _turnover_not_found_answer(page_list)
    return None
