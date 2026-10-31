"""Regression tests for refined procurement title-to-niche rules.

These tests validate candidate classification behavior only. They do not prove
real-world classification accuracy; sampled source notices still need review.
"""
import importlib.util
from pathlib import Path
import pandas as pd

SCRIPT = Path(__file__).parents[1] / "src" / "profile_procurement_categories.py"
spec = importlib.util.spec_from_file_location("profile_procurement_categories", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def map_title(title, classification="Miscellaneous Goods"):
    row = pd.Series({
        "tenderclassification/description": classification,
        "tender/title": title,
    })
    return module.infer_record_niche(row)


def assert_candidate(title, expected_niche, classification="Miscellaneous Goods"):
    niche, method, rationale, review = map_title(title, classification)
    assert niche == expected_niche, (title, niche, expected_niche, rationale)
    assert method == "TITLE_KEYWORD_CANDIDATE"
    assert review == "YES"


def test_plant_protection_materials_is_agriculture():
    assert_candidate("THE SUPPLY OF PLANT PROTECTION MATERIALS", "Agriculture & Forestry")


def test_factory_building_rental_is_property():
    assert_candidate(
        "Monthly Rental Price of Factory Building erstwhile Multi Fruit Processing Plant",
        "Property, Space & Facilities"
    )


def test_short_lan_token_is_word_bounded():
    assert_candidate("Annual maintenance of LAN and network equipment", "Computer, Network & Electronics")


def test_ferry_vessel_is_not_civil_construction():
    assert_candidate(
        "Design, Construction, Supply, Testing and Commissioning of Cruise Ferry Vessel, Floating Steel Barge Pontoon",
        "Transport & Logistics"
    )


def test_monthly_guesthouse_weighbridge_rent_is_property():
    assert_candidate(
        "Monthly Lease or Rent of Guest House, Transshipment Platform and Weigh Bridge",
        "Property, Space & Facilities"
    )


def test_office_supplies_are_not_misclassified_due_to_department_context():
    assert_candidate(
        "Supply of office furniture office stationery and electronic gadgets for set up of the newly created Irrigation Division",
        "Office & General Supplies"
    )


def test_immunization_logistics_is_healthcare_not_transport():
    assert_candidate("Routine Immunization Logistics", "Healthcare & Laboratory")


def test_city_drain_desilting_is_water_sanitation_not_housekeeping():
    assert_candidate(
        "CLEANING, DESILTING AND MAINTENANCE OF ALL CITY DRAINS IN GUWAHATI CITY",
        "Water, Sanitation & Environmental Services"
    )


def test_coffee_table_book_is_media_not_housekeeping():
    assert_candidate(
        "DEVELOPMENT OF COFFEE-TABLE BOOK ON SWACHH ASSAM AND SANITATION CHAMPIONS",
        "Media, Printing & Creative Services"
    )


def test_training_provider_is_business_services_not_construction():
    assert_candidate(
        "EOI from Training Providers for conducting onsite training of Rural Mason for the construction of houses",
        "Professional & Business Services"
    )


def test_digital_tracking_platform_is_it_not_construction():
    assert_candidate(
        "Comprehensive platform for TRACKING and inspection of civil works of the schools",
        "IT & Software Services"
    )


def test_explicit_road_construction_remains_construction():
    assert_candidate("Construction of road from village A to village B", "Construction & Civil Infrastructure")


def test_desktop_computer_is_computer_network():
    assert_candidate("Supply and installation of desktop computer with monitor", "Computer, Network & Electronics")


def test_unmatched_ambiguous_record_remains_review():
    niche, method, rationale, review = map_title("General miscellaneous requirements")
    assert niche == "Other / Needs Review"
    assert method == "UNRESOLVED"
    assert review == "YES"
