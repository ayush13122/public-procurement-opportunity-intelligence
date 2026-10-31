from app.copilot_review_state import (
    REVIEW_FIELD_NAMES,
    REVIEW_WIDGET_KEYS,
    collect_widget_values,
    initial_review_values,
    merge_saved_review_values,
    update_review_value,
)


def sample_fields():
    return {
        "tender_title": {"value": "Supply of computers"},
        "required_capabilities": {"value": "computer supply, warranty"},
        "target_region": {"value": "Assam"},
        "min_years_experience": {"value": "3"},
        "min_similar_projects": {"value": "2"},
        "min_annual_turnover_inr": {"value": "3000000"},
        "required_certifications": {"value": "GST registration"},
        "emd_required_inr": {"value": "75000"},
        "closing_date": {"value": "2026-11-30"},
    }


def test_initial_review_values_covers_every_form_field():
    result = initial_review_values(sample_fields())
    assert set(result) == set(REVIEW_FIELD_NAMES)
    assert result["tender_title"] == "Supply of computers"
    assert result["emd_required_inr"] == "75000"


def test_saved_user_edits_override_extracted_values_after_navigation():
    saved = {"tender_title": "User corrected tender title", "emd_required_inr": "80000"}
    result = merge_saved_review_values(sample_fields(), saved)
    assert result["tender_title"] == "User corrected tender title"
    assert result["emd_required_inr"] == "80000"
    assert result["target_region"] == "Assam"


def test_intentionally_blank_saved_field_does_not_restore_old_candidate():
    result = merge_saved_review_values(sample_fields(), {"target_region": ""})
    assert result["target_region"] == ""


def test_widget_change_updates_non_widget_saved_values():
    saved = initial_review_values(sample_fields())
    updated = update_review_value(saved, "tender_title", "  Corrected title  ")
    assert updated["tender_title"] == "Corrected title"
    assert saved["tender_title"] == "Supply of computers"  # input mapping is not mutated


def test_collect_widget_values_captures_edits_and_keeps_unchanged_values():
    saved = initial_review_values(sample_fields())
    updated = collect_widget_values(saved, {"tender_title": "Edited title", "target_region": "Meghalaya"})
    assert updated["tender_title"] == "Edited title"
    assert updated["target_region"] == "Meghalaya"
    assert updated["min_years_experience"] == "3"


def test_widget_key_mapping_is_unique_and_complete():
    assert set(REVIEW_WIDGET_KEYS) == set(REVIEW_FIELD_NAMES)
    assert len(set(REVIEW_WIDGET_KEYS.values())) == len(REVIEW_FIELD_NAMES)
