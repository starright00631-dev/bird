"""Audit monitoring inputs and estimate held-out exposure-only baselines."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median
import sys

import scipy
from scipy.optimize import minimize_scalar

from .approach_events import VideoAnnotation, analyze_approach
from .pane_registry import PaneIdentity, PaneRegistry
from .scene_optics import RectPatch


APPROACH = "glass_contact_given_approach"
PATROL = "detected_carcass_presence"
OUTCOMES = {"glass_contact", "opaque_contact", "no_contact", "right_censored", "recording_gap"}
OPTICAL_MECHANISMS = {"reflection", "transmission", "both", "unknown"}
PANE_FIELDS = ("pane_id", "building_id", "facade_id", "model_version")
PANE_EVIDENCE_FIELDS = PANE_FIELDS + ("registration_status", "registration_source_id",
                                     "optical_mechanism", "optical_source_id")
APPROACH_FIELDS = PANE_FIELDS + ("approach_id", "video_id", "source_id", "reviewer_id", "trial_id",
                                 "individual_id", "gate_at", "outcome", "contacted_surface_id", "complete_followup")
PATROL_FIELDS = PANE_FIELDS + ("patrol_id", "time_block_id", "start", "end", "source_id", "status",
                               "effort_hours", "detected_carcasses")
VIDEO_FIELDS = PANE_FIELDS + ("video_id", "time_block_id", "start", "end", "source_id", "sampling",
                              "gate_id", "frames_per_second")


def _id(value, field):
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} requires a nonblank ID without surrounding whitespace")
    return value


def _time(value):
    timestamp = datetime.fromisoformat(_id(value, "timestamp").replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("Monitoring timestamps require an explicit UTC offset")
    return timestamp


def _positive(value, field):
    if type(value) not in {int, float} or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be positive and finite")
    return value


def _row_index(rows, key):
    indexed = {}
    for row in rows:
        identity = _id(row[key], key)
        if identity in indexed:
            raise ValueError(f"Duplicate {key}: {identity}")
        indexed[identity] = row
    return indexed


def _interval(row, blocks):
    start, end = _time(row["start"]), _time(row["end"])
    first, last = blocks[row["time_block_id"]]
    if not first <= start < end <= last:
        raise ValueError("Monitoring intervals must lie within one declared time block")
    return start, end


def _same_pane(row, pane):
    if any(row[key] != pane[key] for key in PANE_FIELDS):
        raise ValueError("Monitoring row and pane registration disagree")


def _synthetic_track_check(event, session, geometry):
    points = event["trajectory"]
    patches = [RectPatch(**patch) for patch in geometry[session["building_id"]]]
    outcome = event["outcome"]
    annotation = VideoAnnotation(
        outcome if outcome in {"glass_contact", "opaque_contact", "no_contact"} else "unknown",
        event["contacted_surface_id"],
        complete_video_coverage=event["complete_followup"], reviewed_from_source_video=True,
    )
    replay = analyze_approach(
        clip_id=event["approach_id"], rows=points, patches=patches, annotation=annotation,
        frames_per_second=session["frames_per_second"], geometry_registered=True,
        gate_distance_m=session["gate_distance_m"], scene_sources=event["scene_sources"],
    )
    frames = sorted(point["frame"] for point in points)
    has_gap = any(second != first + 1 for first, second in zip(frames, frames[1:]))
    if outcome in {"recording_gap", "right_censored"} and (outcome == "recording_gap") != has_gap:
        raise ValueError(f"Synthetic recording gap disagrees with frame coverage for {event['approach_id']}")
    expected = {"glass_contact": "video_verified_glass_contact",
                "opaque_contact": "video_verified_opaque_contact",
                "no_contact": "video_verified_geometric_clearance",
                "right_censored": "right_censored", "recording_gap": "right_censored"}
    kinds = sorted({ray["kind"] for ray in replay.optical_rays})
    if (replay.first_risk_pane != event["pane_id"] or replay.status != expected[outcome]
            or kinds != sorted(event["expected_ray_kinds"])
            or replay.observed_geometry_first_contact != event["contacted_surface_id"]):
        raise ValueError(f"Synthetic geometry or annotation disagrees for {event['approach_id']}")
    return {"geometry_status": replay.status, "first_risk_pane": replay.first_risk_pane,
            "observed_geometry_contact": replay.observed_geometry_first_contact,
            "ray_kinds": kinds}


def _approaches(data, panes, blocks, surfaces):
    coverage = _row_index(data["video_sessions"], "video_id")
    session_windows = {}
    for video_id, session in coverage.items():
        _same_pane(session, panes[session["pane_id"]])
        _id(session["source_id"], "video source_id")
        _id(session["gate_id"], "gate_id")
        _positive(session["frames_per_second"], "frames_per_second")
        if session["sampling"] != "continuous":
            raise ValueError("Selected clips and opportunity reports are ineligible as monitoring inputs")
        if session.get("annotation_status", "unknown") not in {"complete", "partial", "unknown"}:
            raise ValueError("Invalid video session annotation status")
        session_windows[video_id] = _interval(session, blocks)

    results = []
    source_trials = set()
    for event in _row_index(data["approaches"], "approach_id").values():
        session = coverage[event["video_id"]]
        _same_pane(event, session)
        _id(event["source_id"], "annotation source_id")
        _id(event["reviewer_id"], "reviewer_id")
        trial_id = _id(event["trial_id"], "trial_id")
        if event.get("individual_id") is not None:
            _id(event["individual_id"], "individual_id")
        trial_key = (session["source_id"], trial_id)
        if trial_key in source_trials:
            raise ValueError("One source trial cannot supply multiple approaches")
        source_trials.add(trial_key)

        start, end = session_windows[event["video_id"]]
        if not start <= _time(event["gate_at"]) < end:
            raise ValueError("Approach gate time falls outside the source video session")
        outcome = event["outcome"]
        if outcome not in OUTCOMES or type(event["complete_followup"]) is not bool:
            raise ValueError("Unsupported approach outcome or follow-up flag")
        contact = event["contacted_surface_id"]
        if outcome in {"glass_contact", "opaque_contact"}:
            surface = surfaces.get(contact)
            if (surface is None or surface["building_id"] != session["building_id"]
                    or surface["material"] != outcome.removesuffix("_contact")):
                raise ValueError("First-contact surface disagrees with the registered scene or outcome")
            if not event["complete_followup"]:
                raise ValueError("First contact requires observation through the contact")
        elif contact is not None:
            raise ValueError("Only a contact event can name a contacted surface")
        if outcome == "no_contact" and not event["complete_followup"]:
            raise ValueError("Incomplete follow-up cannot certify a no-contact outcome")
        if outcome in {"right_censored", "recording_gap"} and event["complete_followup"]:
            raise ValueError("Censoring and recording gaps require incomplete follow-up")

        result = {**{field: event.get(field) for field in APPROACH_FIELDS},
                  "time_block_id": session["time_block_id"],
                  "gate_id": session["gate_id"], "video_source_id": session["source_id"],
                  "target": (int(outcome == "glass_contact") if outcome in {
                      "glass_contact", "opaque_contact", "no_contact"} else None)}
        if data["evidence_kind"] == "synthetic" and "synthetic_geometry" in data:
            result["synthetic_replay"] = _synthetic_track_check(event, session, data["synthetic_geometry"])
        results.append(result)
    event_counts = Counter(row["video_id"] for row in results)
    sessions = []
    for video_id, session in sorted(coverage.items()):
        status = session.get("annotation_status", "unknown")
        sessions.append({**{field: session[field] for field in VIDEO_FIELDS},
                         "annotation_status": status, "annotated_approach_count": event_counts[video_id],
                         "complete_session_approach_count": event_counts[video_id] if status == "complete" else None})
    return results, sessions


def _patrols(data, panes, blocks):
    results = []
    visits = set()
    surveyed_intervals = {}
    for row in _row_index(data["patrols"], "patrol_id").values():
        _same_pane(row, panes[row["pane_id"]])
        _id(row["source_id"], "patrol source_id")
        start, end = _interval(row, blocks)
        visit_key = (row["pane_id"], start, end)
        if visit_key in visits:
            raise ValueError("Duplicate pane patrol interval")
        visits.add(visit_key)
        effort, count = row["effort_hours"], row["detected_carcasses"]
        if row["status"] == "surveyed":
            _positive(effort, "effort_hours")
            if effort > (end - start).total_seconds() / 3600 + 1e-10:
                raise ValueError("Effective patrol hours cannot exceed elapsed survey time")
            if type(count) is not int or count < 0:
                raise ValueError("A completed patrol requires an explicit nonnegative count")
            surveyed_intervals.setdefault(row["pane_id"], []).append((start, end))
        elif row["status"] not in {"not_surveyed", "unknown"} or effort is not None or count is not None:
            raise ValueError("A missing patrol must leave both the count and effort blank")
        results.append({**{field: row[field] for field in PATROL_FIELDS},
                        "target": int(count > 0) if count is not None else None})
    for intervals in surveyed_intervals.values():
        intervals.sort()
        if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
            raise ValueError("Surveyed patrol intervals overlap for the same pane")
    return results


def _patrol_probabilities(train, test):
    # Constant Poisson detection rate with a log-effort offset, observable as
    # Bernoulli presence: P(any detected carcass) = 1 - exp(-rate * hours).
    reference_hours = median(row["effort_hours"] for row in train)

    def negative_log_likelihood(log_rate):
        rate = math.exp(log_rate - math.log(reference_hours))
        return sum(-math.log(-math.expm1(-rate * row["effort_hours"]))
                   if row["target"] else rate * row["effort_hours"] for row in train)

    result = minimize_scalar(negative_log_likelihood, bounds=(-25, 25), method="bounded")
    if not result.success or abs(result.x) >= 24.99:
        return None
    rate = math.exp(result.x - math.log(reference_hours))
    return [-math.expm1(-rate * row["effort_hours"]) for row in test]


def _baseline_folds(records, blocks, endpoint, id_key):
    folds = []
    for building, block in sorted({(row["building_id"], row["time_block_id"]) for row in records}):
        test = [row for row in records if row["building_id"] == building and row["time_block_id"] == block]
        held_sources = {row[key] for row in test for key in ("source_id", "video_source_id") if key in row}
        held_individuals = {row["individual_id"] for row in test if row.get("individual_id")}
        train = [row for row in records if row["building_id"] != building
                 and blocks[row["time_block_id"]][1] <= blocks[block][0]
                 and row["source_id"] not in held_sources and row.get("video_source_id") not in held_sources
                 and row.get("individual_id") not in held_individuals]
        fold = {"held_out_building_id": building, "held_out_time_block_id": block,
                "training_ids": sorted(row[id_key] for row in train),
                "held_out_ids": sorted(row[id_key] for row in test),
                "training_positives": sum(row["target"] == 1 for row in train),
                "held_out_positives": sum(row["target"] == 1 for row in test),
                "brier": None, "predictions": [], "reason": None}
        if endpoint == APPROACH and len({row["gate_id"] for row in [*train, *test]}) > 1:
            fold["reason"] = "incompatible_risk_gate_definitions"
        elif endpoint == APPROACH and any(row["target"] is None for row in [*train, *test]):
            fold["reason"] = "censored_approach_model_required"
        else:
            train = [row for row in train if row["target"] is not None]
            test = sorted((row for row in test if row["target"] is not None), key=lambda row: row[id_key])
            fold["scored_ids"] = [row[id_key] for row in test]
            fold["fitted_ids"] = sorted(row[id_key] for row in train)
            if not test or {row["target"] for row in train} != {0, 1}:
                fold["reason"] = "insufficient_training_classes_or_held_out_observations"
            else:
                if endpoint == APPROACH:
                    probabilities = [sum(row["target"] for row in train) / len(train)] * len(test)
                else:
                    probabilities = _patrol_probabilities(train, test)
                if probabilities is None:
                    fold["reason"] = "baseline_rate_not_identified"
                else:
                    fold["predictions"] = [{id_key: row[id_key], "observed": row["target"], "baseline": probability}
                                           for row, probability in zip(test, probabilities)]
                    fold["brier"] = sum((p["baseline"] - p["observed"]) ** 2
                                        for p in fold["predictions"]) / len(test)
        folds.append(fold)
    return folds


def run_monitoring(data):
    """Build a versioned audit report. Baseline fold scores cannot release site risk."""
    if data["schema_version"] != 1 or data["evidence_kind"] not in {"synthetic", "bnbu_monitoring"}:
        raise ValueError("Unsupported monitoring schema or input evidence kind")
    _id(data["evidence_snapshot_id"], "evidence_snapshot_id")
    blocks = {key: (_time(row["start"]), _time(row["end"]))
              for key, row in _row_index(data["time_blocks"], "time_block_id").items()}
    ordered_blocks = sorted(blocks.values())
    if (any(start >= end for start, end in ordered_blocks)
            or any(a[1] > b[0] for a, b in zip(ordered_blocks, ordered_blocks[1:]))):
        raise ValueError("Time blocks must be ordered, disjoint and nonempty")

    panes = _row_index(data["panes"], "pane_id")
    local_input = data["evidence_kind"] == "bnbu_monitoring"
    registry = PaneRegistry.from_dict(data["pane_registry"]) if local_input and "pane_registry" in data else None
    surfaces = {key: {"building_id": row["building_id"], "material": "glass"}
                for key, row in panes.items()}
    for pane in panes.values():
        for field in ("building_id", "facade_id", "model_version", "registration_source_id"):
            _id(pane[field], field)
        if pane["optical_mechanism"] not in OPTICAL_MECHANISMS:
            raise ValueError("Unsupported optical mechanism")
        if local_input:
            if registry is None or pane["registration_status"] != "field_verified":
                raise ValueError("BNBU monitoring requires a field-verified pane registry")
            identity = PaneIdentity(pane["pane_id"], pane["building_id"], pane["facade_id"], pane["model_version"])
            registered = registry.require(identity, field_verified=True)
            if registered.geometry_source_id != pane["registration_source_id"]:
                raise ValueError("Pane monitoring registration source conflicts with the registry")
            if pane["optical_mechanism"] != "unknown":
                _id(pane["optical_source_id"], "optical_source_id")
    for key, row in _row_index(data["opaque_surfaces"], "surface_id").items():
        _id(row["building_id"], "opaque surface building_id")
        if key in surfaces:
            raise ValueError("Surface IDs must be unique across opaque structures and panes")
        surfaces[key] = {"building_id": row["building_id"], "material": "opaque"}

    approaches, sessions = _approaches(data, panes, blocks, surfaces)
    patrols = _patrols(data, panes, blocks)
    reports = []
    for pane_id, pane in sorted(panes.items()):
        pane_approaches = sorted((row for row in approaches if row["pane_id"] == pane_id),
                                 key=lambda row: row["approach_id"])
        pane_patrols = sorted((row for row in patrols if row["pane_id"] == pane_id),
                              key=lambda row: row["patrol_id"])
        reports.append({"pane": {field: pane.get(field) for field in PANE_EVIDENCE_FIELDS},
                        "approaches": pane_approaches, "patrols": pane_patrols,
                        "video_sessions": [session for session in sessions if session["pane_id"] == pane_id],
                        "approach_outcomes": dict(Counter(row["outcome"] for row in pane_approaches)),
                        "patrol_statuses": dict(Counter(row["status"] for row in pane_patrols)),
                        "effective_patrol_hours": (sum(row["effort_hours"] for row in pane_patrols
                            if row["status"] == "surveyed")
                            if any(row["status"] == "surveyed" for row in pane_patrols) else None),
                        "risk_predictions": {endpoint: {"value": None, "interval": None,
                            "reason": ("synthetic_evidence" if data["evidence_kind"] == "synthetic"
                                       else "no_approved_bnbu_model_validation_artifact")}
                            for endpoint in (APPROACH, PATROL)}})

    return {"schema_version": 1, "evidence_kind": data["evidence_kind"],
            "evidence_snapshot_id": data["evidence_snapshot_id"], "panes": reports,
            "site_validation": {
                "status": "synthetic_only" if not local_input else "awaiting_validation",
                "missing": [reason for reason, present in (
                    ("field_verified_panes", bool(panes) and local_input),
                    ("continuous_approach_outcomes", local_input and any(row["target"] is not None for row in approaches)),
                    ("standardized_patrols", local_input and any(row["target"] is not None for row in patrols)),
                    ("local_detection_and_persistence_trials", False),
                    ("approved_bnbu_model_validation_artifact", False),
                ) if not present],
            },
            "baselines": {
                APPROACH: _baseline_folds(approaches, blocks, APPROACH, "approach_id"),
                PATROL: _baseline_folds(patrols, blocks, PATROL, "patrol_id"),
            }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Versioned monitoring JSON")
    parser.add_argument("output", type=Path, help="Output directory")
    args = parser.parse_args()
    input_bytes = args.input.read_bytes()
    try:
        report = run_monitoring(json.loads(input_bytes))
    except (KeyError, TypeError, ValueError) as exc:
        parser.error(f"Invalid monitoring input: {exc}")

    report_bytes = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "monitoring_report.json").write_bytes(report_bytes)
    code_files = sorted(Path(__file__).parent.glob("*.py"))
    manifest = {"input_sha256": sha256(input_bytes).hexdigest(),
                "code_sha256": {path.name: sha256(path.read_bytes()).hexdigest() for path in code_files},
                "report_sha256": sha256(report_bytes).hexdigest(), "python": sys.version.split()[0],
                "scipy": scipy.__version__}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
