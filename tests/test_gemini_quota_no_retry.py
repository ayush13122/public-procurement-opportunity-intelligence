import pytest

from app.gemini_runtime import GeminiProviderUnavailableError, generate_content_with_retry


def test_quota_exhaustion_is_not_retried(monkeypatch):
    monkeypatch.setenv("GEMINI_TENDER_MAX_RETRIES", "3")

    class Models:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            raise RuntimeError("429 RESOURCE_EXHAUSTED: You exceeded your current quota. Requests per day limit reached.")

    class Client:
        def __init__(self):
            self.models = Models()

    client = Client()
    with pytest.raises(GeminiProviderUnavailableError, match="Further retries were skipped"):
        generate_content_with_retry(client, model="model", contents="question", config={})
    assert client.models.calls == 1


def test_503_is_still_retried(monkeypatch):
    monkeypatch.setenv("GEMINI_TENDER_MAX_RETRIES", "1")
    monkeypatch.setenv("GEMINI_TENDER_RETRY_BASE_SECONDS", "0")

    class Models:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("503 UNAVAILABLE: high demand")
            return type("Response", (), {"text": "ok"})()

    class Client:
        def __init__(self):
            self.models = Models()

    client = Client()
    result = generate_content_with_retry(client, model="model", contents="question", config={})
    assert result.text == "ok"
    assert client.models.calls == 2


def test_wrapped_provider_quota_message_is_recognized_by_ui_latch():
    from app.gemini_runtime import is_quota_exhaustion_error

    exc = GeminiProviderUnavailableError(
        "Gemini quota is exhausted for the current limit window. Further retries were skipped."
    )
    assert is_quota_exhaustion_error(exc)


def test_transient_503_is_not_retried_by_default_for_fast_local_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_TENDER_MAX_RETRIES", raising=False)

    class Models:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            raise RuntimeError("503 UNAVAILABLE: high demand")

    class Client:
        def __init__(self):
            self.models = Models()

    client = Client()
    with pytest.raises(GeminiProviderUnavailableError, match="one request was made"):
        generate_content_with_retry(client, model="model", contents="question", config={})
    assert client.models.calls == 1


def test_gemini_client_disables_sdk_retry(monkeypatch):
    import sys
    import types as pytypes

    captured = {}

    class FakeRetryOptions:
        def __init__(self, *, attempts):
            captured["attempts"] = attempts

    class FakeHttpOptions:
        def __init__(self, *, retry_options):
            captured["retry_options"] = retry_options

    class FakeClient:
        def __init__(self, *, api_key, http_options):
            captured["api_key"] = api_key
            captured["http_options"] = http_options

    google_module = pytypes.ModuleType("google")
    google_module.__path__ = []
    genai_module = pytypes.ModuleType("google.genai")
    genai_module.Client = FakeClient
    sdk_types = pytypes.ModuleType("google.genai.types")
    sdk_types.HttpRetryOptions = FakeRetryOptions
    sdk_types.HttpOptions = FakeHttpOptions
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", sdk_types)

    from app.gemini_runtime import create_gemini_client

    client = create_gemini_client("test-key")
    assert isinstance(client, FakeClient)
    assert captured["api_key"] == "test-key"
    assert captured["attempts"] == 1


def test_old_gemini_sdk_gives_actionable_optional_upgrade_message(monkeypatch):
    import sys
    import types as pytypes

    google_module = pytypes.ModuleType("google")
    google_module.__path__ = []
    genai_module = pytypes.ModuleType("google.genai")
    genai_module.Client = object
    sdk_types = pytypes.ModuleType("google.genai.types")
    sdk_types.HttpOptions = object
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", sdk_types)

    from app.gemini_runtime import create_gemini_client

    with pytest.raises(GeminiProviderUnavailableError, match="requirements-gemini.txt"):
        create_gemini_client("test-key")


def test_non_quota_429_error_reports_actual_attempt_count(monkeypatch):
    monkeypatch.delenv("GEMINI_TENDER_MAX_RETRIES", raising=False)

    class Models:
        calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            raise RuntimeError("429 rate limit temporarily exceeded")

    client = type("Client", (), {"models": Models()})()
    with pytest.raises(GeminiProviderUnavailableError, match="one request was made"):
        generate_content_with_retry(client, model="model", contents="question", config={})
    assert client.models.calls == 1
