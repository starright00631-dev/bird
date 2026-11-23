import json
from pathlib import Path
import subprocess
import sys

import pytest

from birdglass.pane_registry import PaneRegistry
from birdglass.pane_vegetation import summarize_pane_vegetation
from birdglass.vegetation import VEGETATION_BUFFERS


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "data/examples/synthetic_pane_vegetation.json"


@pytest.fixture
def bundle():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_mask_counts_keep_land_cover_reflection_transmission_and_routes_separate(bundle):
    summary = summarize_pane_vegetation(bundle)
    assert summary["dataset_kind"] == "synthetic"
    assert summary["pane"] == bundle["pane"]
    land = summary["land_cover"]
    assert tuple(land["bands"]) == VEGETATION_BUFFERS
    assert land["season"] == "winter"
    assert land["source_ref"] == "synthetic:orthomap"
    assert land["position_reference"] == "synthetic:projected-pixel-grid"
    ring = land["bands"]["0_5m"]
    assert ring["tree_canopy_cover_percent"] == 50
    assert ring["class_cover_percent"]["impervious"] == 50
    assert ring["valid_area_m2"] == 2
    assert ring["footprint_area_m2"] == 4
    assert ring["occluded_area_m2"] == 1
    assert ring["unclassified_area_m2"] == 1
    assert summary["site_context"]["facade_tree_cover_50m_percent"] == 35
    views = {view["view_id"]: view for view in summary["reflection_views"]}
    morning = views["synthetic-morning"]
    afternoon = views["synthetic-afternoon"]
    assert morning["approach_bearing_deg"] == afternoon["approach_bearing_deg"]
    assert morning["recorded_at"] != afternoon["recorded_at"]
    assert morning["reflected_vegetation_share"] == pytest.approx(1 / 3)
    assert morning["transmitted_vegetation_share"] == pytest.approx(1 / 3)
    assert morning["interpretable_share"] == 0.75
    assert afternoon["reflected_vegetation_share"] == 0
    evening = views["synthetic-evening"]
    assert evening["reflected_vegetation_share"] is None
    assert evening["reason"] and evening["review_action"]
    session = summary["approach_monitoring"][0]
    assert session["effort_s"] == 900
    assert session["observed_route_count"] == 1
    assert session["routes"][0]["track_ref"].endswith("#frame=100-180")


def test_out_of_band_pixel_is_rejected_even_if_occluded(bundle):
    ring = bundle["land_cover"]["bands"]["5_25m"]
    ring["upper_left_pixel_center_xy_m"] = [10004, 10000]
    ring["mask"][0][0] = "occluded"
    with pytest.raises(ValueError, match="outside its annulus"):
        summarize_pane_vegetation(bundle)


def test_missing_and_uninterpretable_masks_stay_missing(bundle):
    bands = bundle["land_cover"]["bands"]
    bands["5_25m"]["mask"] = [["occluded", "unclassified"]]
    bands.pop("25_100m")
    bundle["reflections"][0]["mask"] = [["outside", "occluded"]]
    summary = summarize_pane_vegetation(bundle)
    rings = summary["land_cover"]["bands"]
    assert rings["5_25m"]["status"] == "missing"
    assert rings["5_25m"]["valid_area_m2"] == 0
    assert rings["25_100m"]["status"] == "missing"
    assert "tree_canopy_cover_percent" not in rings["5_25m"]
    morning = next(view for view in summary["reflection_views"] if view["view_id"] == "synthetic-morning")
    assert morning["status"] == "missing"
    assert morning["reflected_vegetation_share"] is None
    assert morning["review_action"]


def test_rejected_summary_keeps_provenance_and_withholds_numbers(bundle):
    bundle["land_cover"].update(status="rejected", reason="Registration failed")
    bundle["reflections"][0].update(status="pending", reason="Reflection ambiguous")
    summary = summarize_pane_vegetation(bundle)
    land = summary["land_cover"]
    assert land["source_id"] == "synthetic-orthomap"
    assert all(row["status"] == "missing" for row in land["bands"].values())
    assert "tree_canopy_cover_percent" not in land["bands"]["0_5m"]
    morning = next(view for view in summary["reflection_views"] if view["view_id"] == "synthetic-morning")
    assert morning["reflected_vegetation_share"] is None
    assert morning["reason"] == "Reflection ambiguous"


@pytest.mark.parametrize("identity_key", ["pane_id", "building_id", "facade_id", "model_version"])
def test_evidence_from_an_adjacent_pane_or_wrong_registration_is_rejected(bundle, identity_key):
    bundle["reflections"][0]["pane"][identity_key] = "mismatch"
    with pytest.raises(ValueError, match="pane identity does not match"):
        summarize_pane_vegetation(bundle)


def test_field_bundle_requires_its_own_verified_registration(bundle):
    bundle["dataset_kind"] = "field"
    with pytest.raises(ValueError, match="field-verified pane registry"):
        summarize_pane_vegetation(bundle)
    candidate = PaneRegistry.from_dict({"dataset_kind": "field", "panes": [{"identity": bundle["pane"]}]})
    with pytest.raises(ValueError, match="no field verification"):
        summarize_pane_vegetation(bundle, registry=candidate)
    synthetic = PaneRegistry.from_dict({"dataset_kind": "synthetic", "panes": [{"identity": bundle["pane"]}]})
    with pytest.raises(ValueError, match="dataset_kind must match"):
        summarize_pane_vegetation(bundle, registry=synthetic)

    verified = PaneRegistry.from_dict({
        "dataset_kind": "field",
        "panes": [{
            "identity": bundle["pane"],
            "floor": "1",
            "bay": "A",
            "coordinate_system": "test-local-metric",
            "corners_m": [[0, 0, 1], [1, 0, 1], [1, 0, 2], [0, 0, 2]],
            "outward_azimuth_deg": 180,
            "registration_error_m": 0.05,
            "geometry_source_id": "test-geometry",
            "photos": [{
                "photo_id": "test-registration-photo",
                "source_id": "test-photo-index",
                "captured_at": "2026-01-08T08:01:00+08:00",
            }],
            "field_verified_at": "2026-01-08T08:05:00+08:00",
        }],
    })
    assert summarize_pane_vegetation(bundle, registry=verified)["pane"] == bundle["pane"]


def test_continuous_zero_requires_explicit_routes_while_selected_evidence_stays_unknown(bundle):
    row = bundle["monitoring"][0]
    row["routes"] = []
    result = summarize_pane_vegetation(bundle)["approach_monitoring"][0]
    assert result["observed_route_count"] == 0
    row.update(coverage_mode="selected", effort_s=30)
    result = summarize_pane_vegetation(bundle)["approach_monitoring"][0]
    assert result["observed_route_count"] is None
    row["coverage_mode"] = "continuous"
    with pytest.raises(ValueError, match="cannot contain gaps"):
        summarize_pane_vegetation(bundle)
    row["effort_s"] = 900
    del row["routes"]
    with pytest.raises(ValueError, match="explicit routes list"):
        summarize_pane_vegetation(bundle)


def test_duplicate_tracks_and_out_of_session_timestamps_are_rejected(bundle):
    routes = bundle["monitoring"][0]["routes"]
    routes.append(routes[0].copy())
    with pytest.raises(ValueError, match="Duplicate track_id"):
        summarize_pane_vegetation(bundle)
    routes.pop()
    routes[0]["observed_at"] = "2026-01-08T08:30:00+08:00"
    with pytest.raises(ValueError, match="within its monitoring session"):
        summarize_pane_vegetation(bundle)


def test_rerunnable_cli():
    command = [sys.executable, "-m", "birdglass.pane_vegetation", str(EXAMPLE)]
    first = subprocess.check_output(command, cwd=ROOT)
    assert subprocess.check_output(command, cwd=ROOT) == first
    assert json.loads(first)["land_cover"]["bands"]["1_10km"]["valid_area_m2"] == 2
