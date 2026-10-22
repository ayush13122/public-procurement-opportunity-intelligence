from pathlib import Path
import pandas as pd
import pytest

from app.market_explorer_data import filter_market_data, get_filter_options, load_market_data, summarize_market


def sample_data():
    return pd.DataFrame([
        {
            "ocid": "ocid-1", "fiscal_year": "2020-2021", "tender/title": "Road repair",
            "tender/mainProcurementCategory": "Works", "tenderclassification/description": "Civil Works",
            "buyer/name": "Public Works Department", "tender/datePublished": "2020-06-01 10:00:00",
            "tender/stage": "AOC", "tender/value/amount": 100000,
            "suggested_analytical_niche": "Construction & Civil Infrastructure", "mapping_method": "SOURCE_CLASSIFICATION",
            "mapping_rationale": "Source label suggests civil works", "manual_review_required": "NO", "tender/numberOfTenderers": 5,
        },
        {
            "ocid": "ocid-2", "fiscal_year": "2021-2022", "tender/title": "Supply of computers",
            "tender/mainProcurementCategory": "Goods", "tenderclassification/description": "Computer-H/W",
            "buyer/name": "Education Department", "tender/datePublished": "2021-07-01 10:00:00",
            "tender/stage": "To be Opened", "tender/value/amount": 0,
            "suggested_analytical_niche": "Computer, Network & Electronics", "mapping_method": "TITLE_KEYWORD_CANDIDATE",
            "mapping_rationale": "Title suggests computer equipment", "manual_review_required": "YES", "tender/numberOfTenderers": None,
        },
        {
            "ocid": "ocid-3", "fiscal_year": "2021-2022", "tender/title": "General supply contract",
            "tender/mainProcurementCategory": "Goods", "tenderclassification/description": "Miscellaneous Goods",
            "buyer/name": "Education Department", "tender/datePublished": "2021-08-01 10:00:00",
            "tender/stage": None, "tender/value/amount": None,
            "suggested_analytical_niche": "Other / Needs Review", "mapping_method": "UNRESOLVED",
            "mapping_rationale": None, "manual_review_required": "YES", "tender/numberOfTenderers": None,
        },
    ])


def test_get_filter_options_returns_dimensions():
    data = sample_data()
    options = get_filter_options(data)
    assert options["categories"] == ["Goods", "Works"]
    assert "Computer, Network & Electronics" in options["niches"]
    assert options["fiscal_years"] == ["2020-2021", "2021-2022"]


def test_filter_by_title_is_case_insensitive_literal():
    data = sample_data()
    result = filter_market_data(data, title_search="COMPUTERS")
    assert result["ocid"].tolist() == ["ocid-2"]


def test_filter_by_category_niche_and_year():
    data = sample_data()
    result = filter_market_data(data, categories=["Goods"], niches=["Computer, Network & Electronics"], fiscal_years=["2021-2022"])
    assert result["ocid"].tolist() == ["ocid-2"]


def test_excluding_review_records_removes_flagged_entries():
    data = sample_data()
    result = filter_market_data(data, include_review_required=False)
    assert result["ocid"].tolist() == ["ocid-1"]


def test_value_filters_exclude_missing_values_and_respect_bounds():
    data = sample_data()
    result = filter_market_data(data, min_value=1, max_value=150000)
    assert result["ocid"].tolist() == ["ocid-1"]


def test_summary_separates_positive_zero_missing_and_review_counts():
    summary = summarize_market(sample_data())
    assert summary["records"] == 3
    assert summary["buyers"] == 2
    assert summary["positive_value_records"] == 1
    assert summary["zero_value_records"] == 1
    assert summary["missing_value_records"] == 1
    assert summary["review_required_records"] == 2
    assert summary["median_positive_value"] == 100000


def test_load_market_data_joins_one_to_one_and_preserves_all_records(tmp_path: Path):
    root = tmp_path
    (root / "data/processed").mkdir(parents=True)
    (root / "reports").mkdir()
    source = sample_data().drop(columns=["suggested_analytical_niche", "mapping_method", "mapping_rationale", "manual_review_required"])
    assignments = sample_data()[["ocid", "suggested_analytical_niche", "mapping_method", "mapping_rationale", "manual_review_required"]]
    source.to_csv(root / "data/processed/assam_procurement_cleaned.csv", index=False)
    assignments.to_csv(root / "reports/assam_record_niche_assignments.csv", index=False)
    loaded = load_market_data(root)
    assert len(loaded) == 3
    assert loaded["ocid"].is_unique
    assert loaded["tender_value_numeric"].tolist()[:2] == [100000, 0]


def test_load_market_data_rejects_duplicate_ocid(tmp_path: Path):
    root = tmp_path
    (root / "data/processed").mkdir(parents=True)
    (root / "reports").mkdir()
    source = sample_data().drop(columns=["suggested_analytical_niche", "mapping_method", "mapping_rationale", "manual_review_required"])
    source = pd.concat([source, source.iloc[[0]]], ignore_index=True)
    assignments = sample_data()[["ocid", "suggested_analytical_niche"]]
    source.to_csv(root / "data/processed/assam_procurement_cleaned.csv", index=False)
    assignments.to_csv(root / "reports/assam_record_niche_assignments.csv", index=False)
    with pytest.raises(ValueError, match="duplicate OCIDs"):
        load_market_data(root)
