"""Safe structured rendering helpers for tender evidence excerpts."""
from __future__ import annotations

import html
import re
from typing import Iterable

from app.tender_question_intents import question_intents, question_match_terms

def query_terms(question: str) -> tuple[str, ...]:
    """Use shared state-agnostic tender synonyms for highlighting."""
    return question_match_terms(question)


def matched_query_terms(question: str, text: str) -> tuple[str, ...]:
    normalized = " ".join((text or "").casefold().split())
    found = []
    for term in query_terms(question):
        if " " in term:
            pattern = r"\b" + r"\s+".join(re.escape(part) for part in term.split()) + r"\b"
        else:
            pattern = rf"\b{re.escape(term)}\b"
        if re.search(pattern, normalized):
            found.append(term)
    return tuple(found)


def highlight_evidence_html(text: str, question: str) -> str:
    """Escape source text first, then highlight question/intent words safely."""
    safe = html.escape(text or "")
    # Use one combined regex so a shorter alias cannot create nested <mark>
    # elements inside a longer phrase that was already highlighted.
    terms = sorted(query_terms(question), key=len, reverse=True)
    alternatives = [r"\s+".join(re.escape(part) for part in term.split()) for term in terms]
    if alternatives:
        pattern = r"\b(?:" + "|".join(alternatives) + r")\b"
        safe = re.sub(
            pattern,
            lambda match: f'<mark class="tender-hit">{match.group(0)}</mark>',
            safe,
            flags=re.IGNORECASE,
        )
    return safe.replace("\n", "<br>")


def structure_evidence_text(text: str) -> list[str]:
    """Split a retrieval chunk into readable clauses/table cells for UI display."""
    source = " ".join((text or "").split())
    if not source:
        return []
    # Table cells are often flattened as | separators by PDF extractors. Show
    # their cells as independent lines instead of a single wide paragraph.
    if " | " in source:
        parts = [part.strip() for part in source.split(" | ") if part.strip()]
    else:
        prepared = re.sub(r"(?<!\d)\s+(?=\d{1,2}(?:\.\d+){0,2}\s+[A-Z])", "\n", source)
        prepared = re.sub(r"(?<=[.!?;])\s+(?=[A-Z0-9(])", "\n", prepared)
        parts = [part.strip() for part in prepared.splitlines() if part.strip()]
    # Avoid turning every small phrase into a separate visual row. Merge tiny
    # fragments with the previous clause, but retain separate table cells.
    if " | " not in source:
        merged: list[str] = []
        for part in parts:
            if merged and len(part) < 38:
                merged[-1] += " " + part
            else:
                merged.append(part)
        parts = merged
    return parts[:16]


_CURRENCY_AMOUNT_RE = re.compile(
    # Include magnitude suffixes and tolerate a single OCR space after a decimal
    # point. Example: "Rs. 111. 0 Cr." must remain "Rs. 111.0 Cr.", not "Rs. 111".
    r"(?P<raw>(?:₹\s*|\bRs\.?\s*|\bINR\s*)\d[\d,]*(?:\.\s*\d+)?"
    r"(?:\s*(?:/-|crores?|cr\.?|lakhs?|lacs?))?)",
    re.I,
)
_DEADLINE_LABEL_RE = re.compile(
    r"\b(?:bid\s+closing\s+date(?:\s*&\s*time)?|closing\s+date(?:\s+and\s+time)?|"
    r"submission\s+deadline|deadline\s+for\s+submission(?:\s+of\s+bids)?|"
    r"last\s+date(?:\s+and\s+time)?\s+for\s+(?:bid\s+)?submission|"
    r"bid\s+submission\s+(?:end|closing)\s+date(?:\s*&\s*time)?|due\s+date)\b",
    re.I,
)
_DATE_RE = re.compile(
    r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|"
    r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*,?\s*\d{4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},?\s+\d{4})\b",
    re.I,
)
_AMOUNT_LABELS: dict[str, tuple[str, ...]] = {
    "emd": ("bid security amount", "earnest money deposit", "earnest money", "bid security", "emd", "bid bond"),
    "tender_fee": ("tender processing fee", "fee for tender document", "tender document fee", "tender document cost", "cost of tender document", "bid document fee", "tender fee", "document fee", "processing fee"),
    "turnover": (
        "average annual financial turn over", "average annual financial turnover",
        "minimum annual financial turn over", "minimum annual financial turnover",
        "annual financial turn over", "annual financial turnover", "financial turn over",
        "financial turnover", "minimum annual turnover", "average annual turnover",
        "annual turnover", "turn over", "turnover",
    ),
    "net_worth": ("positive net worth", "net worth"),
    "performance_security": ("contract performance security", "performance bank guarantee", "performance security", "pbg"),
    "tender_value": ("estimated tender value", "estimated cost of work", "estimated cost", "approximate value", "contract value", "value put to tender"),
}
_DEADLINE_PORTAL_PHRASES = (
    "as mentioned in online e-tender portal", "as mentioned on the portal", "as specified in the portal",
    "as indicated in the portal", "will be available on the portal", "displayed on e-procurement portal",
    "as per the e-tender portal", "as available on the online procurement portal", "as available on the portal", "refer to the portal", "portal only",
)


def _location(item: object) -> str:
    return str(getattr(item, "source_location", "") or f"PDF page {getattr(item, 'page_number', '?')}")


def _find_labeled_amounts(intent: str, items: list[object]) -> list[tuple[str, str, str]]:
    """Return money strings only when a known generic label is close to the amount."""
    labels = _AMOUNT_LABELS.get(intent, ())
    found: list[tuple[int, str, str, str]] = []
    for item in items:
        text = " ".join(str(getattr(item, "text", "") or "").split())
        # OCR can flatten the source as "Rs. 111. 0 Cr."; repair that specific
        # currency-token spacing before searching, while retaining the source page.
        text = re.sub(r"(?i)(\bRs\.?\s*\d[\d,]*)\.\s+(\d+)(?=\s*(?:cr\.?|crores?\b|lakhs?\b|lacs?\b|/-|\b))", r"\1.\2", text)
        text = re.sub(r"(?i)(₹\s*\d[\d,]*)\.\s+(\d+)(?=\s*(?:cr\.?|crores?\b|lakhs?\b|lacs?\b|/-|\b))", r"\1.\2", text)
        label_hits: list[tuple[int, int]] = []
        for label in labels:
            pattern = r"\b" + r"\s+".join(re.escape(part) for part in label.split()) + r"\b"
            label_hits.extend((m.start(), m.end()) for m in re.finditer(pattern, text, re.I))
        amount_hits = list(_CURRENCY_AMOUNT_RE.finditer(text))
        for label_start, label_end in label_hits:
            viable = [m for m in amount_hits if -70 <= m.start() - label_end <= 220 or -120 <= m.end() - label_start <= 20]
            if not viable:
                continue
            amount = min(viable, key=lambda m: abs(m.start() - label_end))
            context_start = max(0, min(label_start, amount.start()) - 45)
            context_end = min(len(text), max(label_end, amount.end()) + 180)
            context = text[context_start:context_end].strip()
            raw_amount = amount.group("raw").strip()
            raw_amount = re.sub(r"(?<=\d)\.\s+(?=\d)", ".", raw_amount)
            # Prefer longer, more-specific labels (e.g. "bid security amount" over "bid security").
            found.append((label_end - label_start, raw_amount, _location(item), context))
    # Deduplicate repeated mentions of the same amount across summary table and annexure.
    unique: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for _specificity, amount, location, context in sorted(found, key=lambda row: row[0], reverse=True):
        digits = re.sub(r"\D", "", amount)
        key = digits or amount.casefold()
        if key not in seen:
            seen.add(key)
            unique.append((amount, location, context))
    return unique


def _direct_local_answer(question: str, items: list[object]) -> str | None:
    """Answer common field-style questions from labelled evidence, without a model call."""
    intents = question_intents(question)
    # If a query matches multiple concepts, prefer the clearest specific field intent.
    for intent in ("emd", "tender_fee", "turnover", "net_worth", "performance_security", "tender_value"):
        if intent not in intents:
            continue
        candidates = _find_labeled_amounts(intent, items)
        if not candidates:
            continue
        if len(candidates) > 1:
            values = ", ".join(f"{amount} [{location}]" for amount, location, _ in candidates[:4])
            return f"**Matching amounts found:** {values}. Please check each cited clause and any amendments before relying on one value."
        amount, location, context = candidates[0]
        label = {
            "emd": "EMD / Bid Security", "tender_fee": "Tender / Bid Document Fee", "turnover": "Turnover criterion",
            "net_worth": "Net worth criterion", "performance_security": "Performance Security", "tender_value": "Estimated tender / contract value",
        }[intent]
        return f"**{label}: {amount}** [{location}]\n\nRelevant wording: “{context}”"

    if "deadline" in intents:
        for item in items:
            text = " ".join(str(getattr(item, "text", "") or "").split())
            for match in _DEADLINE_LABEL_RE.finditer(text):
                following = text[match.end():match.end() + 145]
                # A portal placeholder explicitly means the PDF does not give the date here.
                if any(phrase in following.casefold() for phrase in _DEADLINE_PORTAL_PHRASES):
                    return (
                        f"**Exact submission deadline not stated in this tender excerpt.** The document directs bidders to the official e-tender portal. [{_location(item)}]\n\n"
                        "Check the live tender listing and any corrigendum/extension notice; do not infer a date from the tender issue date."
                    )
                date_match = _DATE_RE.search(following[:100])
                # Do not pick dates that occur after a portal placeholder or after a separate field label.
                if date_match:
                    between = following[:date_match.start()].casefold()
                    if not any(phrase in between for phrase in _DEADLINE_PORTAL_PHRASES):
                        time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM|HRS?|HOURS?)?\b", following[date_match.end():date_match.end() + 45], re.I)
                        date_text = date_match.group(0)
                        time_text = f" {time_match.group(0)}" if time_match else ""
                        return f"**Submission deadline found in the retrieved text:** {date_text}{time_text} [{_location(item)}]\n\nVerify it against the latest official portal notice/corrigendum before relying on it."
        # Only make a document-absence claim where the retrieved clauses point to the portal.
        if any(any(phrase in str(getattr(item, "text", "") or "").casefold() for phrase in _DEADLINE_PORTAL_PHRASES) for item in items):
            return "**Exact submission deadline is not stated in the retrieved tender text.** Check the official tender portal and any corrigendum/extension notice."

    # For nonnumeric questions, select the most directly stated clause instead of
    # merely showing a ranking of whole paragraphs. The clauses are still quotations,
    # not inferred legal conclusions.
    clause_intent_patterns: dict[str, tuple[tuple[str, int], ...]] = {
        "delivery": ((r"within\s+\d+\s*(?:calendar\s+)?days", 5), (r"shall\s+be\s+delivered", 5), (r"delivery\s+schedule", 4), (r"delivery\s+period", 2), (r"time\s+for\s+completion", 3)),
        "payment": ((r"payment\s+terms?", 4), (r"payment\s+shall\s+be\s+made", 5), (r"payment\s+will\s+be\s+made", 5), (r"within\s+\d+\s+days\s+of\s+(?:receipt|submission|invoice)", 4)),
        "documents": ((r"documents?\s+(?:to\s+be\s+)?submitted", 4), (r"must\s+submit", 4), (r"shall\s+submit", 4), (r"mandatory\s+documents?", 5), (r"registration\s+certificate", 2)),
        "scope": ((r"scope\s+of\s+(?:work|supply|services)", 5), (r"technical\s+specifications?", 4), (r"item\s+description", 4), (r"quantity\s+required", 3)),
        "experience": ((r"similar\s+(?:works?|supplies|contracts?)", 5), (r"purchase\s+orders?", 4), (r"work\s+orders?", 4), (r"successfully\s+completed", 4), (r"completed\s+(?:work|supply|project)", 4)),
        "eligibility": ((r"eligibility\s+criteria", 5), (r"bid\s+evaluation\s+criteria", 5), (r"minimum\s+requirements?", 4), (r"eligible\s+bidder", 4), (r"technical\s+qualification", 4)),
        "performance_security": ((r"performance\s+(?:bank\s+)?guarantee", 5), (r"performance\s+security", 5), (r"contract\s+performance\s+security", 5)),
        "bid_validity": ((r"bid\s+validity", 5), (r"validity\s+of\s+(?:the\s+)?bid", 5), (r"offer\s+shall\s+remain\s+valid", 4)),
        "warranty": ((r"warranty\s+period", 5), (r"defect\s+liability\s+period", 5), (r"guarantee\s+period", 4)),
        "location": ((r"place\s+of\s+delivery", 5), (r"shall\s+be\s+delivered\s+at", 5), (r"delivery\s+address", 5), (r"location\s+of\s+execution", 4), (r"work\s+site", 3)),
        "submission_mode": ((r"bid\s+submission\s+mode", 5), (r"online\s+submission", 4), (r"upload\s+(?:the\s+)?bid", 4), (r"offline\s+submission", 4)),
    }
    for intent in ("delivery", "payment", "documents", "scope", "experience", "eligibility", "performance_security", "bid_validity", "warranty", "location", "submission_mode"):
        if intent not in intents:
            continue
        patterns = clause_intent_patterns.get(intent, ())
        ranked_clauses: list[tuple[int, object, str]] = []
        for item in items:
            text = " ".join(str(getattr(item, "text", "") or "").split())
            text_lower = text.casefold()
            score = 0
            for pattern, weight in patterns:
                if re.search(pattern, text_lower, re.I):
                    score += weight
            if intent == "delivery" and re.search(r"experience|similar work|certificate", text_lower):
                score -= 4
            if intent == "documents" and re.search(r"file format|pdf/xls|digitally signed", text_lower):
                score -= 2
            if score > 0:
                ranked_clauses.append((score, item, text))
        ranked_clauses.sort(key=lambda row: row[0], reverse=True)
        if ranked_clauses:
            _score, item, text = ranked_clauses[0]
            loc = _location(item)
            # Keep evidence readable and avoid surfacing the whole flattened paragraph.
            segment = text
            for pattern, _weight in patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    start = max(0, match.start() - 90)
                    end = min(len(text), match.end() + 210)
                    segment = text[start:end].strip()
                    if start:
                        segment = "…" + segment
                    if end < len(text):
                        segment += "…"
                    break
            return f"**Relevant {intent.replace('_', ' ')} clause:** [{loc}]\n\n“{segment}”\n\nThis is the closest matching source wording in the retrieved passages; review the full clause and related annexures before relying on it."

    return None


def local_evidence_summary(
    question: str,
    hits: Iterable[object],
    *,
    all_evidence: Iterable[object] | None = None,
) -> str:
    """Produce source-backed answers using the whole index when available.

    ``hits`` are shown in the UI, but direct amount/label matching searches
    ``all_evidence`` when supplied so a top-k retrieval miss does not hide the
    only page that states the actual threshold.
    """
    items = list(hits)
    corpus = list(all_evidence) if all_evidence is not None else items
    if not items and not corpus:
        return (
            "**Local evidence summary — not an AI-generated conclusion**\n\n"
            "I could not find a sufficiently relevant clause in the extracted text. Try a different wording, check other tender annexures/BOQ files, or inspect the official notice manually."
        )
    direct = _direct_local_answer(question, corpus)
    lines = ["**Local evidence answer — not an AI-generated conclusion**", "", f"**Question:** {question.strip()}", ""]
    if direct:
        lines.extend([direct, ""])
    else:
        lines.append("**Best matching source passages** (use them as evidence, not as a final legal/eligibility decision):")
        lines.append("")

    # When full-corpus search finds a direct amount, make sure its source page is
    # included in the evidence list even when TF-IDF top-k omitted the clause.
    support_items = list(items)
    if direct and all_evidence is not None:
        intent_list = question_intents(question)
        labels = [label for intent in intent_list for label in _AMOUNT_LABELS.get(intent, ())]
        ranked: list[tuple[int, object]] = []
        for item in corpus:
            text = " ".join(str(getattr(item, "text", "") or "").split())
            text_lower = text.casefold()
            score = 0
            for label in labels:
                pattern = r"\b" + r"\s+".join(re.escape(part) for part in label.split()) + r"\b"
                if re.search(pattern, text, re.I):
                    score = max(score, 5 + len(label.split()))
            if _CURRENCY_AMOUNT_RE.search(text):
                score += 3
            if re.search(r"average|minimum|gross|should have had|must have|bid closing|deadline", text_lower):
                score += 2
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        selected = [item for _, item in ranked[:3]]
        # Use the ranked corpus evidence first, then top retrieval hits if room remains.
        support_items = selected + [item for item in items if item not in selected]

    lines.append("**Supporting evidence**")
    lines.append("")
    for item in support_items[:3]:
        location = _location(item)
        text = " ".join(str(getattr(item, "text", "")).split())
        if len(text) > 360:
            text = text[:357].rsplit(" ", 1)[0] + "..."
        lines.append(f"- **[{location}]** {text}")
    lines.extend([
        "",
        "Verify material terms against the latest official tender notice and corrigenda before making a Bid/No-Bid decision.",
    ])
    return "\n".join(lines)

