"""Inspect the EDA summary and list the generated analysis artifacts.

Run from project root: python src/inspect_eda_outputs.py
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDA_DIR = ROOT / "reports" / "eda"
OUT = ROOT / "reports" / "terminal_checks"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    summary = EDA_DIR / "EDA_SUMMARY.md"
    if not summary.exists():
        print("EDA summary not found. Run src/run_procurement_eda.py first.")
        return 2
    text = summary.read_text(encoding="utf-8", errors="replace")
    files = sorted(p for p in EDA_DIR.rglob("*") if p.is_file())
    listing = ["# EDA Output Inventory", "", f"EDA folder: `{EDA_DIR.relative_to(ROOT)}`", "", "## Files", ""]
    listing.extend(f"- `{p.relative_to(ROOT)}` ({p.stat().st_size:,} bytes)" for p in files)
    listing += ["", "## EDA Summary Contents", "", text, ""]
    out = OUT / "eda_output_inventory.md"
    out.write_text("\n".join(listing), encoding="utf-8")
    print("=== EDA SUMMARY ===\n")
    print(text)
    print("\n=== GENERATED FILES ===")
    for p in files:
        print(f"{p.relative_to(ROOT)} | {p.stat().st_size:,} bytes")
    print("\nInventory saved:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
