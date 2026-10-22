"""Regression tests for high-risk source-label/title conflicts.

These tests exercise candidate classification rules only; they do not declare
all live procurement classifications verified ground truth.
"""
import importlib.util
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).parents[1] / "src" / "profile_procurement_categories.py"
spec = importlib.util.spec_from_file_location("profile_procurement_categories", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def map_record(title: str, classification: str):
    row = pd.Series({
        "tenderclassification/description": classification,
        "tender/title": title,
    })
    return module.infer_record_niche(row)


def assert_candidate(title: str, classification: str, expected_niche: str):
    niche, method, rationale, review = map_record(title, classification)
    assert niche == expected_niche, (title, classification, niche, expected_niche, rationale)
    assert method == "TITLE_KEYWORD_CANDIDATE"
    assert review == "YES"
    assert "Original" in rationale or "Title" in rationale or "Title contains" in rationale


def test_coal_label_road_improvement_uses_title():
    assert_candidate("Improvement of Noltoli Jawani Road", "Coal", "Construction & Civil Infrastructure")


def test_coal_label_road_construction_uses_title():
    assert_candidate("Construction of Road with earth filling", "Coal", "Construction & Civil Infrastructure")


def test_chemical_label_street_light_uses_electrical_niche():
    assert_candidate(
        "Renovation of utility Service (Street Light) in NH-37",
        "Chemicals/Minerals",
        "Electrical, Energy & Utilities",
    )


def test_musical_instruments_label_electrification_uses_electrical_niche():
    assert_candidate(
        "INTERNAL AND EXTERNAL ELECTRIFICATION WORKS AT DHUPDHARA P.S.",
        "Entertainment/Musical Instruments",
        "Electrical, Energy & Utilities",
    )


def test_paddy_transplanter_label_vaccine_uses_healthcare():
    assert_candidate("RATE CONTRACT TO SUPPLY JE VACCINE", "Paddy Transplanter", "Healthcare & Laboratory")


def test_multi_crop_thresher_label_cardiology_equipment_uses_healthcare():
    assert_candidate(
        "Supply and installation of equipment related to Cardiology Department",
        "Multi-crop Thresher",
        "Healthcare & Laboratory",
    )


def test_explosive_label_high_mast_lighting_uses_electrical():
    assert_candidate(
        "Installation of High Mast Lighting System at various locations",
        "Explosive",
        "Electrical, Energy & Utilities",
    )


def test_security_service_is_not_computer_hardware():
    assert_candidate("TENDER FOR HIRING PRIVATE SECURITY SERVICE", "Security System", "Safety & Security Systems")


def test_outsourcing_security_services_uses_safety_security():
    assert_candidate("Out Sourcing of Security Services", "Security System", "Safety & Security Systems")


def test_hiring_godown_is_property_space():
    assert_candidate("E-Tender for Hiring Godown", "Allotment of Space", "Property, Space & Facilities")


def test_cold_storage_lease_is_property_space():
    assert_candidate("LEASING OF THE MULTI-COMMODITY COLD STORAGE", "Allotment of Space", "Property, Space & Facilities")


def test_advertising_agency_is_media_creative():
    assert_candidate(
        "Empanelment of Creative and Advertising Agency",
        "Photostat Services",
        "Media, Printing & Creative Services",
    )


def test_medical_tender_with_photostat_label_is_healthcare():
    assert_candidate(
        "For engagement of super specialty hospital for carrying out liver transplant in children",
        "Photostat Services",
        "Healthcare & Laboratory",
    )


def test_vehicle_disposal_auction_is_left_unresolved():
    niche, method, rationale, review = map_record("Dispose off vehicles through auction system", "Photostat Services")
    assert niche == "Other / Needs Review"
    assert method == "TITLE_KEYWORD_CANDIDATE" or method == "UNRESOLVED"
    assert review == "YES"


def test_vehicle_tracking_is_computer_network_candidate():
    assert_candidate("ASTC Vehicle Tracking RFP", "Security System", "Computer, Network & Electronics")


def test_chemical_dosing_title_gets_chemical_niche():
    assert_candidate(
        "Biennial Contract for Supply of Chemicals Dosing and Maintenance of Cooling Tower Water",
        "Chemicals/Minerals",
        "Chemicals & Industrial Materials",
    )


def test_high_risk_source_labels_are_review_only_at_label_level():
    for label in ["Coal", "Security System", "Photostat Services", "Explosive"]:
        niche, rationale, status = module.suggest_niche(label)
        assert niche == "Other / Needs Review"
        assert status == "REVIEW"


def test_normal_source_label_can_still_use_source_classification():
    row = pd.Series({
        "tenderclassification/description": "Civil Works",
        "tender/title": "Construction of a village road",
    })
    niche, method, rationale, review = module.infer_record_niche(row)
    assert niche == "Construction & Civil Infrastructure"
    assert method == "SOURCE_CLASSIFICATION"
    assert review == "SAMPLE_REVIEW"
