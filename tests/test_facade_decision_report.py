from __future__ import annotations

import pytest

from birdglass.facade_decision_report import build_facade_decision_report
from birdglass.glass_observation import GlassObservation
from birdglass.vegetation_exposure import VegetationExposure


def test_facade_report_joins_glass_vegetation_and_retrofit_decision():
    glass = GlassObservation(
        facade_id="B1::F1", visual_class="transparent",
        evidence_source="human_inspection", reviewed_by_human=True,
    )
    vegetation = VegetationExposure(
        facade_id="B1::F1", facade_tree_cover_50m_percent=30,
        stories_reflecting_canopy=2,
    )
    report = build_facade_decision_report(glass, vegetation)
    assert report["facade_id"] == "B1::F1"
    assert report["risk_prediction"]["status"] == "not_provided"
    assert report["retrofit_decision"]["recommendations"][0]["intervention_id"] == "exterior_visual_markers"


def test_facade_report_requires_model_metadata_and_valid_probability():
    glass = GlassObservation(facade_id="B1::F2", visual_class="unknown")
    vegetation = VegetationExposure(facade_id="B1::F2")
    with pytest.raises(ValueError, match="model_name and model_scope"):
        build_facade_decision_report(
            glass, vegetation, predicted_detected_carcass_probability_24h=0.2
        )
    with pytest.raises(ValueError, match="must be in"):
        build_facade_decision_report(
            glass, vegetation, predicted_detected_carcass_probability_24h=1.2,
            model_name="x", model_scope="y"
        )
