from __future__ import annotations

import pytest

from birdglass.glass_observation import GlassObservation


def test_transparent_glass_flags_transparency_mechanism():
    observation = GlassObservation(
        facade_id="B1::F1",
        visual_class="transparent",
        evidence_source="human_inspection",
        classification_confidence=0.95,
        reviewed_by_human=True,
        transmittance_percent=85,
    )
    result = observation.mechanisms()
    assert result["transparency_confusion"] is True
    assert result["reflected_habitat"] is False
    assert result["requires_human_review"] is False


def test_reflective_glass_flags_reflection_mechanism():
    observation = GlassObservation(
        facade_id="B1::F2",
        visual_class="reflective",
        evidence_source="instrument_measurement",
        reflectance_percent=42,
    )
    assert observation.mechanisms()["reflected_habitat"] is True


def test_photo_only_or_unknown_glass_requires_human_review():
    observation = GlassObservation(
        facade_id="B1::F3",
        visual_class="unknown",
        evidence_source="zero_shot_image_model",
    )
    assert observation.needs_human_review is True
    assert observation.mechanisms()["risk_probability_estimated"] is False


def test_pattern_screening_requires_exterior_spacing_width_coverage_and_contrast():
    compliant = GlassObservation(
        facade_id="B1::F4",
        visual_class="patterned",
        surface_treatment="external_markers",
        mounting_surface="exterior",
        pattern_spacing_cm=5,
        pattern_width_mm=5,
        pattern_coverage_percent=95,
        pattern_contrast=0.8,
        evidence_source="human_inspection",
        reviewed_by_human=True,
    )
    assert compliant.pattern_is_screening_compliant is True
    interior = GlassObservation(
        facade_id="B1::F5",
        visual_class="reflective",
        surface_treatment="external_markers",
        mounting_surface="interior",
        pattern_spacing_cm=4,
        pattern_width_mm=6,
        pattern_coverage_percent=100,
        pattern_contrast=0.9,
    )
    assert interior.pattern_is_screening_compliant is False
    assert interior.mechanisms()["interior_treatment_may_leave_exterior_reflection"] is True


def test_invalid_optical_percentages_are_rejected():
    with pytest.raises(ValueError, match="reflectance_percent"):
        GlassObservation(facade_id="B1::F6", reflectance_percent=120).validate()
