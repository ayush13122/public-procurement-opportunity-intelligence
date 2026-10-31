"""Train an explainable baseline NLP classifier for broad procurement category.

Run from the project root:
    python src/train_procurement_category_model.py

Purpose:
    Predict the source-provided broad category (Works / Goods / Services) from
    tender title text only. The latest fiscal year (2021-2022) is held out to
    mimic applying the model to later procurement records.

This is not a niche classifier, bid-win prediction model, eligibility engine,
profit predictor, or evidence of causal business impact.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "assam_procurement_cleaned.csv"
DEFAULT_HOLDOUT_YEAR = "2021-2022"
TARGET_COLUMN = "tender/mainProcurementCategory"
TEXT_COLUMN = "tender/title"
YEAR_COLUMN = "fiscal_year"
ID_COLUMN = "ocid"
CLASS_ORDER = ["Goods", "Services", "Works"]


def validate_input_frame(df: pd.DataFrame) -> None:
    """Fail early if the minimum required columns are unavailable."""
    required = {TEXT_COLUMN, TARGET_COLUMN, YEAR_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")
    categories = set(df[TARGET_COLUMN].dropna().astype(str).str.strip().unique())
    unexpected = categories - set(CLASS_ORDER)
    if unexpected:
        raise ValueError(f"Unexpected target categories found: {sorted(unexpected)}")
    if not categories:
        raise ValueError("No non-missing target categories found")


def prepare_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the declared target and text field plus evaluation metadata.

    Intentionally excludes the category field, source classification, buyer,
    dates and provisional niche assignments from model input to avoid leakage.
    """
    validate_input_frame(df)
    columns = [c for c in [ID_COLUMN, YEAR_COLUMN, TEXT_COLUMN, TARGET_COLUMN] if c in df.columns]
    data = df[columns].copy()
    data[TEXT_COLUMN] = data[TEXT_COLUMN].fillna("").astype(str).str.strip()
    data[YEAR_COLUMN] = data[YEAR_COLUMN].fillna("").astype(str).str.strip()
    data[TARGET_COLUMN] = data[TARGET_COLUMN].fillna("").astype(str).str.strip()
    data = data.loc[
        data[TEXT_COLUMN].ne("")
        & data[YEAR_COLUMN].ne("")
        & data[TARGET_COLUMN].isin(CLASS_ORDER)
    ].copy()
    return data


def split_chronologically(df: pd.DataFrame, holdout_year: str = DEFAULT_HOLDOUT_YEAR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on earlier fiscal years and evaluate only on the specified later year."""
    test_mask = df[YEAR_COLUMN].eq(holdout_year)
    train_mask = df[YEAR_COLUMN].ne(holdout_year)
    train = df.loc[train_mask].copy()
    test = df.loc[test_mask].copy()
    if train.empty or test.empty:
        years = sorted(df[YEAR_COLUMN].dropna().astype(str).unique())
        raise ValueError(
            f"Chronological split needs both earlier years and holdout year {holdout_year!r}. "
            f"Available fiscal years: {years}"
        )
    missing_train = set(CLASS_ORDER) - set(train[TARGET_COLUMN].unique())
    missing_test = set(CLASS_ORDER) - set(test[TARGET_COLUMN].unique())
    if missing_train or missing_test:
        raise ValueError(
            f"All categories must occur in both train and test. "
            f"Missing in train={sorted(missing_train)}; missing in test={sorted(missing_test)}"
        )
    return train, test


def build_classifier() -> Pipeline:
    """Create a reproducible sparse-text baseline with balanced class weighting."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=60_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1500,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def _metrics(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def _normalize_title(title: object) -> str:
    text = unicodedata.normalize("NFKC", str(title)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def run_training(input_path: Path = DEFAULT_INPUT, holdout_year: str = DEFAULT_HOLDOUT_YEAR) -> dict[str, Any]:
    """Train/evaluate model, persist artifacts and return the run summary."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found: {input_path}")

    raw = pd.read_csv(input_path, low_memory=False)
    data = prepare_model_frame(raw)
    train, test = split_chronologically(data, holdout_year)

    model = build_classifier()
    model.fit(train[TEXT_COLUMN], train[TARGET_COLUMN])
    predictions = model.predict(test[TEXT_COLUMN])
    proba = model.predict_proba(test[TEXT_COLUMN])
    model_confidence = proba.max(axis=1)

    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(train[TEXT_COLUMN], train[TARGET_COLUMN])
    dummy_predictions = dummy.predict(test[TEXT_COLUMN])

    report_dict = classification_report(
        test[TARGET_COLUMN], predictions, labels=CLASS_ORDER, output_dict=True, zero_division=0
    )
    report_df = pd.DataFrame(report_dict).T
    report_df.index.name = "class_or_average"

    cm = confusion_matrix(test[TARGET_COLUMN], predictions, labels=CLASS_ORDER)
    cm_df = pd.DataFrame(
        cm,
        index=[f"actual_{c}" for c in CLASS_ORDER],
        columns=[f"predicted_{c}" for c in CLASS_ORDER],
    )
    cm_df.index.name = "actual_category"

    report_dir = PROJECT_ROOT / "reports" / "ml"
    model_dir = PROJECT_ROOT / "models"
    report_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    pred_cols = [c for c in [ID_COLUMN, YEAR_COLUMN, TEXT_COLUMN, TARGET_COLUMN] if c in test.columns]
    predictions_df = test[pred_cols].copy().rename(
        columns={TEXT_COLUMN: "tender_title", TARGET_COLUMN: "actual_category"}
    )
    predictions_df["predicted_category"] = predictions
    predictions_df["model_confidence_uncalibrated"] = model_confidence.round(4)
    predictions_df["correct"] = predictions_df["actual_category"].eq(predictions_df["predicted_category"])
    predictions_df.to_csv(report_dir / "category_holdout_predictions.csv", index=False, encoding="utf-8-sig")
    report_df.to_csv(report_dir / "category_classification_report.csv", encoding="utf-8-sig")
    cm_df.to_csv(report_dir / "category_confusion_matrix.csv", encoding="utf-8-sig")

    train_titles = set(train[TEXT_COLUMN].map(_normalize_title))
    test_normalized_titles = test[TEXT_COLUMN].map(_normalize_title)
    title_overlap_count = int(test_normalized_titles.isin(train_titles).sum())

    summary: dict[str, Any] = {
        "model_name": "TF-IDF + Logistic Regression (class_weight=balanced)",
        "purpose": "Predict source-provided Works/Goods/Services category from tender title only",
        "input_file": str(input_path.relative_to(PROJECT_ROOT) if input_path.is_relative_to(PROJECT_ROOT) else input_path),
        "text_feature": TEXT_COLUMN,
        "target": TARGET_COLUMN,
        "target_classes": CLASS_ORDER,
        "holdout_fiscal_year": holdout_year,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_years": sorted(train[YEAR_COLUMN].unique().tolist()),
        "test_years": sorted(test[YEAR_COLUMN].unique().tolist()),
        "train_class_counts": {str(k): int(v) for k, v in train[TARGET_COLUMN].value_counts().items()},
        "test_class_counts": {str(k): int(v) for k, v in test[TARGET_COLUMN].value_counts().items()},
        "normalized_title_overlap_rows_in_test": title_overlap_count,
        "normalized_title_overlap_pct_of_test": round(title_overlap_count / len(test) * 100, 2),
        "model_metrics": _metrics(test[TARGET_COLUMN], pd.Series(predictions, index=test.index)),
        "dummy_baseline_metrics": _metrics(test[TARGET_COLUMN], pd.Series(dummy_predictions, index=test.index)),
        "per_class_metrics": report_dict,
        "confusion_matrix_label_order": CLASS_ORDER,
        "notes": [
            "Uses only tender title as model input; target is the dataset's source-provided broad category.",
            "Test set is the latest fiscal year specified, with earlier fiscal years used for training.",
            "Model confidence values are uncalibrated class probabilities, not win probabilities.",
            "The 19-class suggested niche taxonomy is provisional and was intentionally not used as target labels.",
            "Results describe this Assam historical snapshot and must not be presented as all-India performance.",
            "Exact normalized title overlap is reported because repeated procurement templates can make a temporal test easier.",
        ],
    }
    (report_dir / "category_classifier_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    model_path = model_dir / "procurement_broad_category_classifier.joblib"
    joblib.dump(model, model_path)
    write_markdown_summary(summary, report_dir / "CATEGORY_CLASSIFIER_RESULTS.md", model_path.relative_to(PROJECT_ROOT))
    return summary


def write_markdown_summary(summary: dict[str, Any], output_path: Path, model_relative_path: Path) -> None:
    m = summary["model_metrics"]
    b = summary["dummy_baseline_metrics"]
    pc = summary["per_class_metrics"]
    lines = [
        "# Broad Procurement Category Classifier — Baseline Results",
        "",
        "## What this model predicts",
        "",
        "The model reads a tender title and predicts the source-provided broad category: **Works, Goods, or Services**.",
        "It does not predict a niche, bid eligibility, bid success, profitability, or tender status.",
        "",
        "## Data split",
        "",
        f"- Training records: **{summary['train_rows']:,}** (fiscal years {', '.join(summary['train_years'])})",
        f"- Held-out test records: **{summary['test_rows']:,}** (fiscal year {summary['holdout_fiscal_year']})",
        "- Input feature: tender title only.",
        "- Target: the existing source-provided `tender/mainProcurementCategory` field.",
        f"- Test titles that also occur in training after simple normalization: **{summary['normalized_title_overlap_rows_in_test']:,} ({summary['normalized_title_overlap_pct_of_test']}%)**. Repeated tender templates may make the test easier.",
        "",
        "## Test metrics",
        "",
        "| Metric | TF-IDF + balanced Logistic Regression | Most-frequent baseline |",
        "|---|---:|---:|",
        f"| Accuracy | {m['accuracy']:.3f} | {b['accuracy']:.3f} |",
        f"| Macro F1 | {m['macro_f1']:.3f} | {b['macro_f1']:.3f} |",
        f"| Weighted F1 | {m['weighted_f1']:.3f} | {b['weighted_f1']:.3f} |",
        f"| Balanced accuracy | {m['balanced_accuracy']:.3f} | {b['balanced_accuracy']:.3f} |",
        "",
        "## Per-class performance",
        "",
        "| Category | Precision | Recall | F1 | Test rows |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in CLASS_ORDER:
        item = pc[label]
        lines.append(
            f"| {label} | {item['precision']:.3f} | {item['recall']:.3f} | {item['f1-score']:.3f} | {int(item['support']):,} |"
        )
    lines += [
        "",
        "## Files generated",
        "",
        f"- Trained model: `{model_relative_path.as_posix()}`",
        "- `category_classifier_metrics.json`: run metadata and all metrics.",
        "- `category_classification_report.csv`: per-class precision/recall/F1.",
        "- `category_confusion_matrix.csv`: actual vs predicted categories.",
        "- `category_holdout_predictions.csv`: held-out records and model outputs for error analysis.",
        "",
        "## Interpretation and limitations",
        "",
        "- The dummy baseline always predicts the most frequent class, so its accuracy alone is misleading under class imbalance.",
        "- Macro F1 and per-class recall help show that minority classes matter; `Services` remains harder than `Works` and `Goods`.",
        "- The temporal split is more realistic than a random split, but some normalized tender titles repeat across years. This is reported rather than hidden.",
        "- This is a first baseline, not an approved production classifier. Inspect errors and consider a grouped/unique-title test or additional manually audited labels before making stronger claims.",
        "- Confidence values are not calibrated and are not the probability of winning a tender.",
        "- These results apply only to the Assam historical dataset and its source category labels.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Cleaned historical CSV")
    parser.add_argument("--holdout-year", default=DEFAULT_HOLDOUT_YEAR, help="Fiscal year held out for evaluation")
    args = parser.parse_args()
    summary = run_training(args.input, args.holdout_year)
    print("Training complete.")
    print(f"Train rows: {summary['train_rows']:,}; test rows: {summary['test_rows']:,}")
    for key, value in summary["model_metrics"].items():
        print(f"{key}: {value:.4f}")
    print(f"Results: {(PROJECT_ROOT / 'reports/ml/CATEGORY_CLASSIFIER_RESULTS.md')}")
    print(f"Model: {PROJECT_ROOT / 'models/procurement_broad_category_classifier.joblib'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
