"""Interpretable facade assessment and intervention decision support.

This is a modular mechanism-and-decision system, not a single black-box risk
score. It never emits an absolute collision probability from incident reports
or habitat proxies alone.
"""
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Sequence

from .evidence import EvidenceTier, Measurement, measurement_dict
from .glazing import (
    GlassAppearance,
    GlassPanel,
    PatternStatus,
    assess_glazing,
)
from .vegetation import VegetationProfile, vegetation_pathways


class Priority(IntEnum):
    HIGH = 0
    MEDIUM = 1
    CONDITIONAL = 2
    LOW = 3


@dataclass(frozen=True)
class ApproachSample:
    """Pane-specific sample of all approaches crossing a defined risk gate.

    sampling_frame must be continuous_video before a conditional contact rate
    is identifiable. Selected collision clips are not a denominator.
    """

    total_approaches: int
    glass_contacts: int
    opaque_contacts: int
    no_contact: int
    censored: int = 0
    continuous_video_coverage: bool = False
    sampling_frame: str = "selected_events"
    source_id: str | None = None

    def __post_init__(self) -> None:
        values = (
            self.total_approaches, self.glass_contacts, self.opaque_contacts,
            self.no_contact, self.censored,
        )
        if any(not isinstance(v, int) or v < 0 for v in values):
            raise ValueError("Approach counts must be nonnegative integers")
        if self.total_approaches <= 0:
            raise ValueError("total_approaches must be positive")
        if sum(values[1:]) != self.total_approaches:
            raise ValueError(
                "glass + opaque + no-contact + censored must equal total"
            )
        if self.sampling_frame not in {"continuous_video", "selected_events"}:
            raise ValueError("Unsupported sampling_frame")

    def conditional_glass_contact_rate(self) -> dict:
        if self.sampling_frame != "continuous_video":
            return {
                "identified": False,
                "reason": "Selected events do not provide an approach denominator",
                "lower": None,
                "upper": None,
                "estimate": None,
            }
        if not self.continuous_video_coverage:
            return {
                "identified": False,
                "reason": "Continuous coverage past the risk gate is not verified",
                "lower": None,
                "upper": None,
                "estimate": None,
            }
        lower = self.glass_contacts / self.total_approaches
        upper = (self.glass_contacts + self.censored) / self.total_approaches
        if self.censored:
            return {
                "identified": False,
                "reason": "Right-censored approaches only identify an interval",
                "lower": lower,
                "upper": upper,
                "estimate": None,
            }
        return {
            "identified": True,
            "reason": "Complete continuous-video approach sample",
            "lower": lower,
            "upper": upper,
            "estimate": lower,
        }


@dataclass(frozen=True)
class FacadeContext:
    glass: GlassPanel
    vegetation: VegetationProfile = field(default_factory=VegetationProfile)
    bird_activity: Measurement | None = None
    approaches_per_hour: Measurement | None = None
    approach_sample: ApproachSample | None = None
    nocturnal_migrant_activity: Measurement | None = None
    artificial_light_level: Measurement | None = None


def _has_value(value: Measurement | None) -> bool:
    return value is not None and value.value is not None


def _recommendation(action: str, priority: Priority, rationale: str,
                    conditions: Sequence[str], evidence_base: str,
                    caveat: str) -> dict:
    return {
        "action": action,
        "priority": priority.name.lower(),
        "priority_order": int(priority),
        "rationale": rationale,
        "conditions": list(conditions),
        "evidence_base": evidence_base,
        "caveat": caveat,
    }


def evaluate_facade(context: FacadeContext) -> dict:
    """Return a multi-pathway profile and ranked, conditional actions."""

    glass = context.glass
    glazing = assess_glazing(glass)
    vegetation = vegetation_pathways(context.vegetation)
    pattern_status = PatternStatus(glazing["pattern_status"])
    high_hazard_appearance = glass.appearance in {
        GlassAppearance.CLEAR_TRANSPARENT,
        GlassAppearance.HIGHLY_REFLECTIVE,
        GlassAppearance.REFLECTIVE_AND_TRANSPARENT,
    }
    reflected_share = context.vegetation.reflected_vegetation_share
    if reflected_share is None:
        reflected_share = glass.reflected_vegetation_share
    reflected_habitat_measured = (
        _has_value(reflected_share)
        and reflected_share.tier in {EvidenceTier.MEASURED, EvidenceTier.LOCAL_SURVEY}
        and reflected_share.value > 0
    )
    local_activity_measured = (
        _has_value(context.bird_activity)
        and context.bird_activity.tier in {
            EvidenceTier.MEASURED, EvidenceTier.LOCAL_SURVEY
        }
    )
    approach_rate_measured = _has_value(context.approaches_per_hour)

    approach_rate = (
        context.approach_sample.conditional_glass_contact_rate()
        if context.approach_sample is not None else {
            "identified": False,
            "reason": "No pane-specific approach sample",
            "lower": None,
            "upper": None,
            "estimate": None,
        }
    )
    expected_contacts_per_hour = None
    if approach_rate["identified"] and approach_rate_measured:
        expected_contacts_per_hour = (
            approach_rate["estimate"] * context.approaches_per_hour.value
        )

    findings = []
    data_gaps = []
    recommendations = []

    if high_hazard_appearance:
        findings.append({
            "pathway": "glass_optics",
            "status": glazing["optical_hazard_profile"],
            "explanation": (
                "The recorded glass appearance can create a reflected habitat "
                "image or a false see-through flight path. The two mechanisms "
                "must remain separate in later calibration."
            ),
        })
    elif glass.appearance in {
        GlassAppearance.UNKNOWN, GlassAppearance.TINTED_OR_LOW_E
    }:
        data_gaps.append(
            "Classify the complete glass assembly from outside views and "
            "measure exterior reflectance/transmittance."
        )
    if reflected_habitat_measured:
        findings.append({
            "pathway": "vegetation_to_reflection",
            "status": "direct_scene_evidence_present",
            "explanation": (
                "Vegetation is measured in the reflected scene. This is a "
                "direct optical pathway, not proof that birds approach or collide."
            ),
        })
    if context.vegetation.cover_pct:
        findings.append({
            "pathway": "vegetation_scale",
            "status": "multi_scale_measurements_available",
            "explanation": (
                "Local canopy (0–100 m) and landscape cover (100 m–10 km) "
                "are reported separately; no universal signed vegetation "
                "coefficient is applied."
            ),
        })
    if _has_value(context.bird_activity):
        findings.append({
            "pathway": "bird_activity",
            "status": "measured_proxy_or_local_observation",
            "measurement": measurement_dict(context.bird_activity),
            "explanation": (
                "Bird activity is an exposure covariate, not a count of "
                "approaches to this pane."
            ),
        })
    else:
        data_gaps.append(
            "Obtain local species/guild activity with survey effort; regional "
            "occurrence alone is not facade approach flow."
        )
    if approach_rate_measured:
        findings.append({
            "pathway": "approach_flow",
            "status": "measured",
            "measurement": measurement_dict(context.approaches_per_hour),
        })
    else:
        data_gaps.append(
            "Measure all at-risk approaches through a defined pane-specific "
            "gate; collision reports are not an approach denominator."
        )

    if approach_rate["identified"]:
        findings.append({
            "pathway": "conditional_glass_contact",
            "status": "identified_from_continuous_video",
            "estimate": approach_rate["estimate"],
            "lower": approach_rate["lower"],
            "upper": approach_rate["upper"],
            "source_id": (
                context.approach_sample.source_id
                if context.approach_sample else None
            ),
        })
    elif context.approach_sample is not None:
        findings.append({
            "pathway": "conditional_glass_contact",
            "status": "not_identified",
            "reason": approach_rate["reason"],
            "lower": approach_rate["lower"],
            "upper": approach_rate["upper"],
        })
    else:
        data_gaps.append(
            "Independently verify glass contacts, opaque contacts, escapes "
            "and right-censored approaches from continuous video."
        )

    if high_hazard_appearance and pattern_status not in {
        PatternStatus.GUIDELINE_2X2, PatternStatus.GUIDELINE_2X4
    }:
        priority = (
            Priority.HIGH
            if reflected_habitat_measured or local_activity_measured
            or approach_rate_measured
            else Priority.MEDIUM
        )
        recommendations.append(_recommendation(
            "retrofit_full_pane_exterior_visual_markers",
            priority,
            "The glass has a plausible reflection/transparency hazard and "
            "does not have a verified guideline-conforming exterior pattern.",
            [
                "Cover the entire glass surface, not isolated stickers.",
                "Use high-contrast markers on the exterior/first surface.",
                "Prefer maximum clear gaps of 5 cm horizontally and vertically "
                "(the more conservative 2x2 pattern).",
                "Use marker elements at least 5 mm wide and verify contrast "
                "against actual reflections and transmitted backgrounds.",
                "Inspect from bird approach views at multiple times and angles.",
            ],
            "Canada.ca glass-collision guidance; ABC 2025 Prescriptive Rating; "
            "Lawson et al. 2026 field BACI study; Lysyk et al. 2026 Ottawa study",
            "Published effects are study-specific and are not a predicted "
            "BNBU percentage reduction.",
        ))
    elif pattern_status == PatternStatus.GUIDELINE_2X4:
        recommendations.append(_recommendation(
            "consider_upgrade_to_2x2_pattern",
            Priority.MEDIUM,
            "The current pattern meets the less conservative 2x4 spacing "
            "category; a 5x5 cm grid is more conservative for small birds.",
            [
                "Confirm actual marker contrast and complete pane coverage.",
                "Prioritize the stricter spacing where small-bodied local taxa "
                "are documented.",
            ],
            "ABC 2025 Prescriptive Rating and Canadian guidance",
            "This is a design preference, not a quantified incremental benefit.",
        ))

    vlr = glass.exterior_vlr_pct.value if glass.exterior_vlr_pct else None
    if vlr is not None and vlr > 15.0 and pattern_status != PatternStatus.GUIDELINE_2X2:
        recommendations.append(_recommendation(
            "measure_first_surface_reflection_and_marker_contrast",
            Priority.HIGH,
            "Exterior visible-light reflectance exceeds the 15% boundary used "
            "by the ABC rating procedure for some non-first-surface patterns.",
            [
                "Prefer a pattern on the exterior/first surface, or obtain a "
                "bird-vision contrast assessment using measured spectra.",
                "Measure the complete insulating-glass assembly, not a generic "
                "glass-type label.",
            ],
            "ABC 2025 Prescriptive Rating",
            "15% is a rating-procedure boundary, not a universal biological "
            "risk threshold.",
        ))

    if high_hazard_appearance and pattern_status not in {
        PatternStatus.GUIDELINE_2X2, PatternStatus.GUIDELINE_2X4
    }:
        recommendations.append(_recommendation(
            "consider_external_screen_or_cord_system",
            Priority.MEDIUM,
            "A physical exterior interruption can provide an alternative where "
            "a continuous marker film is not feasible.",
            [
                "Specify safe mesh/cord spacing and stand-off from glass.",
                "Check entanglement, maintenance, fire, egress, wind-load and "
                "human-safety constraints before installation.",
                "Verify that the intervention does not simply transfer contact "
                "to an opaque frame or another pane.",
            ],
            "Bird-collision prevention guidance and field retrofit practice",
            "Do not assume a screen or net is harmless or effective without "
            "installation-specific validation.",
        ))

    if reflected_habitat_measured:
        recommendations.append(_recommendation(
            "audit_reflection_by_solar_time_and_approach_view",
            Priority.HIGH,
            "Measured vegetation reflection gives a direct reason to test "
            "the reflection pathway at this panel.",
            [
                "Repeat external photographs or radiance measurements at "
                "different solar azimuths, altitudes and cloud conditions.",
                "Record which vegetation patches appear in the pane from "
                "plausible bird approach directions.",
                "Treat the glass first; do not remove trees solely because "
                "canopy cover is high.",
            ],
            "Canada.ca guidance; ABC 2025 rating method; optical-scene mechanism",
            "A reflection image is not a measurement of bird attraction or "
            "collision probability.",
        ))

    nocturnal_activity_supported = (
        _has_value(context.nocturnal_migrant_activity)
        and context.nocturnal_migrant_activity.tier in {
            EvidenceTier.MEASURED, EvidenceTier.LOCAL_SURVEY
        }
    )
    if nocturnal_activity_supported:
        if _has_value(context.artificial_light_level) and (
            context.artificial_light_level.value > 0
        ):
            recommendations.append(_recommendation(
                "seasonal_night_lighting_controls",
                Priority.HIGH,
                "Nocturnal migrant activity and artificial light are both "
                "represented in the site evidence.",
                [
                    "Switch off unnecessary interior/decorative lighting "
                    "during locally supported migration windows.",
                    "Use downward shielding, timers and occupancy controls.",
                    "Keep this intervention separate from daytime glass marking.",
                ],
                "Van Doren et al. 2021; China 2025 multi-scale ALAN study",
                "The direction and magnitude of ALAN effects can vary by "
                "season and region; validate locally.",
            ))
        else:
            data_gaps.append(
                "Pair nocturnal migration activity with calibrated ALAN "
                "measurements before prioritizing a lighting intervention."
            )

    if context.vegetation.cover_pct:
        recommendations.append(_recommendation(
            "retain_vegetation_as_a_multiscale_context_variable",
            Priority.CONDITIONAL,
            "Vegetation has attraction, routing, reflection and obstruction "
            "pathways whose directions can differ by scale.",
            [
                "Keep 0–5 m, 5–25 m, 25–100 m, 100 m–1 km and 1–10 km "
                "cover as separate features.",
                "Measure canopy height, distance, pane-height overlap and "
                "reflected vegetation.",
                "Do not recommend blanket tree removal from cover percentage alone.",
            ],
            "China 2025 study of 3,078 buildings; Lysyk et al. 2026 Ottawa study",
            "The studies report different local vegetation associations; neither "
            "identifies a universal causal tree-removal rule.",
        ))

    if high_hazard_appearance:
        recommendations.append(_recommendation(
            "evaluate_uv_pattern_only_after_spectral_and_species_checks",
            Priority.CONDITIONAL,
            "UV treatments have experimental evidence for some species and "
            "illumination conditions, but transfer to local species and "
            "subtropical field lighting is uncertain.",
            [
                "Obtain measured spectral reflectance/transmittance of the "
                "complete glass and film assembly.",
                "Check the local focal species' visual sensitivities and "
                "pattern contrast across daylight and low-light conditions.",
                "Run a local non-injurious choice/visibility test before "
                "using UV-only treatment as the primary intervention.",
            ],
            "Swaddle et al. 2020 controlled flight-tunnel study",
            "Two tested songbird species do not establish universal UV efficacy.",
        ))

    if not approach_rate_measured or not approach_rate["identified"]:
        recommendations.append(_recommendation(
            "establish_standardized_pane_approach_monitoring",
            Priority.HIGH,
            "The main missing denominator is all at-risk approaches, not more "
            "opportunistic collision reports.",
            [
                "Use continuous video with a declared 3D pane-specific risk gate.",
                "Annotate glass contact, opaque contact, no contact and "
                "right-censored events independently of trajectory fitting.",
                "Keep bird, trial, building and date identifiers for grouped "
                "validation splits.",
            ],
            "Samuels et al. 2022 selected-video limitations; project "
            "approach-event and censoring protocol",
            "Motion-triggered collision clips alone cannot estimate "
            "conditional contact probability per approach.",
        ))

    recommendations.sort(key=lambda item: (item["priority_order"], item["action"]))

    if approach_rate["identified"] and approach_rate_measured:
        identifiability = "expected_hourly_contact_rate_identified"
    elif approach_rate["identified"]:
        identifiability = "conditional_contact_identified_absolute_rate_not_identified"
    else:
        identifiability = "mechanism_profile_only"

    risk_profile = {
        "ecological_activity": (
            "measured" if local_activity_measured else "not_measured"
        ),
        "approach_flow": (
            "measured" if approach_rate_measured else "not_measured"
        ),
        "optical_hazard": glazing["optical_hazard_profile"],
        "conditional_glass_contact": approach_rate,
        "expected_glass_contacts_per_hour": expected_contacts_per_hour,
        "absolute_collision_probability": None,
        "injury_probability": None,
        "overall_scalar_score": None,
        "identifiability": identifiability,
        "identifiability_note": (
            "An absolute pane/time collision rate requires an effort-corrected "
            "approach flow and independently observed outcomes. Injury risk "
            "requires a separate injury dataset."
        ),
    }

    return {
        "model": "BNBU Bird-Glass Interpretable Decision Support",
        "model_version": "0.1.0",
        "panel_id": glass.panel_id,
        "risk_profile": risk_profile,
        "glass_assessment": glazing,
        "vegetation_pathways": vegetation,
        "findings": findings,
        "recommendations": recommendations,
        "data_gaps": sorted(set(data_gaps)),
        "prohibited_inferences": [
            "Do not convert Neotropical event counts into collision probabilities.",
            "Do not convert vegetation cover into one universal signed risk score.",
            "Do not convert ABC Threat Factor or tunnel choice ratios into field "
            "percentage reductions.",
            "Do not interpret a missing collision report as a surveyed zero.",
            "Do not infer BNBU-specific efficacy from another climate or species assemblage.",
        ],
    }
