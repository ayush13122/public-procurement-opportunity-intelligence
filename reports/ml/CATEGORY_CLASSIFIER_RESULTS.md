# Broad Procurement Category Classifier — Baseline Results

## What this model predicts

The model reads a tender title and predicts the source-provided broad category: **Works, Goods, or Services**.
It does not predict a niche, bid eligibility, bid success, profitability, or tender status.

## Data split

- Training records: **29,542** (fiscal years 2016-2017, 2017-2018, 2018-2019, 2019-2020, 2020-2021)
- Held-out test records: **4,690** (fiscal year 2021-2022)
- Input feature: tender title only.
- Target: the existing source-provided `tender/mainProcurementCategory` field.
- Test titles that also occur in training after simple normalization: **385 (8.21%)**. Repeated tender templates may make the test easier.

## Test metrics

| Metric | TF-IDF + balanced Logistic Regression | Most-frequent baseline |
|---|---:|---:|
| Accuracy | 0.933 | 0.759 |
| Macro F1 | 0.867 | 0.288 |
| Weighted F1 | 0.937 | 0.655 |
| Balanced accuracy | 0.916 | 0.333 |

## Per-class performance

| Category | Precision | Recall | F1 | Test rows |
|---|---:|---:|---:|---:|
| Goods | 0.869 | 0.944 | 0.905 | 816 |
| Services | 0.639 | 0.866 | 0.735 | 313 |
| Works | 0.987 | 0.937 | 0.962 | 3,561 |

## Files generated

- Trained model: `models/procurement_broad_category_classifier.joblib`
- `category_classifier_metrics.json`: run metadata and all metrics.
- `category_classification_report.csv`: per-class precision/recall/F1.
- `category_confusion_matrix.csv`: actual vs predicted categories.
- `category_holdout_predictions.csv`: held-out records and model outputs for error analysis.

## Interpretation and limitations

- The dummy baseline always predicts the most frequent class, so its accuracy alone is misleading under class imbalance.
- Macro F1 and per-class recall help show that minority classes matter; `Services` remains harder than `Works` and `Goods`.
- The temporal split is more realistic than a random split, but some normalized tender titles repeat across years. This is reported rather than hidden.
- This is a first baseline, not an approved production classifier. Inspect errors and consider a grouped/unique-title test or additional manually audited labels before making stronger claims.
- Confidence values are not calibrated and are not the probability of winning a tender.
- These results apply only to the Assam historical dataset and its source category labels.
