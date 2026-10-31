# Milestone 1 — Broad Procurement Category Classifier

## Goal

Build a first, reproducible NLP/ML baseline that predicts the source-provided broad procurement category (`Works`, `Goods`, `Services`) from the tender title alone.

This milestone deliberately does **not** train on the 19 provisional analytical niches. Those labels have uneven support and are not yet human-verified ground truth.

## Why this target was selected

The cleaned historical dataset contains 34,232 records. The title and source-provided broad category are present for all records. By contrast, the provisional niche labels are highly imbalanced: `Construction & Civil Infrastructure` has 26,781 records, `Other / Needs Review` has 2,113, and several niche classes have only 2–25 records. Training a 19-class model immediately would risk turning provisional mapping decisions into pseudo-ground-truth.

## Method

- **Input feature:** `tender/title` only.
- **Target:** `tender/mainProcurementCategory` (`Works`, `Goods`, `Services`).
- **Text representation:** TF-IDF with word unigrams and bigrams.
- **Classifier:** Logistic Regression with balanced class weights.
- **Training split:** FY 2016–17 through FY 2020–21 (29,542 records).
- **Held-out test split:** FY 2021–22 (4,690 records).
- **Leakage prevention:** do not use the target category, source classification, provisional niche, buyer, or derived report fields as input features.
- **Reproducibility:** fixed holdout fiscal year and fixed model settings.

## First test results

| Metric | Model | Most-frequent baseline |
|---|---:|---:|
| Accuracy | 93.35% | 75.93% |
| Macro F1 | 86.73% | 28.77% |
| Weighted F1 | 93.66% | 65.54% |
| Balanced accuracy | 91.55% | 33.33% |

| Category | Precision | Recall | F1 | Test records |
|---|---:|---:|---:|---:|
| Goods | 86.9% | 94.4% | 90.5% | 816 |
| Services | 63.9% | 86.6% | 73.5% | 313 |
| Works | 98.7% | 93.7% | 96.2% | 3,561 |

The model made 312 incorrect predictions out of 4,690 held-out records. `Services` is the most difficult class and needs targeted error analysis.

## Important caveats

1. The target is a source-provided broad category, not the provisional niche taxonomy.
2. The data is historical Assam procurement data only; metrics do not demonstrate all-India generalisation.
3. 385 test rows (8.21%) have normalized titles that also occur in earlier training years. Tender templates repeat over time, so this may make the test easier. That overlap is reported explicitly.
4. The most-frequent baseline's 75.93% accuracy is misleading because it predicts only `Works`. Macro F1 and per-class recall show minority-class performance better.
5. The Logistic Regression class probabilities are not calibrated. `model_confidence_uncalibrated` is not the probability of winning a tender, being eligible, or making a profit.
6. This is a baseline, not a production-approved classifier. Inspect `reports/ml/category_holdout_predictions.csv`; consider grouped/unique-title evaluation and human verification before making stronger claims.

## Run it

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -q
python src/train_procurement_category_model.py
```

The training script writes:

- `models/procurement_broad_category_classifier.joblib`
- `reports/ml/category_classifier_metrics.json`
- `reports/ml/category_classification_report.csv`
- `reports/ml/category_confusion_matrix.csv`
- `reports/ml/category_holdout_predictions.csv`
- `reports/ml/CATEGORY_CLASSIFIER_RESULTS.md`

## Next milestone

Review a compact, stratified sample of classification errors and title/category conflicts. Then decide whether an audited niche-level classifier is justified. Do not train a 19-class model on the current provisional niche labels without reviewing label quality first.
