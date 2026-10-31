"""Small, bounded retry wrapper for transient Google Gemini API failures."""
from __future__ import annotations

import os
import time
from typing import Any


class GeminiProviderUnavailableError(RuntimeError):
    """A transient or service-side Gemini failure that remained after retries."""


def is_transient_gemini_error(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}".casefold()
    return any(token in message for token in (
        "503", "unavailable", "high demand", "spikes in demand", "429",
        "resource_exhausted", "rate limit", "500", "internal server error",
        "temporarily unavailable", "try again later",
    ))


def is_quota_exhaustion_error(exc: Exception) -> bool:
    """Identify quota-exhaustion responses that retries cannot fix immediately."""
    message = f"{type(exc).__name__}: {exc}".casefold()
    hard_quota_signals = (
        "resource_exhausted", "you exceeded your current quota", "quota exceeded", "quota is exhausted",
        "quota exhausted", "requests per day", "request limit per day", "daily limit", "daily quota",
        "limit: 0", "billing account", "free tier quota",
    )
    return any(token in message for token in hard_quota_signals)


def create_gemini_client(api_key: str) -> Any:
    """Create a Gemini client with SDK-level retries disabled.

    The application owns the retry/fallback policy. Leaving the SDK default enabled
    nests up to five HTTP attempts inside each application retry and can make a local
    fallback wait much longer than intended. HttpRetryOptions(attempts=1) means one
    HTTP attempt total, with no SDK retry.
    """
    from google import genai
    from google.genai import types

    retry_options_type = getattr(types, "HttpRetryOptions", None)
    http_options_type = getattr(types, "HttpOptions", None)
    if retry_options_type is None or http_options_type is None:
        raise GeminiProviderUnavailableError(
            "The installed Google Gen AI SDK is too old to disable its built-in retries safely. "
            "To enable Gemini, run `python -m pip install --upgrade -r requirements-gemini.txt`, "
            "then restart Streamlit. Rule-based (offline) mode does not need this optional SDK."
        )
    try:
        http_options = http_options_type(
            retry_options=retry_options_type(attempts=1)
        )
        return genai.Client(api_key=api_key, http_options=http_options)
    except (AttributeError, TypeError) as exc:
        raise GeminiProviderUnavailableError(
            "The installed Google Gen AI SDK does not support the bounded-retry configuration required by this app. "
            "Run `python -m pip install --upgrade -r requirements-gemini.txt`, then restart Streamlit. "
            "Rule-based (offline) mode remains available without Gemini."
        ) from exc


def generate_content_with_retry(
    client: Any,
    *,
    model: str,
    contents: str,
    config: dict[str, Any],
) -> Any:
    """Call Gemini with finite exponential backoff for transient errors only.

    Retries are disabled by default for an interactive app; one failed request falls
    back to local evidence immediately. Set GEMINI_TENDER_MAX_RETRIES=1 only when a
    single bounded retry is operationally preferred. The SDK client is configured
    separately with its own HTTP retries disabled to avoid nested retry loops.
    """
    try:
        retries = int(os.getenv("GEMINI_TENDER_MAX_RETRIES", "0"))
    except ValueError:
        retries = 0
    retries = max(0, min(retries, 4))
    try:
        base_seconds = float(os.getenv("GEMINI_TENDER_RETRY_BASE_SECONDS", "0.5"))
    except ValueError:
        base_seconds = 1.0
    base_seconds = max(0.0, min(base_seconds, 5.0))

    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as exc:
            # Daily quota / RESOURCE_EXHAUSTED is not a transient server overload.
            # Retrying only burns more calls and delays the local fallback.
            if is_quota_exhaustion_error(exc):
                raise GeminiProviderUnavailableError(
                    "Gemini quota is exhausted for the current limit window. Further retries were skipped to "
                    "avoid wasting requests. Use the local structured-answer/offline extraction; retry Gemini "
                    "after the quota reset or after changing the billing/limit tier."
                ) from exc
            if not is_transient_gemini_error(exc):
                raise
            if attempt < retries:
                time.sleep(base_seconds * (2 ** attempt))
                continue
            msg = str(exc).casefold()
            if "503" in msg or "unavailable" in msg or "high demand" in msg:
                attempts_made = attempt + 1
                attempt_note = "one request was made" if attempts_made == 1 else f"{attempts_made} attempts were made"
                raise GeminiProviderUnavailableError(
                    "Google Gemini is temporarily overloaded (503 UNAVAILABLE); " + attempt_note + ". "
                    "Your uploaded document and evidence index remain available. "
                    "Use Rule-based (offline) extraction, or enable one bounded retry after checking service status. "
                    "This is not a PDF parsing error."
                ) from exc
            attempts_made = attempt + 1
            attempt_note = "one request was made" if attempts_made == 1 else f"{attempts_made} attempts were made"
            raise GeminiProviderUnavailableError(
                "Gemini is temporarily rate-limited or experiencing a service error; " + attempt_note + ". "
                "Wait for the limit window to reset or use the local evidence-only/offline option."
            ) from exc
    raise GeminiProviderUnavailableError("Gemini request could not be completed.")
