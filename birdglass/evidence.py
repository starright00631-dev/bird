"""Typed evidence values used by the evidence-aware decision system.

A value is never silently promoted from a literature prior or proxy to a
local measurement. Missing values remain missing; they are not zeroes.
"""
from dataclasses import dataclass
from enum import Enum
from math import isfinite


class EvidenceTier(str, Enum):
    MEASURED = "measured"
    LOCAL_SURVEY = "local_survey"
    FIELD_STUDY = "field_study"
    CONTROLLED_EXPERIMENT = "controlled_experiment"
    OBSERVATIONAL = "observational"
    REMOTE_SENSING = "remote_sensing"
    PROXY = "proxy"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Measurement:
    """A numeric value with units, provenance tier and optional uncertainty."""

    value: float | None
    unit: str
    tier: EvidenceTier = EvidenceTier.UNKNOWN
    source_id: str | None = None
    lower: float | None = None
    upper: float | None = None

    def __post_init__(self) -> None:
        if not self.unit or not self.unit.strip():
            raise ValueError("Measurement unit is required")
        if not isinstance(self.tier, EvidenceTier):
            raise ValueError("tier must be an EvidenceTier")
        for name in ("value", "lower", "upper"):
            number = getattr(self, name)
            if number is not None and not isfinite(float(number)):
                raise ValueError(f"{name} must be finite or None")
        if self.lower is not None and self.upper is not None:
            if self.lower > self.upper:
                raise ValueError("lower bound cannot exceed upper bound")
        if self.value is not None:
            if self.lower is not None and self.value < self.lower:
                raise ValueError("value is below its lower bound")
            if self.upper is not None and self.value > self.upper:
                raise ValueError("value is above its upper bound")

    @property
    def available(self) -> bool:
        return self.value is not None


def measurement_dict(measurement: Measurement | None) -> dict | None:
    if measurement is None:
        return None
    return {
        "value": measurement.value,
        "unit": measurement.unit,
        "evidence_tier": measurement.tier.value,
        "source_id": measurement.source_id,
        "lower": measurement.lower,
        "upper": measurement.upper,
    }
