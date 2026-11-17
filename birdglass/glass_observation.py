"""Evidence-preserving façade glass intake adapter.

This module does not implement a second glass-risk classifier. It converts
human/spec/instrument observations into the canonical GlassPanel and
PatternSpec types in birdglass.glazing. Photo/CLIP-only labels remain
provisional until human review or a qualifying local measurement.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from .evidence import EvidenceTier, Measurement, measurement_dict
from .glazing import (
    GlassAppearance,
    GlassPanel,
    MarkerContrast,
    MarkerSurface,
    PatternSpec,
    assess_glazing,
    classify_pattern,
)

VISUAL_CLASS_TO_CANONICAL = {
    "transparent": GlassAppearance.CLEAR_TRANSPARENT,
    "reflective": GlassAppearance.HIGHLY_REFLECTIVE,
    "mirrored": GlassAppearance.HIGHLY_REFLECTIVE,
    "tinted": GlassAppearance.TINTED_OR_LOW_E,
    "fritted": GlassAppearance.FRITTED_OR_PATTERNED,
    "patterned": GlassAppearance.FRITTED_OR_PATTERNED,
    "frosted_translucent": GlassAppearance.FROSTED_TRANSLUCENT,
    "opaque_spandrel": GlassAppearance.OPAQUE_SPANDREL,
    "unknown": GlassAppearance.UNKNOWN,
}
SURFACE_TREATMENTS = {
    "none", "low_e_coating", "ceramic_frit", "applied_film",
    "external_markers", "external_screen", "unknown",
}
COATING_POSITIONS = {
    "surface1_exterior", "surface2_interior", "between_panes",
    "not_applicable", "unknown",
}
PATTERN_TYPES = {"dot", "line", "frit", "film", "cord", "screen", "other"}
CONFIRMED_VISUAL_TIERS = {EvidenceTier.MEASURED, EvidenceTier.LOCAL_SURVEY}


def _check_measurement(
    value: Measurement | None,
    units: set[str],
    lower: float,
    upper: float,
    label: str,
) -> None:
    if value is None or value.value is None:
        return
    if value.unit not in units:
        raise ValueError(f"{label} must use one of {sorted(units)}")
    if not lower <= value.value <= upper:
        raise ValueError(f"{label} must lie in [{lower}, {upper}]")
    if not value.source_id or not value.source_id.strip():
        raise ValueError(f"{label} requires source_id")


@dataclass(frozen=True)
class PatternObservation:
    """Measured marker/frit geometry; not a product certification."""

    marker_type: str
    surface: MarkerSurface
    covers_entire_pane: bool | None
    max_horizontal_gap_cm: Measurement | None
    max_vertical_gap_cm: Measurement | None
    min_feature_dimension_mm: Measurement | None
    contrast: MarkerContrast = MarkerContrast.UNKNOWN
    product_or_specification_id: str | None = None

    def validate(self) -> "PatternObservation":
        if self.marker_type not in PATTERN_TYPES:
            raise ValueError(f"Unsupported marker_type: {self.marker_type}")
        if not isinstance(self.surface, MarkerSurface):
            raise ValueError("surface must be a MarkerSurface")
        if self.covers_entire_pane is not None and not isinstance(self.covers_entire_pane, bool):
            raise ValueError("covers_entire_pane must be a bool or None")
        if not isinstance(self.contrast, MarkerContrast):
            raise ValueError("contrast must be a MarkerContrast")
        _check_measurement(self.max_horizontal_gap_cm, {"cm"}, 0, 1000, "horizontal gap")
        _check_measurement(self.max_vertical_gap_cm, {"cm"}, 0, 1000, "vertical gap")
        _check_measurement(self.min_feature_dimension_mm, {"mm"}, 0, 1000, "feature dimension")
        return self

    def to_pattern_spec(self) -> PatternSpec:
        self.validate()
        return PatternSpec(
            surface=self.surface,
            covers_entire_pane=self.covers_entire_pane,
            max_horizontal_gap_cm=self.max_horizontal_gap_cm,
            max_vertical_gap_cm=self.max_vertical_gap_cm,
            min_marker_width_mm=self.min_feature_dimension_mm,
            contrast=self.contrast,
        )

    def component_dimension_screen(self) -> dict:
        """Return a component-only ABC geometry screen, never a full rating."""
        self.validate()
        value = (
            self.min_feature_dimension_mm.value
            if self.min_feature_dimension_mm is not None
            else None
        )
        if value is None:
            status = "not_assessed"
            threshold = None
        elif self.marker_type == "line":
            threshold = 3.175  # 1/8 inch
            status = "component_dimension_met" if value >= threshold else "component_dimension_below_screen"
        elif self.marker_type == "dot":
            threshold = 6.35  # 1/4 inch
            status = "component_dimension_met" if value >= threshold else "component_dimension_below_screen"
        else:
            threshold = None
            status = "marker_type_specific_dimension_not_assessed"
        return {
            "marker_type": self.marker_type,
            "measured_min_dimension_mm": value,
            "component_dimension_threshold_mm": threshold,
            "status": status,
            "scope": "component dimension only; not ABC Threat Factor rating or product certification",
        }

    def as_dict(self) -> dict:
        self.validate()
        return {
            "marker_type": self.marker_type,
            "surface": self.surface.value,
            "covers_entire_pane": self.covers_entire_pane,
            "max_horizontal_gap_cm": measurement_dict(self.max_horizontal_gap_cm),
            "max_vertical_gap_cm": measurement_dict(self.max_vertical_gap_cm),
            "min_feature_dimension_mm": measurement_dict(self.min_feature_dimension_mm),
            "contrast": self.contrast.value,
            "product_or_specification_id": self.product_or_specification_id,
            "abc_component_dimension_screen": self.component_dimension_screen(),
        }


@dataclass(frozen=True)
class GlassObservation:
    """One façade's optical/glass evidence, with provisional labels preserved."""

    facade_id: str
    visual_class: str = "unknown"
    visual_class_evidence_tier: EvidenceTier = EvidenceTier.UNKNOWN
    visual_class_source_id: str | None = None
    reviewed_by_human: bool = False
    surface_treatment: str = "unknown"
    coating_position: str = "unknown"
    area_m2: Measurement | None = None
    exterior_vlr_pct: Measurement | None = None
    exterior_vlt_pct: Measurement | None = None
    reflected_vegetation_share: Measurement | None = None
    transmitted_habitat_share: Measurement | None = None
    pattern: PatternObservation | None = None
    photo_ids: tuple[str, ...] = ()
    specification_id: str | None = None
    observed_at: str | None = None
    observer_id: str | None = None

    def validate(self) -> "GlassObservation":
        if not self.facade_id.strip():
            raise ValueError("facade_id is required")
        if self.visual_class not in VISUAL_CLASS_TO_CANONICAL:
            raise ValueError(f"Unsupported visual_class: {self.visual_class}")
        if not isinstance(self.visual_class_evidence_tier, EvidenceTier):
            raise ValueError("visual_class_evidence_tier must be an EvidenceTier")
        if self.visual_class != "unknown" and (
            self.reviewed_by_human or self.visual_class_evidence_tier != EvidenceTier.UNKNOWN
        ):
            if not self.visual_class_source_id or not self.visual_class_source_id.strip():
                raise ValueError("A reviewed/non-unknown visual class requires visual_class_source_id")
        if self.surface_treatment not in SURFACE_TREATMENTS:
            raise ValueError(f"Unsupported surface_treatment: {self.surface_treatment}")
        if self.coating_position not in COATING_POSITIONS:
            raise ValueError(f"Unsupported coating_position: {self.coating_position}")
        _check_measurement(self.area_m2, {"m2", "m^2"}, 0.000001, 1e9, "area_m2")
        _check_measurement(self.exterior_vlr_pct, {"percent", "%"}, 0, 100, "exterior_vlr_pct")
        _check_measurement(self.exterior_vlt_pct, {"percent", "%"}, 0, 100, "exterior_vlt_pct")
        _check_measurement(self.reflected_vegetation_share, {"fraction"}, 0, 1, "reflected_vegetation_share")
        _check_measurement(self.transmitted_habitat_share, {"fraction"}, 0, 1, "transmitted_habitat_share")
        if self.pattern is not None:
            self.pattern.validate()
        if any(not value.strip() for value in self.photo_ids):
            raise ValueError("photo_ids cannot contain empty values")
        return self

    @property
    def visual_class_confirmed(self) -> bool:
        return (
            self.visual_class != "unknown"
            and (
                self.reviewed_by_human
                or self.visual_class_evidence_tier in CONFIRMED_VISUAL_TIERS
            )
        )

    def to_glass_panel(self) -> GlassPanel:
        """Convert to the canonical glass model; never trust unreviewed photo labels."""
        self.validate()
        appearance = (
            VISUAL_CLASS_TO_CANONICAL[self.visual_class]
            if self.visual_class_confirmed
            else GlassAppearance.UNKNOWN
        )
        pattern_spec = self.pattern.to_pattern_spec() if self.pattern else None
        return GlassPanel(
            panel_id=self.facade_id,
            appearance=appearance,
            area_m2=self.area_m2,
            exterior_vlr_pct=self.exterior_vlr_pct,
            exterior_vlt_pct=self.exterior_vlt_pct,
            reflected_vegetation_share=self.reflected_vegetation_share,
            transmitted_habitat_share=self.transmitted_habitat_share,
            pattern=pattern_spec,
        )

    def as_dict(self) -> dict:
        self.validate()
        panel = self.to_glass_panel()
        return {
            "facade_id": self.facade_id,
            "provisional_visual_class": self.visual_class,
            "canonical_appearance_used": panel.appearance.value,
            "visual_class_confirmed": self.visual_class_confirmed,
            "visual_class_evidence_tier": self.visual_class_evidence_tier.value,
            "visual_class_source_id": self.visual_class_source_id,
            "reviewed_by_human": self.reviewed_by_human,
            "surface_treatment": self.surface_treatment,
            "coating_position": self.coating_position,
            "area_m2": measurement_dict(self.area_m2),
            "exterior_vlr_pct": measurement_dict(self.exterior_vlr_pct),
            "exterior_vlt_pct": measurement_dict(self.exterior_vlt_pct),
            "reflected_vegetation_share": measurement_dict(self.reflected_vegetation_share),
            "transmitted_habitat_share": measurement_dict(self.transmitted_habitat_share),
            "pattern": self.pattern.as_dict() if self.pattern else None,
            "photo_ids": list(self.photo_ids),
            "specification_id": self.specification_id,
            "observed_at": self.observed_at,
            "observer_id": self.observer_id,
            "canonical_glazing_assessment": assess_glazing(panel),
            "canonical_pattern_status": classify_pattern(panel.pattern).value,
        }
