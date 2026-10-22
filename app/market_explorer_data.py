"""Data-loading and filtering helpers for the Historical Market Explorer.

This module contains no Streamlit UI code, so its data logic can be unit-tested.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable
import re

import pandas as pd


CLEANED_DEFAULT = Path("data/processed/assam_procurement_cleaned.csv")
ASSIGNMENTS_DEFAULT = Path("reports/assam_record_niche_assignments.csv")

BASE_REQUIRED_COLUMNS = [
    "ocid",
    "fiscal_year",
    "tender/title",
    "tender/mainProcurementCategory",
    "tenderclassification/description",
    "buyer/name",
    "tender/datePublished",
    "tender/stage",
    "tender/value/amount",
]
ASSIGNMENT_REQUIRED_COLUMNS = [
    "ocid",
    "suggested_analytical_niche",
]
ASSIGNMENT_OPTIONAL_COLUMNS = [
    "mapping_method",
    "mapping_rationale",
    "manual_review_required",
]


def _clean_text_series(series: pd.Series) -> pd.Series:
    """Normalize blank and NA-like string labels for display/filtering."""
    out = series.astype("string").str.strip()
    return out.mask(out.str.lower().isin({"", "na", "n/a", "n.a.", "nil", "null", "none", "nan", "<na>"}), pd.NA)


def _numeric_value(series: pd.Series) -> pd.Series:
    """Parse tender value without guessing or adding a currency symbol."""
    text = series.astype("string").str.strip()
    text = text.str.replace(",", "", regex=False).str.replace("₹", "", regex=False)
    text = text.str.replace("INR", "", regex=False).str.strip()
    return pd.to_numeric(text, errors="coerce")


def load_market_data(
    project_root: Path | str,
    cleaned_path: Path | str | None = None,
    assignments_path: Path | str | None = None,
) -> pd.DataFrame:
    """Load clean source records and current niche assignments, joined on OCID.

    Does not overwrite or modify either input file. Fails loudly if the join
    could create duplicate records or important fields are missing.
    """
    root = Path(project_root).resolve()
    clean_file = Path(cleaned_path) if cleaned_path else root / CLEANED_DEFAULT
    assignment_file = Path(assignments_path) if assignments_path else root / ASSIGNMENTS_DEFAULT
    if not clean_file.is_absolute():
        clean_file = root / clean_file
    if not assignment_file.is_absolute():
        assignment_file = root / assignment_file

    missing_files = [str(p) for p in (clean_file, assignment_file) if not p.exists()]
    if missing_files:
        raise FileNotFoundError(
            "Required dashboard input file(s) not found:\n- " + "\n- ".join(missing_files)
        )

    source = pd.read_csv(clean_file, low_memory=False)
    assignments = pd.read_csv(assignment_file, low_memory=False)

    missing_source_columns = [c for c in BASE_REQUIRED_COLUMNS if c not in source.columns]
    if missing_source_columns:
        raise ValueError(f"Cleaned dataset is missing required columns: {missing_source_columns}")
    missing_assignment_columns = [c for c in ASSIGNMENT_REQUIRED_COLUMNS if c not in assignments.columns]
    if missing_assignment_columns:
        raise ValueError(f"Niche assignment file is missing required columns: {missing_assignment_columns}")

    for frame, name in ((source, "cleaned dataset"), (assignments, "niche assignment file")):
        if frame["ocid"].isna().any():
            raise ValueError(f"The {name} contains missing OCID values; resolve before dashboarding.")
        if frame["ocid"].duplicated().any():
            duplicate_count = int(frame["ocid"].duplicated(keep=False).sum())
            raise ValueError(f"The {name} contains {duplicate_count} rows with duplicate OCIDs.")

    assignment_keep = ["ocid", "suggested_analytical_niche"] + [
        c for c in ASSIGNMENT_OPTIONAL_COLUMNS if c in assignments.columns
    ]
    assignment_slim = assignments[assignment_keep].copy()
    merged = source.merge(assignment_slim, on="ocid", how="left", validate="one_to_one", indicator=True)
    unmatched_count = int((merged["_merge"] != "both").sum())
    if unmatched_count:
        raise ValueError(
            f"{unmatched_count} cleaned records do not have a matching niche assignment. "
            "Regenerate the niche assignment file before opening the dashboard."
        )
    merged = merged.drop(columns="_merge")

    # Normalize dimensions; preserve source columns as provided in the clean file.
    for col in [
        "fiscal_year", "tender/title", "tender/mainProcurementCategory",
        "tenderclassification/description", "buyer/name", "tender/stage",
        "suggested_analytical_niche", "mapping_method", "mapping_rationale",
        "manual_review_required",
    ]:
        if col in merged.columns:
            merged[col] = _clean_text_series(merged[col])

    merged["tender_value_numeric"] = _numeric_value(merged["tender/value/amount"])
    merged["publication_date_parsed"] = pd.to_datetime(
        merged["tender/datePublished"], errors="coerce", dayfirst=True
    )
    if "tender/numberOfTenderers" in merged.columns:
        merged["tenderers_numeric"] = pd.to_numeric(merged["tender/numberOfTenderers"], errors="coerce")
    else:
        merged["tenderers_numeric"] = pd.NA

    # Explicit display labels for unknown dimension values.
    for col in [
        "fiscal_year", "tender/mainProcurementCategory", "tenderclassification/description",
        "buyer/name", "tender/stage", "suggested_analytical_niche",
    ]:
        if col in merged.columns:
            merged[col] = merged[col].fillna("Unknown / Not supplied")

    if "manual_review_required" not in merged.columns:
        merged["manual_review_required"] = "UNKNOWN"
    else:
        merged["manual_review_required"] = merged["manual_review_required"].fillna("UNKNOWN").astype(str).str.upper()

    return merged


def get_filter_options(data: pd.DataFrame) -> dict[str, list[str]]:
    """Return stable sorted filter options for the UI."""
    option_columns = {
        "categories": "tender/mainProcurementCategory",
        "niches": "suggested_analytical_niche",
        "fiscal_years": "fiscal_year",
        "stages": "tender/stage",
        "buyers": "buyer/name",
    }
    options: dict[str, list[str]] = {}
    for key, column in option_columns.items():
        if column not in data.columns:
            options[key] = []
        else:
            values = data[column].dropna().astype(str).unique().tolist()
            options[key] = sorted(values, key=str.casefold)
    return options


def _with_derived_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with numeric amount and normalized review fields available.

    This also lets the filtering helpers accept small DataFrames in tests and
    future imported data, not only frames returned by load_market_data().
    """
    out = data.copy()
    if "tender_value_numeric" not in out.columns:
        if "tender/value/amount" in out.columns:
            out["tender_value_numeric"] = _numeric_value(out["tender/value/amount"])
        else:
            out["tender_value_numeric"] = pd.Series(pd.NA, index=out.index, dtype="Float64")
    else:
        out["tender_value_numeric"] = pd.to_numeric(out["tender_value_numeric"], errors="coerce")
    if "manual_review_required" not in out.columns:
        out["manual_review_required"] = "UNKNOWN"
    return out


def filter_market_data(
    data: pd.DataFrame,
    *,
    categories: Iterable[str] | None = None,
    niches: Iterable[str] | None = None,
    fiscal_years: Iterable[str] | None = None,
    stages: Iterable[str] | None = None,
    buyer_search: str = "",
    title_search: str = "",
    include_review_required: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
) -> pd.DataFrame:
    """Filter records using optional selections; empty selections mean all."""
    filtered = _with_derived_columns(data)
    categorical_filters = [
        ("tender/mainProcurementCategory", categories),
        ("suggested_analytical_niche", niches),
        ("fiscal_year", fiscal_years),
        ("tender/stage", stages),
    ]
    for column, selected in categorical_filters:
        if selected:
            filtered = filtered[filtered[column].astype(str).isin(set(map(str, selected)))]

    if buyer_search.strip():
        filtered = filtered[
            filtered["buyer/name"].astype("string").str.contains(
                buyer_search.strip(), case=False, regex=False, na=False
            )
        ]
    if title_search.strip():
        filtered = filtered[
            filtered["tender/title"].astype("string").str.contains(
                title_search.strip(), case=False, regex=False, na=False
            )
        ]

    if not include_review_required and "manual_review_required" in filtered.columns:
        review_values = filtered["manual_review_required"].astype(str).str.upper()
        filtered = filtered[~review_values.isin({"YES", "TRUE", "1", "Y"})]

    if min_value is not None:
        filtered = filtered[filtered["tender_value_numeric"].notna() & (filtered["tender_value_numeric"] >= min_value)]
    if max_value is not None:
        filtered = filtered[filtered["tender_value_numeric"].notna() & (filtered["tender_value_numeric"] <= max_value)]
    return filtered.copy()


def summarize_market(data: pd.DataFrame) -> dict[str, int | float | None]:
    """Calculate truthful summary metrics for the currently filtered view."""
    prepared = _with_derived_columns(data)
    values = pd.to_numeric(prepared.get("tender_value_numeric", pd.Series(dtype=float)), errors="coerce")
    positive = values[values > 0]
    return {
        "records": int(len(prepared)),
        "buyers": int(prepared["buyer/name"].nunique(dropna=True)) if "buyer/name" in prepared else 0,
        "positive_value_records": int((values > 0).sum()),
        "zero_value_records": int((values == 0).sum()),
        "missing_value_records": int(values.isna().sum()),
        "review_required_records": int(prepared["manual_review_required"].astype(str).str.upper().isin({"YES", "TRUE", "1", "Y"}).sum()) if "manual_review_required" in prepared else 0,
        "median_positive_value": float(positive.median()) if not positive.empty else None,
    }
