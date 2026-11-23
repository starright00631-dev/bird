import csv
from pathlib import Path

import pytest

from birdglass.evidence import EvidenceTier, Measurement
from birdglass.facade_decision_report import (
    ValidatedRiskPrediction,
    build_facade_decision_report,
)
from birdglass.glass_observation import GlassObservation
from birdglass.vegetation_observation import VegetationObservation


def m(value, unit, tier=EvidenceTier.MEASURED, source="local-record"):
    return Measurement(value, unit, tier, source_id=source)


def make_glass(facade_id="B1::F1"):
    return GlassObservation(
        facade_id=facade_id,
        visual_class="reflective",
        visual_class_evidence_tier=EvidenceTier.LOCAL_SURVEY,
        visual_class_source_id="inspection-001",
        reviewed_by_human=True,
        exterior_vlr_pct=m(22, "percent"),
    )


def make_vegetation(facade_id="B1::F1"):
    return VegetationObservation(
        facade_id=facade_id,
        cover_pct_by_band={"0_5m": m(35, "percent", EvidenceTier.REMOTE_SENSING)},
        facade_tree_cover_50m_percent=m(42, "percent", EvidenceTier.REMOTE_SENSING),
        stories_reflecting_canopy=m(2.5, "stories", EvidenceTier.FIELD_STUDY),
    )


def test_report_uses_canonical_decision_engine_and_no_unvalidated_probability():
    report = build_facade_decision_report(make_glass(), make_vegetation())
    assert report["facade_id"] == "B1::F1"
    assert report["risk_prediction"]["status"] == "not_site_calibrated"
    assert report["risk_prediction"]["value"] is None
    assert report["risk_profile"]["absolute_collision_probability"] is None
    assert report["intervention_comparison"]["effectiveness_ranked"] is False
    marker = next(x for x in report["recommendations"] if x["action"] == "retrofit_full_pane_exterior_visual_markers")
    assert "OTTAWA_TREATMENT_2026" in marker["evidence_source_ids"]
    assert "OKLAHOMA_MARKER_BACI" in marker["evidence_source_ids"]
    candidate = next(x for x in report["intervention_comparison"]["candidates"] if x["action"] == "full_pane_exterior_visual_markers")
    assert candidate["site_effect_estimate"] is None


def test_report_requires_glass_and_vegetation_facade_ids_to_match():
    with pytest.raises(ValueError, match="same facade_id"):
        build_facade_decision_report(make_glass("B1::F1"), make_vegetation("B1::F2"))


def test_bare_probability_is_not_a_validated_prediction():
    with pytest.raises(TypeError):
        build_facade_decision_report(make_glass(), make_vegetation(), prediction=0.2)


def test_prediction_requires_site_calibration_and_heldout_validation():
    with pytest.raises(ValueError, match="Only site_calibrated"):
        ValidatedRiskPrediction(
            value=0.2, endpoint="detected_carcass_presence",
            exposure_definition="24h survey interval", model_name="UBC GLMM",
            model_artifact_sha256="a" * 64, training_data_source="UBC",
            target_site="BNBU", calibration_status="external_descriptive_only",
            validation_design="held_out_building", validation_report_id="report-1",
        )


def test_validated_prediction_requires_bnbu_target_and_artifact_hash():
    with pytest.raises(ValueError, match="target_site must be BNBU"):
        ValidatedRiskPrediction(
            value=0.2, endpoint="detected_carcass_presence",
            exposure_definition="24h survey interval", model_name="BNBU model",
            model_artifact_sha256="a" * 64, training_data_source="BNBU",
            target_site="UBC", calibration_status="site_calibrated",
            validation_design="held_out_building", validation_report_id="report-1",
        )
    with pytest.raises(ValueError, match="SHA-256"):
        ValidatedRiskPrediction(
            value=0.2, endpoint="detected_carcass_presence",
            exposure_definition="24h survey interval", model_name="BNBU model",
            model_artifact_sha256="bad", training_data_source="BNBU",
            target_site="BNBU", calibration_status="site_calibrated",
            validation_design="held_out_building", validation_report_id="report-1",
        )


def test_intervention_evidence_ids_resolve_in_machine_readable_registry():
    path = Path(__file__).parents[1] / "data" / "reference" / "intervention_evidence.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        source_ids = {row["source_id"] for row in csv.DictReader(handle)}
    report = build_facade_decision_report(make_glass(), make_vegetation())
    for item in report["recommendations"]:
        assert set(item["evidence_source_ids"]).issubset(source_ids)


def test_claimed_bnbu_prediction_is_withheld_without_verified_artifacts():
    prediction = ValidatedRiskPrediction(
        value=0.12,
        endpoint="detected_carcass_presence",
        exposure_definition="24-hour standardized façade survey",
        model_name="BNBU-seasonal-GLMM",
        model_artifact_sha256="b" * 64,
        training_data_source="BNBU-local-panel-v1",
        target_site="BNBU",
        calibration_status="site_calibrated",
        validation_design="held_out_building",
        validation_report_id="BNBU-VALIDATION-REPORT-001",
    )
    report = build_facade_decision_report(make_glass(), make_vegetation(), prediction=prediction)
    assert report["risk_prediction"]["status"] == "validation_artifact_unverified"
    assert report["risk_prediction"]["value"] is None
    assert report["risk_prediction"]["endpoint"] == "detected_carcass_presence"
    assert report["risk_prediction"]["model_artifact_sha256"] == "b" * 64
