"""Structured glass observations and collision-relevant visual mechanisms.

A photo-only class is provisional. Optical measurements/specifications and
human review take precedence over zero-shot image-model labels.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

VISUAL_CLASSES = {
    "transparent", "reflective", "mirrored", "tinted",
    "fritted", "patterned", "frosted_translucent", "unknown",
}
SURFACE_TREATMENTS = {
    "none", "low_e_coating", "ceramic_frit", "applied_film",
    "external_markers", "external_screen", "unknown",
}
MOUNTING_SURFACES = {"exterior", "interior", "between_panes", "unknown"}
EVIDENCE_SOURCES = {
    "manufacturer_spec", "instrument_measurement", "human_inspection",
    "site_photo", "zero_shot_image_model", "unknown",
}
MAX_PATTERN_SPACING_CM = 5.0
MIN_PATTERN_WIDTH_MM = 5.0
MIN_PATTERN_COVERAGE_PERCENT = 90.0
MIN_PATTERN_CONTRAST = 0.5


def _optional_range(value: Optional[float], low: float, high: float, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or not low <= float(value) <= high:
        raise ValueError(f"{field} must be in [{low}, {high}]")


@dataclass(frozen=True)
class GlassObservation:
    facade_id: str
    visual_class: str = "unknown"
    surface_treatment: str = "unknown"
    mounting_surface: str = "unknown"
    reflectance_percent: Optional[float] = None
    transmittance_percent: Optional[float] = None
    pattern_spacing_cm: Optional[float] = None
    pattern_width_mm: Optional[float] = None
    pattern_coverage_percent: Optional[float] = None
    pattern_contrast: Optional[float] = None
    evidence_source: str = "unknown"
    classification_confidence: Optional[float] = None
    reviewed_by_human: bool = False
    photo_id: Optional[str] = None
    specification_id: Optional[str] = None

    def validate(self) -> "GlassObservation":
        if not self.facade_id.strip():
            raise ValueError("facade_id is required")
        if self.visual_class not in VISUAL_CLASSES:
            raise ValueError(f"Unsupported visual_class: {self.visual_class}")
        if self.surface_treatment not in SURFACE_TREATMENTS:
            raise ValueError(f"Unsupported surface_treatment: {self.surface_treatment}")
        if self.mounting_surface not in MOUNTING_SURFACES:
            raise ValueError(f"Unsupported mounting_surface: {self.mounting_surface}")
        if self.evidence_source not in EVIDENCE_SOURCES:
            raise ValueError(f"Unsupported evidence_source: {self.evidence_source}")
        _optional_range(self.reflectance_percent, 0, 100, "reflectance_percent")
        _optional_range(self.transmittance_percent, 0, 100, "transmittance_percent")
        _optional_range(self.pattern_coverage_percent, 0, 100, "pattern_coverage_percent")
        _optional_range(self.pattern_contrast, 0, 1, "pattern_contrast")
        _optional_range(self.classification_confidence, 0, 1, "classification_confidence")
        if self.pattern_spacing_cm is not None and self.pattern_spacing_cm < 0:
            raise ValueError("pattern_spacing_cm cannot be negative")
        if self.pattern_width_mm is not None and self.pattern_width_mm < 0:
            raise ValueError("pattern_width_mm cannot be negative")
        return self

    @property
    def needs_human_review(self) -> bool:
        if self.visual_class == "unknown":
            return True
        if self.evidence_source in {"site_photo", "zero_shot_image_model", "unknown"} and not self.reviewed_by_human:
            return True
        if self.classification_confidence is not None and self.classification_confidence < 0.8:
            return True
        pattern_expected = (
            self.visual_class in {"fritted", "patterned"}
            or self.surface_treatment in {"ceramic_frit", "applied_film", "external_markers"}
        )
        if pattern_expected and self.pattern_is_screening_compliant is None:
            return True
        return False

    @property
    def pattern_is_screening_compliant(self) -> Optional[bool]:
        values = (
            self.pattern_spacing_cm, self.pattern_width_mm,
            self.pattern_coverage_percent, self.pattern_contrast,
        )
        if any(value is None for value in values):
            return None
        return bool(
            self.mounting_surface == "exterior"
            and self.pattern_spacing_cm <= MAX_PATTERN_SPACING_CM
            and self.pattern_width_mm >= MIN_PATTERN_WIDTH_MM
            and self.pattern_coverage_percent >= MIN_PATTERN_COVERAGE_PERCENT
            and self.pattern_contrast >= MIN_PATTERN_CONTRAST
        )

    def mechanisms(self) -> dict:
        self.validate()
        transparency = (
            self.visual_class == "transparent"
            or (self.transmittance_percent is not None and self.transmittance_percent >= 70)
        )
        reflection = (
            self.visual_class in {"reflective", "mirrored"}
            or (self.reflectance_percent is not None and self.reflectance_percent >= 30)
        )
        uncertain_tinted = self.visual_class == "tinted" and self.reflectance_percent is None
        pattern_compliant = self.pattern_is_screening_compliant
        pattern_present = (
            self.visual_class in {"fritted", "patterned"}
            or self.surface_treatment in {"ceramic_frit", "applied_film", "external_markers"}
        )
        pattern_noncompliant = pattern_present and pattern_compliant is False
        interior_treatment = (
            self.mounting_surface == "interior"
            and (reflection or self.visual_class in {"transparent", "tinted"})
        )
        return {
            "transparency_confusion": transparency,
            "reflected_habitat": reflection,
            "tinted_optics_unresolved": uncertain_tinted,
            "pattern_present": pattern_present,
            "pattern_screening_compliant": pattern_compliant,
            "pattern_noncompliant_or_incomplete": pattern_noncompliant,
            "pattern_geometry_unverified": pattern_present and pattern_compliant is None,
            "interior_treatment_may_leave_exterior_reflection": interior_treatment,
            "requires_human_review": self.needs_human_review,
            "risk_probability_estimated": False,
        }

    def to_dict(self) -> dict:
        self.validate()
        result = asdict(self)
        result["mechanisms"] = self.mechanisms()
        return result
