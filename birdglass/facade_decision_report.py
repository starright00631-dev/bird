"""Combine glass, vegetation, model output and retrofit recommendations."""
from __future__ import annotations

from typing import Optional

from birdglass.glass_observation import GlassObservation
from birdglass.retrofit_decision import recommend_interventions
from birdglass.vegetation_exposure import VegetationExposure


def build_facade_decision_report(
    glass: GlassObservation,
    vegetation: VegetationExposure,
    *,
    predicted_detected_carcass_probability_24h: Optional[float] = None,
    model_name: Optional[str] = None,
    model_scope: Optional[str] = None,
    night_lighting_problem_confirmed: bool = False,
) -> dict:
    """Produce a joined, evidence-aware façade report without conflating endpoints."""
    glass.validate()
    vegetation.validate()
    if predicted_detected_carcass_probability_24h is not None:
        if not 0 <= predicted_detected_carcass_probability_24h <= 1:
            raise ValueError("predicted probability must be in [0,1]")
        if not model_name or not model_scope:
            raise ValueError("model_name and model_scope are required with a prediction")
    recommendations = recommend_interventions(
        glass, vegetation,
        night_lighting_problem_confirmed=night_lighting_problem_confirmed,
    )
    if predicted_detected_carcass_probability_24h is None:
        risk_prediction = {
            "status": "not_provided",
            "value": None,
            "endpoint": "detected carcass presence",
            "warning": "No trained site-relevant model prediction supplied.",
        }
    else:
        risk_prediction = {
            "status": "provided",
            "value": float(predicted_detected_carcass_probability_24h),
            "endpoint": "predicted detected-carcass probability over a 24-hour survey interval",
            "model_name": model_name,
            "model_scope": model_scope,
            "warning": "This is not true collision probability or detection-corrected mortality.",
        }
    return {
        "facade_id": glass.facade_id,
        "glass": glass.to_dict(),
        "vegetation": vegetation.summary(),
        "risk_prediction": risk_prediction,
        "retrofit_decision": recommendations,
        "decision_limitations": [
            "Glass appearance class does not replace measured optical properties.",
            "Vegetation cover is not a direct measure of bird approach frequency.",
            "Intervention recommendations are evidence-tiered; no unverified efficacy percentage is generated.",
            "BNBU absolute risk requires local survey effort, detection information and validation.",
        ],
    }
