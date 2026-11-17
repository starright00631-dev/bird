"""Evidence-aware classification of glass appearance and bird-safe patterns.

The module reports mechanism categories, not a calibrated collision
probability. Glass appearance must be measured/viewed from the bird approach
side because reflections change with illumination and viewing angle.
"""
from dataclasses import dataclass
from enum import Enum

from .evidence import Measurement, measurement_dict


class GlassAppearance(str, Enum):
    CLEAR_TRANSPARENT = "clear_transparent"
    HIGHLY_REFLECTIVE = "highly_reflective"
    REFLECTIVE_AND_TRANSPARENT = "reflective_and_transparent"
    TINTED_OR_LOW_E = "tinted_or_low_e"
    FRITTED_OR_PATTERNED = "fritted_or_patterned"
    OPAQUE_SPANDREL = "opaque_spandrel"
    UNKNOWN = "unknown"


class MarkerSurface(str, Enum):
    EXTERIOR = "exterior"
    INTERIOR = "interior"
    NONE = "none"
    UNKNOWN = "unknown"


class MarkerContrast(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"


class PatternStatus(str, Enum):
    UNTREATED = "untreated"
    INTERIOR_ONLY = "interior_only"
    INCOMPLETE = "incomplete"
    UNVERIFIED = "unverified"
    LOW_CONTRAST = "low_contrast"
    UNDERSIZED = "undersized_markers"
    GUIDELINE_2X2 = "guideline_2x2"
    GUIDELINE_2X4 = "guideline_2x4"
    NONCOMPLIANT = "noncompliant"


@dataclass(frozen=True)
class PatternSpec:
    surface: MarkerSurface
    covers_entire_pane: bool | None
    max_horizontal_gap_cm: Measurement | None
    max_vertical_gap_cm: Measurement | None
    min_marker_width_mm: Measurement | None
    contrast: MarkerContrast = MarkerContrast.UNKNOWN


@dataclass(frozen=True)
class GlassPanel:
    panel_id: str
    appearance: GlassAppearance
    area_m2: Measurement | None = None
    exterior_vlr_pct: Measurement | None = None
    exterior_vlt_pct: Measurement | None = None
    reflected_vegetation_share: Measurement | None = None
    transmitted_habitat_share: Measurement | None = None
    pattern: PatternSpec | None = None

    def __post_init__(self) -> None:
        if not self.panel_id.strip():
            raise ValueError("panel_id is required")
        if self.area_m2 is not None and self.area_m2.value is not None:
            if self.area_m2.unit not in {"m2", "m^2"} or self.area_m2.value <= 0:
                raise ValueError("area_m2 must be a positive square-metre value")
        for label, measurement in (
            ("exterior_vlr_pct", self.exterior_vlr_pct),
            ("exterior_vlt_pct", self.exterior_vlt_pct),
        ):
            if measurement is not None and measurement.value is not None:
                if measurement.unit not in {"percent", "%"}:
                    raise ValueError(f"{label} must use percent")
                if not 0.0 <= measurement.value <= 100.0:
                    raise ValueError(f"{label} must lie in [0, 100]")
        for label, measurement in (
            ("reflected_vegetation_share", self.reflected_vegetation_share),
            ("transmitted_habitat_share", self.transmitted_habitat_share),
        ):
            if measurement is not None and measurement.value is not None:
                if measurement.unit != "fraction":
                    raise ValueError(f"{label} must use fraction")
                if not 0.0 <= measurement.value <= 1.0:
                    raise ValueError(f"{label} must lie in [0, 1]")


def classify_pattern(pattern: PatternSpec | None) -> PatternStatus:
    if pattern is None or pattern.surface == MarkerSurface.NONE:
        return PatternStatus.UNTREATED
    if pattern.surface == MarkerSurface.INTERIOR:
        return PatternStatus.INTERIOR_ONLY
    if pattern.surface != MarkerSurface.EXTERIOR:
        return PatternStatus.UNVERIFIED
    if pattern.covers_entire_pane is False:
        return PatternStatus.INCOMPLETE
    if pattern.covers_entire_pane is not True:
        return PatternStatus.UNVERIFIED
    if pattern.contrast == MarkerContrast.LOW:
        return PatternStatus.LOW_CONTRAST
    if pattern.contrast != MarkerContrast.HIGH:
        return PatternStatus.UNVERIFIED

    values = (
        pattern.max_horizontal_gap_cm,
        pattern.max_vertical_gap_cm,
        pattern.min_marker_width_mm,
    )
    if any(v is None or v.value is None for v in values):
        return PatternStatus.UNVERIFIED
    horizontal, vertical, width = (v.value for v in values)
    if any(v.unit != "cm" for v in values[:2]) or values[2].unit != "mm":
        raise ValueError("Pattern gaps must use cm and marker width must use mm")
    if min(horizontal, vertical, width) < 0:
        raise ValueError("Pattern dimensions cannot be negative")
    if width < 5.0:
        return PatternStatus.UNDERSIZED
    if horizontal <= 5.0 and vertical <= 5.0:
        return PatternStatus.GUIDELINE_2X2
    # This is a spacing-only 2x4 screen. ABC Threat Factor rating also
    # evaluates marker geometry/area, material, surface and the full assembly.
    if horizontal <= 10.0 and vertical <= 5.0:
        return PatternStatus.GUIDELINE_2X4
    return PatternStatus.NONCOMPLIANT


def assess_glazing(panel: GlassPanel) -> dict:
    status = classify_pattern(panel.pattern)
    high_hazard_appearance = panel.appearance in {
        GlassAppearance.CLEAR_TRANSPARENT,
        GlassAppearance.HIGHLY_REFLECTIVE,
        GlassAppearance.REFLECTIVE_AND_TRANSPARENT,
    }
    vlr = panel.exterior_vlr_pct.value if panel.exterior_vlr_pct else None
    reflected = (
        panel.reflected_vegetation_share.value
        if panel.reflected_vegetation_share else None
    )
    transmitted = (
        panel.transmitted_habitat_share.value
        if panel.transmitted_habitat_share else None
    )
    reflection_rating_flag = vlr is not None and vlr > 15.0
    low_e_mechanism_observed = (
        panel.appearance == GlassAppearance.TINTED_OR_LOW_E
        and (reflection_rating_flag or (reflected is not None and reflected > 0)
             or (transmitted is not None and transmitted > 0))
    )
    opaque_reflection_observed = (
        panel.appearance == GlassAppearance.OPAQUE_SPANDREL
        and (reflection_rating_flag or (reflected is not None and reflected > 0))
    )
    surface2_rating_review_flag = (
        reflection_rating_flag
        and panel.pattern is not None
        and panel.pattern.surface == MarkerSurface.INTERIOR
    )
    if status == PatternStatus.GUIDELINE_2X2:
        optical_hazard = "reduced_not_eliminated"
    elif status == PatternStatus.GUIDELINE_2X4:
        optical_hazard = "partially_mitigated"
    elif high_hazard_appearance or low_e_mechanism_observed:
        optical_hazard = "elevated"
    elif panel.appearance == GlassAppearance.OPAQUE_SPANDREL:
        optical_hazard = (
            "reflective_opaque_surface_requires_review"
            if opaque_reflection_observed
            else "transparency_not_present_reflection_unassessed"
        )
    elif panel.appearance in {
        GlassAppearance.UNKNOWN, GlassAppearance.TINTED_OR_LOW_E
    }:
        optical_hazard = "unclassified"
    else:
        optical_hazard = "requires_visual_and_spectral_review"

    findings = []
    if panel.appearance in {
        GlassAppearance.HIGHLY_REFLECTIVE,
        GlassAppearance.REFLECTIVE_AND_TRANSPARENT,
    }:
        findings.append("external_reflection_pathway")
    if panel.appearance in {
        GlassAppearance.CLEAR_TRANSPARENT,
        GlassAppearance.REFLECTIVE_AND_TRANSPARENT,
    }:
        findings.append("see_through_or_false_passage_pathway")
    if reflected is not None and reflected > 0:
        findings.append("measured_reflected_vegetation_present")
    if transmitted is not None and transmitted > 0:
        findings.append("measured_transmitted_habitat_present")
    if reflection_rating_flag:
        findings.append("exterior_vlr_above_15_percent_rating_review_flag")

    pattern_standard_scope = (
        "ECCC general 2x2 spacing screen only: whole-pane exterior coverage, "
        "high contrast, no more than 5 cm clear gaps and at least 5 mm components. "
        "This is not an ABC Threat Factor certification."
        if status == PatternStatus.GUIDELINE_2X2 else
        "2x4 spacing geometry screen only. ABC marker geometry, area, material, "
        "surface, low-E position and complete assembly criteria are not assessed."
        if status == PatternStatus.GUIDELINE_2X4 else
        "No product certification or Threat Factor is inferred from this pattern status."
    )

    return {
        "panel_id": panel.panel_id,
        "appearance": panel.appearance.value,
        "area_m2": measurement_dict(panel.area_m2),
        "exterior_vlr_pct": measurement_dict(panel.exterior_vlr_pct),
        "exterior_vlt_pct": measurement_dict(panel.exterior_vlt_pct),
        "pattern_status": status.value,
        "pattern_standard_scope": pattern_standard_scope,
        "optical_hazard_profile": optical_hazard,
        "reflection_rating_review_flag_gt_15pct": reflection_rating_flag,
        "surface2_rating_review_flag_gt_15pct": surface2_rating_review_flag,
        "findings": findings,
        "caveat": (
            "The >15% exterior visible-light-reflectance value is a boundary "
            "used in the ABC rating procedure, not a universal biological "
            "collision-risk threshold. Site, angle, illumination and full "
            "insulating-glass-unit construction still matter."
        ),
    }
