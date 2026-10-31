"""Small, testable wrapper around the trained broad-category text classifier."""
from __future__ import annotations

from typing import Any


def predict_broad_category(model: Any, tender_title: str, *, top_n: int = 3) -> dict[str, Any]:
    """Predict Works/Goods/Services from a tender title.

    Returned scores are the model's uncalibrated class scores/probabilities,
    not probabilities of tender eligibility, success or profitability.
    """
    title = str(tender_title or "").strip()
    if not title:
        raise ValueError("Enter a tender title before requesting a prediction.")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    predicted = str(model.predict([title])[0])
    if not hasattr(model, "predict_proba") or not hasattr(model, "classes_"):
        raise ValueError("The loaded model must support predict_proba and expose classes_.")
    scores = model.predict_proba([title])[0]
    classes = [str(label) for label in model.classes_]
    ranking = sorted(
        [{"category": label, "score": float(score)} for label, score in zip(classes, scores)],
        key=lambda item: item["score"],
        reverse=True,
    )[: min(top_n, len(classes))]
    predicted_score = next((item["score"] for item in ranking if item["category"] == predicted), None)
    if predicted_score is None:
        # Include the predicted class even if top_n was smaller than the classes list.
        predicted_score = float(scores[classes.index(predicted)])
    return {
        "tender_title": title,
        "predicted_category": predicted,
        "score_uncalibrated": float(predicted_score),
        "ranked_categories": ranking,
    }
