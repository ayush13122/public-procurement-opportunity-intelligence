"""Check the project Python environment and expected files.

Run from the project root:
    python src/check_environment.py
This script only checks; it does not install or modify packages.
"""
from __future__ import annotations
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "terminal_checks"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

PACKAGES = {
    "pandas": "pandas",
    "numpy": "numpy",
    "plotly": "plotly",
    "streamlit": "streamlit",
    "scikit-learn": "sklearn",
    "openpyxl": "openpyxl",
    "pytest": "pytest",
    "tabulate": "tabulate",
}
EXPECTED = [
    "requirements.txt",
    "data/raw/datasets_of_assam_public_procurement_data_7259310.zip",
    "data/processed/assam_procurement_cleaned.csv",
    "reports/assam_record_niche_assignments.csv",
    "reports/eda/EDA_SUMMARY.md",
    "reports/taxonomy_review/TAXONOMY_REVIEW_SUMMARY.md",
]


def main() -> int:
    lines = ["# Environment Check", "", f"- Python version: `{sys.version.split()[0]}`",
             f"- Python executable: `{sys.executable}`", f"- Project root: `{ROOT}`", "", "## Packages", ""]
    print("=== PYTHON ENVIRONMENT ===")
    print("Python version:", sys.version.split()[0])
    print("Python executable:", sys.executable)
    print("Project root:", ROOT)
    missing = []
    for display_name, module_name in PACKAGES.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "version not exposed")
            status = f"OK ({version})"
        except Exception as exc:  # report broken/missing imports without crashing the whole check
            status = f"MISSING / ERROR ({type(exc).__name__}: {exc})"
            missing.append(display_name)
        print(f"{display_name}: {status}")
        lines.append(f"- {display_name}: {status}")
    lines.extend(["", "## Expected Project Files", ""])
    absent = []
    for rel in EXPECTED:
        exists = (ROOT / rel).exists()
        print(f"{'OK' if exists else 'MISSING'}: {rel}")
        lines.append(f"- {'OK' if exists else 'MISSING'}: `{rel}`")
        if not exists:
            absent.append(rel)
    lines += ["", "## Summary", "", f"- Missing/broken packages: {len(missing)}", f"- Missing expected files: {len(absent)}", ""]
    out = REPORT_DIR / "environment_check.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\nReport saved:", out)
    return 1 if missing or absent else 0


if __name__ == "__main__":
    raise SystemExit(main())
