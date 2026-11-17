import pytest

from birdglass.glass_image_classifier import rank_visual_class_scores


REVISION = "a" * 40


def test_clip_scores_are_relative_and_human_reviewed():
    result = rank_visual_class_scores(
        {"transparent": 0.66, "reflective": 0.74, "tinted": 0.52},
        model_name="openai/clip-vit-base-patch32",
        model_revision=REVISION,
    )
    assert result["visual_class"] == "reflective"
    assert result["top_score_margin"] == pytest.approx(0.08)
    assert result["requires_human_review"] is True
    assert "not calibrated" in result["score_semantics"]
    assert result["model_revision"] == REVISION


def test_clip_scores_require_immutable_model_revision():
    with pytest.raises(ValueError, match="immutable 40-character"):
        rank_visual_class_scores(
            {"transparent": 0.5},
            model_name="openai/clip-vit-base-patch32",
            model_revision="main",
        )


def test_clip_scores_reject_unknown_or_nonfinite_values():
    with pytest.raises(ValueError, match="Unknown visual classes"):
        rank_visual_class_scores({"glass": 0.5}, model_name="clip", model_revision=REVISION)
    with pytest.raises(ValueError, match="Non-finite"):
        rank_visual_class_scores({"transparent": float("nan")}, model_name="clip", model_revision=REVISION)
