import pytest

from birdglass.decision import FacadeContext, evaluate_facade
from birdglass.evidence import EvidenceTier, Measurement
from birdglass.glass_observation import GlassObservation
from birdglass.glazing import GlassAppearance
from birdglass.vegetation import VEGETATION_BUFFERS, vegetation_pathways
from birdglass.vegetation_observation import VegetationObservation


def m(value, unit, tier=EvidenceTier.REMOTE_SENSING, source="veg-source"):
    return Measurement(value, unit, tier, source_id=source)


def test_five_annular_bands_map_to_canonical_profile_without_cumulative_mix():
    obs = VegetationObservation(
        facade_id="B1::F1",
        cover_pct_by_band={
            "0_5m": m(10, "percent"),
            "5_25m": m(20, "percent"),
            "25_100m": m(30, "percent"),
            "100m_1km": m(40, "percent"),
            "1_10km": m(50, "percent"),
        },
        facade_porous_cover_50m_percent=m(35, "percent"),
        facade_tree_cover_50m_percent=m(25, "percent"),
        stories_reflecting_canopy=m(2.5, "stories", EvidenceTier.FIELD_STUDY),
        building_vegetation_proportion=m(0.42, "fraction"),
    )
    profile = obs.to_profile()
    assert tuple(profile.cover_pct) == VEGETATION_BUFFERS
    pathways = vegetation_pathways(profile)
    assert pathways["local_structure"]["0_5m"]["value"] == 10
    assert pathways["facade_specific_50m_buffer"]["tree_canopy_cover_percent"]["value"] == 25
    assert pathways["vertical_reflection_context"]["stories_reflecting_canopy"]["value"] == 2.5
    assert pathways["building_level_context"]["vegetation_proportion"]["value"] == 0.42


def test_stories_reflecting_canopy_is_not_direct_reflection_evidence():
    vegetation = VegetationObservation(
        facade_id="B1::F2",
        facade_tree_cover_50m_percent=m(50, "percent"),
        stories_reflecting_canopy=m(4, "stories", EvidenceTier.FIELD_STUDY),
    )
    glass = GlassObservation(
        facade_id="B1::F2",
        visual_class="reflective",
        visual_class_evidence_tier=EvidenceTier.MEASURED,
        visual_class_source_id="glass-inspection",
    )
    result = evaluate_facade(FacadeContext(
        glass=glass.to_glass_panel(),
        vegetation=vegetation.to_profile(),
    ))
    actions = {item["action"] for item in result["recommendations"]}
    assert "audit_reflection_by_solar_time_and_approach_view" not in actions


def test_only_measured_reflected_scene_triggers_reflection_specific_audit():
    vegetation = VegetationObservation(
        facade_id="B1::F3",
        facade_tree_cover_50m_percent=m(50, "percent"),
        stories_reflecting_canopy=m(4, "stories", EvidenceTier.FIELD_STUDY),
        reflected_vegetation_share=m(0.4, "fraction", EvidenceTier.LOCAL_SURVEY),
    )
    glass = GlassObservation(
        facade_id="B1::F3",
        visual_class="reflective",
        visual_class_evidence_tier=EvidenceTier.MEASURED,
        visual_class_source_id="glass-inspection",
    )
    result = evaluate_facade(FacadeContext(
        glass=glass.to_glass_panel(),
        vegetation=vegetation.to_profile(),
    ))
    actions = {item["action"] for item in result["recommendations"]}
    assert "audit_reflection_by_solar_time_and_approach_view" in actions


def test_proxy_reflection_does_not_trigger_reflection_specific_action():
    vegetation = VegetationObservation(
        facade_id="B1::F4",
        reflected_vegetation_share=m(0.4, "fraction", EvidenceTier.PROXY),
    )
    glass = GlassObservation(
        facade_id="B1::F4",
        visual_class="reflective",
        visual_class_evidence_tier=EvidenceTier.MEASURED,
        visual_class_source_id="glass-inspection",
    )
    result = evaluate_facade(FacadeContext(
        glass=glass.to_glass_panel(),
        vegetation=vegetation.to_profile(),
    ))
    actions = {item["action"] for item in result["recommendations"]}
    assert "audit_reflection_by_solar_time_and_approach_view" not in actions


def test_unknown_cumulative_band_names_fail_closed():
    with pytest.raises(ValueError, match="Unsupported annular"):
        VegetationObservation(
            facade_id="B1::F5",
            cover_pct_by_band={"0_25m": m(25, "percent")},
        ).validate()


def test_missing_bands_remain_missing_not_zero():
    obs = VegetationObservation(
        facade_id="B1::F6",
        cover_pct_by_band={"0_5m": m(10, "percent")},
    )
    profile = obs.to_profile()
    assert profile.cover_pct["0_5m"].value == 10
    assert "5_25m" not in profile.cover_pct
