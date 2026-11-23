from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from birdglass.bnbu_monitoring import APPROACH, PATROL, run_monitoring


EXAMPLE = Path(__file__).resolve().parents[1] / "data/examples/synthetic_bnbu_monitoring.json"


@pytest.fixture
def inputs():
    return json.loads(EXAMPLE.read_bytes())


def test_synthetic_replay_and_endpoint_denominators(inputs):
    report = run_monitoring(inputs)
    a, adjacent, b = report["panes"]
    assert a["approach_outcomes"] == {"glass_contact": 1, "opaque_contact": 1, "no_contact": 1,
                                      "right_censored": 1, "recording_gap": 1}
    assert a["approaches"][1]["synthetic_replay"]["observed_geometry_contact"] == "SYN-A-FRAME"
    assert a["approaches"][0]["synthetic_replay"]["ray_kinds"] == ["reflection"]
    assert b["approaches"][0]["synthetic_replay"]["ray_kinds"] == ["transmission"]
    assert [row["target"] for row in a["approaches"]] == [1, 0, 0, None, None]
    assert [row["target"] for row in b["patrols"]] == [1, 0, None, None]
    assert adjacent["approaches"] == adjacent["patrols"] == []
    assert all(prediction["value"] is None and prediction["reason"] == "synthetic_evidence"
               for pane in report["panes"] for prediction in pane["risk_predictions"].values())


def test_baselines_leave_building_and_future_out_and_abstain_on_censoring(inputs):
    report = run_monitoring(inputs)
    approach_a_early, approach_a_late, approach_b_late = report["baselines"][APPROACH]
    assert approach_a_early["training_ids"] == []
    assert approach_a_late["reason"] == "censored_approach_model_required"
    assert approach_b_late["fitted_ids"] == ["A-1", "A-2", "A-3"]
    assert [r["baseline"] for r in approach_b_late["predictions"]] == pytest.approx([1 / 3, 1 / 3])
    patrol_b_late = report["baselines"][PATROL][1]
    assert patrol_b_late["scored_ids"] == ["patrol-B-3", "patrol-B-4"]
    first, second = patrol_b_late["predictions"]
    assert 0 < second["baseline"] < first["baseline"] < 1

    # The same identified bird in another building is still a held-out bird.
    inputs["approaches"][5]["individual_id"] = "SYN-bird-A-1"
    held_out = run_monitoring(inputs)["baselines"][APPROACH][2]
    assert held_out["fitted_ids"] == ["A-2", "A-3"]
    assert held_out["predictions"] == []


def test_shared_annotation_source_stays_out_of_training(inputs):
    inputs["approaches"][0]["source_id"] = inputs["approaches"][5]["source_id"]
    held_out = run_monitoring(inputs)["baselines"][APPROACH][2]
    assert held_out["fitted_ids"] == ["A-2", "A-3"]


def test_same_facade_swap_does_not_inherit_video(inputs):
    inputs["approaches"][0]["pane_id"] = "SYN-A-2"
    with pytest.raises(ValueError, match="pane registration disagree"):
        run_monitoring(inputs)


def test_outcome_source_rules_and_distinct_missing_from_zero(inputs):
    inputs["patrols"][4]["detected_carcasses"] = 0
    with pytest.raises(ValueError, match="leave both"):
        run_monitoring(inputs)

    inputs["patrols"][4]["detected_carcasses"] = None
    inputs["approaches"][2]["complete_followup"] = False
    with pytest.raises(ValueError, match="cannot certify"):
        run_monitoring(inputs)


def test_duplicate_trials_and_pane_patrols_are_rejected(inputs):
    duplicate = deepcopy(inputs["approaches"][0])
    inputs["approaches"].append({**duplicate, "approach_id": "duplicate"})
    with pytest.raises(ValueError, match="source trial"):
        run_monitoring(inputs)
    inputs["approaches"].pop()
    patrol = deepcopy(inputs["patrols"][0])
    inputs["patrols"].append({**patrol, "patrol_id": "duplicate"})
    with pytest.raises(ValueError, match="Duplicate pane patrol"):
        run_monitoring(inputs)
    inputs["patrols"][-1]["start"] = "2026-01-01T10:55:00+08:00"
    with pytest.raises(ValueError, match="overlap"):
        run_monitoring(inputs)


def test_recording_gap_is_distinct_from_truncated_track(inputs):
    inputs["approaches"][4]["outcome"] = "right_censored"
    with pytest.raises(ValueError, match="recording gap disagrees"):
        run_monitoring(inputs)


def test_session_zero_requires_completed_annotation_and_exports_known_fields(inputs):
    session = inputs["video_sessions"][0]
    inputs["video_sessions"] += [{**session, "video_id": "known-zero"},
                                 {**session, "video_id": "unknown-zero", "annotation_status": "unknown"}]
    for row in [inputs["panes"][0], inputs["approaches"][0], inputs["patrols"][0]]:
        row["unmodeled_note"] = "should stay in the input"
    result = run_monitoring(inputs)
    sessions = {row["video_id"]: row for row in result["panes"][0]["video_sessions"]}
    assert sessions["known-zero"]["complete_session_approach_count"] == 0
    assert sessions["unknown-zero"]["complete_session_approach_count"] is None
    assert "unmodeled_note" not in json.dumps(result)


def test_unsupported_provenance_and_unverified_local_records_are_rejected(inputs):
    with pytest.raises(ValueError, match="input evidence kind"):
        run_monitoring({**inputs, "evidence_kind": "external_benchmark"})
    with pytest.raises(ValueError, match="field-verified"):
        run_monitoring({**inputs, "evidence_kind": "bnbu_monitoring"})
    inputs["video_sessions"][0]["sampling"] = "selected_clip"
    with pytest.raises(ValueError, match="ineligible"):
        run_monitoring(inputs)


def test_pending_local_intake_explains_missing_evidence():
    inputs = json.loads(EXAMPLE.with_name("bnbu_monitoring_intake_pending.json").read_bytes())
    report = run_monitoring(inputs)
    assert report["panes"] == []
    assert report["site_validation"]["status"] == "awaiting_validation"
    assert "field_verified_panes" in report["site_validation"]["missing"]
    assert report["baselines"] == {APPROACH: [], PATROL: []}


def test_local_intake_requires_exact_field_registry_and_source():
    inputs = json.loads(EXAMPLE.with_name("bnbu_monitoring_intake_pending.json").read_bytes())
    registry = json.loads(EXAMPLE.with_name("synthetic_pane_registry.json").read_bytes())
    entry = registry["panes"][0]
    inputs["pane_registry"] = registry
    pane = {**entry["identity"], "registration_status": "field_verified", "optical_mechanism": "unknown",
            "registration_source_id": entry["geometry_source_id"]}
    inputs["panes"] = [pane]
    with pytest.raises(ValueError, match="no field verification"):
        run_monitoring(inputs)

    # Exercise the field input path in the test without publishing any field assertion.
    registry["dataset_kind"] = "field"
    inputs["time_blocks"] = [{"time_block_id": "local", "start": "2026-02-01T00:00:00+08:00",
                              "end": "2026-02-02T00:00:00+08:00"}]
    inputs["patrols"] = [{**entry["identity"], "patrol_id": "pending", "time_block_id": "local",
                          "start": "2026-02-01T09:00:00+08:00", "end": "2026-02-01T09:30:00+08:00",
                          "source_id": "pending-source", "status": "unknown", "effort_hours": None,
                          "detected_carcasses": None}]
    report = run_monitoring(inputs)
    assert report["panes"][0]["risk_predictions"][APPROACH]["value"] is None
    assert "standardized_patrols" in report["site_validation"]["missing"]
    pane["registration_source_id"] = "another-source"
    with pytest.raises(ValueError, match="source conflicts"):
        run_monitoring(inputs)


def test_demo_cli_reproduces_and_pins_outputs(tmp_path):
    command = [sys.executable, "-m", "birdglass.bnbu_monitoring", str(EXAMPLE), str(tmp_path)]
    subprocess.run(command, cwd=EXAMPLE.parents[2], check=True)
    report = tmp_path / "monitoring_report.json"
    original = report.read_bytes()
    manifest = json.loads((tmp_path / "manifest.json").read_bytes())
    assert manifest["input_sha256"] == sha256(EXAMPLE.read_bytes()).hexdigest()
    assert manifest["report_sha256"] == sha256(original).hexdigest()
    assert "approach_events.py" in manifest["code_sha256"]
    subprocess.run(command, cwd=EXAMPLE.parents[2], check=True)
    assert report.read_bytes() == original
