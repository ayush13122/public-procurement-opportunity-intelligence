"""
Audit the taxonomy review workbook and generate a review-action report.
This script does not modify the workbook, cleaned dataset, or current taxonomy outputs.
Run from the project root:
    python src/audit_taxonomy_workbook.py
"""
from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = PROJECT_ROOT / "reports" / "taxonomy_review" / "Taxonomy_Review_Workbook.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "taxonomy_review" / "workbook_audit"

# These are review observations, not automatic final classifications.
# They are based on titles and proposed niches in the supplied review workbook.
MANUAL_REVIEW_RULES = [
    {
        "rule_id": "KW001",
        "match": r"sale out of the taken over assets.*publishing company|publishing company private limited",
        "finding": "The word 'Publishing' appears to be part of a company name in an asset-sale tender, not the procured deliverable.",
        "recommended_action": "Do not classify by this keyword alone; inspect full title/documents and use Property/Assets or Other/Needs Review if confirmed.",
        "priority": "HIGH",
        "area": "keyword false positive",
    },
    {
        "rule_id": "KW002",
        "match": r"books and journals.*medical institute",
        "finding": "The buyer is medical-related, but the deliverable is books and journals. Buyer sector and supplier/deliverable niche are not the same.",
        "recommended_action": "Classify by the procured deliverable (publishing/education supplies) unless the tender is specifically a healthcare service.",
        "priority": "MEDIUM",
        "area": "buyer-vs-deliverable mismatch",
    },
    {
        "rule_id": "KW003",
        "match": r"supply of housekeeping and household items",
        "finding": "The title appears to procure physical items; it may not be a housekeeping service contract.",
        "recommended_action": "Review as Goods / household supplies unless the complete notice includes facility-service obligations.",
        "priority": "MEDIUM",
        "area": "goods-vs-service ambiguity",
    },
    {
        "rule_id": "KW004",
        "match": r"e-tender for hiring godown|hiring godown",
        "finding": "A godown rental/hiring notice can be property/space rental or logistics storage, so title-only logistics mapping is ambiguous.",
        "recommended_action": "Keep manual review or apply a multi-axis tag (property/space + storage/logistics) after checking the notice.",
        "priority": "MEDIUM",
        "area": "cross-niche ambiguity",
    },
    {
        "rule_id": "KW005",
        "match": r"supply,installation and maintenance of compute items|supply.*compute items.*data center",
        "finding": "The tender may combine hardware supply and IT operations; 'data center' alone does not prove software services.",
        "recommended_action": "Review deliverables; use Computer/Network/Electronics for hardware or IT/Software Services for service/software components.",
        "priority": "MEDIUM",
        "area": "hardware-vs-service ambiguity",
    },
    {
        "rule_id": "KW006",
        "match": r"networking structure cabling system and it infrastructure|system integrator",
        "finding": "Network cabling/infrastructure is not necessarily software development.",
        "recommended_action": "Prefer Computer/Network/Electronics or a network-infrastructure tag when physical cabling/network setup is the main deliverable.",
        "priority": "MEDIUM",
        "area": "hardware-vs-service ambiguity",
    },
    {
        "rule_id": "KW007",
        "match": r"biomining segregation of legacy waste",
        "finding": "Legacy-waste processing, trommels and allied infrastructure are environmental/waste-management work, not generic consultancy/manpower.",
        "recommended_action": "Use Water, Sanitation & Environmental Services, with Works/Services retained as the original procurement type.",
        "priority": "HIGH",
        "area": "likely niche mismatch",
    },
    {
        "rule_id": "KW008",
        "match": r"for hiring.*private security service|security service",
        "finding": "A security manpower service should not be classified as computer/network equipment just because the source label is Security System.",
        "recommended_action": "Use Safety & Security Services for guard/manpower contracts; reserve Computer/Network/Electronics for security devices/systems.",
        "priority": "HIGH",
        "area": "source-label-vs-title conflict",
    },
    {
        "rule_id": "KW009",
        "match": r"uniform of religious madrassa|uniforms?",
        "finding": "Uniforms/apparel are not general office supplies in supplier-capability terms.",
        "recommended_action": "Consider a Textiles, Uniforms & Apparel niche or map to a carefully defined General Goods group.",
        "priority": "MEDIUM",
        "area": "taxonomy design",
    },
    {
        "rule_id": "KW010",
        "match": r"sports goods|foot ball and volley ball|sports goods/equipments",
        "finding": "Sports goods are not office supplies.",
        "recommended_action": "Consider a Sports & Recreation Supplies niche, or keep under General Goods only if deliberately broad.",
        "priority": "MEDIUM",
        "area": "taxonomy design",
    },
    {
        "rule_id": "KW011",
        "match": r"paddy transplanter|multi-crop thresher",
        "finding": "The original source label suggests agricultural machinery but the displayed sample titles appear unrelated, indicating possible source-label/title inconsistencies.",
        "recommended_action": "Do not approve at label level; review these individual records against their OCID and original tender title.",
        "priority": "HIGH",
        "area": "source-data consistency",
    },
    {
        "rule_id": "KW012",
        "match": r"coal|explosive|entertainment/musical instruments|chemicals/minerals",
        "finding": "Some low-frequency source labels have sample titles that appear unrelated to the label.",
        "recommended_action": "Keep the affected records flagged until record-level source consistency is checked; do not assign niche from label alone.",
        "priority": "HIGH",
        "area": "source-data consistency",
    },
    {
        "rule_id": "KW013",
        "match": r"medical institute|medical college|hospital",
        "finding": "Buyer identity alone can over-influence sector classification when the tender is for unrelated goods.",
        "recommended_action": "Prioritise deliverable/title classification; store buyer-sector as a separate field if useful.",
        "priority": "MEDIUM",
        "area": "taxonomy design",
    },
]

def normalise(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()

def load_sheets() -> dict[str, pd.DataFrame]:
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(
            f"Workbook not found: {WORKBOOK_PATH}\n"
            "Copy the latest Taxonomy_Review_Workbook.xlsx to reports/taxonomy_review/."
        )
    xls = pd.ExcelFile(WORKBOOK_PATH, engine="openpyxl")
    return {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}

def make_action_rows(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    actions = []
    for sheet_name in ("Keyword_Candidate_Sample", "Unresolved_Sample", "Source_Label_Review"):
        df = sheets.get(sheet_name)
        if df is None or df.empty:
            continue
        # Source-label sheets keep sample titles in sample_tender_titles/sample_titles_for_review.
        if sheet_name == "Source_Label_Review":
            title_col = "sample_tender_titles"
            niche_col = "suggested_analytical_niche"
            label_col = "original_classification"
            rows = df.to_dict("records")
            text_field_col = "sample_tender_titles"
        else:
            title_col = "tender/title"
            niche_col = "suggested_analytical_niche"
            label_col = "tenderclassification/description"
            rows = df.to_dict("records")
            text_field_col = "tender/title"

        for row in rows:
            title_text = normalise(row.get(text_field_col, ""))
            label_text = normalise(row.get(label_col, ""))
            niche_text = normalise(row.get(niche_col, ""))
            context = " ".join([title_text, label_text, niche_text, normalise(row.get("mapping_rationale", ""))])
            for rule in MANUAL_REVIEW_RULES:
                if re.search(rule["match"], context, flags=re.IGNORECASE):
                    actions.append({
                        "source_sheet": sheet_name,
                        "rule_id": rule["rule_id"],
                        "priority": rule["priority"],
                        "area": rule["area"],
                        "original_classification": label_text,
                        "tender_title_or_sample_titles": title_text[:1500],
                        "current_suggested_niche": niche_text,
                        "finding": rule["finding"],
                        "recommended_action": rule["recommended_action"],
                    })
                    break
    if not actions:
        return pd.DataFrame(columns=[
            "source_sheet","rule_id","priority","area","original_classification",
            "tender_title_or_sample_titles","current_suggested_niche","finding","recommended_action"
        ])
    return pd.DataFrame(actions).drop_duplicates()

def main() -> int:
    print("Auditing taxonomy review workbook...")
    sheets = load_sheets()
    required = {"Source_Label_Review", "Keyword_Candidate_Sample", "Unresolved_Sample",
                "All_Flagged_Records", "Niche_Counts", "Mapping_Methods"}
    missing = required - set(sheets)
    if missing:
        raise ValueError(f"Workbook is missing required sheets: {sorted(missing)}")

    source = sheets["Source_Label_Review"]
    candidates = sheets["Keyword_Candidate_Sample"]
    unresolved = sheets["Unresolved_Sample"]
    flagged = sheets["All_Flagged_Records"]
    niche_counts = sheets["Niche_Counts"]
    methods = sheets["Mapping_Methods"]

    actions = make_action_rows(sheets)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    actions_path = OUTPUT_DIR / "taxonomy_manual_review_actions.csv"
    actions.to_csv(actions_path, index=False, encoding="utf-8-sig")

    report = [
        "# Taxonomy Workbook Audit",
        "",
        "This report reviews candidate mapping risks visible in the workbook. It does not approve or overwrite any classifications.",
        "",
        "## Workbook counts",
        f"- Source-label rows: {len(source):,}",
        f"- Candidate sample rows: {len(candidates):,}",
        f"- Unresolved sample rows: {len(unresolved):,}",
        f"- All flagged records: {len(flagged):,}",
        f"- Niche-count rows: {len(niche_counts):,}",
        f"- Mapping-method rows: {len(methods):,}",
        "",
        "## Current mapping-method counts",
        methods.to_markdown(index=False),
        "",
        "## Highest-count provisional niches",
        niche_counts.sort_values("records", ascending=False).head(12).to_markdown(index=False),
        "",
        "## Manual review actions detected from sample evidence",
        f"- Action rows written: {len(actions):,}",
        "",
        "See `taxonomy_manual_review_actions.csv` for the tender titles, current suggestions, issue type, and recommended review action.",
        "",
        "## Recommendations",
        "1. Keep the original broad category and original detailed classification unchanged.",
        "2. Treat the suggested analytical niche as provisional until reviewed; mapping coverage is not classification accuracy.",
        "3. Classify primarily from the actual deliverable/tender title and documents, not buyer name or accidental words in an organisation name.",
        "4. Keep procurement type (Works/Goods/Services) as a separate axis from supplier/business niche.",
        "5. Use `Other / Needs Review` for conflicting or insufficient evidence rather than forcing a category.",
        "6. For mixed tenders (e.g., IT hardware + support), allow multiple tags or a primary niche plus a secondary capability tag.",
        "7. Do not infer current bid availability, profit, or win probability from historical classification data alone.",
        "",
    ]
    report_path = OUTPUT_DIR / "TAXONOMY_WORKBOOK_AUDIT.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"Source labels: {len(source):,}")
    print(f"Candidate sample rows: {len(candidates):,}")
    print(f"Unresolved sample rows: {len(unresolved):,}")
    print(f"Flagged records: {len(flagged):,}")
    print(f"Review action rows: {len(actions):,}")
    print(f"Report: {report_path}")
    print(f"Action CSV: {actions_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
