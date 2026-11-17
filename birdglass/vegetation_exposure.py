"""Multi-scale vegetation exposure schema and reference-relative summaries."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional

ALLOWED_BUFFER_RADII_M = {5, 25, 50, 100, 1000, 10000}


def _pct(value: Optional[float], name: str) -> None:
    if value is not None and not 0 <= float(value) <= 100:
        raise ValueError(f"{name} must be in [0,100]")


@dataclass(frozen=True)
class VegetationBuffer:
    radius_m: int
    tree_canopy_percent: Optional[float] = None
    shrub_percent: Optional[float] = None
    groundcover_percent: Optional[float] = None
    porous_surface_percent: Optional[float] = None
    impervious_percent: Optional[float] = None
    water_percent: Optional[float] = None
    source: str = "unknown"
    resolution_m: Optional[float] = None

    def validate(self) -> "VegetationBuffer":
        if self.radius_m not in ALLOWED_BUFFER_RADII_M:
            raise ValueError(f"Unsupported buffer radius: {self.radius_m}")
        for name in (
            "tree_canopy_percent", "shrub_percent", "groundcover_percent",
            "porous_surface_percent", "impervious_percent", "water_percent",
        ):
            _pct(getattr(self, name), name)
        if self.resolution_m is not None and self.resolution_m <= 0:
            raise ValueError("resolution_m must be positive")
        return self


@dataclass(frozen=True)
class VegetationExposure:
    facade_id: str
    buffers: tuple[VegetationBuffer, ...] = field(default_factory=tuple)
    facade_porous_cover_50m_percent: Optional[float] = None
    facade_tree_cover_50m_percent: Optional[float] = None
    stories_reflecting_canopy: Optional[float] = None
    building_vegetation_proportion_0_1: Optional[float] = None
    observation_date: Optional[str] = None

    def validate(self) -> "VegetationExposure":
        if not self.facade_id.strip():
            raise ValueError("facade_id is required")
        radii = [buffer.radius_m for buffer in self.buffers]
        if len(radii) != len(set(radii)):
            raise ValueError("Vegetation buffer radii must be unique")
        for buffer in self.buffers:
            buffer.validate()
        _pct(self.facade_porous_cover_50m_percent, "facade_porous_cover_50m_percent")
        _pct(self.facade_tree_cover_50m_percent, "facade_tree_cover_50m_percent")
        if self.stories_reflecting_canopy is not None and self.stories_reflecting_canopy < 0:
            raise ValueError("stories_reflecting_canopy cannot be negative")
        if self.building_vegetation_proportion_0_1 is not None:
            if not 0 <= self.building_vegetation_proportion_0_1 <= 1:
                raise ValueError("building_vegetation_proportion_0_1 must be in [0,1]")
        return self

    def summary(self) -> dict:
        self.validate()
        by_radius = {
            str(buffer.radius_m): asdict(buffer)
            for buffer in sorted(self.buffers, key=lambda item: item.radius_m)
        }
        canopy_reflection = bool(
            (self.stories_reflecting_canopy or 0) > 0
            and (self.facade_tree_cover_50m_percent or 0) > 0
        )
        return {
            "facade_id": self.facade_id,
            "buffers": by_radius,
            "facade_porous_cover_50m_percent": self.facade_porous_cover_50m_percent,
            "facade_tree_cover_50m_percent": self.facade_tree_cover_50m_percent,
            "stories_reflecting_canopy": self.stories_reflecting_canopy,
            "building_vegetation_proportion_0_1": self.building_vegetation_proportion_0_1,
            "canopy_reflection_exposure_flag": canopy_reflection,
            "vegetation_management_default": "preserve vegetation; evaluate glass-side mitigation first",
        }


def empirical_percentile(value: float, reference_values: Iterable[float]) -> float:
    """Return empirical percentile rank in [0,100]; no absolute ecological threshold implied."""
    reference = sorted(float(x) for x in reference_values)
    if not reference:
        raise ValueError("reference_values cannot be empty")
    less = sum(x < value for x in reference)
    equal = sum(x == value for x in reference)
    return 100.0 * (less + 0.5 * equal) / len(reference)


def relative_exposure_band(value: float, reference_values: Iterable[float]) -> dict:
    reference = list(reference_values)
    percentile = empirical_percentile(value, reference)
    if percentile < 25:
        band = "lower_quartile_relative_to_reference"
    elif percentile > 75:
        band = "upper_quartile_relative_to_reference"
    else:
        band = "middle_half_relative_to_reference"
    return {
        "value": float(value),
        "reference_percentile": percentile,
        "band": band,
        "absolute_threshold_claimed": False,
    }
