from pathlib import Path
import sys

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.category_prediction import predict_broad_category  # noqa: E402


class FakeModel:
    classes_ = np.array(["Goods", "Services", "Works"])

    def predict(self, values):
        assert len(values) == 1
        return np.array(["Goods"])

    def predict_proba(self, values):
        return np.array([[0.7, 0.2, 0.1]])


def test_predict_broad_category_returns_predicted_label_and_score():
    result = predict_broad_category(FakeModel(), " Supply computer systems ")
    assert result["tender_title"] == "Supply computer systems"
    assert result["predicted_category"] == "Goods"
    assert result["score_uncalibrated"] == pytest.approx(0.7)
    assert result["ranked_categories"][0]["category"] == "Goods"


def test_predict_broad_category_rejects_blank_title():
    with pytest.raises(ValueError, match="Enter a tender title"):
        predict_broad_category(FakeModel(), "  ")


def test_predict_broad_category_rejects_invalid_top_n():
    with pytest.raises(ValueError, match="top_n"):
        predict_broad_category(FakeModel(), "Supply computers", top_n=0)
