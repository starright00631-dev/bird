"""Evidence-preserving vegetation intake adapter to the canonical five-band profile."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .evidence import Measurement, measurement_dict
from .vegetation import VEGETATION_BUFFERS, VegetationProfile, vegetation_pathways


def _check(value: Measurement | None, units: set[str], lower: float, upper: float, label: str) -> None:
    if value is None or value.value is None:
        return
    if value.unit not in units:
        raise ValueError(f"{label} must use one of {sorted(units)}")
    if not lower <= value.value <= upper:
        raise ValueError(f"{label} must lie in [{lower}, {upper}]")
    if not value.source_id or not value.source_id.strip():
        raise ValueError(f"{label} requires source_id")


@dataclass(frozen=True)
class VegetationObservation:
    """Measurements for one façade; cover bands are non-overlapping annuli.

    Cumulative buffers (e.g. 0-25 m and 0-100 m) must not be supplied as if
    they were annular bands. Convert them using area-weighted ring differences
    only when the valid clipped area for each cumulative buffer is known.
    """

    facade_id: str
    cover_pct_by_band: Mapping[str, Measurement] = field(default_factory=dict)
    facade_porous_cover_50m_percent: Measurement | None = None
    facade_tree_cover_50m_percent: Measurement | None = None
    stories_reflecting_canopy: Measurement | None = None
    building_vegetation_proportion: Measurement | None = None
    nearest_crown_distance_m: Measurement | None = None
    canopy_height_m: Measurement | None = None
    pane_sill_height_m: Measurement | None = None
    reflected_vegetation_share: Measurement | None = None
    canopy_overlap_share: Measurement | None = None
    corridor_obstruction_share: Measurement | None = None
    resource_attraction_note: str | None = None
    observation_date: str | None = None
    source_image_id: str | None = None
    source_id: str | None = None

    def validate(self) -> "VegetationObservation":
        if not self.facade_id.strip():
            raise ValueError("facade_id is required")
        unknown = set(self.cover_pct_by_band) - set(VEGETATION_BUFFERS)
        if unknown:
            raise ValueError(f"Unsupported annular vegetation bands: {sorted(unknown)}")
        for band, value in self.cover_pct_by_band.items():
            _check(value, {"percent", "%"}, 0, 100, f"cover_pct_by_band[{band}]")
        _check(self.facade_porous_cover_50m_percent, {"percent", "%"}, 0, 100, "facade_porous_cover_50m_percent")
        _check(self.facade_tree_cover_50m_percent, {"percent", "%"}, 0, 100, "facade_tree_cover_50m_percent")
        _check(self.stories_reflecting_canopy, {"stories"}, 0, 100, "stories_reflecting_canopy")
        _check(self.building_vegetation_proportion, {"fraction"}, 0, 1, "building_vegetation_proportion")
        _check(self.nearest_crown_distance_m, {"m"}, 0, 100000, "nearest_crown_distance_m")
        _check(self.canopy_height_m, {"m"}, 0, 200, "canopy_height_m")
        _check(self.pane_sill_height_m, {"m"}, 0, 1000, "pane_sill_height_m")
        _check(self.reflected_vegetation_share, {"fraction"}, 0, 1, "reflected_vegetation_share")
        _check(self.canopy_overlap_share, {"fraction"}, 0, 1, "canopy_overlap_share")
        _check(self.corridor_obstruction_share, {"fraction"}, 0, 1, "corridor_obstruction_share")
        return self

    def to_profile(self) -> VegetationProfile:
        self.validate()
        return VegetationProfile(
            cover_pct=dict(self.cover_pct_by_band),
            nearest_crown_distance_m=self.nearest_crown_distance_m,
            canopy_height_m=self.canopy_height_m,
            pane_sill_height_m=self.pane_sill_height_m,
            reflected_vegetation_share=self.reflected_vegetation_share,
            canopy_overlap_share=self.canopy_overlap_share,
            corridor_obstruction_share=self.corridor_obstruction_share,
            resource_attraction_note=self.resource_attraction_note,
            facade_porous_cover_50m_percent=self.facade_porous_cover_50m_percent,
            facade_tree_cover_50m_percent=self.facade_tree_cover_50m_percent,
            stories_reflecting_canopy=self.stories_reflecting_canopy,
            building_vegetation_proportion=self.building_vegetation_proportion,
        )

    def as_dict(self) -> dict:
        self.validate()
        profile = self.to_profile()
        return {
            "facade_id": self.facade_id,
            "cover_pct_by_band": {
                band: measurement_dict(self.cover_pct_by_band.get(band))
                for band in VEGETATION_BUFFERS
            },
            "facade_porous_cover_50m_percent": measurement_dict(self.facade_porous_cover_50m_percent),
            "facade_tree_cover_50m_percent": measurement_dict(self.facade_tree_cover_50m_percent),
            "stories_reflecting_canopy": measurement_dict(self.stories_reflecting_canopy),
            "building_vegetation_proportion": measurement_dict(self.building_vegetation_proportion),
            "source_image_id": self.source_image_id,
            "source_id": self.source_id,
            "observation_date": self.observation_date,
            "pathways": vegetation_pathways(profile),
            "interpretation": (
                "Vegetation cover is context, not a signed collision-risk score. "
                "Stories reflecting canopy is a potential vertical reflection context, "
                "not proof that canopy is visible in the pane."
            ),
        }
