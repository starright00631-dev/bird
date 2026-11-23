"""Build a pane-linked BACI preregistration and feasibility report for one action."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from datetime import datetime
from math import isfinite
from pathlib import Path
from random import Random

from .decision import FacadeContext, evaluate_facade
from .evidence import EvidenceTier, Measurement
from .facade_decision_report import EVIDENCE_BY_ACTION
from .glass_observation import GlassObservation, PatternObservation
from .glazing import MarkerContrast, MarkerSurface, PatternSpec
from .pane_registry import PaneGlassObservation, PaneIdentity, PaneRegistry
from .vegetation import VegetationProfile

MARKERS = "full_pane_exterior_visual_markers"
SCREEN = "external_screen_or_cord_system"
SHADE = "external_shading_or_solar_screen"
LIGHT = "seasonal_night_lighting_controls"
BLINDS = "internal_blinds_or_indoor_plant_repositioning"
UV = "uv_only_pattern"
VEGETATION = "vegetation_reconfiguration"
PRIMARY_ACTIONS = (MARKERS, "consider_upgrade_from_2x4_to_2x2", SCREEN, SHADE, LIGHT)
PHASES = ("before", "after")
ROLES = ("treatment", "control")
MEASURED = {EvidenceTier.MEASURED, EvidenceTier.LOCAL_SURVEY}
ACTION_CHECKS = {
    MARKERS: ("whole_pane_exterior_pattern_and_contrast", "glass_compatibility"),
    "consider_upgrade_from_2x4_to_2x2": ("whole_pane_exterior_pattern_and_contrast", "glass_compatibility"),
    SCREEN: ("structural_wind_load", "entanglement_and_standoff"),
    SHADE: ("structural_wind_load", "multi_time_multi_angle_reflection"),
    LIGHT: ("preserved_emergency_and_access_lighting", "local_night_activity_and_measured_light"),
    BLINDS: ("measured_false_passage",),
    UV: ("assembly_spectra_and_local_species_visibility",),
    VEGETATION: ("route_resource_and_reflection_attribution",),
}
DEFERRED = {
    BLINDS: "Confirm transmission from approach views. Consider as a supplement for false passage.",
    UV: "Measure full-assembly spectra and local species visibility under shade, overcast and low light.",
    VEGETATION: "Confirm route, resource and reflection pathways and obtain ecological review.",
}
PROTOCOL_FIELDS = (
    "sample_size_basis", "seasonal_trends_and_sampling_schedule", "fixed_risk_gate_and_censoring",
    "compliance_audit", "observer_bias_and_blinded_review", "detection_and_persistence_protocol",
    "analysis_and_uncertainty", "early_stop_rules",
)


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value


def _number(value, label, *, minimum=0, maximum=float("inf")):
    if type(value) not in (int, float) or not isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be finite and within [{minimum}, {maximum}]")
    return value


def _positive_integer(value, label):
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _time(value):
    result = datetime.fromisoformat(_text(value, "timestamp"))
    if result.utcoffset() is None:
        raise ValueError("A timestamp must include a UTC offset")
    return result


def _measurement(row):
    if row is None:
        return None
    return Measurement(**{**row, "tier": EvidenceTier(row["tier"])})


def _local_measurement(row, label, unit, upper=float("inf")):
    value = _measurement(row)
    if value is None or value.tier not in MEASURED or value.unit != unit:
        raise ValueError(f"{label} requires local measured evidence in {unit}")
    _text(value.source_id, f"{label} source_id")
    _number(value.value, label, maximum=upper)
    return value


def _evaluate_pane(row, registration, registry, registered_at):
    view = row["glass_view"]
    observed_at = _time(view["observed_at"])
    if (registration.field_verified_at is None or registration.field_verified_at > registered_at
            or observed_at > registered_at):
        raise ValueError("Pane registration and its glass evidence must predate preregistration")
    appearance_tier = EvidenceTier(view["appearance_tier"])
    if appearance_tier not in MEASURED:
        raise ValueError("BACI matching requires a human-reviewed or measured glass appearance")
    _text(view["reviewer_id"], "glass view reviewer_id")
    pattern = view.get("existing_pattern")
    pattern_status = view["existing_pattern_status"]
    if pattern_status not in {"no_pattern_observed", "recorded", "unverified"} or (
        (pattern_status == "recorded") != (pattern is not None)
    ):
        raise ValueError("Existing pattern claims require a consistent field inspection status")
    if pattern is not None:
        pattern = PatternObservation(
            **{**pattern, "surface": MarkerSurface(pattern["surface"]),
               "contrast": MarkerContrast(pattern["contrast"]),
               **{name: _measurement(pattern.get(name)) for name in (
                   "max_horizontal_gap_cm", "max_vertical_gap_cm", "min_feature_dimension_mm",
               )}},
        )
    observation = PaneGlassObservation(
        registration.identity, view["evidence_id"], observed_at,
        GlassObservation(
            facade_id=registration.identity.facade_id, observed_at=view["observed_at"],
            visual_class=view["appearance"], visual_class_evidence_tier=appearance_tier,
            visual_class_source_id=view["source_id"],
            reviewed_by_human=True, observer_id=view["reviewer_id"],
            photo_ids=tuple(view["photo_ids"]), pattern=pattern,
            reflected_vegetation_share=_measurement(view.get("reflected_habitat_fraction")),
            transmitted_habitat_share=_measurement(view.get("transmitted_habitat_fraction")),
        ),
        "field_view", view["source_id"], view_id=view["view_id"],
        approach_azimuth_deg=view["approach_azimuth_deg"], lighting_context=view["lighting_context"],
    )
    registry.validate_glass(observation)
    glass = replace(observation.observation.to_glass_panel(), panel_id=registration.identity.pane_id)
    if pattern_status == "unverified":
        glass = replace(glass, pattern=PatternSpec(MarkerSurface.UNKNOWN, None, None, None, None))
    canopy = _local_measurement(row["canopy_cover_50m"], "canopy_cover_50m", "percent", 100)
    flow = _local_measurement(row["bird_flow"], "bird_flow", "approaches/hour")
    decision = evaluate_facade(FacadeContext(
        glass=glass, vegetation=VegetationProfile(facade_tree_cover_50m_percent=canopy),
        approaches_per_hour=flow,
        nocturnal_migrant_activity=_measurement(row.get("nocturnal_activity")),
        artificial_light_level=_measurement(row.get("night_light")),
    ))
    return observation, glass, canopy, flow, decision


def _review_candidate(candidate, review, registry_sources, registered_at):
    action = candidate["action"]
    required = ("fire_and_egress", "ecological_impact", *ACTION_CHECKS.get(action, ()))
    checks = review.get("checks", {})
    if set(checks) - set(required):
        raise ValueError(f"Unexpected feasibility checks for {action}")
    reviewed_checks = {}
    for name in required:
        check = checks.get(name, {"status": "pending"})
        if check["status"] not in {"pending", "pass", "veto"}:
            raise ValueError(f"Unknown review status for {name}")
        if check["status"] != "pending":
            _text(check["source_id"], f"{name} review source_id")
            _text(check["notes"], f"{name} review notes")
            if _time(check["reviewed_at"]) > registered_at:
                raise ValueError(f"{name} review postdates preregistration")
        reviewed_checks[name] = check
    cost, maintenance, daylight = (review.get(key) for key in ("cost_cny", "maintenance", "daylight"))
    if cost is not None:
        _number(cost, "cost_cny")
        _text(review.get("cost_source_id"), "cost_source_id")
    for label, value in (("maintenance", maintenance), ("daylight", daylight)):
        if value is not None:
            _text(value, label)
    vetoes = [name for name, result in reviewed_checks.items() if result["status"] == "veto"]
    missing = [name for name, result in reviewed_checks.items() if result["status"] == "pending"]
    missing.extend(key for key in ("cost_cny", "maintenance", "daylight") if review.get(key) is None)
    return {
        **candidate,
        "feasibility": "vetoed" if vetoes else "pending_review" if missing else "checks_documented",
        "requirements": reviewed_checks, "vetoes": vetoes, "missing": missing,
        "cost_cny": cost, "cost_source_id": review.get("cost_source_id"),
        "maintenance": maintenance, "daylight": daylight,
        "evidence_sources": [registry_sources[source_id] for source_id in EVIDENCE_BY_ACTION.get(action, ())],
        "site_effect_estimate": None, "site_effect_interval": None,
    }


def build_retrofit_trial(plan):
    """Validate one-preregistered-action plans and return an auditable proposal."""
    if plan["schema_version"] != 1 or plan["evidence_kind"] not in {"synthetic", "bnbu_preregistration"}:
        raise ValueError("Unsupported trial schema or evidence kind")
    trial_id = _text(plan["trial_id"], "trial_id")
    registry = PaneRegistry.from_dict(plan["pane_registry"])
    synthetic = plan["evidence_kind"] == "synthetic"
    if synthetic != (registry.dataset_kind == "synthetic"):
        raise ValueError("Trial evidence kind must match the pane registry")
    path = Path(__file__).resolve().parents[1] / "data/reference/intervention_evidence.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        registry_sources = {row["source_id"]: row for row in csv.DictReader(handle)}
    action = plan["treatment_action"]
    if action not in PRIMARY_ACTIONS:
        raise ValueError("The treatment must be a primary candidate supported by the decision engine")
    registered_at = _time(plan["registered_at"])
    periods = {phase: tuple(_time(plan["periods"][phase][key]) for key in ("start", "end")) for phase in PHASES}
    before, after = periods["before"], periods["after"]
    if not registered_at <= before[0] < before[1] <= after[0] < after[1]:
        raise ValueError("Preregister before ordered, nonoverlapping before and after periods")
    protocol = plan["protocol"]
    for label in PROTOCOL_FIELDS:
        _text(protocol[label], label)
    minimum_effect = _number(protocol["minimum_meaningful_absolute_risk_difference"], "minimum meaningful effect", minimum=1e-12, maximum=1)
    target_pairs = _positive_integer(protocol["target_independent_pairs"], "target_independent_pairs")
    pretrend_blocks = _positive_integer(protocol["minimum_pretrend_blocks"], "minimum_pretrend_blocks")
    if pretrend_blocks < 2:
        raise ValueError("Pretrend assessment requires at least two planned baseline blocks")
    allocation = plan["allocation"]
    if allocation["method"] not in {"matched_pairs", "randomized_within_pairs"}:
        raise ValueError("Unsupported BACI allocation method")
    _text(allocation["source_id"], "allocation source_id")
    thresholds = tuple(_number(allocation[key], key) for key in (
        "max_azimuth_difference_deg", "max_canopy_difference_pct_points", "max_flow_difference_per_hour",
    ))
    rng = None
    if allocation["method"] == "randomized_within_pairs":
        seed = allocation["seed"]
        if type(seed) is not int:
            raise ValueError("The allocation seed must be an integer")
        rng = Random(seed)

    panes, blocks, tracked_surfaces, neighborhoods = {}, {}, set(), set()
    effort = {role: {phase: {"camera_hours": 0, "target_approaches": 0, "patrol_hours": 0}
                     for phase in PHASES} for role in ROLES}
    for row in plan["panes"]:
        identity = PaneIdentity(**row["identity"])
        pane = registry.require(identity, field_verified=not synthetic)
        if identity.pane_id in panes or row["role"] not in ROLES:
            raise ValueError("Each primary pane has a distinct ID and a valid treatment or control role")
        block = _text(row["pair_id"], "pair ID")
        neighborhood = _text(row["assignment_neighborhood_id"], "assignment neighborhood ID")
        if neighborhood in neighborhoods:
            raise ValueError("Assign only one primary pane per interference neighborhood")
        neighborhoods.add(neighborhood)
        surfaces = row["monitor_surfaces"]
        by_kind = {surface["kind"] for surface in surfaces}
        if by_kind - {"adjacent_pane", "frame", "screen"} or not {"adjacent_pane", "frame"} <= by_kind:
            raise ValueError("Each pane requires adjacent glass and frame follow-up")
        if action == SCREEN and row["role"] == "treatment" and "screen" not in by_kind:
            raise ValueError("Screen trials require contact and injury follow-up on the screen")
        for surface in surfaces:
            surface_id = _text(surface["surface_id"], "contact surface ID")
            _text(surface["source_id"], "contact surface source_id")
            if surface_id in tracked_surfaces or surface_id == identity.pane_id:
                raise ValueError("Spillover surface IDs must be unique across assignment neighborhoods")
            tracked_surfaces.add(surface_id)
            if surface["kind"] == "adjacent_pane":
                neighbor = registry.require(PaneIdentity(**surface["identity"]), field_verified=not synthetic)
                if neighbor.identity.pane_id != surface_id or neighbor.identity.building_id != identity.building_id:
                    raise ValueError("Adjacent glass must match a registered pane on the same building")
        for phase in PHASES:
            span = (periods[phase][1] - periods[phase][0]).total_seconds() / 3600
            window = row["effort"][phase]
            hours = _number(window["camera_hours"], "camera_hours", minimum=1e-12, maximum=span)
            patrol = _number(window["patrol_hours"], "patrol_hours", minimum=1e-12, maximum=span)
            approaches = _positive_integer(window["target_approaches"], "target_approaches")
            effort[row["role"]][phase]["camera_hours"] += hours
            effort[row["role"]][phase]["patrol_hours"] += patrol
            effort[row["role"]][phase]["target_approaches"] += approaches

        view, glass, canopy, flow, assessment = _evaluate_pane(row, pane, registry, registered_at)
        assembly = _text(row["glass_assembly_class"], "glass assembly class")
        assembly_source = _text(row["glass_assembly_source_id"], "glass assembly source_id")
        candidates = {item["action"]: item for item in assessment["intervention_comparison"]["candidates"]}
        for name, evidence_needed in DEFERRED.items():
            candidate = candidates.setdefault(name, {"action": name, "decision": "deferred"})
            candidate["evidence_needed"] = evidence_needed
        reviews = row.get("candidate_reviews", {})
        if set(reviews) - set(candidates):
            raise ValueError("Feasibility reviews must match a candidate on the same pane")
        candidates = {
            name: _review_candidate(candidate, reviews.get(name, {}), registry_sources, registered_at)
            for name, candidate in candidates.items()
        }
        eligible = [name for name in PRIMARY_ACTIONS if name in candidates and not candidates[name]["vetoes"]]
        first_comparison = eligible[0] if eligible else None
        first_reason = None
        if first_comparison == MARKERS:
            first_reason = "A visible full-pane exterior pattern addresses both reflective and transmitted obstacle cues."
        elif first_comparison is not None:
            first_reason = candidates[first_comparison]["mechanism_match"]
        selected_feasibility = None
        if row["role"] == "treatment":
            selected_feasibility = candidates.get(action, {}).get("feasibility", "unsupported")
        panes[identity.pane_id] = {
            "identity": identity.as_dict(), "role": row["role"], "pair_id": block,
            "assignment_neighborhood_id": neighborhood, "glass_view": view.as_dict(),
            "existing_pattern_inspection": row["glass_view"]["existing_pattern_status"],
            "existing_pattern_assessment": assessment["glass_assessment"],
            "matching_evidence": {"glass_assembly_class": assembly, "glass_assembly_source_id": assembly_source,
                                  "canopy_cover_50m": row["canopy_cover_50m"], "bird_flow": row["bird_flow"]},
            "monitor_surfaces": surfaces, "planned_effort": row["effort"],
            "first_comparison_for_mechanism_review": first_comparison,
            "first_comparison_reason": first_reason,
            "selected_feasibility": selected_feasibility,
            "candidate_review": list(candidates.values()),
        }
        azimuth = _number(pane.outward_azimuth_deg, "pane azimuth", maximum=360)
        glass_context = (glass.appearance, assembly, assessment["glass_assessment"]["pattern_status"])
        blocks.setdefault(block, []).append((identity.pane_id, row["role"], azimuth, glass_context, canopy.value, flow.value))

    if not blocks or set(panes) & tracked_surfaces:
        raise ValueError("Require an independent treatment-control pair without primary panes in spillover areas")
    for pair_id, rows in sorted(blocks.items()):
        if sorted(member[1] for member in rows) != sorted(ROLES):
            raise ValueError("Each pair must have one treatment pane and one control pane")
        first, second = sorted(rows)
        difference = abs(first[2] - second[2])
        azimuth = min(difference, 360 - difference)
        differences = (azimuth, abs(first[4] - second[4]), abs(first[5] - second[5]))
        if first[3] != second[3] or any(actual > allowed for actual, allowed in zip(differences, thresholds)):
            raise ValueError(f"Pair {pair_id} fails the preregistered matching criteria")
        if rng is not None and rng.choice((first, second))[1] != "treatment":
            raise ValueError(f"Pair {pair_id} does not match the preregistered seed allocation")

    blockers = ["no_comparable_local_after_data_or_effect_interval"]
    if synthetic:
        blockers.append("synthetic_preregistration")
    if len(blocks) < target_pairs:
        blockers.append("target_independent_pairs_not_allocated")
    selected_reviews = {pane["selected_feasibility"] for pane in panes.values() if pane["role"] == "treatment"}
    if selected_reviews & {"unsupported", "vetoed"}:
        blockers.append("selected_action_unsupported_or_vetoed")
    if "pending_review" in selected_reviews:
        blockers.append("selected_action_needs_feasibility_review")
    if any(pane["existing_pattern_inspection"] == "unverified" for pane in panes.values()):
        blockers.append("existing_pattern_needs_verification")
    return {
        "schema_version": 1, "trial_id": trial_id, "evidence_kind": plan["evidence_kind"],
        "registered_at": plan["registered_at"], "periods": plan["periods"], "allocation": allocation,
        "primary_endpoint": "first contact on any monitored surface per at-risk approach",
        "secondary_endpoints": [
            "first contact on target pane, adjacent panes, frame or screen per at-risk approach",
            "observed injury per at-risk approach with unknown injury retained",
            "carcass detection per effective standardized patrol-hour, analyzed separately",
        ],
        "protocol": protocol, "treatment_action": action,
        "target_independent_pairs": target_pairs, "allocated_pairs": len(blocks), "planned_effort": effort,
        "minimum_meaningful_absolute_risk_difference": minimum_effect,
        "pane_candidates": list(panes.values()),
        "site_effect_estimate": None, "site_effect_interval": None, "local_efficacy_ranked": False,
        "authorized_for_installation": False,
        "evidence_to_collect": [
            "Verify continuous follow-up and treatment adherence in each arm and both periods.",
            "When uncertainty spans the meaningful effect, add independent pairs and repeated seasonal effort.",
            "When patrol detection is sparse, prioritize local searcher and persistence trials.",
        ],
        "blockers": blockers,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_retrofit_trial(json.loads(args.plan.read_text(encoding="utf-8")))
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.error(f"Invalid trial plan {args.plan}: {error}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
