"""One-request Gemini diagnostic for this project's current integration.

Run from the repository root:
    .\\.venv\\Scripts\\python.exe tools\\diagnose_gemini.py

The script prints no API key or secret values. It uses the same env variable,
model setting, client factory and JSON response mode as the Copilot extractor.
"""
from __future__ import annotations

import importlib.metadata
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_project_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        print(f"Project .env file: NOT FOUND ({env_path})")
        return

    # Match Streamlit page behavior: python-dotenv, no override of existing env.
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=False)
        print("Project .env file: loaded with python-dotenv")
        return
    except Exception as exc:
        print(f"python-dotenv unavailable ({type(exc).__name__}); using simple .env reader")

    # Small fallback for ordinary KEY=VALUE entries. Does not support every
    # shell interpolation feature; the project's .env should use simple values.
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(name, value)
    print("Project .env file: loaded with fallback reader")


def get_status(exc: BaseException) -> str:
    for attr in ("code", "status_code", "status"):
        value = getattr(exc, attr, None)
        if value is not None:
            return str(value)
    match = re.search(r"\b(400|401|402|403|404|408|429|500|502|503|504)\b", str(exc))
    return match.group(1) if match else "not exposed by SDK"


def main() -> int:
    print("=== PROCUREMENT COPILOT / GEMINI DIAGNOSTIC ===")
    print("Project root:", ROOT)
    print("Python:", sys.executable)
    load_project_env()

    try:
        sdk_version = importlib.metadata.version("google-genai")
        print("google-genai:", sdk_version)
    except importlib.metadata.PackageNotFoundError:
        print("RESULT: SDK_NOT_INSTALLED")
        print("Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements-gemini.txt")
        return 2

    # This is the exact key name used by the current Streamlit page and extractor.
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("RESULT: GEMINI_API_KEY_MISSING")
        print("The current app reads GEMINI_API_KEY specifically from project-root .env.")
        print("GOOGLE_API_KEY present:", bool(os.getenv("GOOGLE_API_KEY", "").strip()))
        print("Add GEMINI_API_KEY=your_key to the existing project-root .env, then restart Streamlit.")
        return 2

    model = os.getenv("GEMINI_TENDER_EXTRACTION_MODEL", "gemini-3.8-flash").strip().strip("\"'")
    print("GEMINI_API_KEY found: YES (value hidden)")
    print("GOOGLE_API_KEY also present:", bool(os.getenv("GOOGLE_API_KEY", "").strip()))
    print("Model used by Copilot:", model)

    client = None
    try:
        # Use this repository's own bounded-retry client factory.
        from app.gemini_runtime import create_gemini_client
        client = create_gemini_client(api_key)

        # Mirrors the actual extractor config (JSON structured output, temperature 0).
        response = client.models.generate_content(
            model=model,
            contents='Return only this JSON object: {"status":"GEMINI_OK"}',
            config={"response_mime_type": "application/json", "temperature": 0},
        )
        response_text = (getattr(response, "text", None) or "").strip()
        if not response_text:
            print("RESULT: EMPTY_RESPONSE")
            print("The API call returned no text. This is not a local PDF/OCR error.")
            return 1

        print("RESULT: SUCCESS")
        print("Model response:", response_text[:300])
        print("Meaning: key + model + SDK + JSON output request all worked in this environment.")
        return 0

    except Exception as exc:
        message = str(exc).replace(api_key, "[REDACTED_API_KEY]")
        message = re.sub(r"AIza[0-9A-Za-z_\\-]{20,}", "[REDACTED_API_KEY]", message)
        print("RESULT: FAILED")
        print("Exception:", type(exc).__name__)
        print("HTTP/API status:", get_status(exc))
        print("Provider error (key redacted):", message[:1800])
        status = get_status(exc)
        if status == "401":
            print("Interpretation: invalid/revoked API key or authentication failure.")
        elif status == "403":
            print("Interpretation: project/API permission, billing or access restriction.")
        elif status == "404":
            print("Interpretation: model/endpoint not found or not available to this project.")
        elif status == "429":
            print("Interpretation: rate limit or quota. The provider message distinguishes the limit type.")
        elif status == "503":
            print("Interpretation: temporary provider overload/unavailability, not a PDF parsing failure.")
        else:
            print("Interpretation: inspect the provider error above; this diagnostic bypasses Streamlit and tests the SDK directly.")
        return 1

    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
