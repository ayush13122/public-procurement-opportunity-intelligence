from pathlib import Path
import importlib.util

SCRIPT = Path(__file__).resolve().parents[1] / "src" / "audit_taxonomy_workbook.py"
spec = importlib.util.spec_from_file_location("audit_taxonomy_workbook", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_known_risky_pattern_matches_publishing_company_false_positive():
    rule = next(item for item in module.MANUAL_REVIEW_RULES if item["rule_id"] == "KW001")
    assert module.re.search(rule["match"], "Sale out of the taken over assets of M/s Baruah Publishing Company Private Limited", module.re.I)

def test_known_household_items_is_flagged_for_review():
    rule = next(item for item in module.MANUAL_REVIEW_RULES if item["rule_id"] == "KW003")
    assert module.re.search(rule["match"], "NOTICE INVITING QUOTATION FOR SUPPLY OF HOUSEKEEPING AND HOUSEHOLD ITEMS FOR GUEST HOUSE", module.re.I)

def test_known_agri_label_conflict_is_flagged():
    rule = next(item for item in module.MANUAL_REVIEW_RULES if item["rule_id"] == "KW011")
    assert module.re.search(rule["match"], "Supply of vaccine under Paddy Transplanter classification", module.re.I)
