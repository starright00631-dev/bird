"""Join field observations to the canonical mechanism and decision engine."""
from __future__ import annotations

import re
import math
from dataclasses import dataclass

from .decision import ApproachSample, FacadeContext, evaluate_facade
from .evidence import EvidenceTier, Measurement
from .glass_observation import GlassObservation
from .vegetation_observation import VegetationObservation

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VALIDATION_DESIGNS = {"held_out_facade", "held_out_building", "held_out_time", "external_site"}


@dataclass(frozen=True)
class ValidatedRiskPrediction:
    """A site-calibrated prediction record; a bare float is never accepted."""

    value: float
    endpoint: str
    exposure_definition: str
    model_name: str
    model_artifact_sha256: str
    training_data_source: str
    target_site: str
    calibration_status: str
    validation_design: str
    validation_report_id: str

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise ValueError("prediction value must be numeric")
        if not math.isfinite(float(self.value)) or not 0 <= self.value <= 1:
            raise ValueError("prediction value must be finite and in [0,1]")
        if self.endpoint not in {"detected_carcass_presence", "glass_contact_given_approach"}:
            raise ValueError("unsupported prediction endpoint")
        if not self.exposure_definition.strip():
            raise ValueError("exposure_definition is required")
        if not self.model_name.strip() or not SHA256_RE.fullmatch(self.model_artifact_sha256 or ""):
            raise ValueError("model_name and a 64-character model artifact SHA-256 are required")
        if not self.training_data_source.strip() or not self.target_site.strip():
            raise ValueError("training_data_source and target_site are required")
        if self.target_site.strip().upper() != "BNBU":
            raise ValueError("target_site must be BNBU for this project")
        if self.calibration_status != "site_calibrated":
            raise ValueError("Only site_calibrated predictions can be displayed")
        if self.validation_design not in VALIDATION_DESIGNS:
            raise ValueError("prediction requires a recognized held-out validation design")
        if not self.validation_report_id.strip():
            raise ValueError("validation_report_id is required")


EVIDENCE_BY_ACTION = {
    "retrofit_full_pane_exterior_visual_markers": [
        "ECCC_GLASS_GUIDANCE", "ABC_2025_RATING",
        "OTTAWA_TREATMENT_2026", "OKLAHOMA_MARKER_BACI",
    ],
    "full_pane_exterior_visual_markers": [
        "ECCC_GLASS_GUIDANCE", "ABC_2025_RATING",
        "OTTAWA_TREATMENT_2026", "OKLAHOMA_MARKER_BACI",
    ],
    "maintain_and_audit_exterior_2x2_pattern": ["ECCC_GLASS_GUIDANCE", "ABC_2025_RATING"],
    "consider_upgrade_from_2x4_to_2x2": ["ECCC_GLASS_GUIDANCE", "ABC_2025_RATING"],
    "consider_upgrade_to_2x2_pattern": ["ECCC_GLASS_GUIDANCE", "ABC_2025_RATING"],
    "consider_external_screen_or_cord_system": ["KLEM2013"],
    "external_screen_or_cord_system": ["KLEM2013"],
    "external_shading_or_solar_screen": ["UBC_ZULIAN_2023", "CHINA_BUILDINGS"],
    "audit_reflection_by_solar_time_and_approach_view": ["UBC_ZULIAN_2023", "CHINA_BUILDINGS"],
    "seasonal_night_lighting_controls": ["CHINA_BUILDINGS", "VAN_DOREN_2021"],
    "vegetation_reconfiguration": ["CHINA_BUILDINGS", "UBC_ZULIAN_2023"],
    "retain_vegetation_as_a_multiscale_context_variable": ["CHINA_BUILDINGS", "UBC_ZULIAN_2023"],
    "uv_only_pattern": ["UV_FILM_2020", "FILM_POSITION_2023"],
    "evaluate_uv_pattern_only_after_spectral_and_species_checks": ["UV_FILM_2020", "FILM_POSITION_2023"],
    "measure_first_surface_reflection_and_marker_contrast": ["ABC_2025_RATING"],
    "establish_standardized_pane_approach_monitoring": ["UBC_ZULIAN_2023", "UBC_DEGROOT_2021"],
}


def _attach_evidence(items: list[dict]) -> list[dict]:
    output = []
    for item in items:
        row = dict(item)
        source_ids = EVIDENCE_BY_ACTION.get(row.get("action"), [])
        row["evidence_source_ids"] = source_ids
        row["evidence_scope"] = (
            "published mechanism/design context; not a BNBU treatment effect"
            if source_ids else "no source mapping; evidence review required"
        )
        output.append(row)
    return output


def build_facade_decision_report(
    glass: GlassObservation,
    vegetation: VegetationObservation,
    *,
    bird_activity: Measurement | None = None,
    approaches_per_hour: Measurement | None = None,
    approach_sample: ApproachSample | None = None,
    nocturnal_migrant_activity: Measurement | None = None,
    artificial_light_level: Measurement | None = None,
    prediction: ValidatedRiskPrediction | None = None,
) -> dict:
    glass.validate()
    vegetation.validate()
    if glass.facade_id != vegetation.facade_id:
        raise ValueError("Glass and vegetation observations must use the same facade_id")
    canonical_glass = glass.to_glass_panel()
    canonical_vegetation = vegetation.to_profile()
    decision = evaluate_facade(FacadeContext(
        glass=canonical_glass,
        vegetation=canonical_vegetation,
        bird_activity=bird_activity,
        approaches_per_hour=approaches_per_hour,
        approach_sample=approach_sample,
        nocturnal_migrant_activity=nocturnal_migrant_activity,
        artificial_light_level=artificial_light_level,
    ))
    if prediction is None:
        risk_prediction = {
            "status": "not_site_calibrated",
            "value": None,
            "reason": "No BNBU-calibrated model with a pinned artifact and held-out validation report was supplied.",
            "external_benchmark": "UBC Zulian 2023 seasonal GLMM is descriptive only; held-out-building performance did not demonstrate improvement over the exposure-only baseline.",
        }
    else:
        risk_prediction = {
            "status": "site_calibrated",
            "value": prediction.value,
            "endpoint": prediction.endpoint,
            "exposure_definition": prediction.exposure_definition,
            "model_name": prediction.model_name,
            "model_artifact_sha256": prediction.model_artifact_sha256,
            "training_data_source": prediction.training_data_source,
            "target_site": prediction.target_site,
            "calibration_status": prediction.calibration_status,
            "validation_design": prediction.validation_design,
            "validation_report_id": prediction.validation_report_id,
            "warning": "A predicted endpoint is not interchangeable with another endpoint or exposure interval.",
        }

    return {
        "facade_id": glass.facade_id,
        "glass_observation": glass.as_dict(),
        "vegetation_observation": vegetation.as_dict(),
        "risk_prediction": risk_prediction,
        "risk_profile": decision["risk_profile"],
        "glass_assessment": decision["glass_assessment"],
        "vegetation_pathways": decision["vegetation_pathways"],
        "findings": decision["findings"],
        "data_gaps": decision["data_gaps"],
        "recommendations": _attach_evidence(decision["recommendations"]),
        "intervention_comparison": {
            **decision["intervention_comparison"],
            "candidates": _attach_evidence(decision["intervention_comparison"]["candidates"]),
        },
        "decision_rule": (
            "Mechanism and evidence fit first. Do not rank efficacy or report a "
            "BNBU probability until comparable local approach denominators, "
            "detection/persistence correction and held-out validation exist."
        ),
    }
