"""Evidence-preserving vegetation intake adapter to the canonical five-band profile."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping

from .evidence import EvidenceTier, Measurement, measurement_dict
from .vegetation import VEGETATION_BUFFERS, VegetationProfile, vegetation_pathways




CUMULATIVE_BUFFER_KEYS = ("0_5m", "0_25m", "0_100m", "0_1km", "0_10km")


def cumulative_cover_to_annular(
    cumulative_cover_pct: Mapping[str, float],
    valid_area_m2: Mapping[str, float],
    *,
    source_ids: Mapping[str, str],
    evidence_tier: EvidenceTier,
) -> dict[str, Measurement]:
    """Convert cumulative cover percentages to disjoint annular percentages.

    The valid clipped area of each cumulative buffer is required. This uses
    area-weighted covered-area differences; it must not assume ideal circular
    areas when campus boundaries or no-data masks clip the buffers.
    """
    missing_cover = set(CUMULATIVE_BUFFER_KEYS) - set(cumulative_cover_pct)
    missing_area = set(CUMULATIVE_BUFFER_KEYS) - set(valid_area_m2)
    missing_source = set(CUMULATIVE_BUFFER_KEYS) - set(source_ids)
    if missing_cover or missing_area or missing_source:
        raise ValueError(
            "Cumulative conversion requires all five cover, valid-area and source keys; "
            f"missing cover={sorted(missing_cover)}, area={sorted(missing_area)}, "
            f"source={sorted(missing_source)}"
        )
    if not isinstance(evidence_tier, EvidenceTier):
        raise ValueError("evidence_tier must be an EvidenceTier")

    covered_area = {}
    valid_area = {}
    for key in CUMULATIVE_BUFFER_KEYS:
        pct = float(cumulative_cover_pct[key])
        area = float(valid_area_m2[key])
        source_id = source_ids[key]
        if not math.isfinite(pct) or not 0 <= pct <= 100:
            raise ValueError(f"Cumulative cover for {key} must be finite and in [0,100]")
        if not math.isfinite(area) or area <= 0:
            raise ValueError(f"Valid clipped area for {key} must be finite and positive")
        if not source_id or not source_id.strip():
            raise ValueError(f"Source ID for {key} is required")
        valid_area[key] = area
        covered_area[key] = area * pct / 100.0

    annular = {}
    for index, (cumulative_key, band) in enumerate(zip(
        CUMULATIVE_BUFFER_KEYS, VEGETATION_BUFFERS
    )):
        if index == 0:
            ring_area = valid_area[cumulative_key]
            ring_covered = covered_area[cumulative_key]
            source_id = source_ids[cumulative_key]
        else:
            previous = CUMULATIVE_BUFFER_KEYS[index - 1]
            ring_area = valid_area[cumulative_key] - valid_area[previous]
            ring_covered = covered_area[cumulative_key] - covered_area[previous]
            source_id = f"{source_ids[previous]}|{source_ids[cumulative_key]}"
        if ring_area <= 0:
            raise ValueError(f"Valid clipped area must increase at cumulative buffer {cumulative_key}")
        tolerance = max(1e-8, ring_area * 1e-10)
        if ring_covered < -tolerance:
            raise ValueError(f"Cumulative covered area decreases at {cumulative_key}")
        pct = 100.0 * max(0.0, ring_covered) / ring_area
        if pct > 100.0 + 1e-8:
            raise ValueError(f"Derived annular cover exceeds 100% at {band}")
        annular[band] = Measurement(
            min(100.0, pct), "percent", evidence_tier, source_id=source_id
        )
    return annular


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
