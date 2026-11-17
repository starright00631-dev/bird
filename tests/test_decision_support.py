from birdglass.decision import ApproachSample, FacadeContext, evaluate_facade
from birdglass.evidence import EvidenceTier, Measurement
from birdglass.glazing import (
    GlassAppearance,
    GlassPanel,
    MarkerContrast,
    MarkerSurface,
    PatternSpec,
    PatternStatus,
    classify_pattern,
)
from birdglass.vegetation import VegetationProfile, relative_cover_band, vegetation_pathways


def m(value, unit, tier=EvidenceTier.MEASURED):
    return Measurement(value=value, unit=unit, tier=tier, source_id="test")


def pattern(horizontal=5.0, vertical=5.0, surface=MarkerSurface.EXTERIOR,
            full=True, contrast=MarkerContrast.HIGH, width=5.0):
    return PatternSpec(
        surface=surface,
        covers_entire_pane=full,
        max_horizontal_gap_cm=m(horizontal, "cm"),
        max_vertical_gap_cm=m(vertical, "cm"),
        min_marker_width_mm=m(width, "mm"),
        contrast=contrast,
    )


def test_exterior_full_pane_5x5_is_strict_pattern():
    assert classify_pattern(pattern()) == PatternStatus.GUIDELINE_2X2


def test_5x10_pattern_is_less_conservative_2x4():
    assert classify_pattern(pattern(horizontal=10, vertical=5)) == PatternStatus.GUIDELINE_2X4


def test_wrong_orientation_does_not_pass_2x4():
    assert classify_pattern(pattern(horizontal=5, vertical=10)) == PatternStatus.NONCOMPLIANT


def test_interior_pattern_does_not_pass():
    assert classify_pattern(pattern(surface=MarkerSurface.INTERIOR)) == PatternStatus.INTERIOR_ONLY


def test_partial_pattern_does_not_pass():
    assert classify_pattern(pattern(full=False)) == PatternStatus.INCOMPLETE


def test_small_markers_do_not_pass():
    assert classify_pattern(pattern(width=4.9)) == PatternStatus.UNDERSIZED


def test_cover_is_reported_at_multiple_scales_without_one_score():
    profile = VegetationProfile(
        cover_pct={
            "0_5m": m(12, "percent", EvidenceTier.REMOTE_SENSING),
            "1_10km": m(68, "percent", EvidenceTier.REMOTE_SENSING),
        }
    )
    pathways = vegetation_pathways(profile)
    assert pathways["local_structure"]["0_5m"]["value"] == 12
    assert pathways["landscape_structure"]["1_10km"]["value"] == 68
    assert pathways["no_single_vegetation_score"] is True


def test_relative_cover_bands_are_region_specific():
    assert relative_cover_band(10, [0, 10, 20, 30, 40, 50]) == "low_relative"
    assert relative_cover_band(50, [0, 10, 20, 30, 40, 50]) == "high_relative"
    assert relative_cover_band(30, [10, 20, 30]) == "insufficient_reference"


def test_no_absolute_risk_from_glass_and_canopy_proxies():
    panel = GlassPanel("P1", GlassAppearance.HIGHLY_REFLECTIVE)
    result = evaluate_facade(FacadeContext(
        glass=panel,
        vegetation=VegetationProfile(
            cover_pct={"0_5m": m(80, "percent", EvidenceTier.REMOTE_SENSING)}
        ),
    ))
    assert result["risk_profile"]["absolute_collision_probability"] is None
    assert result["risk_profile"]["overall_scalar_score"] is None
    assert result["risk_profile"]["identifiability"] == "mechanism_profile_only"


def test_reflected_vegetation_prioritizes_glass_not_tree_removal():
    panel = GlassPanel("P2", GlassAppearance.REFLECTIVE_AND_TRANSPARENT)
    profile = VegetationProfile(
        reflected_vegetation_share=m(0.65, "fraction"),
        cover_pct={"0_5m": m(75, "percent", EvidenceTier.REMOTE_SENSING)},
    )
    result = evaluate_facade(FacadeContext(glass=panel, vegetation=profile))
    actions = [item["action"] for item in result["recommendations"]]
    assert "retrofit_full_pane_exterior_visual_markers" in actions
    assert "audit_reflection_by_solar_time_and_approach_view" in actions
    assert not any("remove_tree" in action for action in actions)


def test_selected_collision_clips_do_not_identify_conditional_rate():
    sample = ApproachSample(
        total_approaches=10,
        glass_contacts=8,
        opaque_contacts=0,
        no_contact=2,
        sampling_frame="selected_events",
        continuous_video_coverage=True,
    )
    assert sample.conditional_glass_contact_rate()["identified"] is False


def test_continuous_complete_video_identifies_conditional_contact_rate():
    sample = ApproachSample(
        total_approaches=100,
        glass_contacts=5,
        opaque_contacts=3,
        no_contact=92,
        sampling_frame="continuous_video",
        continuous_video_coverage=True,
        source_id="camera-1",
    )
    result = sample.conditional_glass_contact_rate()
    assert result["identified"] is True
    assert result["estimate"] == 0.05


def test_right_censoring_produces_bounds_not_point_estimate():
    sample = ApproachSample(
        total_approaches=100,
        glass_contacts=5,
        opaque_contacts=3,
        no_contact=90,
        censored=2,
        sampling_frame="continuous_video",
        continuous_video_coverage=True,
    )
    result = sample.conditional_glass_contact_rate()
    assert result["identified"] is False
    assert result["lower"] == 0.05
    assert result["upper"] == 0.07
    assert result["estimate"] is None


def test_expected_contacts_per_hour_requires_both_rate_and_conditional_sample():
    sample = ApproachSample(
        total_approaches=100,
        glass_contacts=5,
        opaque_contacts=0,
        no_contact=95,
        sampling_frame="continuous_video",
        continuous_video_coverage=True,
    )
    result = evaluate_facade(FacadeContext(
        glass=GlassPanel("P3", GlassAppearance.CLEAR_TRANSPARENT),
        approaches_per_hour=m(20, "approaches/hour"),
        approach_sample=sample,
    ))
    assert result["risk_profile"]["expected_glass_contacts_per_hour"] == 1.0
    assert result["risk_profile"]["identifiability"] == "expected_hourly_contact_rate_identified"


def test_vlr_rating_flag_is_not_a_biological_probability():
    panel = GlassPanel(
        "P4",
        GlassAppearance.TINTED_OR_LOW_E,
        exterior_vlr_pct=m(18, "percent"),
    )
    result = evaluate_facade(FacadeContext(glass=panel))
    assert result["glass_assessment"]["reflection_rating_review_flag_gt_15pct"] is True
    assert result["risk_profile"]["absolute_collision_probability"] is None


def test_guideline_pattern_suppresses_retrofit_recommendation():
    panel = GlassPanel(
        "P5",
        GlassAppearance.HIGHLY_REFLECTIVE,
        pattern=pattern(),
    )
    result = evaluate_facade(FacadeContext(glass=panel))
    actions = [item["action"] for item in result["recommendations"]]
    assert "retrofit_full_pane_exterior_visual_markers" not in actions
    assert "consider_external_screen_or_cord_system" not in actions
