from __future__ import annotations

import pytest

from birdglass.glass_image_classifier import rank_visual_class_scores


def test_rank_visual_class_scores_returns_relative_label_and_requires_review():
    result = rank_visual_class_scores({
        "transparent": 0.31,
        "reflective": 0.82,
        "mirrored": 0.74,
    })
    assert result["visual_class"] == "reflective"
    assert result["top_score_margin"] == pytest.approx(0.08)
    assert result["requires_human_review"] is True
    assert "not a calibrated probability" in result["score_semantics"]


def test_rank_visual_class_scores_rejects_empty_or_unknown_labels():
    with pytest.raises(ValueError, match="cannot be empty"):
        rank_visual_class_scores({})
    with pytest.raises(ValueError, match="Unknown visual classes"):
        rank_visual_class_scores({"glass": 0.5})


def test_rank_visual_class_scores_rejects_nonfinite_values():
    with pytest.raises(ValueError, match="Non-finite"):
        rank_visual_class_scores({"transparent": float("nan")})
