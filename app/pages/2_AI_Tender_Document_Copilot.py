"""Streamlit page for evidence-grounded tender-document review.

Processed document/index, answers and reviewed draft values live in Streamlit session
state so users can navigate to Bid-Fit and back without reprocessing the same file.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tender_copilot import (  # noqa: E402
    LLMGenerationError,
    RetrievedChunk,
    LLMNotConfiguredError,
    PDFProcessingError,
    SUPPORTED_DOCUMENT_EXTENSIONS,
    answer_with_gemini,
    answer_with_llm,
    build_retrieval_index,
    chunk_document_pages,
    extract_document_pages,
    file_sha256,
    get_configured_api_key,
    get_configured_provider,
    get_configured_model,
    get_configured_gemini_model,
    retrieve_relevant_chunks,
)
from app.gemini_tender_extractor import (  # noqa: E402
    GeminiExtractionError,
    GeminiNotConfiguredError,
    extract_tender_requirements_with_gemini,
)
from app.tender_requirements_extractor import (  # noqa: E402
    build_bidfit_prefill_payload,
    extract_tender_requirements_draft,
)
from app.tender_answer_engine import answer_common_tender_question  # noqa: E402
from app.tender_question_intents import LOCAL_FIRST_INTENTS, intent_label, question_intents  # noqa: E402
from app.gemini_runtime import is_quota_exhaustion_error  # noqa: E402
from app.tender_extraction_hybrid import merge_candidate_fields, with_local_fallback_status  # noqa: E402
from app.tender_review_audit import (  # noqa: E402
    build_tender_review_findings,
    enrich_tender_fields,
)
from app.copilot_review_state import (  # noqa: E402
    REVIEW_CONFIRMATION_SAVED_KEY,
    REVIEW_CONFIRMATION_WIDGET_KEY,
    REVIEW_FIELD_NAMES,
    REVIEW_VALUES_STATE_KEY,
    REVIEW_WIDGET_KEYS,
    collect_widget_values,
    initial_review_values,
    merge_saved_review_values,
    update_review_value,
)
from app.tender_evidence_presentation import (  # noqa: E402
    highlight_evidence_html,
    local_evidence_summary,
    matched_query_terms,
    structure_evidence_text,
)

UPLOAD_WIDGET_KEY = "tender_copilot_upload_widget"
DOCUMENT_PROCESSING_VERSION = "2026.10.30-r3"


def _persist_review_widget(field_name: str) -> None:
    """Mirror non-form widget changes to a non-widget key Streamlit won't clean up."""
    widget_key = REVIEW_WIDGET_KEYS[field_name]
    current = st.session_state.get(widget_key, "")
    st.session_state[REVIEW_VALUES_STATE_KEY] = update_review_value(
        st.session_state.get(REVIEW_VALUES_STATE_KEY, {}), field_name, current
    )


def _persist_review_confirmation() -> None:
    st.session_state[REVIEW_CONFIRMATION_SAVED_KEY] = bool(
        st.session_state.get(REVIEW_CONFIRMATION_WIDGET_KEY, False)
    )


GEMINI_QUOTA_LATCH_KEY = "copilot_gemini_quota_exhausted_this_session"
GEMINI_QUOTA_REASON_KEY = "copilot_gemini_quota_reason"
GEMINI_RETRY_ONCE_KEY = "copilot_gemini_retry_once"


def _remember_gemini_quota_failure(exc: Exception, provider: str) -> None:
    """Avoid repeated quota calls after Gemini explicitly says the quota is exhausted."""
    if provider == "gemini" and is_quota_exhaustion_error(exc):
        st.session_state[GEMINI_QUOTA_LATCH_KEY] = True
        st.session_state[GEMINI_QUOTA_REASON_KEY] = str(exc)
        st.session_state[GEMINI_RETRY_ONCE_KEY] = False


def _clear_gemini_quota_latch() -> None:
    st.session_state.pop(GEMINI_QUOTA_LATCH_KEY, None)
    st.session_state.pop(GEMINI_QUOTA_REASON_KEY, None)
    st.session_state[GEMINI_RETRY_ONCE_KEY] = False


def _consume_gemini_retry_once(provider: str) -> None:
    if provider == "gemini":
        st.session_state[GEMINI_RETRY_ONCE_KEY] = False


st.title("AI Tender Document Copilot")
st.caption("Upload a tender document, retrieve relevant clauses, and ask questions with source-location evidence.")
st.caption(f"Local extraction engine · {DOCUMENT_PROCESSING_VERSION}")
st.info(
    "This tool assists document review; it does not verify live tender status, guarantee eligibility, "
    "predict tender wins, or calculate profit from tender value alone. Always confirm material terms "
    "against the official tender portal and corrigenda."
)
if st.session_state.get(GEMINI_QUOTA_LATCH_KEY):
    st.warning(
        "Gemini quota exhaustion was already detected in this browser session. Common labelled questions "
        "and offline Bid-Fit extraction continue locally; the app will skip new Gemini requests to avoid "
        "repeating the same quota error."
    )
    with st.expander("Gemini retry controls", expanded=False):
        st.caption(str(st.session_state.get(GEMINI_QUOTA_REASON_KEY, "Quota exhausted in this session."))[:500])
        if st.button("Allow one Gemini retry (only after checking that quota reset)", key="copilot_allow_single_gemini_retry"):
            st.session_state[GEMINI_RETRY_ONCE_KEY] = True
            st.rerun()
st.markdown(
    """<style>
    .tender-evidence-clause { padding: 0.55rem 0.7rem; margin: 0.35rem 0; border-left: 3px solid #64748b; border-radius: 0.25rem; line-height: 1.6; }
    mark.tender-hit { background: #ffdf70; color: #202124; padding: 0.02rem 0.15rem; border-radius: 0.2rem; font-weight: 700; }
    </style>""",
    unsafe_allow_html=True,
)

with st.expander("Supported formats, privacy and limitations", expanded=False):
    st.markdown(
        "**Supported now:** PDF, DOCX, TXT, CSV, XLSX and legacy XLS. "
        "PDF evidence uses physical page numbers; Word/text/spreadsheet evidence uses paragraph, block, sheet or row locations.\n\n"
        "- Uploaded files are processed in the Streamlit session; this module does not save original files to a database. "
        "Processed text/index and reviewed values persist while this browser session remains active.\n"
        "- Scanned/image-only PDF pages are OCR-processed locally when PyMuPDF OCR support and Tesseract language data are installed. OCR can misread amounts, dates and table cells; verify them against page images.\n"
        "- ZIP/RAR archives, old binary DOC files, images and native CAD drawings are not supported yet. Extract relevant files manually first.\n"
        "- When an API key is configured, only the question and retrieved excerpts—not the full original file—are sent to the configured AI provider. "
        "Do not upload confidential files unless you are authorised to do so.\n"
        "- AI answers and extracted fields can make mistakes. Source locations are pointers for human verification, not proof that the interpretation is correct."
    )

supported_exts = sorted(ext.lstrip(".") for ext in SUPPORTED_DOCUMENT_EXTENSIONS)
uploaded = st.file_uploader(
    "Upload tender notice / eligibility / BOQ file",
    type=supported_exts,
    accept_multiple_files=False,
    key=UPLOAD_WIDGET_KEY,
    help="Supported: PDF, DOCX, TXT, CSV, XLSX and XLS. For a multi-file tender package, process each document separately for now.",
)
selected_bytes = uploaded.getvalue() if uploaded is not None else None
selected_hash = file_sha256(selected_bytes) if selected_bytes is not None else None
processed = st.session_state.get("tender_copilot_document")
processed_is_current = bool(
    processed
    and processed.get("processing_version") == DOCUMENT_PROCESSING_VERSION
)

# A document's extracted pages are session-cached. Invalidate that cache when the
# extraction pipeline changes, even if the uploaded PDF's SHA-256 is unchanged. This
# prevents old OCR/text from silently surviving a code update.
if uploaded is not None and (
    processed is None
    or processed.get("sha256") != selected_hash
    or not processed_is_current
):
    st.caption(f"Selected file: {uploaded.name} · {len(selected_bytes) / (1024 * 1024):.2f} MB")
    if processed and processed.get("sha256") == selected_hash and not processed_is_current:
        st.warning(
            "This PDF was processed by an older extraction engine. Reprocess it once so the updated OCR, "
            "Bid-Fit and question-answer rules are applied to the same file."
        )
    else:
        st.info("This file has not been processed with the current engine. Click **Process selected document** once to index it.")
    if st.button("Process selected document", type="primary", key="process_tender_document"):
        with st.spinner("Reading the file and building the local search index..."):
            try:
                pages = extract_document_pages(uploaded.name, selected_bytes)
                chunks = chunk_document_pages(pages, source_name=uploaded.name)
                if not chunks:
                    raise PDFProcessingError(
                        "No searchable text was extracted. The file may be scanned, blank, or unsupported."
                    )
                vectorizer, matrix = build_retrieval_index(chunks)
                extracted_chars = sum(len(page["text"]) for page in pages)
                document_kind = Path(uploaded.name).suffix.lower().lstrip(".").upper()
                st.session_state["tender_copilot_document"] = {
                    "sha256": selected_hash,
                    "processing_version": DOCUMENT_PROCESSING_VERSION,
                    "filename": uploaded.name,
                    "extension": Path(uploaded.name).suffix.lower(),
                    "document_kind": document_kind,
                    "pages": pages,
                    "chunks": chunks,
                    "vectorizer": vectorizer,
                    "matrix": matrix,
                    "extracted_chars": extracted_chars,
                }
                for key in (
                    "tender_copilot_last_answer",
                    "copilot_bidfit_draft",
                    "copilot_bidfit_reviewed_values",
                    "bidfit_pending_prefill",
                    "bidfit_prefill_metadata",
                    "bidfit_last_reviewed_import",
                    "bidfit_prefill_notice",
                    "last_bid_fit_result",
                    "last_bid_fit_title",
                ):
                    st.session_state.pop(key, None)
                for field_name in REVIEW_FIELD_NAMES:
                    # Remove the current widget key and legacy form key from earlier patch versions.
                    st.session_state.pop(REVIEW_WIDGET_KEYS[field_name], None)
                    st.session_state.pop(f"copilot_review_{field_name}", None)
                st.session_state.pop(REVIEW_CONFIRMATION_WIDGET_KEY, None)
                st.session_state.pop(REVIEW_CONFIRMATION_SAVED_KEY, None)
                # A newly processed tender invalidates old tender requirements/result,
                # but keep the user's company profile for reuse.
                tender_form_keys = {
                    "bidfit_tender_title", "bidfit_tender_capabilities_raw", "bidfit_target_region",
                    "bidfit_min_years_raw", "bidfit_min_projects_raw", "bidfit_min_turnover_raw",
                    "bidfit_required_certifications_raw", "bidfit_emd_required_raw", "bidfit_source_url",
                    "bidfit_closing_date_known", "bidfit_closing_date", "bidfit_requirements_reviewed",
                    "bidfit_official_source_checked",
                }
                for key in tender_form_keys:
                    st.session_state.pop(key, None)
                saved_form = dict(st.session_state.get("bidfit_saved_form_values", {}))
                for key in tender_form_keys:
                    saved_form.pop(key, None)
                if saved_form:
                    st.session_state["bidfit_saved_form_values"] = saved_form
                else:
                    st.session_state.pop("bidfit_saved_form_values", None)
                st.success("Document processed and indexed. Your index will remain available while this session is active.")
                st.rerun()
            except (PDFProcessingError, ValueError) as exc:
                st.error(str(exc))
            except Exception as exc:  # Keep UI errors actionable without exposing a full traceback.
                st.error(f"Document processing failed: {exc}")
elif uploaded is not None and processed and processed.get("sha256") == selected_hash and processed_is_current:
    st.caption(f"Selected file: {uploaded.name} · {len(selected_bytes) / (1024 * 1024):.2f} MB · already processed")

# If the uploader's widget state was cleared on navigation, use the session-cached
# document. If another file is selected but not processed yet, don't silently query the old one.
active_document = processed if processed_is_current else None
if uploaded is not None and processed and (
    processed.get("sha256") != selected_hash or not processed_is_current
):
    active_document = None
if uploaded is not None and processed is None:
    active_document = None
if uploaded is None and processed and not processed_is_current:
    st.warning("The cached document was created by an older extraction engine. Re-upload the same PDF and process it once to refresh the evidence index.")

if active_document:
    filename = active_document["filename"]
    extension = active_document.get("extension", Path(filename).suffix.lower())
    kind = active_document.get("document_kind", extension.lstrip(".").upper())
    units = active_document["pages"]
    chunks = active_document["chunks"]
    st.success(f"Loaded document: **{filename}**. No need to process it again when returning to this page in the same session.")
    if st.button("Clear loaded document and its draft", key="clear_loaded_tender_document"):
        for key in (
            "tender_copilot_document",
            "tender_copilot_last_answer",
            "copilot_bidfit_draft",
            "copilot_bidfit_reviewed_values",
            "bidfit_pending_prefill",
            "bidfit_prefill_metadata",
            "bidfit_last_reviewed_import",
            "bidfit_prefill_notice",
        ):
            st.session_state.pop(key, None)
        for field_name in REVIEW_FIELD_NAMES:
            st.session_state.pop(REVIEW_WIDGET_KEYS[field_name], None)
            st.session_state.pop(f"copilot_review_{field_name}", None)
        st.session_state.pop(REVIEW_CONFIRMATION_WIDGET_KEY, None)
        st.session_state.pop(REVIEW_CONFIRMATION_SAVED_KEY, None)
        st.rerun()

    has_text = sum(bool(unit.get("text")) for unit in units)
    a, b, c = st.columns(3)
    a.metric("File format", kind)
    b.metric("Text blocks / pages", f"{has_text:,}")
    c.metric("Searchable chunks", f"{len(chunks):,}")
    ocr_pages_count = sum(bool(unit.get("ocr_used")) for unit in units)
    if ocr_pages_count:
        st.info(
            f"Local OCR extracted text from {ocr_pages_count} page(s). "
            "Scanned-page OCR can misread amounts, dates and table cells; verify these against the original page images."
        )
    if has_text < len(units):
        st.warning(f"{len(units) - has_text} unit(s) yielded no readable text after extraction/OCR. Check those original pages manually.")

    st.subheader("Ask about the tender")
    question_widget_key = "copilot_question_widget"
    top_k_widget_key = "copilot_top_k_widget"
    if question_widget_key not in st.session_state:
        st.session_state[question_widget_key] = st.session_state.get("copilot_question_saved", "")
    if top_k_widget_key not in st.session_state:
        st.session_state[top_k_widget_key] = st.session_state.get("copilot_top_k_saved", 5)

    with st.form("tender_question_form", clear_on_submit=False):
        question = st.text_area(
            "Question",
            placeholder="e.g. What is the EMD amount? Is prior experience mandatory? What is the submission deadline?",
            height=95,
            key=question_widget_key,
        )
        top_k = st.slider("Evidence passages to retrieve", min_value=3, max_value=8, value=int(st.session_state[top_k_widget_key]), key=top_k_widget_key)
        submitted = st.form_submit_button("Find evidence and answer", type="primary")

    if submitted:
        st.session_state["copilot_question_saved"] = question
        st.session_state["copilot_top_k_saved"] = top_k
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            # Run direct, evidence-grounded answers over every extracted page before calling an LLM.
            # This avoids relying on top-k ranking for labelled facts such as turnover/EMD/deadline,
            # and does not spend Gemini quota on questions that can be answered deterministically.
            direct_answer = answer_common_tender_question(question, units)
            if direct_answer is not None:
                direct_hit = RetrievedChunk(
                    page_number=direct_answer.page_number,
                    chunk_index=-1,
                    text=direct_answer.evidence,
                    source_name=filename,
                    similarity=1.0,
                    source_location=direct_answer.source_location,
                    matched_terms=(),
                )
                # The whole-document rule already selected the authoritative labelled
                # passage/schedule. Avoid a second TF-IDF retrieval pass for simple
                # questions; this path must return immediately and never call Gemini.
                hits = [direct_hit]
                st.session_state["tender_copilot_last_answer"] = {
                    "question": question,
                    "answer": direct_answer.answer,
                    "hits": hits,
                    "mode": "Local structured answer from the full extracted document (Gemini not required)",
                    "error": None,
                    "document_sha256": active_document["sha256"],
                }
            else:
                hits = retrieve_relevant_chunks(
                    question, chunks, active_document["vectorizer"], active_document["matrix"], top_k=top_k
                )
                if not hits:
                    st.warning("I could not find relevant text in this document for that question. Try different wording or verify manually.")
                    st.session_state["tender_copilot_last_answer"] = None
                else:
                    intents = question_intents(question)
                    local_only = bool(set(intents) & LOCAL_FIRST_INTENTS)
                    if local_only:
                        label = next(
                            (intent_label(intent) for intent in intents if intent in LOCAL_FIRST_INTENTS),
                            "this tender requirement",
                        )
                        evidence_summary = local_evidence_summary(question, hits, all_evidence=chunks)
                        answer_text = (
                            f"**I could not confidently identify a single explicit answer for {label} in the extracted document.** "
                            "No amount, date or duration has been inferred. Review the evidence passages below and check the "
                            "original clause, schedules and latest corrigenda.\n\n" + evidence_summary
                        )
                        st.session_state["tender_copilot_last_answer"] = {
                            "question": question,
                            "answer": answer_text,
                            "hits": hits,
                            "mode": "Local evidence review (no provider request; no unsupported value inferred)",
                            "error": None,
                            "document_sha256": active_document["sha256"],
                        }
                    provider = get_configured_provider() if not local_only else None
                    if provider and not local_only:
                        quota_latched = provider == "gemini" and bool(st.session_state.get(GEMINI_QUOTA_LATCH_KEY))
                        retry_once = bool(st.session_state.get(GEMINI_RETRY_ONCE_KEY))
                        if quota_latched and not retry_once:
                            reason = str(st.session_state.get(GEMINI_QUOTA_REASON_KEY, "Gemini quota exhausted earlier in this session."))
                            st.session_state["tender_copilot_last_answer"] = {
                                "question": question,
                                "answer": local_evidence_summary(question, hits, all_evidence=chunks),
                                "hits": hits,
                                "mode": "Local evidence-only fallback (known Gemini quota exhaustion; no new API request sent)",
                                "error": reason,
                                "document_sha256": active_document["sha256"],
                            }
                        else:
                            _consume_gemini_retry_once(provider)
                            with st.spinner("Answering from the retrieved tender evidence..."):
                                try:
                                    if provider == "openai":
                                        answer = answer_with_llm(question, hits, api_key=get_configured_api_key(), model=get_configured_model())
                                        mode = "AI-generated from retrieved evidence (OpenAI)"
                                    else:
                                        answer = answer_with_gemini(question, hits, model=get_configured_gemini_model())
                                        mode = "AI-generated from retrieved evidence (Gemini)"
                                        _clear_gemini_quota_latch()
                                    st.session_state["tender_copilot_last_answer"] = {
                                        "question": question, "answer": answer, "hits": hits,
                                        "mode": mode, "error": None,
                                        "document_sha256": active_document["sha256"],
                                    }
                                except (LLMGenerationError, LLMNotConfiguredError) as exc:
                                    _remember_gemini_quota_failure(exc, provider)
                                    st.session_state["tender_copilot_last_answer"] = {
                                        "question": question,
                                        "answer": local_evidence_summary(question, hits, all_evidence=chunks),
                                        "hits": hits,
                                        "mode": f"Local evidence-only fallback ({provider} answer failed)",
                                        "error": str(exc),
                                        "document_sha256": active_document["sha256"],
                                    }
                    elif not local_only:
                        st.session_state["tender_copilot_last_answer"] = {
                            "question": question,
                            "answer": local_evidence_summary(question, hits, all_evidence=chunks),
                            "hits": hits,
                            "mode": "Local evidence-only summary; no AI API key configured",
                            "error": None,
                            "document_sha256": active_document["sha256"],
                        }

    last = st.session_state.get("tender_copilot_last_answer")
    if last and last.get("document_sha256") == active_document["sha256"]:
        st.subheader("Answer")
        if last["answer"]:
            st.markdown(last["answer"])
        else:
            st.info(
                "No answer text was returned. Relevant passages are shown below for manual review."
            )
        if last.get("error"):
            st.warning(last["error"])
        if "no AI API key configured" in last["mode"]:
            st.info("No API key was detected. Add GEMINI_API_KEY to the local .env to use the same Gemini setup as tender-field extraction; without a key, the local evidence summary still works.")
        st.caption(f"Mode: {last['mode']}")
        st.subheader("Retrieved evidence")
        for i, hit in enumerate(last["hits"], start=1):
            location = getattr(hit, "source_location", "") or f"PDF page {hit.page_number}"
            terms = matched_query_terms(last["question"], hit.text)
            matched = ", ".join(terms[:10]) if terms else "Related wording; no direct query words matched"
            with st.expander(f"Evidence {i} · {location} · score {hit.similarity:.3f}"):
                st.caption(f"Matched words / phrases: {matched}")
                clauses = structure_evidence_text(hit.text)
                for clause in clauses:
                    st.markdown(
                        f'<div class="tender-evidence-clause">{highlight_evidence_html(clause, last["question"])}</div>',
                        unsafe_allow_html=True,
                    )
                st.caption("Use this source location to check the original tender file.")

    st.divider()
    st.subheader("Prepare a Bid-Fit draft from this document")
    st.caption(
        "Local evidence extraction always runs as a safety net. Gemini may enrich the draft when available, "
        "but missing/failed AI fields are automatically filled only where a labelled source-backed local rule succeeds. "
        "All values remain unverified candidates; review page evidence before Bid-Fit."
    )
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    except Exception:
        pass
    gemini_key_available = bool(os.getenv("GEMINI_API_KEY", "").strip())
    if st.session_state.get("copilot_extraction_mode_version") != DOCUMENT_PROCESSING_VERSION:
        st.session_state["copilot_field_extraction_mode"] = "Rule-based (offline)"
        st.session_state["copilot_extraction_mode_version"] = DOCUMENT_PROCESSING_VERSION
    elif "copilot_field_extraction_mode" not in st.session_state:
        st.session_state["copilot_field_extraction_mode"] = "Rule-based (offline)"
    extraction_mode = st.radio(
        "Field extraction method",
        options=["Gemini AI", "Rule-based (offline)"],
        index=1,
        horizontal=True,
        help="Rule-based (offline) is the default and uses the uploaded text/OCR locally. Select Gemini only when your API quota is available; Gemini errors must not block the local result.",
        key="copilot_field_extraction_mode",
    )
    if extraction_mode == "Gemini AI" and not gemini_key_available:
        st.warning("GEMINI_API_KEY is not configured. Add it to your local .env file and restart the app, or select Rule-based (offline).")
    if st.button("Extract candidate fields for Bid-Fit", type="secondary", key="extract_bidfit_draft"):
        # Always calculate a local, evidence-backed baseline first. This is intentionally
        # independent of Gemini availability and makes sure an empty AI field cannot erase
        # a clear amount/page already present in the document.
        local_fields = extract_tender_requirements_draft(units)
        extraction_notice = None
        if extraction_mode == "Gemini AI":
            quota_latched = bool(st.session_state.get(GEMINI_QUOTA_LATCH_KEY))
            retry_once = bool(st.session_state.get(GEMINI_RETRY_ONCE_KEY))
            if quota_latched and not retry_once:
                reason = "Gemini quota was already exhausted in this browser session"
                fields = with_local_fallback_status(local_fields, reason=reason)
                extraction_notice = (
                    "Skipped another Gemini request because quota exhaustion was already detected. "
                    "The source-backed local candidates below were used; retry only after confirming the quota reset."
                )
            else:
                _consume_gemini_retry_once("gemini")
                try:
                    gemini_fields = extract_tender_requirements_with_gemini(units)
                    fields = merge_candidate_fields(local_fields, gemini_fields)
                    _clear_gemini_quota_latch()
                except GeminiNotConfiguredError as exc:
                    fields = with_local_fallback_status(local_fields, reason="Gemini API key unavailable")
                    extraction_notice = f"Gemini was not configured; local evidence extraction was used instead. {exc}"
                except GeminiExtractionError as exc:
                    _remember_gemini_quota_failure(exc, "gemini")
                    fields = with_local_fallback_status(local_fields, reason="Gemini request failed or quota is unavailable")
                    extraction_notice = f"Gemini did not complete. Local evidence extraction was automatically used; no second manual extraction step is needed. Details: {exc}"
        else:
            fields = local_fields
        # Cross-check source phrases after either extraction mode. This enriches
        # the evidence and flags complex criteria without turning them into an
        # automatic eligibility verdict.
        fields = enrich_tender_fields(units, fields)
        audit_findings = build_tender_review_findings(units)
        if extraction_notice:
            st.warning(extraction_notice)
        st.session_state["copilot_bidfit_draft"] = {
            "sha256": active_document["sha256"],
            "processing_version": DOCUMENT_PROCESSING_VERSION,
            "filename": filename,
            "fields": fields, "audit_findings": audit_findings,
        }
        initial_values = initial_review_values(fields)
        st.session_state[REVIEW_VALUES_STATE_KEY] = initial_values.copy()
        # Seed widget keys before those widgets are rendered on this run.
        for field_name, value in initial_values.items():
            st.session_state[REVIEW_WIDGET_KEYS[field_name]] = value
        st.session_state[REVIEW_CONFIRMATION_WIDGET_KEY] = False
        st.session_state[REVIEW_CONFIRMATION_SAVED_KEY] = False
        st.session_state.pop("bidfit_pending_prefill", None)
        st.rerun()

    draft = st.session_state.get("copilot_bidfit_draft")
    if draft and draft.get("processing_version") != DOCUMENT_PROCESSING_VERSION:
        # A draft can outlive a page rerun even when the uploaded PDF hash is the
        # same. Never display old field values under a new extractor version.
        st.session_state.pop("copilot_bidfit_draft", None)
        draft = None
        st.info("The saved Bid-Fit draft was created by an older extraction engine. Run 'Extract candidate fields for Bid-Fit' again to refresh it.")
    if draft and draft.get("sha256") == active_document["sha256"]:
        st.info(
            "Detected values are candidates. Blank fields were not confidently extracted; enter them manually only if the official document specifies them."
        )
        evidence_rows = []
        for field_name, field_info in draft["fields"].items():
            source_locations = field_info.get("source_locations") or [f"Page {n}" for n in field_info.get("page_numbers", [])]
            draft_value = str(field_info.get("value", "") or "").strip()
            status_text = str(field_info.get("status", "Review") or "Review")
            if not draft_value and "work-specific emd schedule" in status_text.casefold():
                draft_value = "Varies by work — select serial"
            elif not draft_value and "conflicting submission-date" in status_text.casefold():
                draft_value = "Conflicting dates — verify portal"
            elif not draft_value and "multiple alternative similar-work routes" in status_text.casefold():
                counts = re.findall(r"\b(one|two|three|four|\d+)\s+similar\s+completed\s+works?", str(field_info.get("evidence", "")), re.I)
                words = {"one": "1", "two": "2", "three": "3", "four": "4"}
                readable_counts = [words.get(value.casefold(), value) for value in counts]
                draft_value = "Alternative routes — " + " / ".join(readable_counts) + " similar completed works" if readable_counts else "Alternative similar-work routes — review evidence"
            elif not draft_value and "no numeric minimum annual turnover" in status_text.casefold():
                draft_value = "No numeric threshold found — verify schedules"
            elif not draft_value and "multiple work sites" in status_text.casefold():
                draft_value = "Multiple sites — select work serial"
            elif not draft_value and "multiple different work scopes" in status_text.casefold():
                draft_value = "Multiple scopes — select work serial"
            else:
                draft_value = draft_value or "Not found"
            evidence_rows.append({
                "Field": field_name.replace("_", " ").title(),
                "Draft value": draft_value,
                "Source location(s)": "; ".join(source_locations) or "—",
                "Status": status_text,
                "Evidence": field_info.get("evidence", "") or "No extracted evidence",
            })
        st.dataframe(evidence_rows, width="stretch", hide_index=True)

        audit_findings = draft.get("audit_findings", [])
        st.subheader("Tender review flags")
        st.caption(
            "These source-backed flags identify requirements that a flat field extractor can miss "
            "or clauses that appear inconsistent. They are not legal conclusions and are not silently "
            "converted into a Bid-Fit score."
        )
        if audit_findings:
            for i, finding in enumerate(audit_findings, start=1):
                label = (
                    f"{finding.get('severity', 'Review')} · {finding.get('title', 'Review finding')} · "
                    f"{', '.join(finding.get('source_locations', [])) or 'source location unavailable'}"
                )
                with st.expander(label, expanded=finding.get("severity") in {"Deadline", "Critical review", "High"}):
                    st.write(finding.get("details", ""))
                    st.markdown("**Recommended action**")
                    st.write(finding.get("recommended_action", "Compare with the original tender and official portal."))
                    st.markdown("**Source evidence**")
                    st.code(finding.get("evidence", "No evidence quote available."), language="text")
        else:
            st.info("No additional pattern-based flags were triggered. This does not mean that all tender terms were verified.")

        saved_review = st.session_state.get(REVIEW_VALUES_STATE_KEY, {})
        restored_values = merge_saved_review_values(draft["fields"], saved_review)
        # Streamlit removes widget-bound keys when switching pages. Re-seed these
        # keys from non-widget session state every time this page is revisited.
        for field_name in REVIEW_FIELD_NAMES:
            widget_key = REVIEW_WIDGET_KEYS[field_name]
            if widget_key not in st.session_state:
                st.session_state[widget_key] = restored_values[field_name]
        if REVIEW_CONFIRMATION_WIDGET_KEY not in st.session_state:
            st.session_state[REVIEW_CONFIRMATION_WIDGET_KEY] = bool(
                st.session_state.get(REVIEW_CONFIRMATION_SAVED_KEY, False)
            )

        st.markdown("**Review / correct the draft values before transfer**")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input(
                "Tender title", key=REVIEW_WIDGET_KEYS["tender_title"],
                on_change=_persist_review_widget, args=("tender_title",),
            )
            st.text_area(
                "Required capability / scope keywords (comma-separated)",
                key=REVIEW_WIDGET_KEYS["required_capabilities"], height=80,
                on_change=_persist_review_widget, args=("required_capabilities",),
            )
            st.text_input(
                "Tender delivery / work region", key=REVIEW_WIDGET_KEYS["target_region"],
                on_change=_persist_review_widget, args=("target_region",),
            )
            st.text_input(
                "Minimum bidder/company experience years (only if explicitly required; not the work lookback window)", key=REVIEW_WIDGET_KEYS["min_years_experience"],
                on_change=_persist_review_widget, args=("min_years_experience",),
            )
            st.text_input(
                "Minimum similar projects (blank if not stated)", key=REVIEW_WIDGET_KEYS["min_similar_projects"],
                on_change=_persist_review_widget, args=("min_similar_projects",),
            )
        with c2:
            st.text_input(
                "Minimum annual turnover (full INR amount)", key=REVIEW_WIDGET_KEYS["min_annual_turnover_inr"],
                on_change=_persist_review_widget, args=("min_annual_turnover_inr",),
            )
            st.text_area(
                "Mandatory certifications / registrations", key=REVIEW_WIDGET_KEYS["required_certifications"], height=80,
                on_change=_persist_review_widget, args=("required_certifications",),
            )
            st.text_input(
                "Required EMD (full INR amount)", key=REVIEW_WIDGET_KEYS["emd_required_inr"],
                on_change=_persist_review_widget, args=("emd_required_inr",),
            )
            st.text_input(
                "Closing date (YYYY-MM-DD; verify any corrigendum)", key=REVIEW_WIDGET_KEYS["closing_date"],
                on_change=_persist_review_widget, args=("closing_date",),
            )
        st.caption(
            "The official source URL is not inferred from arbitrary links in the file. Enter it manually in Bid-Fit. "
            "Official-source and final requirements confirmations remain unchecked."
        )
        st.checkbox(
            "I reviewed these draft values against the cited source locations.",
            key=REVIEW_CONFIRMATION_WIDGET_KEY,
            on_change=_persist_review_confirmation,
        )

        save_col, transfer_col = st.columns([1, 2])
        with save_col:
            save_clicked = st.button("Save draft edits", key="copilot_save_draft_edits")
        with transfer_col:
            transfer_clicked = st.button("Send reviewed draft to Bid-Fit", type="primary", key="copilot_send_reviewed_draft")

        widget_values = {
            name: st.session_state.get(REVIEW_WIDGET_KEYS[name], restored_values[name])
            for name in REVIEW_FIELD_NAMES
        }
        reviewed_values = collect_widget_values(saved_review, widget_values)
        is_reviewed = bool(st.session_state.get(REVIEW_CONFIRMATION_WIDGET_KEY, False))

        if save_clicked or transfer_clicked:
            st.session_state[REVIEW_VALUES_STATE_KEY] = reviewed_values.copy()
            st.session_state[REVIEW_CONFIRMATION_SAVED_KEY] = is_reviewed

        if save_clicked:
            st.success("Draft edits saved for this session. Values will be restored when you return to this page.")

        if transfer_clicked:
            if not is_reviewed:
                st.warning("Review the extracted values and tick the confirmation above before transferring them.")
            elif not reviewed_values.get("tender_title", "").strip():
                st.warning("Tender title is required before sending the draft to Bid-Fit.")
            else:
                st.session_state["bidfit_pending_prefill"] = build_bidfit_prefill_payload(
                    reviewed_values,
                    source_filename=draft["filename"],
                    field_details=draft["fields"],
                )
                st.success("Reviewed draft saved for Bid-Fit. Open the page from the left sidebar; fields will be prefilled.")
                st.page_link("pages/3_Company_Bid_Fit_Analysis.py", label="Open Company Bid-Fit Analysis", icon=":material/arrow_forward:")

else:
    if processed:
        st.info(
            f"The selected upload is different from the currently indexed file ({processed.get('filename')}). "
            "Click **Process selected document** above to replace it, or clear the selection to return to the cached file."
        )
    else:
        st.markdown(
            "**How to use:** select a tender file → click **Process selected document** → ask a question or extract a Bid-Fit draft. "
            "Your processed document and results remain available while the same session is active."
        )
