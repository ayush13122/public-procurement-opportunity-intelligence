import json
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.gemini_tender_extractor import (  # noqa: E402
    GeminiNotConfiguredError,
    GeminiResponseError,
    extract_tender_requirements_with_gemini,
)

class FakeResponse:
    def __init__(self, payload):
        self.text = json.dumps(payload)

class FakeModels:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return FakeResponse(self.payload)

class FakeClient:
    def __init__(self, payload=None, error=None):
        self.models = FakeModels(payload, error)


def test_missing_api_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiNotConfiguredError, match="GEMINI_API_KEY"):
        extract_tender_requirements_with_gemini([{"page_number": 1, "text": "Tender title: Example supply."}])


def test_valid_evidence_and_page_numbers_return_review_required_candidate():
    payload = {
        "tender_title": {"value": "Supply of desktop computers", "page_numbers": [1], "evidence": "Tender title: Supply of desktop computers", "ambiguous": False},
        "emd_required_inr": {"value": "26000", "page_numbers": [2], "evidence": "EMD: INR 26,000", "ambiguous": False},
    }
    client = FakeClient(payload)
    pages = [
        {"page_number": 1, "text": "Tender title: Supply of desktop computers"},
        {"page_number": 2, "text": "EMD: INR 26,000"},
    ]
    result = extract_tender_requirements_with_gemini(pages, client=client)
    assert result["tender_title"]["value"] == "Supply of desktop computers"
    assert result["tender_title"]["page_number"] == 1
    assert result["tender_title"]["source"] == "gemini"
    assert "verification required" in result["tender_title"]["status"]
    assert result["emd_required_inr"]["value"] == "26000"
    assert result["target_region"]["value"] == ""
    assert client.models.calls[0]["config"]["response_mime_type"] == "application/json"


def test_unsupported_evidence_or_invalid_page_is_not_accepted():
    payload = {
        "tender_title": {"value": "Guaranteed winner contract", "page_numbers": [99], "evidence": "This quote does not exist", "ambiguous": False},
    }
    result = extract_tender_requirements_with_gemini(
        [{"page_number": 1, "text": "Tender title: Example contract"}], client=FakeClient(payload)
    )
    assert result["tender_title"]["value"] == ""
    assert result["tender_title"]["status"].startswith("Ambiguous")


def test_ambiguous_currency_and_bad_dates_are_left_blank():
    payload = {
        "emd_required_inr": {"value": "2 lakh maybe", "page_numbers": [1], "evidence": "EMD is approximately 2 lakh", "ambiguous": False},
        "closing_date": {"value": "next Friday", "page_numbers": [1], "evidence": "Bid closes next Friday", "ambiguous": False},
    }
    result = extract_tender_requirements_with_gemini(
        [{"page_number": 1, "text": "EMD is approximately 2 lakh. Bid closes next Friday."}], client=FakeClient(payload)
    )
    assert result["emd_required_inr"]["value"] == ""
    assert result["closing_date"]["value"] == ""


def test_invalid_json_response_raises_response_error():
    class BadResponse:
        text = "not json"
    class BadModels:
        def generate_content(self, **kwargs):
            return BadResponse()
    class BadClient:
        models = BadModels()
    with pytest.raises(GeminiResponseError):
        extract_tender_requirements_with_gemini([{"page_number": 1, "text": "Tender notice"}], client=BadClient())


def test_transient_503_is_retried_then_extraction_succeeds(monkeypatch):
    import app.gemini_runtime as runtime
    monkeypatch.setattr(runtime.time, "sleep", lambda *_: None)
    monkeypatch.setenv("GEMINI_TENDER_MAX_RETRIES", "2")

    payload = {
        "tender_title": {"value": "Supply of transmitters", "page_numbers": [1], "evidence": "Tender title: Supply of transmitters", "ambiguous": False},
    }

    class FlakyModels(FakeModels):
        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) < 3:
                raise RuntimeError("503 UNAVAILABLE: model is currently experiencing high demand")
            return FakeResponse(payload)

    class FlakyClient:
        def __init__(self):
            self.models = FlakyModels()

    client = FlakyClient()
    result = extract_tender_requirements_with_gemini(
        [{"page_number": 1, "text": "Tender title: Supply of transmitters"}], client=client
    )
    assert len(client.models.calls) == 3
    assert result["tender_title"]["value"] == "Supply of transmitters"


def test_persistent_503_raises_actionable_provider_message(monkeypatch):
    import app.gemini_runtime as runtime
    monkeypatch.setattr(runtime.time, "sleep", lambda *_: None)
    monkeypatch.setenv("GEMINI_TENDER_MAX_RETRIES", "1")
    class Always503:
        def generate_content(self, **kwargs):
            raise RuntimeError("503 UNAVAILABLE high demand")
    class Client:
        models = Always503()
    with pytest.raises(Exception, match="temporarily overloaded.*503 UNAVAILABLE"):
        extract_tender_requirements_with_gemini(
            [{"page_number": 1, "text": "Tender title: Sample"}], client=Client()
        )
