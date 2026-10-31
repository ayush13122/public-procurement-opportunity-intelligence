"""Conservative, evidence-preserving draft extraction for tender requirements.

This is a local rule-based parser, not an LLM. Its values are only candidates and
must be reviewed against the official tender document before Bid-Fit evaluation.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable

_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
_NUMBER_TOKEN = r"(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?"
_AMOUNT_TOKEN = rf"(?P<amount>{_NUMBER_TOKEN})(?:\s*(?P<unit>crores?|cr|lakhs?|lacs?|lakh|lac))?"
_MONEY_PREFIX = r"(?:INR|Rs\.?|₹)\s*"

_FIELD_SPECS = {
    "tender_title": "Tender title",
    "required_capabilities": "Required capability / scope keywords",
    "target_region": "Tender delivery / work region",
    "min_years_experience": "Minimum experience years",
    "min_similar_projects": "Minimum similar completed projects",
    "min_annual_turnover_inr": "Minimum annual turnover (INR)",
    "required_certifications": "Mandatory certifications / registrations",
    "emd_required_inr": "Required EMD (INR)",
    "closing_date": "Closing date",
}

_CAPABILITY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Tender-specific equipment classes. These are suggestions extracted from
    # the title/scope, not legal eligibility conclusions.
    ("pressure transmitter supply", re.compile(r"\bpressure\s+transmitters?\b", re.I)),
    ("temperature transmitter supply", re.compile(r"\btemperature\s+transmitters?\b", re.I)),
    ("computer supply", re.compile(r"\b(computer|desktop|laptop)s?\b", re.I)),
    ("network installation", re.compile(r"\bnetwork\b", re.I)),
    ("installation", re.compile(r"\binstall(?:ation|ations|ing)?\b", re.I)),
    ("warranty", re.compile(r"\bwarrant(?:y|ies)\b", re.I)),
    ("road construction", re.compile(r"\broad construction\b", re.I)),
    ("road repair", re.compile(r"\broad repairs?\b", re.I)),
    ("civil works", re.compile(r"\bcivil works?\b", re.I)),
    ("building construction", re.compile(r"\bbuilding construction\b", re.I)),
    ("EPC / infrastructure construction", re.compile(
        r"\b(?:development of integrated check\s*post|development of land port|EPC\s+basis|"
        r"engineering procurement\s*(?:&|and)?\s*construction)\b", re.I
    )),
    ("software support", re.compile(r"\bsoftware support\b", re.I)),
    ("consultancy", re.compile(r"\bconsultancy\b", re.I)),
    ("transport", re.compile(r"\btransport\b", re.I)),
    ("logistics", re.compile(r"\blogistics\b", re.I)),
    ("sanitation", re.compile(r"\bsanitation\b", re.I)),
    ("water supply", re.compile(r"\bwater supply\b", re.I)),
    ("office furniture", re.compile(r"\boffice furniture\b", re.I)),
    ("stationery", re.compile(r"\bstationery\b", re.I)),
    ("laboratory equipment", re.compile(r"\blaboratory equipment\b", re.I)),
    ("medical equipment", re.compile(r"\bmedical equipment\b", re.I)),
    ("maintenance", re.compile(r"\bmaintenance\b", re.I)),
    ("training", re.compile(r"\btraining\b", re.I)),
)


def _clean(value: str) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())


def _empty_field() -> dict[str, Any]:
    return {
        "value": "",
        "page_number": None,
        "page_numbers": [],
        "evidence": "",
        "status": "Not found — enter from the official document if applicable",
    }


def _candidate(value: str, page_number: int, evidence: str, *, status: str = "Candidate extracted — verify") -> dict[str, Any]:
    return {
        "value": value.strip(),
        "page_number": page_number,
        "page_numbers": [page_number],
        "evidence": _clean(evidence),
        "status": status,
    }


def _evidence(text: str, start: int, end: int, *, before: int = 65, after: int = 150) -> str:
    left = max(0, start - before)
    right = min(len(text), max(end, start + 1) + after)
    excerpt = _clean(text[left:right])
    if left > 0:
        excerpt = "…" + excerpt
    if right < len(text):
        excerpt += "…"
    return excerpt


def _amount_to_inr(raw_number: str, unit: str | None) -> str:
    number = float(raw_number.replace(",", ""))
    unit_norm = (unit or "").lower().rstrip("s")
    if unit_norm in {"crore", "cr"}:
        number *= 10_000_000
    elif unit_norm in {"lakh", "lac"}:
        number *= 100_000
    if not number.is_integer():
        return str(int(round(number)))
    return str(int(number))


def _parse_date(raw: str) -> str | None:
    candidate = raw.strip().replace(",", "")
    formats = (
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%b/%Y",
        "%d/%B/%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(candidate, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _looks_like_table_of_contents(text: str) -> bool:
    """Identify index pages so headings/keywords in a contents list are not treated as scope."""
    normalized = _clean(text).lower()
    if "list of annexures" in normalized and ("page no" in normalized or "applicable" in normalized):
        return True
    if "table of contents" in normalized or "contents page" in normalized:
        return True
    appendix_hits = len(re.findall(r"\b(?:annexure|appendix)\s*[-–]?\s*[a-z0-9]+\b", normalized))
    return appendix_hits >= 5 and ("page no" in normalized or "page number" in normalized)



def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return conservative sentence-like spans, avoiding crossing to a new clause.

    Split at sentence/semicolon punctuation only when the next token starts with
    a capital letter. This avoids splitting abbreviations such as ``Rs. 5000``.
    """
    spans: list[tuple[int, int]] = []
    start = 0
    for separator in re.finditer(r"(?<=[.!?;])\s+(?=[A-Z])", text):
        if separator.start() > start:
            spans.append((start, separator.start()))
        start = separator.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans or [(0, len(text))]

def _first_match(pages: Iterable[dict[str, Any]], pattern: re.Pattern[str], group: str | int = 1) -> dict[str, Any] | None:
    for page in pages:
        text = _clean(str(page.get("text", "")))
        if not text:
            continue
        match = pattern.search(text)
        if match:
            return _candidate(
                match.group(group),
                int(page.get("page_number", 1)),
                _evidence(text, match.start(), match.end()),
            )
    return None


def extract_tender_requirements_draft(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Extract likely Bid-Fit fields with page evidence; never marks them verified.

    The extractor intentionally leaves the official source URL blank and does not
    infer company eligibility, tender status, win probability, or profit.
    """
    result = {name: _empty_field() for name in _FIELD_SPECS}
    # Qualification lookback is tracked separately from minimum bidder/company age.
    # It is display-only evidence and is deliberately excluded from Bid-Fit prefill.
    result["experience_lookback_years"] = _empty_field()
    clean_pages = [
        {
            "page_number": int(page.get("page_number", 1)),
            "location": str(page.get("location", f"Page {page.get('page_number', 1)}")),
            "text": _clean(str(page.get("text", ""))),
            "layout_text": str(page.get("layout_text", "") or ""),
        }
        for page in pages
        if _clean(str(page.get("text", "")))
    ]

    # First try a table-aware title label. Scanned NITs often flatten table cells into
    # one long line. The older generic pattern could run past the title on page 1, then
    # incorrectly match an unrelated later phrase such as "name of work ... total payment
    # received" on an eligibility page. Stop at common next-row labels and prefer page 1.
    labelled_work_title_pattern = re.compile(
        r"\b(?:name\s+of\s+work|tender\s+title|work\s+title|"
        r"work\s*/\s*item(?:\(s\))?\s+title)\s*[:\-]?\s*"
        r"(?P<title>.{8,240}?)(?=\s+\b(?:estimated\s+cost(?:\s+put\s+to\s+bid)?|"
        r"estimated\s+(?:tender\s+)?value|earnest\s+money|location|total\s+time\s+period|"
        r"period\s+of\s+completion|last\s+date(?:\s*(?:&|and)?\s*time)?|"
        r"time\s+and\s+date\s+of\s+opening|pre[- ]?bid\s+conference|"
        r"bid\s+submission\s+end\s+date|product\s+category|tender\s+fee|"
        r"work\s+description|pre[- ]?qualification)\b|$)",
        re.I,
    )
    found = _first_match(clean_pages[:3], labelled_work_title_pattern, "title")

    # Multi-work NITs do not have one unique work title. Represent the notice as
    # a package-level document instead of scanning later clauses for a false title.
    multi_work_page = None
    if not found and clean_pages:
        first_page_text = clean_pages[0]["text"]
        multi_work_heading = re.search(
            r"(?:detailed\s+tender\s+call\s+notice\s+for\s+the\s+works|"
            r"works\s+as\s+detailed\s+in\s+table\s+below|invites?\s+.+?\s+for\s+the\s+works)",
            first_page_text, re.I,
        )
        package_numbers = [int(value) for value in re.findall(r"(?:^|\s)(\d{1,2})\.\s+[A-Z]", first_page_text)]
        bid_id = re.search(r"(?:bid\s+identification\s+no\.?|bid\s+id)\s*[:.\-]*\s*([^\s]+(?:/[^\s]+)*)", first_page_text, re.I)
        if multi_work_heading and len(set(package_numbers)) >= 3:
            multi_work_page = clean_pages[0]
            count = len(set(package_numbers))
            identifier = bid_id.group(1).strip(" .-–") if bid_id else "see cover page"
            found = _candidate(
                f"Multiple works ({count} listed packages) — Bid ID {identifier}",
                int(clean_pages[0]["page_number"]),
                _evidence(first_page_text, multi_work_heading.start(), min(len(first_page_text), multi_work_heading.end() + 260)),
                status="Multi-work tender notice — select a work serial number before Bid-Fit review",
            )

    title_pattern = re.compile(
        r"\b(?:tender\s+title|title|name\s+of\s+work|work\s+title)\s*[:\-]?\s*"
        r"(.{5,160}?)(?=\s+(?:issue\s+date|publication\s+date|bid\s+submission\s+deadline|"
        r"submission\s+deadline|estimated\s+(?:tender\s+)?value|estimated\s+cost(?:\s+put\s+to\s+bid)?|"
        r"earnest\s+money|total\s+time\s+period|period\s+of\s+completion|last\s+date|"
        r"tender\s+reference|nit\s+no\.?|procuring\s+entity|work\s+description|"
        r"pre\s+qualification|tender\s+value|product\s+category)\b|[.;]|$)",
        re.I,
    )
    if not found:
        found = _first_match(clean_pages[:3], title_pattern)
    if found and re.search(r"\b(?:total\s+payment\s+received|TDS\s+amount|certificate\s+of\s+financial\s+turn|bidder\s+must\s+submit)\b", found.get("value", ""), re.I):
        # Reject a paragraph that is clearly a document checklist/experience clause, not a title.
        found = None
    if not found:
        # Some notices show the title directly below a generic heading rather than
        # labelling it "Tender title:". Use only a conservative first-page header fallback.
        header_title_pattern = re.compile(
            r"\b(?:request\s+for\s+quotation\s*/\s*tender\s+notice|tender\s+notice)\s+"
            r"(?P<title>.{8,160}?)(?=\s+(?:notice\s+reference|tender\s+reference|nit\s+no\.?|"
            r"procuring\s+entity|issue\s+date|publication\s+date|bid\s+submission\s+deadline|"
            r"technical\s+bid\s+opening|contract\s+location|estimated\s+tender\s+value)\b|[.;]|$)",
            re.I,
        )
        found = _first_match(clean_pages[:1], header_title_pattern, "title")
    if not found:
        # Common supplier-facing tender documents use a header like:
        # "TENDER DOCUMENT FOR SUPPLY OF Pressure Transmitter ...".
        document_header_pattern = re.compile(
            r"\btender\s+document\s+for\s+(?P<title>.{5,160}?)(?=[.;]|\s+(?:invitation\s+for\s+e[- ]?bid|"
            r"tender\s*/\s*ifb\s+no\.?|e[- ]tender\s+website|bid\s+closing\s+date)\b|$)",
            re.I,
        )
        found = _first_match(clean_pages[:2], document_header_pattern, "title")
    if found:
        found["value"] = _clean(found["value"]).strip(" :-|/").rstrip(".")
        # Common OCR confusion in the EPC label: "Mode | / (Engineering...)".
        found["value"] = re.sub(r"\bMode\s*(?:[|/]\s*)+(?=\()", "Mode I ", found["value"], flags=re.I)
        found["value"] = re.sub(r"\s+", " ", found["value"]).strip(" :-|/").rstrip(".")
        found["value"] = re.sub(r"^supply\s+of\b", "Supply of", found["value"], flags=re.I)
        result["tender_title"] = found

    turnover_pattern = re.compile(
        rf"\b(?:minimum\s+average\s+annual|minimum\s+annual|average\s+annual|annual|minimum)?\s*"
        rf"turn[\s-]*over\b.{{0,180}}?{_MONEY_PREFIX}{_AMOUNT_TOKEN}",
        re.I,
    )
    for page in clean_pages:
        text = page["text"]
        for span_start, span_end in _sentence_spans(text):
            segment = text[span_start:span_end]
            match = turnover_pattern.search(segment)
            if match:
                amount = _amount_to_inr(match.group("amount"), match.group("unit"))
                start, end = span_start + match.start(), span_start + match.end()
                result["min_annual_turnover_inr"] = _candidate(
                    amount, page["page_number"], _evidence(text, start, end)
                )
                break
        if result["min_annual_turnover_inr"]["value"]:
            break

    # A multi-package tender may publish one EMD per work row. Never put the
    # first row's amount into a single scalar Bid-Fit field: that would mislead
    # users who selected a different work package.
    emd_schedule_header = next((
        page for page in clean_pages
        if re.search(r"\bEMD\s+in\s+Rs\b", page.get("layout_text", "") or page["text"], re.I)
        and re.search(r"\bClass\s+of\s+Contractor\b", page.get("layout_text", "") or page["text"], re.I)
    ), None)
    if emd_schedule_header:
        header_index = clean_pages.index(emd_schedule_header)
        schedule_pages = clean_pages[header_index:header_index + 2]
        serials: set[int] = set()
        for schedule_index, page in enumerate(schedule_pages):
            layout = page.get("layout_text", "") or page["text"]
            lines = layout.replace("\r", "").splitlines()
            if schedule_index == 0:
                header_line = next((i for i, line in enumerate(lines) if re.search(r"\bEMD\s+in\s+Rs\b", line, re.I)), -1)
                lines = lines[header_line + 1:]
            else:
                # Page-number glyph at the very top of a continuation page is not
                # a work serial; discard that first visible line when it is isolated.
                first_nonempty = next((i for i, line in enumerate(lines) if line.strip()), None)
                if first_nonempty is not None and lines[first_nonempty].strip() == str(page["page_number"]):
                    lines = lines[first_nonempty + 1:]
            for line in lines:
                if re.fullmatch(r"\s*1\s+2\s+3\s+4\s+5\s+6\s+7\s*", line):
                    continue
                row_start = re.match(r"^\s*(1[0-6]|[1-9])(?:\s+|$)", line)
                if row_start:
                    serials.add(int(row_start.group(1)))
        if len(serials) >= 8:
            schedule_text = " ".join(page["text"] for page in schedule_pages)
            result["emd_required_inr"].update({
                "value": "",
                "page_number": emd_schedule_header["page_number"],
                "page_numbers": [page["page_number"] for page in schedule_pages],
                "evidence": _evidence(schedule_text, 0, min(len(schedule_text), 520)),
                "status": f"Work-specific EMD schedule detected ({len(serials)} work rows) — select the work serial; do not use one universal amount",
                "source_location": f"PDF pages {schedule_pages[0]['page_number']}–{schedule_pages[-1]['page_number']}",
                "source_locations": [f"PDF page {page['page_number']}" for page in schedule_pages],
            })
    if not result["emd_required_inr"].get("status", "").startswith("Work-specific EMD schedule"):
        emd_pattern = re.compile(
            rf"\b(?:EMD|earnest\s+money\s+deposit|earnest\s+money|bid\s+security\s+amount)\b"
            rf".{{0,120}}?{_MONEY_PREFIX}{_AMOUNT_TOKEN}",
            re.I,
        )
        for page in clean_pages:
            text = page["text"]
            for span_start, span_end in _sentence_spans(text):
                segment = text[span_start:span_end]
                match = emd_pattern.search(segment)
                if match:
                    amount = _amount_to_inr(match.group("amount"), match.group("unit"))
                    start, end = span_start + match.start(), span_start + match.end()
                    result["emd_required_inr"] = _candidate(
                        amount, page["page_number"], _evidence(text, start, end)
                    )
                    break
            if result["emd_required_inr"]["value"]:
                break

    # OCR can render the rupee symbol as a Latin glyph (commonly "k" in this
    # Banbasa scan). Accept that one-glyph artifact only directly after an EMD
    # label, only with an Indian comma-grouped amount, and only when followed by
    # an amount-in-words parenthesis. This avoids treating arbitrary nearby figures
    # as EMD.
    if not result["emd_required_inr"]["value"]:
        ocr_emd_pattern = re.compile(
            rf"\b(?:EMD|earnest\s+money(?:\s+deposit)?|bid\s+security\s+amount)\b"
            rf".{{0,24}}?[kK]\s*(?P<amount>\d{{1,3}}(?:,\d{{2,3}})+)\s*(?:/-)?"
            rf"(?=\s*\(\s*rupees?\b)",
            re.I,
        )
        for page in clean_pages:
            match = ocr_emd_pattern.search(page["text"])
            if match:
                amount = _amount_to_inr(match.group("amount"), None)
                result["emd_required_inr"] = _candidate(
                    amount, page["page_number"],
                    _evidence(page["text"], match.start(), match.end() + 90),
                    status="OCR-tolerant EMD candidate — verify the currency glyph and amount against the page image",
                )
                break

    number_alternation = "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True))
    number_token = rf"(?P<count>\d+|{number_alternation})"
    project_patterns = [
        re.compile(
            rf"\b(?:minimum|at\s+least|not\s+less\s+than)\s+{number_token}\s+"
            rf"(?:(?:completed|similar|relevant|supply|civil|similar\s+completed)\s+){{0,4}}"
            rf"(?:similar\s+)?(?:projects?|contracts?|works?)\b",
            re.I,
        ),
        re.compile(
            rf"\b{number_token}\s+(?:completed\s+)?(?:supply\s+)?contracts?\s+of\s+similar\b",
            re.I,
        ),
    ]
    for page in clean_pages:
        text = page["text"]
        for pattern in project_patterns:
            match = pattern.search(text)
            if match:
                token = match.group("count").lower()
                count = int(token) if token.isdigit() else _NUMBER_WORDS[token]
                result["min_similar_projects"] = _candidate(
                    str(count), page["page_number"], _evidence(text, match.start(), match.end())
                )
                break
        if result["min_similar_projects"]["value"]:
            break

    years_pattern = re.compile(
        rf"\b(?:minimum(?:\s+of)?|at\s+least|not\s+less\s+than)\s+"
        rf"(?P<years>\d+|{number_alternation})\s+years?\s+(?:of\s+)?"
        rf"(?:relevant\s+|professional\s+|similar\s+)?experience\b",
        re.I,
    )
    for page in clean_pages:
        text = page["text"]
        match = years_pattern.search(text)
        if match:
            token = match.group("years").lower()
            years = int(token) if token.isdigit() else _NUMBER_WORDS[token]
            result["min_years_experience"] = _candidate(
                str(years), page["page_number"], _evidence(text, match.start(), match.end())
            )
            break

    # A qualifying lookback window (e.g. "work experience during the last Seven
    # years") is not the same as a minimum company age. Surface it in its own
    # display-only field so the information is not silently transferred to Bid-Fit
    # as a minimum number of years the bidder has existed. Conflicting windows are
    # preserved as a review status instead of choosing one.
    lookback_patterns = (
        re.compile(
            rf"\b(?:work\s+)?experience\b.{{0,120}}?\b(?:during|in|over|within)\s+"
            rf"(?:the\s+)?(?:immediate\s+)?last\s+(?P<years>\d+|{number_alternation})\s+years?\b",
            re.I,
        ),
        re.compile(
            rf"\b(?:during|in|over|within)\s+(?:the\s+)?(?:immediate\s+)?last\s+"
            rf"(?P<years>\d+|{number_alternation})\s+years?\b.{{0,120}}?\b(?:work\s+)?experience\b",
            re.I,
        ),
        re.compile(
            rf"\bprescribed\s+period\s+of\s+(?P<years>\d+|{number_alternation})\s+years?\b",
            re.I,
        ),
        re.compile(
            rf"\bwithin\s+(?:the\s+)?prescribed\s+period\s+of\s+"
            rf"(?P<years>\d+|{number_alternation})\s+years?\b",
            re.I,
        ),
    )
    lookback_hits: list[tuple[int, int, int, str]] = []
    for page in clean_pages:
        for pattern in lookback_patterns:
            for match in pattern.finditer(page["text"]):
                if "prescribed" in match.group(0).casefold():
                    nearby = page["text"][max(0, match.start() - 260):min(len(page["text"]), match.end() + 180)]
                    if not re.search(r"experience|similar\s+work|work/supply|completed\s+work", nearby, re.I):
                        continue
                token = match.group("years").casefold()
                years = int(token) if token.isdigit() else _NUMBER_WORDS[token]
                lookback_hits.append((years, page["page_number"], match.start(), page["text"]))
    # Deduplicate the same clause captured by both pattern directions.
    unique_lookbacks: dict[tuple[int, int, int], tuple[int, int, int, str]] = {}
    for hit in lookback_hits:
        unique_lookbacks[(hit[0], hit[1], hit[2])] = hit
    lookback_hits = list(unique_lookbacks.values())
    distinct_lookbacks = sorted({hit[0] for hit in lookback_hits})
    if len(distinct_lookbacks) == 1:
        years = distinct_lookbacks[0]
        hit = next(item for item in lookback_hits if item[0] == years)
        result["experience_lookback_years"] = _candidate(
            str(years), hit[1], _evidence(hit[3], hit[2], hit[2] + 1, before=90, after=190),
            status=(f"Experience lookback window — {years} years; this is the period for counting qualifying work, "
                    "not a minimum company age. Review the full eligibility clause."),
        )
    elif len(distinct_lookbacks) > 1:
        evidence_blocks = []
        page_numbers = []
        for years, page_number, start, text in sorted(lookback_hits, key=lambda item: (item[1], item[2])):
            if page_number not in page_numbers:
                page_numbers.append(page_number)
            evidence_blocks.append(f"PDF page {page_number}: {_evidence(text, start, start + 1, before=90, after=160)}")
        result["experience_lookback_years"].update({
            "value": "",
            "page_number": page_numbers[0] if page_numbers else None,
            "page_numbers": page_numbers,
            "evidence": "\n".join(evidence_blocks),
            "status": ("Conflicting experience lookback periods detected: "
                       + " / ".join(f"{value} years" for value in distinct_lookbacks)
                       + "; review the experience clauses and corrigenda; no single period selected"),
        })
    if not result["min_years_experience"].get("value") and lookback_hits:
        if len(distinct_lookbacks) == 1:
            result["min_years_experience"]["status"] = (
                "No separate minimum bidder/company age was identified. A qualifying-work lookback is shown "
                "separately under Experience Lookback Years; do not treat it as company age."
            )
        elif len(distinct_lookbacks) > 1:
            result["min_years_experience"]["status"] = (
                "No separate minimum bidder/company age was identified; the experience lookback wording conflicts. "
                "Review the Experience Lookback Years evidence before assessment."
            )

    date_token = r"(?P<date>\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[/-](?:\d{1,2}|January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[/-]\d{4})"
    deadline_pattern = re.compile(
        rf"(?:\b|(?-i:(?<=[A-Z])))"
        rf"(?:bid\s+submission\s+(?:end|closing)\s+date|bid\s+closing\s+date|"
        rf"bid\s+submission\s+deadline|submission\s+deadline|closing\s+date|"
        rf"last\s+date\s+for\s+(?:bid\s+)?submission|bids?\s+must\s+be\s+submitted\s+before)\b"
        rf"\s*(?:is|:|\-|on|by)?\s*{date_token}",
        re.I,
    )
    portal_date_candidate: dict[str, Any] | None = None
    for page in clean_pages:
        text = page["text"]
        match = deadline_pattern.search(text)
        if not match:
            # OCR/table reading order can place the date between the label parts:
            # "Last date & time of 14/11/2026 up to 15:00 Hrs. online submission of bid".
            # Accept the date only when it is directly after this explicit deadline label
            # and the same short span confirms it is the online bid-submission field.
            table_order_deadline_pattern = re.compile(
                rf"\blast\s+date\s*(?:&|and)?\s*time\s+of\s*{date_token}"
                rf".{{0,90}}?\b(?:online\s+)?submission\s+of\s+(?:the\s+)?bid\b",
                re.I,
            )
            match = table_order_deadline_pattern.search(text)
        if match:
            raw_date = match.group("date")
            parsed = _parse_date(raw_date)
            if parsed:
                result["closing_date"] = _candidate(
                    parsed, page["page_number"], _evidence(text, match.start(), match.end()),
                    status="Candidate extracted — verify date/time and current corrigendum",
                )
                break
        if portal_date_candidate is None:
            portal_reference_pattern = re.compile(
                r"\b(?:bid\s+closing\s+date(?:\s*&\s*time)?|bid\s+submission\s+(?:end\s+)?date(?:\s*&\s*time)?)\b"
                r".{0,140}?\b(?:as\s+mentioned|as\s+specified|as\s+indicated|refer\s+to)\b"
                r".{0,100}?\b(?:online\s+)?e[- ]?tender\s+portal\b",
                re.I,
            )
            portal_match = portal_reference_pattern.search(text)
            if portal_match:
                portal_date_candidate = {
                    "value": "",
                    "page_number": page["page_number"],
                    "page_numbers": [page["page_number"]],
                    "evidence": _evidence(text, portal_match.start(), portal_match.end()),
                    "status": "Portal lookup required — the deadline is not stated in this document",
                }
    if not result["closing_date"]["value"] and portal_date_candidate:
        result["closing_date"] = portal_date_candidate

    # Prefer an explicit delivery destination over a generic office/authority address.
    explicit_store_region_pattern = re.compile(
        r"\bFOR\s*:?[ ]*(?P<region>AGCL\s+Stores?,\s*Duliajan,\s*Assam)\s+basis\b",
        re.I,
    )
    found = _first_match(clean_pages, explicit_store_region_pattern, "region")
    if not found:
        delivered_to_store_pattern = re.compile(
            r"\b(?:delivered\s+at|delivery\s+at)\s+(?P<region>AGCL(?:'s|’s)?\s+Stores?,\s*Duliajan(?:,\s*Assam)?)"
            r"(?=\s+(?:within|on|by|basis)\b|[.;]|$)",
            re.I,
        )
        found = _first_match(clean_pages, delivered_to_store_pattern, "region")
    region_pattern = re.compile(
        r"\b(?:tender\s+delivery\s+region|delivery\s+location|contract\s+location|work\s+location|"
        r"execution\s+location|place\s+of\s+execution|project\s+location|work\s+region)\b"
        r"\s*(?:is|:|\-)?\s*(?P<region>[A-Z][A-Za-z0-9 ,/&()\-]{1,70}?)"
        r"(?=\s+(?:minimum|deadline|closing|emd|eligibility|bid|tender|estimated|submission|the\s+bidder)\b|[.;]|$)",
        re.I,
    )
    if not found:
        found = _first_match(clean_pages, region_pattern, "region")
    if found:
        found["value"] = found["value"].strip(" :-")
        found["value"] = re.sub(r"\s*\((?:fictional|demo)[^)]*\)\s*$", "", found["value"], flags=re.I).strip()
        result["target_region"] = found

    # EPC notice scans sometimes drop the separate "Location" table cell but retain
    # "at <town>, <state>" in the labelled Name of Work. Use that explicit title phrase
    # only as a review-required work-location candidate (not as a delivery address).
    if not result["target_region"]["value"] and result["tender_title"]["value"]:
        title_value = str(result["tender_title"]["value"])
        title_region = re.search(
            r"\bat\s+(?P<region>[A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+){0,2},\s*[A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+){0,2})\b",
            title_value,
        )
        if title_region:
            title_info = result["tender_title"]
            result["target_region"] = _candidate(
                title_region.group("region"),
                int(title_info.get("page_number") or 1),
                title_value,
                status="Work-location candidate parsed from the named work — verify against the official document",
            )

    certification_pattern = re.compile(
        r"\b(?:mandatory\s+certifications?(?:\s*/\s*registrations?)?|"
        r"mandatory\s+registrations?|required\s+certifications?(?:\s*/\s*registrations?)?|"
        r"required\s+registrations?)\s*[:\-]\s*(?P<certs>[^.;]{2,140})",
        re.I,
    )
    found = _first_match(clean_pages, certification_pattern, "certs")
    if not found:
        # Table-style eligibility rows may say "Tax registration | Valid GST registration"
        # rather than "Required certifications: ...".
        tax_registration_pattern = re.compile(
            r"\btax\s+registration\b.{0,100}?\b(?P<certs>(?:valid\s+)?GST\s+registration)\b",
            re.I,
        )
        found = _first_match(clean_pages, tax_registration_pattern, "certs")
    if not found:
        # Prefer an ATEX mention in the Bid Evaluation Criteria over an earlier
        # logistics/checklist mention that may only apply at dispatch.
        bec_atex_pattern = re.compile(
            r"\bbidder\s+must\s+be\b.{0,750}?\b(?P<certs>ATEX\s+Certificate)\b",
            re.I,
        )
        found = _first_match(clean_pages, bec_atex_pattern, "certs")
        if found:
            found["status"] = "Candidate extracted from bid-evaluation criteria — verify applicability"
    if not found:
        # Equipment tenders may specify a product compliance certificate without
        # using the words "mandatory certification".
        equipment_certificate_pattern = re.compile(r"\b(?P<certs>ATEX\s+Certificate)\b", re.I)
        found = _first_match(clean_pages, equipment_certificate_pattern, "certs")
    if found:
        found["value"] = re.sub(r"^valid\s+", "", found["value"].strip(" :-"), flags=re.I)
        if re.search(r"\bATEX\s+Certificate\b", found["value"], re.I):
            found["status"] = "Candidate extracted — verify submission stage and applicability"
        result["required_certifications"] = found

    # Capability/scope terms are suggestions, not legal requirements. Avoid scanning
    # every page blindly (e.g. "Training Department" is not a training service).
    scope_sections: list[tuple[int, str]] = []
    scope_heading = re.compile(
        r"\b(?:technical\s+scope|scope\s+of\s+work|work\s+scope|description\s+of\s+work|"
        r"work\s+description|items\s+to\s+be\s+supplied|scope\s+details)\b\s*[:\-]?\s*"
        r"(?P<body>.*?)(?=\s+\d+\.\s+[A-Z]|\s+(?:documents\s+to\s+submit|submission\s+and\s+verification|"
        r"eligibility\s+requirements|terms\s+and\s+conditions)\b|$)",
        re.I,
    )
    for page in clean_pages:
        if _looks_like_table_of_contents(page["text"]):
            continue
        match = scope_heading.search(page["text"])
        if match and match.group("body").strip():
            scope_sections.append((page["page_number"], match.group("body").strip()))
    # Use the tender title plus any clearly-labelled scope section, not all PDF
    # text (e.g. "Training Department" is not a training-service requirement).
    candidate_contexts: list[tuple[int, str]] = []
    if result["tender_title"]["value"]:
        candidate_contexts.append((
            int(result["tender_title"]["page_number"]),
            result["tender_title"]["value"],
        ))
    candidate_contexts.extend(scope_sections)
    scope_candidates: list[str] = []
    evidence_items: list[str] = []
    page_numbers: list[int] = []
    candidate_text = " ".join(text for _, text in candidate_contexts)
    for label, pattern in _CAPABILITY_RULES:
        if label == "computer supply":
            if not (re.search(r"\b(computer|desktop|laptop)s?\b", candidate_text, re.I) and re.search(r"\b(supply|procure|provide)\b", candidate_text, re.I)):
                continue
        elif label == "network installation":
            # Require the two concepts to occur close together; otherwise "network connectivity"
            # in one sentence plus a separate physical-installation clause creates a false match.
            near_network_installation = re.search(
                r"\bnetwork\s+install(?:ation|ations|ing)?\b|"
                r"\binstall(?:ation|ations|ing)?\s+(?:of\s+)?network\b",
                candidate_text,
                re.I,
            )
            if not near_network_installation:
                continue
        elif not pattern.search(candidate_text):
            continue
        # Add only vocabulary candidates evidenced in a title/scope section.
        scope_candidates.append(label)
        for page_number, context_text in candidate_contexts:
            match = pattern.search(context_text)
            if match:
                page_numbers.append(page_number)
                evidence_items.append(f"Page {page_number}: {_evidence(context_text, match.start(), match.end())}")
                break
    if scope_candidates:
        unique_pages = sorted(set(page_numbers))
        result["required_capabilities"] = {
            "value": ", ".join(scope_candidates),
            "page_number": unique_pages[0] if len(unique_pages) == 1 else None,
            "page_numbers": unique_pages,
            "evidence": "\n".join(evidence_items),
            "status": "Keyword suggestions extracted — verify against actual scope and mandatory clauses",
        }

    # Attach human-readable source locations for non-PDF files. `page_number` remains
    # an internal ordinal so older rules and tests stay compatible, but the UI should
    # show the source location (e.g. DOCX paragraph or Excel row) rather than calling
    # it a physical PDF page.
    location_by_ordinal = {page["page_number"]: page.get("location", f"Page {page['page_number']}") for page in clean_pages}
    for field_info in result.values():
        ordinal = field_info.get("page_number")
        field_info["source_location"] = location_by_ordinal.get(ordinal, "") if ordinal is not None else ""
        field_info["source_locations"] = [
            location_by_ordinal.get(item, f"Page {item}") for item in field_info.get("page_numbers", [])
        ]

    # Never infer an official source URL from arbitrary links in a tender file.
    return result


def build_bidfit_prefill_payload(
    reviewed_values: dict[str, str],
    *,
    source_filename: str,
    field_details: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Prepare cross-page values without asserting official verification.

    The caller should invoke this only after the user has reviewed the draft in
    the Copilot UI. Official source URL/status and final confirmation checkboxes
    are deliberately left unset for the Bid-Fit page.
    """
    allowed = set(_FIELD_SPECS)
    values = {name: str(reviewed_values.get(name, "") or "").strip() for name in allowed}
    return {
        "values": values,
        "source_filename": str(source_filename or "uploaded tender PDF"),
        "field_details": field_details,
        "official_source_url": "",
        "closing_date_known": False,
        "requirements_reviewed": False,
        "official_source_checked": False,
    }
