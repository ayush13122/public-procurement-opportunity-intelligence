"""Streamlit page to interactively test the historical category classifier."""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.category_prediction import predict_broad_category  # noqa: E402
from train_procurement_category_model import run_training  # noqa: E402

MODEL_PATH = PROJECT_ROOT / "models" / "procurement_broad_category_classifier.joblib"

st.title("ML Tender Category Classifier")
st.caption("Enter a tender title to predict its broad category from the Assam historical training data.")
st.warning(
    "This model predicts the dataset's broad category (Works / Goods / Services). "
    "It does not predict tender win probability, eligibility, live status or profitability. "
    "Scores are uncalibrated and performance is only evaluated on the historical Assam dataset."
)

if not MODEL_PATH.exists():
    st.info("The trained model file is not present yet. Train it from this page or run the training script in the project terminal.")
    if st.button("Train / generate model artifact", type="primary"):
        with st.spinner("Training TF-IDF + Logistic Regression on the historical dataset..."):
            try:
                summary = run_training()
                st.success(
                    f"Training complete · {summary['train_rows']:,} training rows · "
                    f"{summary['test_rows']:,} test rows · accuracy {summary['model_metrics']['accuracy']:.2%}"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Model training failed: {exc}")
    st.stop()

try:
    model_mtime = MODEL_PATH.stat().st_mtime
    cache_key = f"{MODEL_PATH}:{model_mtime}"
    if st.session_state.get("category_model_cache_key") != cache_key:
        st.session_state["category_model"] = joblib.load(MODEL_PATH)
        st.session_state["category_model_cache_key"] = cache_key
    model = st.session_state["category_model"]
except Exception as exc:
    st.error("The saved model could not be loaded in this environment. Retrain it using the project Python interpreter.")
    st.code(str(exc))
    if st.button("Retrain model"):
        with st.spinner("Retraining model..."):
            try:
                run_training()
                st.session_state.pop("category_model", None)
                st.session_state.pop("category_model_cache_key", None)
                st.rerun()
            except Exception as train_exc:
                st.error(f"Retraining failed: {train_exc}")
    st.stop()

with st.form("category_predict_form"):
    title = st.text_area(
        "Tender title",
        placeholder="e.g. Supply and installation of desktop computers in government offices",
        height=100,
    )
    submit = st.form_submit_button("Predict broad category", type="primary")

if submit:
    try:
        result = predict_broad_category(model, title)
        st.subheader("Prediction")
        st.metric("Predicted category", result["predicted_category"])
        st.caption(
            f"Model score: {result['score_uncalibrated']:.1%} (uncalibrated; not a probability of winning a tender)."
        )
        st.subheader("Alternative category scores")
        st.dataframe(
            [
                {"Category": item["category"], "Model score (uncalibrated)": f"{item['score']:.1%}"}
                for item in result["ranked_categories"]
            ],
            hide_index=True,
            width="stretch",
        )
        with st.expander("How to interpret this prediction"):
            st.write(
                "The model uses tender-title text and patterns learned from historical Assam records. "
                "Use the prediction as a triage suggestion, not as an official classification. "
                "A model score is not the chance that a company is eligible, wins, or makes a profit."
            )
    except ValueError as exc:
        st.warning(str(exc))
