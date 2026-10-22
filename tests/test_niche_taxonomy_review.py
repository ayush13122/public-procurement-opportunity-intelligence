import importlib.util
from pathlib import Path
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "src" / "review_niche_taxonomy.py"
spec = importlib.util.spec_from_file_location("review_niche_taxonomy", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def class_rows():
    return pd.DataFrame([
        {
            "original_classification": "Civil Works", "record_count": 1500, "record_pct": 50.0,
            "dominant_main_category": "Works", "dominant_category_pct_within_label": 100.0,
            "suggested_analytical_niche": "Construction", "mapping_rationale": "Explicit source label",
            "mapping_status": "PROVISIONAL", "sample_titles_for_review": "Road repair || Building",
        },
        {
            "original_classification": "Miscellaneous Goods", "record_count": 40, "record_pct": 1.3,
            "dominant_main_category": "Goods", "dominant_category_pct_within_label": 100.0,
            "suggested_analytical_niche": "Other / Needs Review", "mapping_rationale": "Ambiguous label",
            "mapping_status": "REVIEW", "sample_titles_for_review": "Seed supply || Fertilizer",
        },
    ])


def record_rows():
    return pd.DataFrame([
        {
            "ocid": "1", "tender/title": "Road work", "tender/mainProcurementCategory": "Works",
            "tenderclassification/description": "Civil Works", "buyer/name": "A", "tender/value/amount": 100,
            "tender/datePublished": "2020-01-01", "suggested_analytical_niche": "Construction",
            "mapping_method": "SOURCE_CLASSIFICATION", "mapping_rationale": "Explicit label",
            "manual_review_required": "SAMPLE_REVIEW",
        },
        {
            "ocid": "2", "tender/title": "Unknown contract", "tender/mainProcurementCategory": "Goods",
            "tenderclassification/description": "Miscellaneous Goods", "buyer/name": "B", "tender/value/amount": 0,
            "tender/datePublished": "2020-01-02", "suggested_analytical_niche": "Other / Needs Review",
            "mapping_method": "UNRESOLVED", "mapping_rationale": "No reliable match",
            "manual_review_required": "YES",
        },
    ])


def test_review_queue_preserves_all_classification_rows():
    out = module.build_taxonomy_review_frames(class_rows(), record_rows())
    assert len(out["classification_review_queue"]) == 2
    assert out["classification_review_queue"]["approved_analytical_niche"].eq("").all()


def test_review_records_includes_unresolved_and_flagged_rows():
    out = module.build_taxonomy_review_frames(class_rows(), record_rows())
    assert out["records_requiring_review"]["ocid"].tolist() == ["2"]


def test_high_priority_for_review_label_and_large_classification():
    assert module.priority_for_mapping("REVIEW", 5) == "HIGH"
    assert module.priority_for_mapping("PROVISIONAL", 1000) == "HIGH"
    assert module.priority_for_mapping("PROVISIONAL", 500) == "MEDIUM"
    assert module.priority_for_mapping("PROVISIONAL", 10) == "LOW"


def test_method_summary_counts_records():
    out = module.build_taxonomy_review_frames(class_rows(), record_rows())
    assert int(out["mapping_method_summary"]["record_count"].sum()) == 2
