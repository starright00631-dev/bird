import json
from pathlib import Path
import random

import pytest

from birdglass.retrofit_trial import MARKERS, SCREEN, SHADE, build_retrofit_trial


@pytest.fixture
def plan():
    path = Path(__file__).resolve().parents[1] / "data/examples/synthetic_retrofit_trial.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_trial_report_prioritizes_mechanism_and_retains_evidence_and_vetoes(plan):
    plan["site_effect_estimate"] = 0.75
    report = build_retrofit_trial(plan)
    treatment = report["pane_candidates"][0]
    candidates = {row["action"]: row for row in treatment["candidate_review"]}
    assert treatment["first_comparison_for_mechanism_review"] == MARKERS
    assert "addresses both" in treatment["first_comparison_reason"]
    assert candidates[MARKERS]["site_effect_estimate"] is None
    assert {row["source_id"] for row in candidates[MARKERS]["evidence_sources"]} >= {"OKLAHOMA_MARKER_BACI"}
    assert candidates[SHADE]["mechanism_match"] == "measured_reflection_pathway"
    assert candidates[SCREEN]["vetoes"] == ["entanglement_and_standoff"]
    assert report["allocated_pairs"] == 1
    assert report["target_independent_pairs"] == 4
    assert report["planned_effort"]["control"]["before"] == {
        "camera_hours": 60, "target_approaches": 120, "patrol_hours": 6,
    }
    assert report["site_effect_estimate"] is report["site_effect_interval"] is None
    assert not report["local_efficacy_ranked"]
    assert not report["authorized_for_installation"]


def test_veto_for_selected_action_is_reported_with_source_and_alternative(plan):
    review = plan["panes"][0]["candidate_reviews"][MARKERS]
    review["checks"] = {"ecological_impact": {
        "status": "veto", "reviewed_at": "2026-01-25T10:00:00+08:00",
        "source_id": "mock-ecology-review", "notes": "Mock risk of adhesive exposure.",
    }}
    report = build_retrofit_trial(plan)
    treated = report["pane_candidates"][0]
    assert "selected_action_unsupported_or_vetoed" in report["blockers"]
    assert treated["selected_feasibility"] == "vetoed"
    assert treated["first_comparison_for_mechanism_review"] == SHADE
    assert treated["candidate_review"][0]["requirements"]["ecological_impact"]["source_id"] == "mock-ecology-review"


def test_foreign_photo_is_not_a_measurement_of_the_target_pane(plan):
    plan["panes"][0]["glass_view"]["photo_ids"] = plan["panes"][1]["glass_view"]["photo_ids"]
    with pytest.raises(ValueError, match="Photo does not belong to the evidence pane"):
        build_retrofit_trial(plan)


def test_matching_rejects_dissimilar_bird_flow(plan):
    plan["panes"][1]["bird_flow"]["value"] = 15
    with pytest.raises(ValueError, match="matching criteria"):
        build_retrofit_trial(plan)


def test_parallel_arms_cannot_share_a_monitored_surface(plan):
    plan["panes"][0]["monitor_surfaces"][1]["surface_id"] = plan["panes"][1]["monitor_surfaces"][1]["surface_id"]
    with pytest.raises(ValueError, match="Spillover surface IDs must be unique"):
        build_retrofit_trial(plan)


def test_pre_before_post_temporal_boundaries_are_enforced(plan):
    plan["periods"]["after"]["start"] = plan["periods"]["before"]["start"]
    with pytest.raises(ValueError, match="nonoverlapping"):
        build_retrofit_trial(plan)


def test_assignment_is_verified_from_seed_and_stable_for_reordered_input(plan):
    plan["allocation"]["method"] = "randomized_within_pairs"
    plan["allocation"]["seed"] = next(seed for seed in range(100) if random.Random(seed).choice(["control", "treatment"]) == "treatment")
    plan["panes"].reverse()
    assert build_retrofit_trial(plan)["allocated_pairs"] == 1
    plan["allocation"]["seed"] = next(seed for seed in range(100) if random.Random(seed).choice(["control", "treatment"]) == "control")
    with pytest.raises(ValueError, match="seed allocation"):
        build_retrofit_trial(plan)


def test_site_preregistration_rejects_synthetic_registry(plan):
    plan["evidence_kind"] = "bnbu_preregistration"
    with pytest.raises(ValueError, match="evidence kind must match"):
        build_retrofit_trial(plan)


def test_unknown_existing_pattern_is_not_untreated_glass(plan):
    for pane in plan["panes"]:
        pane["glass_view"]["existing_pattern_status"] = "unverified"
    report = build_retrofit_trial(plan)
    assert "existing_pattern_needs_verification" in report["blockers"]
    assert report["pane_candidates"][0]["existing_pattern_assessment"]["pattern_status"] == "unverified"


def test_screen_trial_requires_screen_contact_followup(plan):
    plan["treatment_action"] = SCREEN
    with pytest.raises(ValueError, match="follow-up on the screen"):
        build_retrofit_trial(plan)
