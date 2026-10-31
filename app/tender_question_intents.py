"""State-agnostic question intent and terminology expansion for Indian tender Q&A.

The vocabulary intentionally contains generic procurement aliases instead of state,
portal, department, or vendor-specific assumptions. Retrieval is always grounded in
text extracted from the uploaded document; these aliases only help locate passages.
"""
from __future__ import annotations

import re

# (question triggers, retrieval expansions). Triggers are intentionally broad enough
# to cover common wording differences across central/state/PSU tender notices.
_INTENTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "emd": (
        ("emd", "earnest money", "bid security", "bid bond", "bid deposit", "bid security amount", "security for bid", "bid guarantee"),
        ("earnest money deposit", "bid security amount", "bid security", "bid bond", "bid guarantee", "security deposit for bid", "bank guarantee in lieu of bid security", "exemption from bid security"),
    ),
    "tender_fee": (
        ("tender fee", "tender processing fee", "document fee", "bid document fee", "cost of tender document", "cost of bid document", "cost of bid documents", "processing fee", "tender document cost"),
        ("tender processing fee", "cost of bid documents", "cost of bid document", "non refundable fee", "document cost", "online payment", "fee exemption"),
    ),
    "deadline": (
        ("deadline", "closing date", "last date", "submission date", "submit by", "due date", "bid end date", "closing time", "submission time", "kab tak", "last date kab", "submit karne", "jama karne"),
        ("bid closing date", "closing date and time", "last date for submission", "last date and time for submission", "submission deadline", "bid submission end date", "due date for bids", "date and time of opening", "deadline for submission of bids", "as published on the portal", "corrigendum extension"),
    ),
    "bid_opening": (
        ("technical bid opening", "technical bids be opened", "when will bids be opened", "when will the bids be opened", "when are technical bids opened", "bid opening date", "date of bid opening", "opening date of technical bid", "time of bid opening", "when is bid opening"),
        ("technical bid documents will be opened", "technical bid opening date and time", "bids shall be opened", "date and time of opening", "bid opening schedule"),
    ),
    "turnover": (
        (
            "turnover", "turn over", "annual turnover", "average turnover",
            "financial turnover", "financial turn over", "annual financial turnover",
            "annual financial turn over", "average annual financial turnover",
            "average annual financial turn over", "minimum turnover", "gross turnover",
        ),
        (
            "minimum annual turnover", "average annual turnover", "average annual financial turnover",
            "average annual financial turn over", "minimum annual financial turn over",
            "gross annual turnover", "financial turn over", "financial turnover",
            "audited financial statements", "preceding financial years", "financial eligibility criteria",
        ),
    ),
    "net_worth": (
        ("net worth", "networth"),
        ("positive net worth", "audited balance sheet", "financial year", "net worth certificate"),
    ),
    "experience": (
        ("experience", "similar work", "similar works", "similar supply", "similar supplies", "past performance", "work order", "purchase order", "completed project", "completed work", "years of experience", "qualifying order"),
        ("similar work experience", "similar supplies completed", "purchase order", "work order", "completion certificate", "successfully completed", "last three years", "last five years", "lookback period", "number of orders", "qualifying quantity"),
    ),
    "eligibility": (
        ("eligibility", "eligible bidder", "qualification", "qualifying criteria", "who can apply", "who can bid", "technical criteria", "disqualification"),
        ("eligibility criteria", "technical qualification", "bid evaluation criteria", "minimum requirements", "rejection criteria", "mandatory conditions", "qualified bidder"),
    ),
    "performance_security": (
        ("performance security", "performance guarantee", "performance bank guarantee", "pbg", "contract security", "security deposit after award"),
        ("contract performance security", "performance bank guarantee", "percentage of contract value", "validity of performance security", "security deposit after award"),
    ),
    "bid_validity": (
        (
            "bid validity", "validity of bid", "offer validity", "valid for how long",
            "bid remain valid", "bid remains valid", "bid will remain valid", "bid shall remain valid",
            "how long is the bid valid", "how many days is the bid valid", "validity period of bid",
            "validity period of the bid", "remain valid after submission", "remain valid after deadline",
        ),
        (
            "bid validity period", "validity period", "days from bid closing date",
            "period of bid validity", "offer shall remain valid", "bids remain valid",
            "valid for a period of days", "validity of the offer",
        ),
    ),
    "delivery": (
        ("delivery", "delivery period", "delivery schedule", "completion period", "execution period", "work completion time", "within how many days"),
        ("delivery schedule", "delivery period", "within days from purchase order", "time for completion", "completion period", "date of commencement", "dispatch and delivery"),
    ),
    "payment": (
        ("payment", "payment terms", "payment condition", "invoice payment", "when will payment"),
        ("payment terms", "payment shall be made", "after completion of supply", "running account bill", "invoice", "payment within days"),
    ),
    "tender_value": (
        ("estimated cost", "estimated value", "tender value", "contract value", "estimated amount", "project cost", "value of tender"),
        ("estimated tender value", "estimated cost of work", "contract value", "approximate value", "total estimated cost", "value put to tender"),
    ),
    "documents": (
        ("documents required", "required documents", "documents to submit", "document checklist", "which documents", "supporting documents", "certificates required", "mandatory certificates"),
        ("documents to be submitted", "mandatory documents", "technical bid documents", "eligibility documents", "registration certificate", "authorization letter", "experience certificate", "completion certificate", "financial statements", "declaration", "undertaking"),
    ),
    "scope": (
        ("scope of work", "scope of supply", "what items", "item description", "technical specification", "quantity", "qty", "work description", "what is required"),
        ("item description", "scope of work", "scope of supply", "technical specification", "bill of quantities", "quantity required", "schedule of requirements", "deliverables", "service description"),
    ),
    "warranty": (
        ("warranty", "guarantee period", "defect liability", "warranty period", "warranty after completion"),
        ("minimum warranty period", "warranty period", "defect liability period", "guarantee period", "comprehensive warranty", "warranty shall be", "after completion of work"),
    ),
    "joint_venture": (
        ("joint venture", "joint-venture", "jv required", "joint venture required", "works requiring jv"),
        ("joint venture agreement", "registered joint venture", "work serial numbers", "joint venture is required", "electrical contractor"),
    ),
    "contractor_class": (
        ("class of contractor", "classes of contractors", "what classes of contractors", "contractor class", "which class contractor", "which contractor classes", "eligible contractor class", "contractor category"),
        ("class of contractor", "registered class", "equivalent grade", "class c", "class d"),
    ),
    "location": (
        ("delivery location", "delivery address", "where to deliver", "place of delivery", "work location", "site location", "location of work"),
        ("place of delivery", "delivery at site", "destination", "work site", "location of execution", "consignee address", "delivery address"),
    ),
    "submission_mode": (
        ("how to submit", "submission mode", "where to submit", "online or offline", "bid submission mode"),
        ("online submission", "e-procurement portal", "upload the bid", "offline submission", "physical copy", "bid submission mode"),
    ),
}

_BASIC_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "does", "for", "from", "how", "in", "is", "it", "me", "of", "on", "or", "please", "the", "this", "to", "was", "what", "when", "where", "which", "who", "with", "would", "you", "tell", "about", "give", "find", "there", "their", "tender", "notice", "tell", "much", "many", "do", "i", "my", "our", "your", "required", "requirement",
}


def normalize(value: str) -> str:
    return " ".join((value or "").replace("\x00", " ").split()).casefold()


def question_intents(question: str) -> tuple[str, ...]:
    """Return generic tender-query intents detected in a user question."""
    normalized = normalize(question)
    found = []
    for intent, (triggers, _expansions) in _INTENTS.items():
        for trigger in sorted(triggers, key=len, reverse=True):
            pattern = r"\b" + r"\s+".join(re.escape(part) for part in trigger.split()) + r"\b"
            if re.search(pattern, normalized):
                found.append(intent)
                break
    # Generic cost/amount phrasing must not by itself decide what value to fetch.
    # But combined with an intent it tells the answer builder a numeric result is desired.
    return tuple(found)


def intent_expansions(question: str) -> tuple[str, ...]:
    normalized = normalize(question)
    additions: list[str] = []
    for intent in question_intents(question):
        additions.extend(_INTENTS[intent][1])
    if re.search(r"\b(submit|submission|submit karne|jama karne)\b", normalized):
        additions.extend(_INTENTS["deadline"][1])
    return tuple(dict.fromkeys(additions))


def expand_tender_question(question: str) -> str:
    """Append state-neutral procurement wording variants for lexical retrieval."""
    return " ".join([" ".join((question or "").split()), *intent_expansions(question)]).strip()


def question_match_terms(question: str) -> tuple[str, ...]:
    """Direct words first, followed by generic intent aliases for scoring/highlighting."""
    normalized = normalize(question)
    direct = [term for term in re.findall(r"[a-z0-9]+", normalized) if len(term) > 2 and term not in _BASIC_STOPWORDS]
    additions: list[str] = []
    for intent in question_intents(question):
        triggers, expansions = _INTENTS[intent]
        additions.extend(triggers)
        additions.extend(expansions)
    return tuple(dict.fromkeys(direct + additions))


def intent_label(intent: str) -> str:
    labels = {
        "emd": "EMD / Bid Security", "tender_fee": "Tender / Bid Document Fee", "deadline": "Submission Deadline", "bid_opening": "Bid Opening Schedule",
        "turnover": "Turnover Requirement", "net_worth": "Net Worth Requirement", "experience": "Experience Requirement",
        "eligibility": "Eligibility Criteria", "performance_security": "Performance Security", "bid_validity": "Bid Validity",
        "delivery": "Delivery / Completion Period", "payment": "Payment Terms", "tender_value": "Estimated Tender / Contract Value",
        "documents": "Required Documents", "scope": "Scope / Items / Specifications", "warranty": "Warranty / Defect Liability",
        "joint_venture": "Joint Venture Requirement", "contractor_class": "Eligible Contractor Class",
        "location": "Delivery / Work Location", "submission_mode": "Submission Method",
    }
    return labels.get(intent, intent.replace("_", " ").title())


# These intents have a provider-independent full-document answer path or can be
# explicitly reported as not found from the uploaded text. Do not send them to an
# LLM merely because a conservative local rule did not find a scalar value: that
# causes avoidable latency and increases the chance of unsupported answers.
LOCAL_FIRST_INTENTS = frozenset({
    "emd", "tender_fee", "deadline", "bid_opening", "turnover", "net_worth",
    "experience", "performance_security", "bid_validity", "delivery",
    "tender_value", "warranty", "joint_venture", "contractor_class", "location",
    "submission_mode",
})


def should_skip_provider_for_question(question: str) -> bool:
    """Return True when a known tender field should stay on the local evidence path."""
    return bool(set(question_intents(question)) & LOCAL_FIRST_INTENTS)
