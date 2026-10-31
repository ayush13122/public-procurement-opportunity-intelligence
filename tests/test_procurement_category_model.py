from pathlib import Path
import sys

import pandas as pd
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
import train_procurement_category_model as ml


def sample_data():
    rows = [
        ("a", "2020-2021", "Road construction work", "Works"),
        ("b", "2020-2021", "Bridge construction repair", "Works"),
        ("c", "2020-2021", "Supply desktop computer", "Goods"),
        ("d", "2020-2021", "Purchase computer equipment", "Goods"),
        ("e", "2020-2021", "Consultancy services contract", "Services"),
        ("f", "2020-2021", "Professional consultancy support", "Services"),
        ("g", "2021-2022", "Road building and repair", "Works"),
        ("h", "2021-2022", "Supply office laptops", "Goods"),
        ("i", "2021-2022", "Consultancy and advisory service", "Services"),
    ]
    return pd.DataFrame(rows, columns=["ocid", "fiscal_year", "tender/title", "tender/mainProcurementCategory"])


def test_validate_input_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        ml.validate_input_frame(pd.DataFrame({"tender/title": ["title"]}))


def test_validate_input_rejects_unknown_category():
    df = sample_data()
    df.loc[0, "tender/mainProcurementCategory"] = "Unknown"
    with pytest.raises(ValueError, match="Unexpected target categories"):
        ml.validate_input_frame(df)


def test_preparation_keeps_only_rows_with_title_year_and_known_label():
    df = sample_data()
    df.loc[len(df)] = ["j", "", "Missing year", "Goods"]
    df.loc[len(df)] = ["k", "2020-2021", "", "Works"]
    prepared = ml.prepare_model_frame(df)
    assert len(prepared) == len(sample_data())
    assert prepared["tender/title"].ne("").all()
    assert prepared["fiscal_year"].ne("").all()


def test_chronological_split_holds_out_later_fiscal_year():
    data = ml.prepare_model_frame(sample_data())
    train, test = ml.split_chronologically(data, "2021-2022")
    assert set(train["fiscal_year"]) == {"2020-2021"}
    assert set(test["fiscal_year"]) == {"2021-2022"}
    assert len(train) == 6
    assert len(test) == 3


def test_chronological_split_fails_if_category_missing_from_test():
    df = sample_data()
    df = df.loc[~((df["fiscal_year"] == "2021-2022") & (df["tender/mainProcurementCategory"] == "Services"))]
    data = ml.prepare_model_frame(df)
    with pytest.raises(ValueError, match="All categories must occur in both train and test"):
        ml.split_chronologically(data, "2021-2022")


def test_pipeline_uses_tfidf_and_balanced_logistic_regression():
    pipeline = ml.build_classifier()
    assert pipeline.named_steps["tfidf"].ngram_range == (1, 2)
    assert pipeline.named_steps["classifier"].class_weight == "balanced"
    assert pipeline.named_steps["classifier"].max_iter == 1500
