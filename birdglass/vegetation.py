"""Multi-scale vegetation features with separate ecological pathways.

Vegetation is not assigned one universal positive/negative coefficient.
Local canopy, landscape green cover, reflected habitat, attraction and route
obstruction are retained as distinct measurements.
"""
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .evidence import Measurement, measurement_dict

VEGETATION_BUFFERS = (
    "0_5m",
    "5_25m",
    "25_100m",
    "100m_1km",
    "1_10km",
)


def _check_range(measurement: Measurement | None, unit: str,
                 lower: float, upper: float, label: str) -> None:
    if measurement is None or measurement.value is None:
        return
    accepted = {unit, unit.replace("_", " ")}
    if unit == "percent":
        accepted.add("%")
    if measurement.unit not in accepted:
        raise ValueError(f"{label} must use {unit}")
    if not lower <= measurement.value <= upper:
        raise ValueError(f"{label} must lie in [{lower}, {upper}]")


@dataclass(frozen=True)
class VegetationProfile:
    """Vegetation measurements around one glass panel.

    cover_pct keys are fixed, non-overlapping annular bands. Use the same
    land-cover definition, season and raster resolution across bands.
    """

    cover_pct: Mapping[str, Measurement] = field(default_factory=dict)
    nearest_crown_distance_m: Measurement | None = None
    canopy_height_m: Measurement | None = None
    pane_sill_height_m: Measurement | None = None
    reflected_vegetation_share: Measurement | None = None
    canopy_overlap_share: Measurement | None = None
    corridor_obstruction_share: Measurement | None = None
    resource_attraction_note: str | None = None
    facade_porous_cover_50m_percent: Measurement | None = None
    facade_tree_cover_50m_percent: Measurement | None = None
    stories_reflecting_canopy: Measurement | None = None
    building_vegetation_proportion: Measurement | None = None

    def __post_init__(self) -> None:
        unknown = set(self.cover_pct) - set(VEGETATION_BUFFERS)
        if unknown:
            raise ValueError(f"Unsupported vegetation buffers: {sorted(unknown)}")
        for buffer_name, measurement in self.cover_pct.items():
            _check_range(measurement, "percent", 0.0, 100.0,
                         f"cover_pct[{buffer_name}]")
        _check_range(self.reflected_vegetation_share, "fraction", 0.0, 1.0,
                     "reflected_vegetation_share")
        _check_range(self.canopy_overlap_share, "fraction", 0.0, 1.0,
                     "canopy_overlap_share")
        _check_range(self.corridor_obstruction_share, "fraction", 0.0, 1.0,
                     "corridor_obstruction_share")
        _check_range(self.nearest_crown_distance_m, "m", 0.0, 100000.0,
                     "nearest_crown_distance_m")
        _check_range(self.canopy_height_m, "m", 0.0, 200.0, "canopy_height_m")
        _check_range(self.pane_sill_height_m, "m", 0.0, 1000.0,
                     "pane_sill_height_m")
        _check_range(self.facade_porous_cover_50m_percent, "percent", 0.0, 100.0,
                     "facade_porous_cover_50m_percent")
        _check_range(self.facade_tree_cover_50m_percent, "percent", 0.0, 100.0,
                     "facade_tree_cover_50m_percent")
        _check_range(self.stories_reflecting_canopy, "stories", 0.0, 100.0,
                     "stories_reflecting_canopy")
        _check_range(self.building_vegetation_proportion, "fraction", 0.0, 1.0,
                     "building_vegetation_proportion")

    def as_dict(self) -> dict:
        return {
            "cover_pct_by_buffer": {
                key: measurement_dict(self.cover_pct.get(key))
                for key in VEGETATION_BUFFERS
            },
            "nearest_crown_distance_m": measurement_dict(
                self.nearest_crown_distance_m),
            "canopy_height_m": measurement_dict(self.canopy_height_m),
            "pane_sill_height_m": measurement_dict(self.pane_sill_height_m),
            "reflected_vegetation_share": measurement_dict(
                self.reflected_vegetation_share),
            "canopy_overlap_share": measurement_dict(self.canopy_overlap_share),
            "corridor_obstruction_share": measurement_dict(
                self.corridor_obstruction_share),
            "resource_attraction_note": self.resource_attraction_note,
        }


def vegetation_pathways(profile: VegetationProfile) -> dict:
    """Return separate pathway inputs; deliberately do not sum them."""

    return {
        "local_structure": {
            key: measurement_dict(profile.cover_pct.get(key))
            for key in ("0_5m", "5_25m", "25_100m")
        },
        "landscape_structure": {
            key: measurement_dict(profile.cover_pct.get(key))
            for key in ("100m_1km", "1_10km")
        },
        "attraction": {
            "resource_note": profile.resource_attraction_note,
            "interpretation": (
                "Requires bird activity or resource-use evidence; canopy "
                "cover alone is not a bird-abundance measurement."
            ),
        },
        "flight_routing": {
            "nearest_crown_distance_m": measurement_dict(
                profile.nearest_crown_distance_m),
            "canopy_height_m": measurement_dict(profile.canopy_height_m),
            "pane_sill_height_m": measurement_dict(profile.pane_sill_height_m),
            "canopy_overlap_share": measurement_dict(profile.canopy_overlap_share),
            "corridor_obstruction_share": measurement_dict(
                profile.corridor_obstruction_share),
        },
        "facade_specific_50m_buffer": {
            "porous_and_ground_shrub_cover_percent": measurement_dict(
                profile.facade_porous_cover_50m_percent),
            "tree_canopy_cover_percent": measurement_dict(
                profile.facade_tree_cover_50m_percent),
            "interpretation": "Façade-specific 50-m buffer variables; do not substitute building-level vegetation proportion.",
        },
        "vertical_reflection_context": {
            "stories_reflecting_canopy": measurement_dict(profile.stories_reflecting_canopy),
            "interpretation": "Potential vertical reflection exposure only; not proof that canopy is visible in the pane from a bird approach view.",
        },
        "building_level_context": {
            "vegetation_proportion": measurement_dict(profile.building_vegetation_proportion),
            "interpretation": "Building-level vegetation proportion; not interchangeable with façade-level 50-m cover or the five annular bands.",
        },
        "optical_scene": {
            "reflected_vegetation_share": measurement_dict(
                profile.reflected_vegetation_share),
            "interpretation": (
                "A measured vegetation reflection supports the optical-scene "
                "pathway; it does not by itself estimate collision incidence."
            ),
        },
        "no_single_vegetation_score": True,
    }


def relative_cover_band(value_pct: float,
                        regional_reference_pct: Iterable[float]) -> str:
    """Classify cover against a regional sample, never against a universal cut.

    At least six reference observations are required. The returned terciles
    are descriptive ranks within the supplied region/season/resolution only.
    """

    refs = sorted(float(x) for x in regional_reference_pct)
    if len(refs) < 6:
        return "insufficient_reference"
    if not 0.0 <= value_pct <= 100.0:
        raise ValueError("value_pct must lie in [0, 100]")
    if any(not 0.0 <= x <= 100.0 for x in refs):
        raise ValueError("reference cover values must lie in [0, 100]")

    def quantile(q: float) -> float:
        position = (len(refs) - 1) * q
        lo = int(position)
        hi = min(lo + 1, len(refs) - 1)
        weight = position - lo
        return refs[lo] * (1.0 - weight) + refs[hi] * weight

    q33, q67 = quantile(1.0 / 3.0), quantile(2.0 / 3.0)
    if value_pct <= q33:
        return "low_relative"
    if value_pct <= q67:
        return "middle_relative"
    return "high_relative"
