import pandas as pd


def _count_map(series):
    values = series.astype("string").str.strip()
    values = values.mask(values.isna() | values.eq(""), "Unknown / Missing").astype(str)
    return values.value_counts().to_dict()


def test_count_map_sums_to_row_count():
    series = pd.Series(["Works", "Goods", "Works", None, ""])
    result = _count_map(series)
    assert sum(result.values()) == 5
    assert result["Works"] == 2
    assert result["Goods"] == 1
    assert result["Unknown / Missing"] == 2


def test_latest_niche_counts_are_computed_from_assignments():
    assignments = pd.DataFrame({"suggested_analytical_niche": ["Construction", "IT", "Construction", "Other"]})
    assert _count_map(assignments["suggested_analytical_niche"]) == {"Construction": 2, "IT": 1, "Other": 1}


def test_zero_and_missing_values_are_distinct():
    values = pd.to_numeric(pd.Series([100, 0, None, "NA"]), errors="coerce")
    assert int((values > 0).sum()) == 1
    assert int((values == 0).sum()) == 1
    assert int(values.isna().sum()) == 2
