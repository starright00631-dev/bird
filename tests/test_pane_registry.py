import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from birdglass.evidence import EvidenceTier, Measurement
from birdglass.glass_observation import GlassObservation
from birdglass.glazing import GlassAppearance
from birdglass.pane_registry import (
    ImpactLocation,
    PaneGlassObservation,
    PaneRegistry,
    SpectralObservation,
    audit_glass_evidence,
)


EXAMPLE = Path(__file__).resolve().parents[1] / "data/examples/synthetic_pane_registry.json"
AT = datetime.fromisoformat("2026-01-15T09:30:00+08:00")


@pytest.fixture
def registry():
    return PaneRegistry.from_dict(json.loads(EXAMPLE.read_text(encoding="utf-8")))


def field_view(pane):
    return PaneGlassObservation(
        identity=pane.identity,
        evidence_id="field-view-A",
        observed_at=AT,
        observation=GlassObservation(
            facade_id=pane.identity.facade_id,
            visual_class="reflective_and_transparent",
            visual_class_evidence_tier=EvidenceTier.LOCAL_SURVEY,
            visual_class_source_id=pane.photos[0].photo_id,
            photo_ids=(pane.photos[0].photo_id,),
            observer_id="anonymous-reviewer",
        ),
        source_kind="field_view",
        source_id=pane.photos[0].photo_id,
        view_id="view-A",
        approach_azimuth_deg=90,
        lighting_context="sunlit exterior and open passage behind glazing",
    )


def assembly_spec(pane, identifier, vlr, *, angle=10, uncertainty=None):
    lower, upper = uncertainty if uncertainty is not None else (None, None)
    return PaneGlassObservation(
        identity=pane.identity,
        evidence_id=f"record-{identifier}",
        observed_at=AT,
        observation=GlassObservation(
            facade_id=pane.identity.facade_id,
            specification_id=identifier,
            exterior_vlr_pct=Measurement(
                vlr, "%", EvidenceTier.FIELD_STUDY, identifier, lower, upper
            ),
        ),
        source_kind="manufacturer_assembly_spec",
        source_id=identifier,
        incidence_angle_deg=angle,
    )


def test_registry_round_trip_and_synthetic_gate(registry):
    pane = registry.get("SYNTHETIC-A")
    restored = PaneRegistry.from_dict(json.loads(json.dumps(registry.as_dict())))
    assert restored.require(pane.identity) == pane
    assert pane.registration_error_m == 0.03
    assert pane.to_rect_patch().id == pane.identity.pane_id
    with pytest.raises(ValueError, match="no field verification"):
        restored.require(pane.identity, field_verified=True)
    with pytest.raises(ValueError, match="mismatched pane identity"):
        restored.require(replace(pane.identity, model_version="another-version"))
    with pytest.raises(ValueError, match="Duplicate physical pane locator"):
        PaneRegistry((pane, replace(pane, identity=replace(pane.identity, pane_id="duplicate"))))


def test_impact_uncertainty_and_independent_evidence(registry):
    a, b, control = (registry.get(pane_id) for pane_id in ("SYNTHETIC-A", "SYNTHETIC-B", "SYNTHETIC-C"))
    registry = PaneRegistry((a, b, control))
    loc = ImpactLocation("anonymous-001", "microzone", "SYNTHETIC-ZONE")
    assert registry.validate_impact(loc).pane_ids == ()
    candidates = ("SYNTHETIC-B", "SYNTHETIC-A")
    candidate = replace(loc, precision="candidate_panes", pane_ids=candidates)
    assert registry.validate_impact(candidate).pane_ids == candidates
    with pytest.raises(ValueError, match="separate impact evidence"):
        replace(candidate, precision="verified_pane", pane_ids=("SYNTHETIC-A",))
    with pytest.raises(ValueError, match="no field verification"):
        registry.validate_impact(ImpactLocation(
            "anonymous-002", "verified_pane", pane_ids=(control.identity.pane_id,),
            impact_source_id="anonymous-photo-002",
        ))


def test_verified_registration_requires_current_index_and_valid_metric_geometry(registry):
    pane = registry.get("SYNTHETIC-A")
    with pytest.raises(ValueError, match="referenced measured geometry and photos"):
        replace(pane, photos=())
    with pytest.raises(ValueError, match="nonzero ordered area"):
        replace(pane, corners_m=tuple(pane.corners_m[index] for index in (0, 2, 1, 3)))
    with pytest.raises(ValueError, match="nonplanar"):
        replace(pane, corners_m=(*pane.corners_m[:3], (1, 0, 3)))


def test_pane_glass_rejects_same_facade_photo_cross_join(registry):
    a, b = registry.get("SYNTHETIC-A"), registry.get("SYNTHETIC-B")
    field_registry = PaneRegistry((a, b))
    evidence = field_view(a)
    panel = evidence.to_glass_panel(field_registry)
    assert panel.panel_id == a.identity.pane_id
    assert panel.appearance == GlassAppearance.REFLECTIVE_AND_TRANSPARENT
    assert evidence.as_dict()["observed_at"] == AT.isoformat()
    with pytest.raises(ValueError, match="Photo does not belong"):
        replace(evidence, identity=b.identity).to_glass_panel(field_registry)
    with pytest.raises(ValueError, match="Photo postdates"):
        field_registry.validate_glass(replace(evidence, observed_at=AT.replace(hour=8)))


def test_comparable_specs_are_audited_without_mixing_neighbors_or_incidence_angles(registry):
    a, b = registry.get("SYNTHETIC-A"), registry.get("SYNTHETIC-B")
    rows = [
        assembly_spec(a, "nearest-match", 20, uncertainty=(15, 25)),
        assembly_spec(a, "conflicting-spec", 40),
        assembly_spec(a, "different-angle", 70, angle=50),
        assembly_spec(b, "neighbor", 60),
    ]
    assert audit_glass_evidence(registry, reversed(rows)) == [{
        **a.identity.as_dict(),
        "field": "exterior_vlr_pct",
        "evidence_ids": ["record-conflicting-spec", "record-nearest-match"],
        "source_ids": ["conflicting-spec", "nearest-match"],
    }]
    with pytest.raises(ValueError, match="incidence_angle_deg"):
        replace(rows[0], incidence_angle_deg=None)
    with pytest.raises(ValueError, match="Duplicate glass evidence_id"):
        audit_glass_evidence(registry, [rows[0], rows[0]])


def test_clip_review_retains_same_view_provenance(registry):
    pane = registry.get("SYNTHETIC-A")
    original = field_view(pane)
    clip = replace(original, evidence_id="clip-001", source_kind="clip_screen", observation=replace(
        original.observation, visual_class="reflective", visual_class_evidence_tier=EvidenceTier.PROXY,
    ))
    corrected = replace(
        original, reviewed_from_evidence_id=clip.evidence_id,
        observation=replace(original.observation, reviewed_by_human=True),
    )
    assert not clip.as_dict()["observation"]["visual_class_confirmed"]
    assert audit_glass_evidence(registry, [clip, corrected]) == []
    with pytest.raises(ValueError, match="CLIP correction lineage"):
        audit_glass_evidence(registry, [clip, replace(corrected, view_id="other-view")])
    with pytest.raises(ValueError, match="CLIP evidence requires human review"):
        clip.to_glass_panel(PaneRegistry((pane,)))
    with pytest.raises(ValueError, match="Invalid CLIP correction lineage"):
        audit_glass_evidence(registry, [corrected])


def test_spectral_fractions_and_geometry_are_distinct_evidence(registry):
    pane = registry.get("SYNTHETIC-A")
    optical = assembly_spec(pane, "synthetic-spec", 20)
    measure = Measurement(0.3, "fraction", EvidenceTier.MEASURED, "spectrum-example")
    sample = SpectralObservation(530, reflectance=measure)
    assert replace(optical, spectrum=(sample,)).as_dict()["spectrum"][0]["wavelength_nm"] == 530
    with pytest.raises(ValueError, match="sum above one"):
        SpectralObservation(530, reflectance=measure, transmittance=replace(measure, value=0.8))
    geometry = field_view(pane).model_approach_view(
        registry, coordinate_system=pane.coordinate_system, latitude_deg=22, longitude_deg=113,
        viewer_m=(-3, 1, 2), heading_mps=(1, 0, 0),
        reflection_source_m=(-3, 1, 2), transmission_source_m=(3, 1, 2),
    )
    assert geometry["status"] == "geometric_model"
    assert geometry["dataset_kind"] == "synthetic"
    assert geometry["reflection"]["status"] == geometry["transmission"]["status"] == "geometrically_possible"
    assert json.loads(json.dumps(geometry))["solar_alignment"]["pane_id"] == pane.identity.pane_id
