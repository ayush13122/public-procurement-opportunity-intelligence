"""Run the project's pytest suite through a Python entry point.

Run from project root: python src/run_project_tests.py
"""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
# Ensure imports like `from src.run_procurement_eda import ...` resolve reliably
# when this file is launched from IntelliJ or any working directory.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    raise SystemExit(pytest.main(["-q", str(ROOT / "tests")]))
