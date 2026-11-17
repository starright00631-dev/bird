import pytest

from birdglass.decision import ApproachSample, FacadeContext, evaluate_facade
from birdglass.evidence import EvidenceTier, Measurement
from birdglass.glazing import (
    GlassAppearance,
    GlassPanel,
    MarkerContrast,
    MarkerSurface,
    PatternSpec,
    assess_glazing,
)
from birdglass.vegetation import VegetationProfile


def m(value, unit, tier=EvidenceTier.MEASURED):
    return Measurement(value=value, unit=unit, tier=tier, source_id="test")


def pattern(surface=MarkerSurface.EXTERIOR):
    return PatternSpec(
        surface=surface,
        covers_entire_pane=True,
        max_horizontal_gap_cm=m(5, "cm"),
        max_vertical_gap_cm=m(5, "cm"),
        min_marker_width_mm=m(5, "mm"),
        contrast=MarkerContrast.HIGH,
    )


def actions(result):
    return {item["action"] for item in result["recommendations"]}


def test_tinted_or_low_e_label_alone_is_not_a_high_hazard_finding():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("T1", GlassAppearance.TINTED_OR_LOW_E)
    ))
    assert result["glass_assessment"]["optical_hazard_profile"] == "unclassified"
    assert "retrofit_full_pane_exterior_visual_markers" not in actions(result)


def test_tinted_or_low_e_with_measured_high_vlr_triggers_review():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel(
            "T2",
            GlassAppearance.TINTED_OR_LOW_E,
            exterior_vlr_pct=m(18, "percent"),
        )
    ))
    assert result["glass_assessment"]["optical_hazard_profile"] == "elevated"
    assert "retrofit_full_pane_exterior_visual_markers" in actions(result)


def test_opaque_spandrel_reflectance_is_not_automatically_safe():
    result = assess_glazing(GlassPanel(
        "S1",
        GlassAppearance.OPAQUE_SPANDREL,
        exterior_vlr_pct=m(18, "percent"),
    ))
    assert result["optical_hazard_profile"] == "reflective_opaque_surface_requires_review"


def test_missing_vegetation_measurement_is_not_reported_as_available():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("V1", GlassAppearance.UNKNOWN),
        vegetation=VegetationProfile(
            cover_pct={"0_5m": Measurement(None, "percent", EvidenceTier.UNKNOWN)}
        ),
    ))
    assert not any(x["pathway"] == "vegetation_scale" for x in result["findings"])
    assert "retain_vegetation_as_a_multiscale_context_variable" not in actions(result)


def test_vlr_surface2_review_does_not_apply_to_exterior_pattern():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel(
            "P1",
            GlassAppearance.HIGHLY_REFLECTIVE,
            exterior_vlr_pct=m(20, "percent"),
            pattern=pattern(MarkerSurface.EXTERIOR),
        )
    ))
    assert result["glass_assessment"]["surface2_rating_review_flag_gt_15pct"] is False
    assert "measure_first_surface_reflection_and_marker_contrast" not in actions(result)


def test_vlr_surface2_review_applies_to_interior_pattern():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel(
            "P2",
            GlassAppearance.HIGHLY_REFLECTIVE,
            exterior_vlr_pct=m(20, "percent"),
            pattern=pattern(MarkerSurface.INTERIOR),
        )
    ))
    assert result["glass_assessment"]["surface2_rating_review_flag_gt_15pct"] is True
    assert "measure_first_surface_reflection_and_marker_contrast" in actions(result)


def test_proxy_approach_rate_cannot_create_expected_hourly_rate():
    sample = ApproachSample(
        total_approaches=10,
        glass_contacts=2,
        opaque_contacts=0,
        no_contact=8,
        sampling_frame="continuous_video",
        continuous_video_coverage=True,
        source_id="camera-1",
    )
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("A1", GlassAppearance.CLEAR_TRANSPARENT),
        approaches_per_hour=m(20, "approaches/hour", EvidenceTier.PROXY),
        approach_sample=sample,
    ))
    assert result["risk_profile"]["expected_glass_contacts_per_hour"] is None
    assert result["risk_profile"]["identifiability"] == (
        "conditional_contact_identified_absolute_rate_not_identified"
    )


def test_approach_rate_rejects_wrong_units():
    with pytest.raises(ValueError, match="approaches/hour"):
        FacadeContext(
            glass=GlassPanel("A2", GlassAppearance.CLEAR_TRANSPARENT),
            approaches_per_hour=m(20, "birds/hour"),
        )


def test_approach_rate_rejects_negative_values():
    with pytest.raises(ValueError, match="cannot be negative"):
        FacadeContext(
            glass=GlassPanel("A3", GlassAppearance.CLEAR_TRANSPARENT),
            approaches_per_hour=m(-1, "approaches/hour"),
        )


def test_boolean_approach_counts_are_not_accepted_as_integers():
    with pytest.raises(ValueError, match="nonnegative integers"):
        ApproachSample(
            total_approaches=True,
            glass_contacts=0,
            opaque_contacts=0,
            no_contact=1,
        )


def test_intervention_comparison_never_invents_a_best_option_or_effect_size():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("I1", GlassAppearance.REFLECTIVE_AND_TRANSPARENT)
    ))
    comparison = result["intervention_comparison"]
    assert comparison["effectiveness_ranked"] is False
    assert comparison["best_option"] is None
    assert comparison["effect_estimates_for_this_panel"] is None
    assert all(item["site_effect_estimate"] is None for item in comparison["candidates"])


def test_vegetation_removal_is_not_recommended_from_cover_alone():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("V2", GlassAppearance.CLEAR_TRANSPARENT),
        vegetation=VegetationProfile(
            cover_pct={"0_5m": m(85, "percent", EvidenceTier.REMOTE_SENSING)}
        ),
    ))
    candidate = next(
        x for x in result["intervention_comparison"]["candidates"]
        if x["action"] == "vegetation_reconfiguration"
    )
    assert candidate["decision"] == "do_not_recommend_removal_or_pruning_from_cover_alone"


def test_lighting_candidate_requires_measured_night_activity_and_measured_light():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("L1", GlassAppearance.CLEAR_TRANSPARENT),
        nocturnal_migrant_activity=m(1, "index", EvidenceTier.LOCAL_SURVEY),
        artificial_light_level=m(100, "lux", EvidenceTier.PROXY),
    ))
    assert "seasonal_night_lighting_controls" not in actions(result)
    assert all(
        x["action"] != "seasonal_night_lighting_controls"
        for x in result["intervention_comparison"]["candidates"]
    )


def test_lighting_candidate_appears_when_both_inputs_are_measured():
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("L2", GlassAppearance.CLEAR_TRANSPARENT),
        nocturnal_migrant_activity=m(1, "index", EvidenceTier.LOCAL_SURVEY),
        artificial_light_level=m(100, "lux", EvidenceTier.MEASURED),
    ))
    assert "seasonal_night_lighting_controls" in actions(result)
    assert any(
        x["action"] == "seasonal_night_lighting_controls"
        for x in result["intervention_comparison"]["candidates"]
    )


def test_pattern_screen_scope_does_not_claim_abc_certification():
    result = assess_glazing(GlassPanel(
        "P3",
        GlassAppearance.CLEAR_TRANSPARENT,
        pattern=pattern(),
    ))
    scope = result["pattern_standard_scope"].lower()
    assert "eccc" in scope
    assert "not an abc" in scope
