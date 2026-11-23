import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pytest

from birdglass.bnbu_monitoring import run_monitoring
from birdglass.evidence import EvidenceTier, Measurement
from birdglass.glass_observation import GlassObservation
from birdglass.pane_registry import PaneIdentity, PaneGlassObservation, PaneRegistration, PaneRegistry
from birdglass.pane_vegetation import summarize_pane_vegetation
from birdglass.workspace_evidence import export_workspace


EXAMPLES = Path(__file__).resolve().parents[1] / "data" / "examples"
KEYS = ("pane_id", "building_id", "facade_id", "model_version")
WHEN = "2026-01-09T09:00:00+08:00"


def synthetic_workspace():
    monitoring = json.loads((EXAMPLES / "synthetic_bnbu_monitoring.json").read_bytes())
    report = json.dumps(run_monitoring(monitoring), ensure_ascii=False, sort_keys=True).encode()
    identities = [PaneIdentity(**{key: row[key] for key in KEYS}) for row in monitoring["panes"]]
    registry = PaneRegistry([
        PaneRegistration(identity, floor="1", bay=identity.pane_id, geometry_source_id="synthetic_scene_v1")
        for identity in identities
    ], dataset_kind="synthetic")
    mapping = {
        "dataset_kind": "synthetic", "scene_version": "v89", "valid_until": "2099-01-01T00:00:00Z",
        "bindings": [
            {"pane": identity.as_dict(), "object_name": object_name, "mapped_at": WHEN,
             "mapping_source_id": "synthetic_browser_fixture"}
            for identity, object_name in zip(identities, ("MAIN_CC", "LAKE_00"))
        ],
    }
    land = json.loads((EXAMPLES / "synthetic_pane_vegetation.json").read_bytes())
    identity = identities[0].as_dict()
    land["pane"] = land["land_cover"]["pane"] = land["site_context"]["pane"] = identity
    for row in [*land["reflections"], *land["monitoring"]]:
        row["pane"] = identity
    vegetation = summarize_pane_vegetation(land)
    glass_rows = [
        PaneGlassObservation(
            identity=identities[0], evidence_id=source, observed_at=datetime.fromisoformat(WHEN),
            observation=GlassObservation(
                facade_id=identities[0].facade_id,
                exterior_vlr_pct=Measurement(value, "%", EvidenceTier.ASSUMPTION, source),
                exterior_vlt_pct=Measurement(60, "%", EvidenceTier.ASSUMPTION, source),
                specification_id=source,
            ),
            source_kind="manufacturer_assembly_spec", source_id=source, incidence_angle_deg=10,
        ) for source, value in (("synthetic-assembly-one", 22), ("synthetic-assembly-two", 35))
    ]
    return report, registry, mapping, vegetation, glass_rows


def test_workspace_uses_canonical_pane_report_and_vegetation():
    report, registry, mapping, vegetation, glass_rows = synthetic_workspace()
    result = export_workspace(
        report, registry, mapping, vegetation_reports=[vegetation], glass_rows=glass_rows,
    )
    assert result["report_sha256"] == sha256(report).hexdigest()
    a, b = result["bindings"]
    assert a["pane"]["facade_id"] == b["pane"]["facade_id"]
    a_facts = {fact["id"]: fact for fact in a["facts"]}
    b_facts = {fact["id"]: fact for fact in b["facts"]}
    assert a_facts["approach_count"]["value"] == 5
    assert a_facts["tree_cover_0_5_m"]["value"] == 0.5
    assert a_facts["exterior_vlr"]["status"] == "conflict"
    assert len(a_facts["exterior_vlr"]["source_ids"]) == 2
    assert a_facts["exterior_vlt"]["unit"] == "%"
    assert a_facts["exterior_vlt"]["observed_at"] == WHEN
    assert any(fact["view_id"] for fact in a["facts"])
    assert b_facts["approach_count"]["value"] is None
    assert b_facts["tree_cover_0_5_m"]["status"] == "missing"
    assert b_facts["exterior_vlr"]["status"] == "missing"
    for facts in (a_facts, b_facts):
        assert facts["local_treatment_effect"]["value"] is None
        assert facts["glass_contact_risk"]["value"] is None
    assert "reviewer_id" not in json.dumps(result)
    assert "trajectory" not in json.dumps(result)


def test_workspace_rejects_same_facade_swaps_and_unapproved_risk():
    report, registry, mapping, vegetation, glass_rows = synthetic_workspace()
    mapping["bindings"][1]["pane"]["model_version"] = "some-other-version"
    with pytest.raises(ValueError, match="mismatched pane identity"):
        export_workspace(report, registry, mapping, vegetation_reports=[vegetation], glass_rows=glass_rows)
    report, registry, mapping, _, _ = synthetic_workspace()
    tampered = json.loads(report)
    tampered["panes"][0]["risk_predictions"]["glass_contact_given_approach"]["value"] = 0.8
    with pytest.raises(ValueError, match="withheld numerical risk"):
        export_workspace(json.dumps(tampered).encode(), registry, mapping)


def write_browser_fixture(path):
    report, registry, mapping, vegetation, glass_rows = synthetic_workspace()
    data = export_workspace(report, registry, mapping, vegetation_reports=[vegetation], glass_rows=glass_rows)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
