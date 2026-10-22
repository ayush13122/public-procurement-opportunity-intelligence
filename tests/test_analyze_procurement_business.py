import sys
from pathlib import Path

import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
import analyze_procurement_business as analysis


def sample_frame():
    return pd.DataFrame({
        "ocid": ["a", "b", "c", "d"],
        "fiscal_year": ["2020-2021", "2020-2021", "2021-2022", "2021-2022"],
        "tender/mainProcurementCategory": ["Goods", "Services", "Works", "Goods"],
        "tenderclassification/description": ["Computer-H/W", "Consultancy", "Civil Works", "Miscellaneous Goods"],
        "tender/title": ["Laptop supply", "Software support", "Road repairs", "Stationery"],
        "buyer/name": ["Buyer A", "Buyer A", "Buyer B", "Buyer B"],
        "tender/value/amount": ["12,00,000", "0", "NA", "250000"],
        "tender/datePublished": ["2020-08-01", "2020-09-02", "bad date", "2021-07-01"],
        "tender/stage": ["AOC", "Cancelled", "To be Opened", None],
        "tender/numberOfTenderers": ["3", "0", "NA", "2"],
    })


def sample_assignments():
    return pd.DataFrame({
        "ocid": ["a", "b", "c", "d"],
        "suggested_analytical_niche": ["Computer, Network & Electronics", "IT & Software Services", "Construction & Civil Infrastructure", None],
        "mapping_method": ["SOURCE_CLASSIFICATION", "TITLE_KEYWORD_CANDIDATE", "SOURCE_CLASSIFICATION", "UNRESOLVED"],
        "manual_review_required": ["NO", "YES", "NO", "YES"],
    })


def test_parse_amount_indian_grouping_and_zeros():
    result = analysis.parse_amount(pd.Series(["12,00,000", "0", "NA", "-5"]))
    assert result.iloc[0] == 1200000
    assert result.iloc[1] == 0
    assert pd.isna(result.iloc[2])
    assert result.iloc[3] == -5


def test_share_handles_zero_total():
    assert analysis.share(5, 10) == 50.0
    assert analysis.share(5, 0) == 0.0


def test_join_is_one_to_one_and_flags():
    joined, diag = analysis.load_and_join_from_frames(sample_frame(), sample_assignments())
    assert len(joined) == 4
    assert diag["unmatched_assignments"] == 0
    assert diag["positive_values"] == 2
    assert diag["zero_values"] == 1
    assert diag["missing_values"] == 1
    assert diag["records_needing_niche_review"] == 2


def test_category_profile_counts():
    joined, _ = analysis.load_and_join_from_frames(sample_frame(), sample_assignments())
    profile = analysis.category_profile(joined).set_index("main_category")
    assert profile.loc["Goods", "records"] == 2
    assert profile.loc["Goods", "record_share_pct"] == 50.0


def test_niche_profile_marks_unresolved_as_other():
    joined, _ = analysis.load_and_join_from_frames(sample_frame(), sample_assignments())
    profile = analysis.niche_profile(joined).set_index("suggested_niche")
    assert "Other / Needs Review" in profile.index
    assert profile.loc["Other / Needs Review", "records"] == 1


def test_duplicate_ids_raise_error():
    cleaned = pd.concat([sample_frame(), sample_frame().iloc[[0]]], ignore_index=True)
    try:
        analysis.load_and_join_from_frames(cleaned, sample_assignments())
    except ValueError as exc:
        assert "OCID must be unique" in str(exc)
    else:
        raise AssertionError("Expected duplicate OCIDs to raise ValueError")
