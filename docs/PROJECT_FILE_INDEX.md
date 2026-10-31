# Project File Index

This document describes the current repository structure and identifies the canonical application, data, analysis, model, test, and Power BI files.

## Application

- `app/market_explorer.py`: Streamlit entry point and historical procurement explorer.
- `app/market_explorer_data.py`: historical dashboard data loading and filtering.
- `app/category_prediction.py`: broad-category model prediction helper.
- `app/bid_fit_engine.py`: explainable company/tender fit assessment.
- `app/copilot_review_state.py`: Copilot review and session-state helpers.
- `app/gemini_runtime.py`: optional Gemini runtime and retry configuration.
- `app/gemini_tender_extractor.py`: Gemini-assisted tender extraction.
- `app/tender_copilot.py`: PDF extraction, local retrieval and optional LLM answers.
- `app/tender_answer_engine.py`: provider-independent answers for supported questions.
- `app/tender_question_intents.py`: question-intent and terminology handling.
- `app/tender_extraction_hybrid.py`: hybrid tender requirement extraction.
- `app/tender_requirements_extractor.py`: evidence-backed candidate fields.
- `app/tender_evidence_presentation.py`: evidence presentation helpers.
- `app/tender_review_audit.py`: ambiguity and conflicting-clause review flags.
- `app/pages/`: Streamlit ML, document Copilot and Bid-Fit pages.

## Data and assets

- `data/raw/`: original historical Assam procurement source archive.
- `data/processed/`: cleaned analytical dataset.
- `data/metadata/`: source and provenance information, where present.
- `assets/`: dashboard images and fictional tender-PDF demo.
- `models/`: trained broad-category classifier artifact.

Original tender PDFs used during private testing are excluded from the public release. The synthetic demo PDF in `assets/` is fictional.

## Reports

- `reports/eda/`: exploratory data analysis outputs.
- `reports/business_analysis/`: buyer, category, fiscal-year and tender-stage summaries.
- `reports/business_analysis_validation/`: report reconciliation checks.
- `reports/taxonomy_review/`: provisional taxonomy review artifacts.
- `reports/ml/`: classifier metrics, class-level report, confusion matrix and holdout predictions.
- `reports/archive/`: historical diagnostic snapshots, not necessarily the latest authoritative results.

## Reproducible source code

Important scripts under `src/`:

- `check_environment.py`: environment checks.
- `audit_assam_procurement.py`: source archive audit.
- `clean_assam_procurement.py`: cleaning and processed-dataset creation.
- `profile_procurement_categories.py`: category and provisional-niche profiling.
- `run_procurement_eda.py`: EDA outputs.
- `review_niche_taxonomy.py`: taxonomy review workflow.
- `prepare_taxonomy_signoff.py`: review/sign-off workbook preparation.
- `audit_source_classification_consistency.py`: source-to-assignment checks.
- `audit_taxonomy_workbook.py`: taxonomy workbook audit.
- `analyze_procurement_business.py`: business analysis outputs.
- `validate_business_analysis_outputs.py`: report consistency validation.
- `train_procurement_category_model.py`: broad-category classifier training.

## Machine learning

- `models/procurement_broad_category_classifier.joblib`: trained classifier.
- `docs/ML_BROAD_CATEGORY_CLASSIFIER.md`: model design and evaluation.
- `reports/ml/`: saved model evaluation outputs.

The classifier predicts broad source categories only. Its scores are not bid-win, eligibility, niche-accuracy or profitability predictions.

## Power BI

- `powerbi/exports/Public_Procurement_Market_Intelligence.pbix`: native Power BI report.
- `powerbi/Public_Procurement_Market_Intelligence/`: editable PBIP project.
- The PBIP project contains PBIR report definitions and a TMDL semantic model.
- Machine-specific `.pbi` cache and local settings are excluded from version control.

## Tests and tools

- `tests/`: regression tests for data, taxonomy, ML, Copilot, OCR and Bid-Fit.
- `tools/validate_tender_copilot.py`: local PDF/OCR/Q&A/Bid-Fit diagnostic without provider API calls.
- `tools/diagnose_gemini.py`: Gemini configuration diagnostic.
- `tools/consolidate_legacy_work.ps1`: legacy repository consolidation utility.

Run the suite from the repository root:

```powershell
python -m pytest tests -q
```

## Documentation map

- `docs/PROJECT_METHODOLOGY.md`: methods and analysis approach.
- `docs/KNOWN_LIMITATIONS.md`: supported scope and limitations.
- `docs/FINAL_PROJECT_STATUS.md`: current implementation and verification snapshot.
- `docs/FINAL_TESTING_GUIDE.md`: local setup and validation procedure.
- `docs/AI_TENDER_DOCUMENT_COPILOT.md`: document Q&A and configuration.
- `docs/BID_FIT_ANALYSIS.md`: fit scoring and review logic.
- `docs/ML_BROAD_CATEGORY_CLASSIFIER.md`: model design and evaluation.
- `docs/TENDER_SCANNED_PDF_OCR.md`: local OCR setup and limitations.
- `docs/VALIDATION_RESULTS.md`: historical tender diagnostic results.
- `docs/project_history/`: initial planning documents retained as historical records.
- `docs/taxonomy/`: taxonomy rationale, review guidance and decisions.

## Scope

The historical analytical dataset covers Assam procurement for FY 2016-17 through FY 2021-22. This repository is a portfolio decision-support prototype, not a live all-India tender aggregator, legal eligibility opinion, bid-win predictor or guaranteed-profit calculator.