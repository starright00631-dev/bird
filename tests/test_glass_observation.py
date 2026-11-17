import pytest

from birdglass.evidence import EvidenceTier, Measurement
from birdglass.glass_observation import GlassObservation, PatternObservation
from birdglass.glazing import GlassAppearance, MarkerContrast, MarkerSurface, PatternStatus, assess_glazing


def m(value, unit, source="test-source", tier=EvidenceTier.MEASURED):
    return Measurement(value, unit, tier, source_id=source)


def test_human_reviewed_glass_type_maps_to_canonical_glazing():
    observation = GlassObservation(
        facade_id="B1::F1",
        visual_class="reflective",
        visual_class_evidence_tier=EvidenceTier.LOCAL_SURVEY,
        visual_class_source_id="inspection-001",
        reviewed_by_human=True,
        exterior_vlr_pct=m(28, "percent"),
    )
    panel = observation.to_glass_panel()
    assert panel.appearance == GlassAppearance.HIGHLY_REFLECTIVE
    assert assess_glazing(panel)["optical_hazard_profile"] == "elevated"


def test_unreviewed_photo_label_is_provisional_not_a_risk_class():
    observation = GlassObservation(
        facade_id="B1::F2",
        visual_class="reflective",
        visual_class_evidence_tier=EvidenceTier.PROXY,
        visual_class_source_id="clip-run-001",
        reviewed_by_human=False,
    )
    assert observation.to_glass_panel().appearance == GlassAppearance.UNKNOWN
    report = observation.as_dict()
    assert report["provisional_visual_class"] == "reflective"
    assert report["visual_class_confirmed"] is False


def test_frosted_glass_is_preserved_as_a_distinct_review_class():
    observation = GlassObservation(
        facade_id="B1::F3",
        visual_class="frosted_translucent",
        visual_class_evidence_tier=EvidenceTier.MEASURED,
        visual_class_source_id="spec-003",
    )
    assert observation.to_glass_panel().appearance == GlassAppearance.FROSTED_TRANSLUCENT
    assert assess_glazing(observation.to_glass_panel())["optical_hazard_profile"] == "requires_visual_and_spectral_review"


def test_pattern_screen_uses_two_dimensional_gap_geometry_and_full_pane():
    pattern = PatternObservation(
        marker_type="line",
        surface=MarkerSurface.EXTERIOR,
        covers_entire_pane=True,
        max_horizontal_gap_cm=m(5, "cm"),
        max_vertical_gap_cm=m(5, "cm"),
        min_feature_dimension_mm=m(5, "mm"),
        contrast=MarkerContrast.HIGH,
    )
    observation = GlassObservation(
        facade_id="B1::F4",
        visual_class="transparent",
        visual_class_evidence_tier=EvidenceTier.MEASURED,
        visual_class_source_id="survey-004",
        pattern=pattern,
    )
    assert assess_glazing(observation.to_glass_panel())["pattern_status"] == PatternStatus.GUIDELINE_2X2.value
    screen = pattern.component_dimension_screen()
    assert screen["component_dimension_threshold_mm"] == pytest.approx(3.175)
    assert "not ABC Threat Factor" in screen["scope"]


def test_dot_component_dimension_is_not_confused_with_line_dimension():
    pattern = PatternObservation(
        marker_type="dot",
        surface=MarkerSurface.EXTERIOR,
        covers_entire_pane=True,
        max_horizontal_gap_cm=m(5, "cm"),
        max_vertical_gap_cm=m(5, "cm"),
        min_feature_dimension_mm=m(5, "mm"),
        contrast=MarkerContrast.HIGH,
    )
    screen = pattern.component_dimension_screen()
    assert screen["component_dimension_threshold_mm"] == pytest.approx(6.35)
    assert screen["status"] == "component_dimension_below_screen"


def test_interior_or_partial_pattern_does_not_pass_exterior_screen():
    for surface, full, expected in (
        (MarkerSurface.INTERIOR, True, PatternStatus.INTERIOR_ONLY),
        (MarkerSurface.EXTERIOR, False, PatternStatus.INCOMPLETE),
    ):
        pattern = PatternObservation(
            marker_type="dot",
            surface=surface,
            covers_entire_pane=full,
            max_horizontal_gap_cm=m(4, "cm"),
            max_vertical_gap_cm=m(4, "cm"),
            min_feature_dimension_mm=m(7, "mm"),
            contrast=MarkerContrast.HIGH,
        )
        panel = GlassObservation(
            facade_id="B1::F5",
            visual_class="transparent",
            visual_class_evidence_tier=EvidenceTier.MEASURED,
            visual_class_source_id="survey-005",
            pattern=pattern,
        ).to_glass_panel()
        assert assess_glazing(panel)["pattern_status"] == expected.value


def test_no_pattern_geometry_means_no_phantom_compliance():
    observation = GlassObservation(
        facade_id="B1::F6",
        visual_class="transparent",
        visual_class_evidence_tier=EvidenceTier.MEASURED,
        visual_class_source_id="survey-006",
        surface_treatment="external_markers",
        pattern=None,
    )
    assert assess_glazing(observation.to_glass_panel())["pattern_status"] == PatternStatus.UNTREATED.value


def test_measurement_units_and_provenance_are_required():
    with pytest.raises(ValueError, match="must use one of"):
        GlassObservation(
            facade_id="B1::F7",
            exterior_vlr_pct=m(20, "fraction"),
        ).validate()
    with pytest.raises(ValueError, match="source_id"):
        GlassObservation(
            facade_id="B1::F8",
            visual_class="transparent",
            visual_class_evidence_tier=EvidenceTier.MEASURED,
        ).validate()
