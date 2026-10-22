"""Tests for the record-level source classification consistency audit."""
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from audit_source_classification_consistency import (  # noqa: E402
    HIGH_RISK_SOURCE_LABELS,
    GENERIC_LABEL_SAMPLE_SIZES,
    build_joined_audit,
    create_review_queue,
    normalize_text,
)


def test_normalize_text_handles_whitespace_and_case():
    assert normalize_text("  Plant   Protection MATERIALS ") == "plant protection materials"
    assert normalize_text(None) == ""
    assert normalize_text(float("nan")) == ""


def test_join_preserves_rows_and_adds_mapping():
    raw = pd.DataFrame({
        "ocid": ["1", "2"],
        "fiscal_year": ["2020-2021", "2021-2022"],
        "tender/title": ["Road construction", "Medical gas pipeline"],
        "tender/mainProcurementCategory": ["Works", "Goods"],
        "tenderclassification/description": ["Coal", "Industrial/Medical GAS"],
        "buyer/name": ["Dept A", "Dept B"],
        "tender/value/amount": ["100", "200"],
        "tender/datePublished": ["2020-01-01", "2021-01-01"],
        "tender/stage": ["AOC", "AOC"],
        "tender/numberOfTenderers": ["2", "3"],
    })
    assignments = pd.DataFrame({
        "ocid": ["1", "2"],
        "tender/title": ["Road construction", "Medical gas pipeline"],
        "tenderclassification/description": ["Coal", "Industrial/Medical GAS"],
        "suggested_analytical_niche": ["Other / Needs Review", "Healthcare & Laboratory"],
        "mapping_method": ["SOURCE_CLASSIFICATION", "SOURCE_CLASSIFICATION"],
        "mapping_rationale": ["review", "review"],
        "manual_review_required": ["YES", "NO"],
    })
    joined = build_joined_audit(raw, assignments)
    assert len(joined) == 2
    assert joined["suggested_analytical_niche"].tolist() == [
        "Other / Needs Review", "Healthcare & Laboratory"
    ]
    assert joined["source_consistency_issue"].eq("").all()
    assert joined["source_label_review_flag"].tolist() == [True, False]


def test_join_fails_on_duplicate_ocids():
    raw = pd.DataFrame({
        "ocid": ["1", "1"],
        "tender/title": ["a", "b"],
        "tenderclassification/description": ["Coal", "Coal"],
    })
    assignments = pd.DataFrame({
        "ocid": ["1"],
        "tender/title": ["a"],
        "tenderclassification/description": ["Coal"],
        "suggested_analytical_niche": ["Other / Needs Review"],
    })
    with pytest.raises(ValueError, match="duplicate OCIDs"):
        build_joined_audit(raw, assignments)


def test_review_queue_includes_all_high_risk_and_samples_generic_deterministically():
    rows = []
    for i in range(30):
        label = "Coal" if i < 2 else "Miscellaneous Goods" if i < 15 else "Miscellaneous Services"
        rows.append({
            "ocid": str(i),
            "tender/title": f"Title {i}",
            "tenderclassification/description": label,
            "source_label_review_flag": label in HIGH_RISK_SOURCE_LABELS,
            "generic_label_sample_flag": label in GENERIC_LABEL_SAMPLE_SIZES,
            "suggested_analytical_niche": "Other / Needs Review",
            "mapping_method": "UNRESOLVED",
            "source_consistency_issue": "",
        })
    joined = pd.DataFrame(rows)
    queue_1 = create_review_queue(joined, random_state=7)
    queue_2 = create_review_queue(joined, random_state=7)
    assert set(queue_1["ocid"]) == set(queue_2["ocid"])
    assert int(queue_1["source_label_review_flag"].sum()) == 2
    assert queue_1["ocid"].is_unique
    assert "reviewer_approved_niche" in queue_1.columns
