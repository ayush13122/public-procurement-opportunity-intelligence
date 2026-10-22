"""Category profiling and provisional niche-mapping audit for Assam procurement data.

Run from the project root:
    python src/profile_procurement_categories.py

The script reads the original ZIP from data/raw and writes reproducible profiling
reports under reports/. Niche labels are suggestions for human review, not ground truth.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORT_DIR = PROJECT_ROOT / "reports"
EXPECTED_MEMBER = "ocds_mapped_procurement_data_fiscal_year_2016_2017.csv"

# Regex patterns provide provisional candidate niches only. Specific products/services are
# prioritized over generic context words; ambiguous labels remain flagged for manual review.
NICHE_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("Construction & Civil Infrastructure", re.compile(
        r"civil works|construction works|composite works|pipe laying|water works|"
        r"roads?|bridges?|highways?|canal|lift irrigation|civil construction goods", re.I),
        "Classification explicitly refers to civil works/construction/infrastructure."),
    ("IT & Software Services", re.compile(
        r"information technology|infotech|computer-?\s*s/?w|computer-?\s*data processing|"
        r"computer-?\s*manpower", re.I),
        "Classification explicitly refers to IT, software, data processing or IT manpower."),
    ("Computer, Network & Electronics", re.compile(
        r"computer-?\s*h/?w|network\s*/?\s*communication|electronics equipment|"
        r"audio-visual equipment|digital podium|security system|surveillance equipment", re.I),
        "Classification refers to computer hardware, networking or electronic systems."),
    ("Healthcare & Laboratory", re.compile(
        r"medical|medicines|suture|surgical|hospital|lab chemistry|laboratory|x ray|x-ray|"
        r"industrial/medical gas|consumables \(hospital", re.I),
        "Classification refers to healthcare, medicines, medical or laboratory supplies."),
    ("Agriculture & Forestry", re.compile(
        r"agricultural|forestry|crop products|fertili[sz]er|pesticide|paddy|transplanter|"
        r"farm machinery|power tiller|thresher", re.I),
        "Classification refers to agriculture, crops, forestry or farm equipment."),
    ("Electrical, Energy & Utilities", re.compile(
        r"electrical|power/energy|energy projects|oil/gas|street lighting|pumps/motors|"
        r"air-conditioner", re.I),
        "Classification refers to electrical works, energy, utilities or related equipment."),
    ("Transport & Logistics", re.compile(
        r"vehicles?/vehicle spares|shipping/ transportation|cargo / containers|aviation|warehouse", re.I),
        "Classification refers to vehicles, transport, logistics, storage or aviation."),
    ("Industrial Machinery & Equipment", re.compile(
        r"machiner|mechanical engg|metal fabrication|mining|coal|air compressor|weighing system|"
        r"explosive|water equipments?/ meter/ drilling/ boring", re.I),
        "Classification refers to machinery, industrial equipment or specialist operations."),
    ("Safety & Security Systems", re.compile(
        r"fire & safety|security system|surveillance equipment", re.I),
        "Classification refers to safety, security or surveillance."),
    ("Architecture & Technical Design", re.compile(
        r"architecture/interior design|survey", re.I),
        "Classification refers to architecture, interior design or technical survey."),
    ("Chemicals & Industrial Materials", re.compile(
        r"chemicals/minerals|industrial materials", re.I),
        "Classification refers to chemicals, minerals or general materials; verify intended use."),
    ("Food & Catering", re.compile(
        r"food products|hotel/ catering", re.I),
        "Classification refers to food supply or catering/hospitality."),
    ("Office & General Supplies", re.compile(
        r"furniture|fixture|stationery|uniforms|curtains|clothes|sports goods|"
        r"miscellaneous goods|civil construction goods", re.I),
        "Classification refers to general, office, furniture, clothing or recreational goods."),
    ("Media, Printing & Creative Services", re.compile(
        r"publishing/printing|photostat|documentary film|video film|entertainment/musical", re.I),
        "Classification refers to printing, copying, media or creative services."),
    ("Professional & Business Services", re.compile(
        r"consultancy|manpower supply|repair and maintenance|housekeeping|cleaning|"
        r"supply/erection/commissioning services|miscellaneous services", re.I),
        "Classification refers to professional, manpower, maintenance or facility services."),
]


AMBIGUOUS_LABELS = {
    "miscellaneous goods", "miscellaneous works", "miscellaneous services",
    "miscellaneous", "other", "other services",
}

# Source labels flagged by the semantic consistency audit. Keep their original
# values intact, but force record-level title review before accepting a niche.
HIGH_RISK_SOURCE_LABELS = {
    "security system",
    "photostat services",
    "entertainment/musical instruments",
    "chemicals/minerals",
    "coal",
    "paddy transplanter",
    "multi-crop thresher",
    "explosive",
}

# Used only when the original classification label is generic/ambiguous.
# Keep short tokens such as LAN word-bounded: unbounded "lan" matches words like "plant".
# Ordering prioritizes clearer, more specific business themes before general terms.
TITLE_NICHE_RULES: list[tuple[str, re.Pattern[str], str]] = [
    # Specific service/product phrases are ordered before broad infrastructure terms.
    ("IT & Software Services", re.compile(
        r"software development|customized software|software package|application development|"
        r"web portal|website|information technology|e-governance|e governance|digital platform|"
        r"data processing|data centre|data center|cloud service|erp solution|cyber security|"
        r"it infrastructure|antivirus|computer-based test|computer based test|"
        r"platform for (?:tracking|monitoring|inspection)|tracking and inspection of civil works",
        re.I),
        "Title contains software/digital/IT service terms; verify against the notice."),
    ("Healthcare & Laboratory", re.compile(
        r"medicine|medicines|drug supply|drugs|medical|hospital|health centre|healthcare|"
        r"surgical|suture|diagnostic|laboratory|lab equipment|x-ray|vaccine|vaccination|"
        r"immuni[sz]ation|pharma|patient|routine immunization|cardiology|cardiac|cardiovascular", re.I),
        "Title contains healthcare, medical, pharmaceutical, vaccination or laboratory terms; verify notice."),
    ("Chemicals & Industrial Materials", re.compile(
        r"chemical dosing|chemicals dosing|supply of chemicals|chemical treatment|"
        r"chemicals and maintenance of cooling tower|cooling tower water treatment chemical",
        re.I),
        "Title explicitly refers to chemicals/dosing or chemical treatment; verify notice and service scope."),
    # Service-led solicitations should not be classified as agriculture merely because the context mentions it.
    ("Professional & Business Services", re.compile(
        r"consultancy|consultant|implementation support agency|technical support agency|"
        r"support services|manpower|recruitment process|staffing|professional services|"
        r"training services|training providers|onsite training|outsourcing|appointment of agency",
        re.I),
        "Title contains consultancy, staffing, training or business-support terms; verify notice."),
    ("Agriculture & Forestry", re.compile(
        r"hybrid seed|seeds|fertili[sz]er|soil amendment|plant protection material|"
        r"planting material|seedling|paddy|forestry|farm equipment|power tiller|thresher|"
        r"pesticide|crop protection|micro irrigation|drip irrigation|agricultural implements",
        re.I),
        "Title contains agriculture products, seeds, fertilizers, crop protection or farm-equipment terms; verify notice."),
    ("Food & Catering", re.compile(
        r"food product|food supply|catering|canteen|meal supply|mid[- ]day meal|ration supply|"
        r"supply of rice|supply of dal|supply of flour|kitchen services", re.I),
        "Title contains food-supply or catering terms; verify notice."),
    ("Media, Printing & Creative Services", re.compile(
        r"coffee[- ]table book|printing materials|printing|print and supply|publication|publishing|"
        r"question paper|photostat|photocopy|calendar|documentary film|video film|booklet|"
        r"advertising agency|creative and advertising|creative agency|marketing agency",
        re.I),
        "Title contains publication, printing, copying, media or creative-service terms; verify notice."),
    ("Water, Sanitation & Environmental Services", re.compile(
        r"cleaning and desilting|desilting of|city drains?|drain cleaning|drain desilting|"
        r"sewage treatment|sewage treatment plant|wastewater|waste water|solid waste|"
        r"compost and rdf plant|rdf plant|landfill|storm water drainage|sewerage works|"
        r"waste management", re.I),
        "Title concerns drainage, sewage, waste treatment or environmental services; verify notice."),
    ("Property, Space & Facilities", re.compile(
        r"monthly (?:lease|rent|rental)|lease\s*/\s*rent|lease or rent|monthly lease/rent|"
        r"rental price of (?:the )?(?:factory )?building|rent(?:al)? of (?:the )?(?:factory )?building|"
        r"lease of (?:the )?(?:factory )?building|leasing of (?:the )?(?:factory )?building|"
        r"rent of guest house|rent of weigh bridge|truck parking yard|allotment of space|"
        r"hiring\s+(?:of\s+)?(?:the\s+)?(?:godown|warehouse|office accommodation|guest house|building|premises)|"
        r"leasing of (?:the )?(?:multi-commodity )?cold storage|"
        r"leasing of (?:the )?.{0,50}\bspace\b|"
        r"renting of (?:the )?premises|office accommodation on lease basis", re.I),
        "Title describes rental, lease, allotment or use of property/space; verify notice."),
    ("Transport & Logistics", re.compile(
        r"transport|transporter|reverse logistics|logistics|vehicle hiring|truck hiring|"
        r"freight|carriage of|bus hiring|fleet service|godown|warehouse|"
        r"\bvessel\b|\bferry\b|\bbarge\b|\bspeed boat\b|\bmarine\b|\bwatercraft\b|"
        r"shipping service", re.I),
        "Title contains transport, marine-vessel, logistics or storage-service terms; verify notice."),
    ("Safety & Security Systems", re.compile(
        r"security service|security guard|surveillance|cctv|fire safety|fire fighting|alarm system", re.I),
        "Title contains safety, security or surveillance terms; verify notice."),
    ("Electrical, Energy & Utilities", re.compile(
        r"electrical|electricity|transformer|solar power|solar panel|power supply|wiring|"
        r"street light|lighting system|substation|generator|energy project", re.I),
        "Title contains electrical, power, energy or utility terms; verify notice."),
    ("Architecture & Technical Design", re.compile(
        r"architectural planning|architectural design|comprehensive architectural|"
        r"planning, designing and construction supervision|topographic survey|technical survey",
        re.I),
        "Title contains architectural planning, design or technical survey terms; verify notice."),
    # Office/product deliverables should beat generic context words like 'Irrigation Division'.
    ("Office & General Supplies", re.compile(
        r"office furniture|office stationery|office chair|office table|stationery|furniture|"
        r"uniform|curtains|school books|textbook|exercise book|question book|office supplies|"
        r"sports goods|supply of books", re.I),
        "Title contains office, education or general-supply product terms; verify notice."),
    ("Computer, Network & Electronics", re.compile(
        r"desktop computer|computer hardware|computer peripherals|laptop|server|network|"
        r"\blan\b|router|switches|electronic equipment|electronics|ups system|printer|workstation|"
        r"fibre optic|fiber optic|4g/3g data connectivity|data connectivity|vehicle tracking", re.I),
        "Title contains computer hardware, networking, telecommunications or electronics terms; verify notice."),
    ("Industrial Machinery & Equipment", re.compile(
        r"machinery|machine|compressive testing machine|air compressor|pump|motor|cnc|fabrication|"
        r"weighing system|drilling equipment|industrial equipment|furnace system|cremation furnace",
        re.I),
        "Title contains industrial machinery or specialist equipment terms; verify notice."),
    ("Construction & Civil Infrastructure", re.compile(
        r"\bcivil works?\b|\bcivil infrastructure\b|"
        r"\broad construction\b|\broad works?\b|\broad repair\b|\broad widening\b|"
        r"\b(?:improvement|upgradation|widening|repair|maintenance|renovation)\s+of\b.{0,80}\broads?\b|"
        r"\bconstruction of (?:roads?|bridges?|buildings?|houses?|culverts?|canals?|embankments?|"
        r"foot over bridges?|toilet blocks?|schools?|hospitals?|residential buildings?|retaining walls?)\b|"
        r"\bbuilding construction\b|\bbridge construction\b|\bfoot over bridges?\b|"
        r"\bculverts?\b|\bdrainage works?\b|\bembankments?\b|\bpavements?\b|\bpipe laying\b|"
        r"\bstructural works?\b|\brenovation of (?:buildings?|roads?|bridges?|schools?|hospitals?)\b|"
        r"\bconstruction of (?:sewage treatment|compost|rdf)\b", re.I),
        "Title contains explicit civil/infrastructure construction or maintenance terms; verify notice."),
    ("Housekeeping & Facilities Services", re.compile(
        r"housekeeping|cleaning staff|sanitation staff|pest control|facility management|"
        r"office cleaning|campus cleaning", re.I),
        "Title contains housekeeping or facilities-service terms; verify notice."),
]


def find_source_zip() -> Path:
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser()
        if candidate.is_file() and candidate.suffix.lower() == ".zip":
            return candidate
        raise FileNotFoundError(f"ZIP path not found: {candidate}")

    candidates = sorted(RAW_DIR.glob("*.zip")) if RAW_DIR.exists() else []
    for candidate in candidates:
        try:
            with zipfile.ZipFile(candidate) as archive:
                names = archive.namelist()
            if any(EXPECTED_MEMBER in name for name in names):
                return candidate
        except (OSError, zipfile.BadZipFile):
            continue
    raise FileNotFoundError(
        "Source ZIP not found. Put the Assam procurement ZIP in data/raw/, "
        "or run: python src/profile_procurement_categories.py <full-path-to-zip>"
    )


def suggest_niche(label: str) -> tuple[str, str, str]:
    value = str(label or "").strip()
    normalized = re.sub(r"\\s+", " ", value).casefold()
    if normalized == "supply of materials":
        return "Materials & General Supplies", "Generic label; inspect titles to determine the material type.", "REVIEW"
    if normalized in {"packaging", "textile"}:
        return "Materials & Manufacturing Supplies", "Broad product label; verify the actual goods from title/details.", "REVIEW"
    if normalized == "allotment of space":
        return "Property, Space & Facilities", "Source label indicates allotment/space; verify what is being allocated.", "REVIEW"
    if normalized in AMBIGUOUS_LABELS or "miscellaneous" in normalized:
        return "Other / Needs Review", "Ambiguous or miscellaneous source label; do not force a niche.", "REVIEW"
    if normalized in HIGH_RISK_SOURCE_LABELS:
        return (
            "Other / Needs Review",
            "High-risk source label flagged by the record-level consistency audit; classify each record using its title and verify the original notice.",
            "REVIEW",
        )
    for niche, pattern, reason in NICHE_RULES:
        if pattern.search(value):
            return niche, reason, "PROVISIONAL"
    return "Other / Needs Review", "No explicit mapping rule matched this source label.", "REVIEW"


def infer_record_niche(row: pd.Series) -> tuple[str, str, str, str]:
    """Return (niche, method, rationale, review flag) without modifying source labels."""
    label = str(row.get("tenderclassification/description", "") or "").strip()
    title = str(row.get("tender/title", "") or "").strip()
    normalized_label = re.sub(r"\s+", " ", label).casefold()
    normalized_title = re.sub(r"\s+", " ", title).strip()

    # Explicit high-confidence title overrides are still candidates, not ground truth.
    # They apply only to source labels flagged in the semantic consistency audit.
    explicit_override: tuple[str, str] | None = None

    if normalized_label == "allotment of space" and re.search(
        r"hiring\s+(?:of\s+)?(?:the\s+)?godown|lease|leasing|rent|rental|"
        r"office accommodation|cold storage|parking yard|floor space|building",
        normalized_title, re.I,
    ):
        explicit_override = (
            "Property, Space & Facilities",
            "Title and source label indicate property/space leasing, rental or allocation.",
        )
    elif normalized_label == "coal" and re.search(
        r"\b(?:road|roads|highway|highways|bridge|bridges)\b", normalized_title, re.I
    ) and re.search(r"improvement|construction|repair|widening|renovation|earth filling", normalized_title, re.I):
        explicit_override = (
            "Construction & Civil Infrastructure",
            "Title clearly describes road/bridge works; source label 'Coal' conflicts.",
        )
    elif normalized_label == "chemicals/minerals" and re.search(
        r"street light|street lighting|high mast lighting|electrification works", normalized_title, re.I
    ):
        explicit_override = (
            "Electrical, Energy & Utilities",
            "Title clearly describes lighting/electrification works; source label 'Chemicals/Minerals' conflicts.",
        )
    elif normalized_label == "entertainment/musical instruments" and re.search(
        r"electrification works|street light|street lighting|high mast lighting", normalized_title, re.I
    ):
        explicit_override = (
            "Electrical, Energy & Utilities",
            "Title clearly describes electrical/lighting works; source classification conflicts.",
        )
    elif normalized_label == "paddy transplanter" and re.search(
        r"\bvaccines?\b|\bimmuni[sz]ation\b", normalized_title, re.I
    ):
        explicit_override = (
            "Healthcare & Laboratory",
            "Title clearly describes vaccine/immunization procurement; source label 'Paddy Transplanter' conflicts.",
        )
    elif normalized_label == "multi-crop thresher" and re.search(
        r"cardiology|cardiac|medical equipment|hospital equipment", normalized_title, re.I
    ):
        explicit_override = (
            "Healthcare & Laboratory",
            "Title clearly describes medical/cardiology equipment; source label 'Multi-crop Thresher' conflicts.",
        )
    elif normalized_label == "explosive" and re.search(
        r"high mast lighting|street light|street lighting|electrification works", normalized_title, re.I
    ):
        explicit_override = (
            "Electrical, Energy & Utilities",
            "Title clearly describes lighting/electrical work; source label 'Explosive' conflicts.",
        )
    elif normalized_label == "photostat services" and re.search(
        r"liver transplant|cardiology|medical equipment|hospital equipment", normalized_title, re.I
    ):
        explicit_override = (
            "Healthcare & Laboratory",
            "Title describes a clinical/medical service or equipment; source label 'Photostat Services' conflicts.",
        )
    elif normalized_label == "photostat services" and re.search(
        r"dispose\s+off\s+vehicles?|sale\s+of\s+used\s+vehicles?|vehicles?\s+through\s+auction",
        normalized_title, re.I
    ):
        explicit_override = (
            "Other / Needs Review",
            "Title describes vehicle/asset disposal by auction rather than photocopy/printing services.",
        )
    elif normalized_label == "security system" and re.search(
        r"private security service|security services|security personnel|security guards?",
        normalized_title, re.I
    ) and not re.search(r"cctv|surveillance system|drone", normalized_title, re.I):
        explicit_override = (
            "Safety & Security Systems",
            "Title describes human security services/personnel rather than an electronic security system.",
        )

    if explicit_override is not None:
        niche, reason = explicit_override
        return (
            niche,
            "TITLE_KEYWORD_CANDIDATE",
            reason + " Original source classification is preserved; verify the tender notice.",
            "YES",
        )

    label_niche, label_reason, label_status = suggest_niche(label)
    if label_status != "REVIEW":
        return label_niche, "SOURCE_CLASSIFICATION", label_reason, "SAMPLE_REVIEW"
    for niche, pattern, reason in TITLE_NICHE_RULES:
        if pattern.search(title):
            return niche, "TITLE_KEYWORD_CANDIDATE", reason, "YES"
    return "Other / Needs Review", "UNRESOLVED", "Neither the source classification nor title produced a reliable first-pass niche.", "YES"


def main() -> None:
    source_zip = find_source_zip()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip) as archive:
        members = sorted(
            name for name in archive.namelist()
            if name.lower().endswith(".csv")
            and "ocds_mapped_procurement_data_fiscal_year_" in name
        )
        if not members:
            raise ValueError("No expected fiscal-year CSV files found in the ZIP.")
        frames = []
        for member in members:
            with archive.open(member) as stream:
                part = pd.read_csv(stream, low_memory=False)
            part["_source_file"] = Path(member).name
            frames.append(part)
    df = pd.concat(frames, ignore_index=True, sort=False)

    required = [
        "ocid", "fiscal_year", "tender/title", "tender/mainProcurementCategory",
        "tenderclassification/description", "tender/value/amount", "tender/datePublished",
        "tender/stage", "buyer/name", "tender/numberOfTenderers",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Required fields are missing: {missing}")

    broad = "tender/mainProcurementCategory"
    classification = "tenderclassification/description"
    title = "tender/title"
    amount = pd.to_numeric(
        df["tender/value/amount"].astype("string").str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )
    published = pd.to_datetime(df["tender/datePublished"], errors="coerce")
    df["_amount_numeric"] = amount
    df["_published_date_parsed"] = published

    # File-level coverage and original category mix.
    year_profile = (
        df.groupby("fiscal_year", dropna=False)
        .agg(
            records=("ocid", "size"),
            unique_ocids=("ocid", "nunique"),
            published_date_available=("_published_date_parsed", "count"),
            tender_value_numeric=("_amount_numeric", "count"),
            tender_value_zero=("_amount_numeric", lambda s: int((s == 0).sum())),
        )
        .reset_index()
        .sort_values("fiscal_year")
    )
    year_profile.to_csv(REPORT_DIR / "assam_year_profile.csv", index=False)

    broad_profile = (
        df.groupby(broad, dropna=False)
        .agg(records=("ocid", "size"), unique_classifications=(classification, "nunique"),
             unique_buyers=("buyer/name", "nunique"))
        .reset_index()
        .sort_values("records", ascending=False)
    )
    broad_profile["record_pct"] = (broad_profile["records"] / len(df) * 100).round(2)
    broad_profile.to_csv(REPORT_DIR / "assam_broad_category_profile.csv", index=False)

    # Full classification cross-tab by original broad category.
    cross = pd.crosstab(df[classification].fillna("[MISSING CLASSIFICATION]"),
                        df[broad].fillna("[MISSING BROAD CATEGORY]"), margins=False)
    cross["TOTAL"] = cross.sum(axis=1)
    cross = cross.sort_values("TOTAL", ascending=False).reset_index()
    cross.to_csv(REPORT_DIR / "assam_classification_by_broad_category.csv", index=False)

    # Top title examples help the person validating the mapping distinguish ambiguous labels.
    sample_titles: dict[str, str] = {}
    for label, group in df.groupby(classification, dropna=False, sort=False):
        examples = group[title].dropna().astype(str).str.strip()
        examples = examples[examples.ne("")].drop_duplicates().head(3).tolist()
        sample_titles[str(label)] = " || ".join(examples)

    counts = df[classification].fillna("[MISSING CLASSIFICATION]").value_counts(dropna=False)
    class_rows = []
    for label, count in counts.items():
        label_str = str(label)
        niche, rationale, status = suggest_niche(label_str)
        group = df[df[classification].fillna("[MISSING CLASSIFICATION]") == label]
        main_counts = group[broad].value_counts(dropna=False)
        dominant_category = str(main_counts.index[0]) if len(main_counts) else "[MISSING]"
        if len(main_counts) > 1:
            dominant_share = float(main_counts.iloc[0] / len(group) * 100)
        else:
            dominant_share = 100.0 if len(group) else 0.0
        class_rows.append({
            "original_classification": label_str,
            "record_count": int(count),
            "record_pct": round(int(count) / len(df) * 100, 2),
            "dominant_main_category": dominant_category,
            "dominant_category_pct_within_label": round(dominant_share, 2),
            "suggested_analytical_niche": niche,
            "mapping_rationale": rationale,
            "mapping_status": status,
            "sample_titles_for_review": sample_titles.get(label_str, ""),
        })
    niche_review = pd.DataFrame(class_rows).sort_values("record_count", ascending=False)
    niche_review.to_csv(REPORT_DIR / "assam_niche_mapping_review.csv", index=False)

    # Apply class-level suggestions first; use title keywords only for generic/ambiguous labels.
    # Keep original source fields unchanged so suggested labels are auditable.
    mapped = df.apply(infer_record_niche, axis=1, result_type="expand")
    mapped.columns = ["suggested_analytical_niche", "mapping_method", "mapping_rationale", "manual_review_required"]
    record_columns = [
        "ocid", "fiscal_year", "tender/title", "tender/mainProcurementCategory",
        "tenderclassification/description", "buyer/name", "tender/value/amount",
        "tender/datePublished", "tender/stage", "tender/numberOfTenderers",
    ]
    record_assignments = df[record_columns].copy()
    record_assignments["tender_value_numeric"] = amount
    record_assignments = pd.concat([record_assignments, mapped], axis=1)
    record_assignments.to_csv(REPORT_DIR / "assam_record_niche_assignments.csv", index=False)

    niche_distribution = (
        record_assignments.groupby(["suggested_analytical_niche", "mapping_method"], dropna=False)
        .agg(records=("ocid", "size"), unique_buyers=("buyer/name", "nunique"),
             records_with_value=("tender_value_numeric", "count"))
        .reset_index()
        .sort_values("records", ascending=False)
    )
    niche_distribution["record_pct"] = (niche_distribution["records"] / len(record_assignments) * 100).round(2)
    niche_distribution.to_csv(REPORT_DIR / "assam_record_niche_distribution.csv", index=False)
    top_record_groups = niche_distribution.groupby("suggested_analytical_niche", as_index=False)["records"].sum().sort_values("records", ascending=False)
    record_group_lines = "\n".join(
        f"| {row.suggested_analytical_niche} | {int(row.records):,} | {int(row.records) / len(df) * 100:.2f}% |"
        for row in top_record_groups.itertuples(index=False)
    )
    mapping_methods = record_assignments["mapping_method"].value_counts()

    # Field coverage by original category, to see what can support deeper analysis.
    coverage_fields = [
        "tender/value/amount", "tender/datePublished", "tender/tenderPeriod/durationInDays",
        "tender/numberOfTenderers", "tender/stage", "tender/milestones/dueDate",
        "tender/bidOpening/date", "tender/documents/id", "buyer/name",
    ]
    coverage_rows = []
    for category, group in df.groupby(broad, dropna=False):
        for field in coverage_fields:
            nonmissing = int(group[field].notna().sum()) if field in group else 0
            coverage_rows.append({
                "main_procurement_category": category,
                "field": field,
                "records": len(group),
                "non_missing": nonmissing,
                "missing": len(group) - nonmissing,
                "non_missing_pct": round(nonmissing / len(group) * 100, 2) if len(group) else 0,
            })
    pd.DataFrame(coverage_rows).to_csv(REPORT_DIR / "assam_field_coverage_by_category.csv", index=False)

    # Concise markdown summary.
    top_class = niche_review.head(15)
    top_lines = "\n".join(
        f"| {r.original_classification} | {int(r.record_count):,} | {r.record_pct:.2f}% | {r.suggested_analytical_niche} | {r.mapping_status} |"
        for r in top_class.itertuples(index=False)
    )
    broad_lines = "\n".join(
        f"| {r[0]} | {int(r[1]):,} | {r[2]:.2f}% | {int(r[3])} |"
        for r in broad_profile[[broad, "records", "record_pct", "unique_classifications"]].itertuples(index=False, name=None)
    )
    reviewed = int((niche_review["mapping_status"] == "REVIEW").sum())
    mapped_records = int(niche_review.loc[niche_review["mapping_status"] == "PROVISIONAL", "record_count"].sum())
    report = f"""# Assam Procurement Category Profiling & Niche Mapping Audit

## Scope
- Source ZIP: `{source_zip.name}`
- Fiscal-year CSV files read: {len(members)}
- Total records: {len(df):,}
- Source columns (excluding temporary audit columns): {len([c for c in df.columns if not c.startswith('_')])}
- Unique OCIDs: {df['ocid'].nunique():,}
- Original classification labels: {df[classification].nunique(dropna=True)}
- Original broad categories: {df[broad].nunique(dropna=True)}

## Original broad-category profile

| Original category | Records | Record % | Unique classification labels |
|---|---:|---:|---:|
{broad_lines}

## Highest-volume original classifications

| Original classification | Records | Record % | Suggested niche | Mapping status |
|---|---:|---:|---|---|
{top_lines}

## First-pass niche mapping status
- Labels provisionally mapped by explicit keyword rules: {int((niche_review['mapping_status'] == 'PROVISIONAL').sum())}
- Records covered by provisional mappings: {mapped_records:,} ({mapped_records / len(df) * 100:.2f}%)
- Labels needing manual review: {reviewed}
- **Important:** provisional means suggested, not verified ground truth. Inspect `assam_niche_mapping_review.csv`, especially `Other / Needs Review`, miscellaneous labels, and the sample titles before finalizing a taxonomy.

## Record-level niche candidates
The script also creates `assam_record_niche_distribution.csv` and `assam_record_niche_assignments.csv`. For generic classification labels only, it uses a transparent title-keyword rule to suggest a candidate niche. Rows remain marked for review; these rule-based suggestions are not verified truth.

## Record-level niche candidates

| Suggested analytical niche | Records | Record % |
|---|---:|---:|
{record_group_lines}

Mapping method counts:
- Source classification candidate: {int(mapping_methods.get('SOURCE_CLASSIFICATION', 0)):,}
- Title-keyword candidate for generic/ambiguous source labels: {int(mapping_methods.get('TITLE_KEYWORD_CANDIDATE', 0)):,}
- Unresolved; inspect manually: {int(mapping_methods.get('UNRESOLVED', 0)):,}

Title-keyword candidates are suggestions, not validated labels. `assam_record_niche_assignments.csv` retains all source fields and a rationale so a reviewer can inspect these suggestions before they power the app.

## Data availability notes
- Tender values are parsed for coverage reporting, but zero amounts and missing amounts must remain separate states.
- A tender stage is not the same as a tender status or proof of award/winning supplier.
- Detailed eligibility terms may be absent from listing-level fields; original tender documents are still needed for shortlisted current opportunities.
- `assam_field_coverage_by_category.csv` shows available fields by broad category. Use it to decide which metrics are defensible.

## Generated reports
- `assam_broad_category_profile.csv`
- `assam_classification_by_broad_category.csv`
- `assam_niche_mapping_review.csv`
- `assam_field_coverage_by_category.csv`
- `assam_year_profile.csv`
"""
    (REPORT_DIR / "assam_category_profiling_summary.md").write_text(report, encoding="utf-8")

    print("Category profiling complete.")
    print(f"Source: {source_zip.name}")
    print(f"Records: {len(df):,} | source columns: {len([c for c in df.columns if not c.startswith('_')])}")
    print(f"Broad categories: {df[broad].nunique(dropna=True)} | detailed classifications: {df[classification].nunique(dropna=True)}")
    print(f"Provisional mapping coverage: {mapped_records:,} records ({mapped_records / len(df) * 100:.2f}%)")
    print(f"Labels to review manually: {reviewed}")
    print(f"Record-level niche candidates written: {len(record_assignments):,}")
    print(f"Reports saved to: {REPORT_DIR}")


if __name__ == "__main__":
    main()
