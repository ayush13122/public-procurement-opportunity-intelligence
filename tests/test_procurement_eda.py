"""Unit tests for the procurement EDA helper functions."""
import pandas as pd

from src.run_procurement_eda import as_numeric, parse_dates, fiscal_sort_key, numeric_group_summary


def test_as_numeric_keeps_zero_and_parses_commas():
    result = as_numeric(pd.Series(["2,50,000", "0", "NA", None]))
    assert result.iloc[0] == 250000
    assert result.iloc[1] == 0
    assert pd.isna(result.iloc[2])
    assert pd.isna(result.iloc[3])


def test_parse_dates_handles_day_first_and_iso():
    result = parse_dates(pd.Series(["31-03-2022 18:50", "2019-04-01 12:00:00", "NA"]))
    assert result.iloc[0].year == 2022 and result.iloc[0].month == 3 and result.iloc[0].day == 31
    assert result.iloc[1].year == 2019 and result.iloc[1].month == 4 and result.iloc[1].day == 1
    assert pd.isna(result.iloc[2])


def test_fiscal_year_ordering():
    values = ["2021-2022", "2016-2017", "2019-2020"]
    assert sorted(values, key=fiscal_sort_key) == ["2016-2017", "2019-2020", "2021-2022"]


def test_numeric_group_summary_separates_missing_zero_and_positive():
    df = pd.DataFrame({"category": ["Goods", "Goods", "Works", "Works"], "amount": [0, 100, None, 500]})
    result = numeric_group_summary(df, ["category"], "amount").set_index("category")
    assert int(result.loc["Goods", "zero_amount_count"]) == 1
    assert int(result.loc["Goods", "positive_amount_count"]) == 1
    assert int(result.loc["Works", "amount_missing_count"]) == 1
    assert int(result.loc["Works", "positive_amount_count"]) == 1
