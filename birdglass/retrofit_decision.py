"""Evidence-tiered retrofit recommendations for existing glass façades.

This module ranks mechanisms and feasible interventions. It deliberately does
not invent efficacy percentages or convert observational UBC coefficients
into causal treatment effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from birdglass.glass_observation import GlassObservation
from birdglass.vegetation_exposure import VegetationExposure

EVIDENCE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1}
PRIORITY_ORDER = {"high": 3, "medium": 2, "low": 1, "audit_first": 4}

INTERVENTION_EVIDENCE = {
    "glass_optical_audit": {
        "label": "Measure/verify glass appearance and optical properties",
        "evidence_tier": "A",
        "cost_band": "site_quote_required",
        "implementation_complexity": "low_to_medium",
        "source_urls": [],
        "efficacy_estimate": None,
        "evidence_note": "Information-gathering step; not a collision treatment.",
    },
    "exterior_visual_markers": {
        "label": "Install a continuous high-contrast pattern on the exterior glass surface",
        "evidence_tier": "B",
        "cost_band": "site_quote_required",
        "implementation_complexity": "low_to_medium",
        "source_urls": [
            "https://abcbirds.org/glass-collisions/",
            "https://academic.oup.com/condor/article/128/3/1/8677179",
        ],
        "efficacy_estimate": None,
        "evidence_note": "Strongest general retrofit evidence in this decision set; performance depends on spacing, width, contrast, coverage and exterior placement.",
    },
    "exterior_screen": {
        "label": "Install an external screen or mesh with bird-safe aperture and tension",
        "evidence_tier": "C",
        "cost_band": "site_quote_required",
        "implementation_complexity": "medium_to_high",
        "source_urls": ["https://abcbirds.org/glass-collisions/"],
        "efficacy_estimate": None,
        "evidence_note": "Mechanistically interrupts access to the pane and can reduce reflection; site-specific design and maintenance must be checked.",
    },
    "external_shading": {
        "label": "Add an external shade, louvre or awning to interrupt reflected habitat",
        "evidence_tier": "C",
        "cost_band": "site_quote_required",
        "implementation_complexity": "medium_to_high",
        "source_urls": ["https://abcbirds.org/glass-collisions/"],
        "efficacy_estimate": None,
        "evidence_note": "Mechanistically relevant to reflection; quantify solar, wind, drainage and maintenance constraints before selection.",
    },
    "lighting_management": {
        "label": "Reduce unnecessary night lighting and manage blinds after dark",
        "evidence_tier": "C",
        "cost_band": "site_audit_required",
        "implementation_complexity": "low",
        "source_urls": ["https://abcbirds.org/glass-collisions/"],
        "efficacy_estimate": None,
        "evidence_note": "Supporting measure for nocturnal attraction/disorientation; not a substitute for treating hazardous glass.",
    },
    "pattern_upgrade": {
        "label": "Upgrade an existing frit/film/marker pattern to a verified exterior pattern",
        "evidence_tier": "B",
        "cost_band": "site_quote_required",
        "implementation_complexity": "low_to_medium",
        "source_urls": [
            "https://abcbirds.org/glass-collisions/",
            "https://academic.oup.com/condor/article/128/3/1/8677179",
        ],
        "efficacy_estimate": None,
        "evidence_note": "Use when the current pattern is too widely spaced, too narrow, low contrast, incomplete or installed on the interior.",
    },
    "vegetation_pruning": {
        "label": "Targeted vegetation modification only after glass-side options are assessed",
        "evidence_tier": "D",
        "cost_band": "site_ecology_review_required",
        "implementation_complexity": "medium",
        "source_urls": [],
        "efficacy_estimate": None,
        "evidence_note": "Not a default recommendation: canopy provides habitat and may be a reflected-scene trigger; prioritize glass-side mitigation and preserve habitat.",
    },
    "interior_markers_only": {
        "label": "Interior-only decals or markers",
        "evidence_tier": "D",
        "cost_band": "site_quote_required",
        "implementation_complexity": "low",
        "source_urls": [],
        "efficacy_estimate": None,
        "evidence_note": "Not recommended as the sole treatment where the exterior surface still reflects habitat.",
    },
}


@dataclass(frozen=True)
class Recommendation:
    intervention_id: str
    label: str
    priority: str
    evidence_tier: str
    mechanism_match: tuple[str, ...]
    why: str
    implementation_complexity: str
    cost_band: str
    efficacy_estimate: Optional[dict]
    source_urls: tuple[str, ...]
    limitations: tuple[str, ...]


def _recommendation(intervention_id: str, priority: str, mechanisms: tuple[str, ...],
                    why: str, extra_limits: tuple[str, ...] = ()) -> Recommendation:
    evidence = INTERVENTION_EVIDENCE[intervention_id]
    return Recommendation(
        intervention_id=intervention_id,
        label=evidence["label"],
        priority=priority,
        evidence_tier=evidence["evidence_tier"],
        mechanism_match=mechanisms,
        why=why,
        implementation_complexity=evidence["implementation_complexity"],
        cost_band=evidence["cost_band"],
        efficacy_estimate=evidence["efficacy_estimate"],
        source_urls=tuple(evidence["source_urls"]),
        limitations=(
            evidence["evidence_note"],
            "No transferable BNBU efficacy percentage is available from the current data.",
            *extra_limits,
        ),
    )


def recommend_interventions(
    glass: GlassObservation,
    vegetation: VegetationExposure,
    *,
    night_lighting_problem_confirmed: bool = False,
    vegetation_conflict_confirmed: bool = False,
    glass_side_retrofit_feasible: bool = True,
) -> dict:
    """Return transparent, evidence-tiered recommendations for an existing façade."""
    glass.validate()
    vegetation.validate()
    glass_mechanisms = glass.mechanisms()
    vegetation_summary = vegetation.summary()
    reflection_exposure = vegetation_summary["canopy_reflection_exposure_flag"]
    mechanisms = []
    if glass_mechanisms["transparency_confusion"]:
        mechanisms.append("transparency_confusion")
    if glass_mechanisms["reflected_habitat"]:
        mechanisms.append("reflected_habitat")
    if reflection_exposure:
        mechanisms.append("vegetation_reflected_in_glass")
    if glass_mechanisms["pattern_noncompliant_or_incomplete"]:
        mechanisms.append("inadequate_existing_pattern")

    recommendations = []
    if glass_mechanisms["requires_human_review"] or glass_mechanisms["tinted_optics_unresolved"]:
        recommendations.append(_recommendation(
            "glass_optical_audit", "audit_first", tuple(mechanisms),
            "The glass visual class or optical properties are not sufficiently verified; obtain a façade photo set, manufacturer specification or reflectance/transmittance measurement before assigning a glass-type risk.",
        ))

    pattern_compliant = glass_mechanisms["pattern_screening_compliant"] is True
    if not pattern_compliant and (
        glass_mechanisms["transparency_confusion"]
        or glass_mechanisms["reflected_habitat"]
        or glass_mechanisms["pattern_noncompliant_or_incomplete"]
    ):
        reason = (
            "The pane is transparent and/or reflects habitat; an exterior, continuous, high-contrast pattern is the best-supported general retrofit option."
            if not glass_mechanisms["pattern_noncompliant_or_incomplete"]
            else "The existing pattern fails at least one screening criterion (spacing, width, coverage, contrast or exterior placement); upgrade it rather than assuming it is bird-safe."
        )
        recommendations.append(_recommendation(
            "pattern_upgrade" if glass_mechanisms["pattern_noncompliant_or_incomplete"] else "exterior_visual_markers",
            "high", tuple(mechanisms), reason,
            ("The 5 cm spacing / 5 mm width / 90% coverage / 0.5 contrast checks are conservative screening criteria, not a guarantee of collision prevention.",),
        ))

    if glass_mechanisms["reflected_habitat"] and reflection_exposure and glass_side_retrofit_feasible:
        recommendations.append(_recommendation(
            "exterior_screen", "high", ("reflected_habitat", "vegetation_reflected_in_glass"),
            "The glass is reflective and the façade has adjacent canopy that can appear in the reflected scene; an external screen can interrupt the reflection and the bird's direct approach.",
        ))
        recommendations.append(_recommendation(
            "external_shading", "medium", ("reflected_habitat", "vegetation_reflected_in_glass"),
            "External shading/louvres may reduce the reflected habitat view; assess solar and façade engineering constraints before selecting this option.",
        ))
    elif glass_mechanisms["reflected_habitat"] and glass_side_retrofit_feasible:
        recommendations.append(_recommendation(
            "external_shading", "medium", ("reflected_habitat",),
            "Reflection is a plausible mechanism; consider an external screen or shading after confirming the reflected scene and engineering feasibility.",
        ))

    if night_lighting_problem_confirmed:
        recommendations.append(_recommendation(
            "lighting_management", "medium", ("nighttime_attraction_or_disorientation",),
            "Night lighting is elevated in the supplied normalized assessment; reduce unnecessary illumination and manage blinds as a supporting measure.",
        ))

    if glass_mechanisms["interior_treatment_may_leave_exterior_reflection"]:
        recommendations.append(_recommendation(
            "interior_markers_only", "low", ("exterior_reflection_uninterrupted",),
            "Interior-only treatment may leave the exterior reflective surface unchanged; do not rely on it as the sole mitigation.",
        ))

    if vegetation_conflict_confirmed and not glass_side_retrofit_feasible:
        recommendations.append(_recommendation(
            "vegetation_pruning", "low", ("site_specific_vegetation_conflict",),
            "Only consider targeted vegetation modification after a documented local conflict and after glass-side options have been assessed.",
            ("Require an ecological review and preserve habitat wherever possible.",),
        ))

    priority_sort = {"audit_first": 0, "high": 1, "medium": 2, "low": 3}
    evidence_sort = {"A": 0, "B": 1, "C": 2, "D": 3}
    recommendations.sort(key=lambda item: (
        priority_sort[item.priority], evidence_sort[item.evidence_tier], item.intervention_id
    ))

    return {
        "facade_id": glass.facade_id,
        "glass_mechanisms": glass_mechanisms,
        "vegetation_exposure": vegetation_summary,
        "mechanisms_considered": mechanisms,
        "recommendations": [asdict(item) for item in recommendations],
        "not_estimated": [
            "Absolute collision probability for this façade",
            "Causal percentage reduction for any intervention",
            "Cost-effectiveness where local quotes are absent",
        ],
        "decision_rule": "Rank by mechanism match, evidence tier and feasibility; no arbitrary weighted score is used.",
        "vegetation_policy": "Do not recommend tree removal by default; prioritize treatment of hazardous glass.",
    }
