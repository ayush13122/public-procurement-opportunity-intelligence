from app.tender_requirements_extractor import (
    build_bidfit_prefill_payload,
    extract_tender_requirements_draft,
)


def test_prefill_payload_never_marks_official_source_or_requirements_as_verified():
    fields = extract_tender_requirements_draft([
        {"page_number": 1, "text": "Tender title: Example supply contract."}
    ])
    reviewed = {name: info["value"] for name, info in fields.items()}
    payload = build_bidfit_prefill_payload(
        reviewed,
        source_filename="example.pdf",
        field_details=fields,
    )
    assert payload["values"]["tender_title"] == "Example supply contract"
    assert payload["official_source_url"] == ""
    assert payload["closing_date_known"] is False
    assert payload["requirements_reviewed"] is False
    assert payload["official_source_checked"] is False
