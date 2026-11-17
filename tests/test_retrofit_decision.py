from __future__ import annotations

from birdglass.glass_observation import GlassObservation
from birdglass.retrofit_decision import recommend_interventions
from birdglass.vegetation_exposure import VegetationExposure


def test_reflective_glass_with_canopy_prioritizes_glass_side_measures_not_pruning():
    glass = GlassObservation(
        facade_id="B1::F1", visual_class="reflective",
        reflectance_percent=45, evidence_source="instrument_measurement",
    )
    vegetation = VegetationExposure(
        facade_id="B1::F1", facade_tree_cover_50m_percent=42,
        facade_porous_cover_50m_percent=60, stories_reflecting_canopy=4,
    )
    result = recommend_interventions(glass, vegetation)
    ids = [r["intervention_id"] for r in result["recommendations"]]
    assert ids[0] == "exterior_visual_markers"
    assert "exterior_screen" in ids
    assert "external_shading" in ids
    assert "vegetation_pruning" not in ids
    assert all(r["efficacy_estimate"] is None for r in result["recommendations"])
    assert "Do not recommend tree removal" in result["vegetation_policy"]


def test_unknown_glass_type_puts_optical_audit_first():
    glass = GlassObservation(facade_id="B1::F2", visual_class="unknown")
    vegetation = VegetationExposure(facade_id="B1::F2")
    result = recommend_interventions(glass, vegetation)
    assert result["recommendations"][0]["intervention_id"] == "glass_optical_audit"


def test_confirmed_night_lighting_issue_adds_supporting_measure():
    glass = GlassObservation(
        facade_id="B1::F3", visual_class="transparent",
        evidence_source="human_inspection", reviewed_by_human=True,
    )
    vegetation = VegetationExposure(facade_id="B1::F3")
    result = recommend_interventions(glass, vegetation, night_lighting_problem_confirmed=True)
    ids = [r["intervention_id"] for r in result["recommendations"]]
    assert "lighting_management" in ids


def test_pruning_only_appears_after_confirmed_conflict_and_no_glass_retrofit():
    glass = GlassObservation(facade_id="B1::F4", visual_class="unknown")
    vegetation = VegetationExposure(facade_id="B1::F4", facade_tree_cover_50m_percent=70)
    result = recommend_interventions(
        glass, vegetation, vegetation_conflict_confirmed=True,
        glass_side_retrofit_feasible=False,
    )
    ids = [r["intervention_id"] for r in result["recommendations"]]
    assert "vegetation_pruning" in ids
    pruning = next(r for r in result["recommendations"] if r["intervention_id"] == "vegetation_pruning")
    assert pruning["priority"] == "low"


def test_interior_pattern_is_not_treated_as_a_compliant_external_treatment():
    glass = GlassObservation(
        facade_id="B1::F5", visual_class="reflective",
        mounting_surface="interior", surface_treatment="external_markers",
        pattern_spacing_cm=4, pattern_width_mm=6, pattern_coverage_percent=100,
        pattern_contrast=0.9,
    )
    vegetation = VegetationExposure(facade_id="B1::F5")
    result = recommend_interventions(glass, vegetation)
    ids = [r["intervention_id"] for r in result["recommendations"]]
    assert "pattern_upgrade" in ids
    assert "interior_markers_only" in ids
