"""Physical pane identity, location precision, and traceable glass evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from itertools import combinations
from math import isclose, isfinite
from typing import Iterable

import numpy as np

from .evidence import EvidenceTier, Measurement, measurement_dict
from .glass_observation import GlassObservation
from .glazing import GlassPanel
from .scene_optics import RectPatch, scene_ray
from .solar import solar_position_enu, specular_reflection_alignment

Point = tuple[float, float, float]


def _required(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{label} must be nonempty text without surrounding whitespace")


def _aware(value: datetime, label: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{label} must be a timezone-aware timestamp")


def _number(value: float, label: str, lower: float, upper: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (
        isfinite(value) and lower <= value <= upper
    ):
        raise ValueError(f"{label} must be finite and in [{lower}, {upper}]")


@dataclass(frozen=True)
class PaneIdentity:
    """Stable pane ID plus the scope in which evidence can be joined."""

    pane_id: str
    building_id: str
    facade_id: str
    model_version: str

    def __post_init__(self) -> None:
        for label, value in asdict(self).items():
            _required(value, label)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PanePhoto:
    photo_id: str
    source_id: str
    captured_at: datetime

    def __post_init__(self) -> None:
        _required(self.photo_id, "photo_id")
        _required(self.source_id, "photo source_id")
        _aware(self.captured_at, "captured_at")

    def as_dict(self) -> dict:
        return {**asdict(self), "captured_at": self.captured_at.isoformat()}


@dataclass(frozen=True)
class PaneRegistration:
    identity: PaneIdentity
    floor: str | None = None
    bay: str | None = None
    microzone_id: str | None = None
    coordinate_system: str | None = None
    corners_m: tuple[Point, ...] = ()
    outward_azimuth_deg: float | None = None
    registration_error_m: float | None = None
    geometry_source_id: str | None = None
    photos: tuple[PanePhoto, ...] = ()
    field_verified_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, PaneIdentity):
            raise ValueError("identity must be a PaneIdentity")
        for name in ("floor", "bay", "microzone_id", "coordinate_system", "geometry_source_id"):
            value = getattr(self, name)
            if value is not None:
                _required(value, name)
        if self.outward_azimuth_deg is not None:
            _number(self.outward_azimuth_deg, "outward_azimuth_deg", 0, 360)
            if self.outward_azimuth_deg == 360:
                raise ValueError("outward_azimuth_deg must be below 360")
        if self.registration_error_m is not None:
            _number(self.registration_error_m, "registration_error_m", 0, float("inf"))
        corners = tuple(tuple(point) for point in self.corners_m)
        object.__setattr__(self, "corners_m", corners)
        if corners:
            self._check_polygon()
        photos = tuple(self.photos)
        if any(not isinstance(photo, PanePhoto) for photo in photos):
            raise ValueError("photos must be PanePhoto records")
        if len({photo.photo_id for photo in photos}) != len(photos):
            raise ValueError("Duplicate photo_id on pane")
        object.__setattr__(self, "photos", photos)
        if self.field_verified_at is not None:
            _aware(self.field_verified_at, "field_verified_at")
            if not all((self.floor, self.bay, self.coordinate_system, corners,
                        self.geometry_source_id, photos)) or (
                self.outward_azimuth_deg is None or self.registration_error_m is None
            ):
                raise ValueError("Field verification requires floor, bay, referenced measured geometry and photos")
            if not any(photo.captured_at <= self.field_verified_at for photo in photos):
                raise ValueError("At least one registration photo must predate or coincide with field verification")

    def _check_polygon(self) -> None:
        if self.coordinate_system is None or self.geometry_source_id is None:
            raise ValueError("Pane corners require coordinate_system and geometry_source_id")
        if len(self.corners_m) < 3 or len(set(self.corners_m)) != len(self.corners_m):
            raise ValueError("Pane polygon must have at least three distinct corners")
        for point in self.corners_m:
            if len(point) != 3:
                raise ValueError("Pane corners must be finite 3D points")
            for coordinate in point:
                _number(coordinate, "pane coordinate", -float("inf"), float("inf"))
        points = np.asarray(self.corners_m, dtype=float)
        centered = points - points[0]
        _, singular_values, axes = np.linalg.svd(centered, full_matrices=False)
        if singular_values[1] <= 1e-8:
            raise ValueError("Pane polygon cannot be collinear")
        tolerance = max(self.registration_error_m or 0, 1e-8)
        if max(abs(centered @ axes[-1])) > tolerance:
            raise ValueError("Pane polygon is nonplanar beyond registration error")
        x, y = (centered @ axes[:2].T).T
        if abs(x @ np.roll(y, -1) - y @ np.roll(x, -1)) <= 1e-12:
            raise ValueError("Pane polygon must have a nonzero ordered area")

    @property
    def is_field_verified(self) -> bool:
        return self.field_verified_at is not None

    def as_dict(self) -> dict:
        return {
            **asdict(self),
            "photos": [photo.as_dict() for photo in self.photos],
            "field_verified_at": self.field_verified_at.isoformat() if self.field_verified_at else None,
        }

    def to_rect_patch(self) -> RectPatch:
        """Use exact rectangular geometry without stretching survey polygons."""
        if len(self.corners_m) != 4:
            raise ValueError("Finite-pane optics require four rectangular corners")
        first, second, third, fourth = np.asarray(self.corners_m)
        if not np.allclose(third - first, second - first + fourth - first, rtol=0, atol=1e-8):
            raise ValueError("Finite-pane optics require four rectangular corners")
        return RectPatch(
            self.identity.pane_id,
            tuple((first + third) / 2),
            tuple(second - first),
            tuple(fourth - first),
        )


@dataclass(frozen=True)
class ImpactLocation:
    """Localization assertion retaining unresolved candidates at their original precision."""

    report_id: str
    precision: str
    microzone_id: str | None = None
    pane_ids: tuple[str, ...] = ()
    impact_source_id: str | None = None

    def __post_init__(self) -> None:
        _required(self.report_id, "report_id")
        if self.microzone_id is not None:
            _required(self.microzone_id, "microzone_id")
        if self.impact_source_id is not None:
            _required(self.impact_source_id, "impact_source_id")
        panes = tuple(self.pane_ids)
        for pane_id in panes:
            _required(pane_id, "pane_id")
        if len(panes) != len(set(panes)):
            raise ValueError("Duplicate impact candidate")
        object.__setattr__(self, "pane_ids", panes)
        if self.precision == "verified_pane":
            if len(panes) != 1 or self.impact_source_id is None:
                raise ValueError("A verified impact requires exactly one pane and separate impact evidence")
        elif self.precision == "candidate_panes":
            if not panes:
                raise ValueError("A candidate location must have at least one pane")
        elif self.precision == "microzone":
            if self.microzone_id is None or panes:
                raise ValueError("A microzone-only report cannot specify panes")
        elif self.precision == "unknown":
            if self.microzone_id is not None or panes:
                raise ValueError("An unknown location cannot specify a microzone or pane")
        else:
            raise ValueError("Unknown impact location precision")


class PaneRegistry:
    def __init__(self, panes: Iterable[PaneRegistration], *, dataset_kind: str = "field") -> None:
        if dataset_kind not in {"field", "synthetic"}:
            raise ValueError("dataset_kind must be field or synthetic")
        self._dataset_kind = dataset_kind
        self._panes: dict[str, PaneRegistration] = {}
        self._photos: dict[str, tuple[PaneIdentity, PanePhoto]] = {}
        locations = set()
        for pane in panes:
            identity = pane.identity
            if identity.pane_id in self._panes:
                raise ValueError(f"Duplicate pane_id: {identity.pane_id}")
            if pane.floor is not None and pane.bay is not None:
                location = (identity.building_id, identity.facade_id, pane.floor, pane.bay)
                if location in locations:
                    raise ValueError(f"Duplicate physical pane locator: {location}")
                locations.add(location)
            for photo in pane.photos:
                if photo.photo_id in self._photos:
                    raise ValueError(f"Duplicate pane photo annotation ID: {photo.photo_id}")
                self._photos[photo.photo_id] = identity, photo
            self._panes[identity.pane_id] = pane

    @property
    def dataset_kind(self) -> str:
        return self._dataset_kind

    def get(self, pane_id: str) -> PaneRegistration | None:
        return self._panes.get(pane_id)

    def require(self, identity: PaneIdentity, *, field_verified: bool = False) -> PaneRegistration:
        pane = self.get(identity.pane_id)
        if pane is None or pane.identity != identity:
            raise ValueError(f"Unknown or mismatched pane identity: {identity.pane_id}")
        if field_verified and (self.dataset_kind != "field" or not pane.is_field_verified):
            raise ValueError(f"Pane has no field verification: {identity.pane_id}")
        return pane

    def validate_impact(self, location: ImpactLocation) -> ImpactLocation:
        for pane_id in location.pane_ids:
            pane = self.get(pane_id)
            if pane is None:
                raise ValueError(f"Unknown impact candidate: {pane_id}")
            if location.microzone_id is not None and pane.microzone_id != location.microzone_id:
                raise ValueError(f"Pane {pane_id} is not registered to the reported microzone")
            if location.precision == "verified_pane":
                self.require(pane.identity, field_verified=True)
        return location

    def validate_glass(
        self, evidence: PaneGlassObservation, *, field_verified: bool = False
    ) -> PaneRegistration:
        pane = self.require(evidence.identity, field_verified=field_verified)
        for photo_id in evidence.observation.photo_ids:
            record = self._photos.get(photo_id)
            if record is None or record[0] != evidence.identity:
                raise ValueError(f"Photo does not belong to the evidence pane: {photo_id}")
            if record[1].captured_at > evidence.observed_at:
                raise ValueError(f"Photo postdates the glass evidence: {photo_id}")
        return pane

    def as_dict(self) -> dict:
        return {
            "dataset_kind": self.dataset_kind,
            "panes": [pane.as_dict() for pane in self._panes.values()],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> PaneRegistry:
        panes = []
        for row in payload["panes"]:
            fields = dict(row)
            fields["identity"] = PaneIdentity(**row["identity"])
            fields["photos"] = tuple(
                PanePhoto(**{**photo, "captured_at": datetime.fromisoformat(photo["captured_at"])})
                for photo in row.get("photos", ())
            )
            if row.get("field_verified_at") is not None:
                fields["field_verified_at"] = datetime.fromisoformat(row["field_verified_at"])
            panes.append(PaneRegistration(**fields))
        return cls(panes, dataset_kind=payload["dataset_kind"])


@dataclass(frozen=True)
class SpectralObservation:
    wavelength_nm: float
    reflectance: Measurement | None = None
    transmittance: Measurement | None = None

    def __post_init__(self) -> None:
        _number(self.wavelength_nm, "wavelength_nm", 1, float("inf"))
        present = [value for value in (self.reflectance, self.transmittance) if value is not None]
        if not present:
            raise ValueError("Spectral observation requires reflectance or transmittance")
        for value in present:
            if value.unit != "fraction" or not value.available:
                raise ValueError("Spectral measurements require available fractions")
            _number(value.value, "spectral fraction", 0, 1)
            _required(value.source_id, "spectral source_id")
        if sum(value.value for value in present) > 1 + 1e-12:
            raise ValueError("Spectral reflectance and transmittance cannot sum above one")

    def as_dict(self) -> dict:
        return {
            "wavelength_nm": self.wavelength_nm,
            "reflectance": measurement_dict(self.reflectance),
            "transmittance": measurement_dict(self.transmittance),
        }


@dataclass(frozen=True)
class PaneGlassObservation:
    identity: PaneIdentity
    evidence_id: str
    observed_at: datetime
    observation: GlassObservation
    source_kind: str
    source_id: str
    incidence_angle_deg: float | None = None
    view_id: str | None = None
    approach_azimuth_deg: float | None = None
    lighting_context: str | None = None
    spectrum: tuple[SpectralObservation, ...] = ()
    reviewed_from_evidence_id: str | None = None

    def __post_init__(self) -> None:
        _required(self.evidence_id, "evidence_id")
        _required(self.source_id, "source_id")
        _aware(self.observed_at, "observed_at")
        glass = self.observation.validate()
        if self.identity.facade_id != glass.facade_id:
            raise ValueError("Glass evidence facade_id does not match pane identity")
        if glass.observed_at is not None and datetime.fromisoformat(glass.observed_at) != self.observed_at:
            raise ValueError("Glass evidence timestamp does not match pane observation")
        if self.source_kind not in {"field_view", "instrument", "manufacturer_assembly_spec", "clip_screen"}:
            raise ValueError("Unknown pane glass source_kind")
        spectrum = tuple(self.spectrum)
        if len({sample.wavelength_nm for sample in spectrum}) != len(spectrum):
            raise ValueError("Duplicate wavelength in pane observation")
        object.__setattr__(self, "spectrum", spectrum)
        optical_values = (glass.exterior_vlr_pct, glass.exterior_vlt_pct)
        if spectrum or any(value is not None and value.available for value in optical_values):
            if self.source_kind not in {"instrument", "manufacturer_assembly_spec"}:
                raise ValueError("VLR, VLT and spectral fractions require instrument or assembly spec evidence")
            if self.incidence_angle_deg is None:
                raise ValueError("VLR, VLT and spectral measurements require incidence_angle_deg")
        if self.incidence_angle_deg is not None:
            _number(self.incidence_angle_deg, "incidence_angle_deg", 0, 90)
        if self.source_kind == "manufacturer_assembly_spec":
            _required(glass.specification_id, "assembly specification_id")
            if glass.visual_class != "unknown":
                raise ValueError("Assembly specifications cannot assert onsite visible appearance")
        for label, value in (("view_id", self.view_id), ("lighting_context", self.lighting_context)):
            if value is not None:
                _required(value, label)
        if self.approach_azimuth_deg is not None:
            _number(self.approach_azimuth_deg, "approach_azimuth_deg", 0, 360)
            if self.approach_azimuth_deg == 360:
                raise ValueError("approach_azimuth_deg must be below 360")
        view_shares = (glass.reflected_vegetation_share, glass.transmitted_habitat_share)
        if self.source_kind in {"field_view", "clip_screen"} or any(
            value is not None and value.available for value in view_shares
        ):
            if not (self.view_id and self.approach_azimuth_deg is not None
                    and self.lighting_context and glass.photo_ids):
                raise ValueError("View evidence requires annotated photos, view_id, approach azimuth and lighting context")
        if self.source_kind == "clip_screen" and (
            glass.visual_class_evidence_tier != EvidenceTier.PROXY or glass.reviewed_by_human
            or any(value is not None for value in (*view_shares, glass.area_m2, glass.pattern))
            or glass.surface_treatment != "unknown" or glass.coating_position != "unknown"
            or glass.specification_id is not None
        ):
            raise ValueError("CLIP can supply only provisional photo triage")
        if self.reviewed_from_evidence_id is not None:
            _required(self.reviewed_from_evidence_id, "reviewed_from_evidence_id")
            _required(glass.observer_id, "reviewer observer_id")
            if not glass.reviewed_by_human or self.reviewed_from_evidence_id == self.evidence_id:
                raise ValueError("A correction requires human review and a distinct prior evidence ID")

    def as_dict(self) -> dict:
        observation = self.observation.as_dict()
        return {
            **asdict(self),
            "observed_at": self.observed_at.isoformat(),
            "spectrum": [sample.as_dict() for sample in self.spectrum],
            "observation": {
                key: value for key, value in observation.items()
                if not key.startswith("canonical_")
            },
        }

    def to_glass_panel(self, registry: PaneRegistry) -> GlassPanel:
        registry.validate_glass(self, field_verified=True)
        if self.source_kind == "clip_screen":
            raise ValueError("CLIP evidence requires human review before glazing assessment")
        return replace(self.observation.to_glass_panel(), panel_id=self.identity.pane_id)

    def model_approach_view(
        self,
        registry: PaneRegistry,
        *,
        coordinate_system: str,
        latitude_deg: float,
        longitude_deg: float,
        viewer_m: Point,
        heading_mps: Point,
        reflection_source_m: Point | None = None,
        transmission_source_m: Point | None = None,
        blockers: tuple[RectPatch, ...] = (),
    ) -> dict:
        """Evaluate hypothetical geometric paths in the registered local ENU frame."""
        pane = registry.validate_glass(self)
        if not coordinate_system or pane.coordinate_system != coordinate_system:
            raise ValueError("Approach coordinates must be in the registered local ENU coordinate system")
        patch = pane.to_rect_patch()
        sun = solar_position_enu(self.observed_at, latitude_deg, longitude_deg)
        alignment = specular_reflection_alignment(
            patch.id, patch.normal, sun.direction_enu, np.asarray(viewer_m) - patch.center_m
        )
        result = {}
        for kind, source in (("reflection", reflection_source_m), ("transmission", transmission_source_m)):
            if source is None:
                result[kind] = {"status": "unassessed", "ray": None}
                continue
            ray = scene_ray(viewer_m, heading_mps, source, patch, kind, blockers=blockers)
            result[kind] = {
                "status": "geometrically_possible" if ray else "no_path",
                "ray": asdict(ray) if ray is not None else None,
            }
        return {
            **self.identity.as_dict(),
            "dataset_kind": registry.dataset_kind,
            "evidence_id": self.evidence_id,
            "status": "geometric_model",
            "solar_position": asdict(sun),
            "solar_alignment": {**asdict(alignment), "sun_above_horizon": bool(alignment.sun_above_horizon)},
            **result,
        }


def audit_glass_evidence(registry: PaneRegistry, rows: Iterable[PaneGlassObservation]) -> list[dict]:
    """Retain conflicting assembly/optical records for review instead of averaging them."""
    by_id: dict[str, PaneGlassObservation] = {}
    for row in rows:
        registry.validate_glass(row)
        if row.evidence_id in by_id:
            raise ValueError(f"Duplicate glass evidence_id: {row.evidence_id}")
        by_id[row.evidence_id] = row
    for row in by_id.values():
        if row.reviewed_from_evidence_id is None:
            continue
        original = by_id.get(row.reviewed_from_evidence_id)
        if (original is None or original.source_kind != "clip_screen"
                or original.identity != row.identity or original.view_id != row.view_id
                or not set(original.observation.photo_ids) <= set(row.observation.photo_ids)
                or original.observed_at > row.observed_at):
            raise ValueError(f"Invalid CLIP correction lineage: {row.evidence_id}")

    groups: dict[PaneIdentity, list[PaneGlassObservation]] = {}
    for row in by_id.values():
        if row.source_kind != "clip_screen":
            groups.setdefault(row.identity, []).append(row)
    conflicts = []
    for pane_rows in groups.values():
        for left, right in combinations(sorted(pane_rows, key=lambda row: row.evidence_id), 2):
            compared = [
                (field, getattr(left.observation, field), getattr(right.observation, field))
                for field in ("surface_treatment", "coating_position")
            ]
            if (left.observed_at == right.observed_at and left.view_id is not None
                    and (left.view_id, left.approach_azimuth_deg, left.lighting_context)
                    == (right.view_id, right.approach_azimuth_deg, right.lighting_context)
                    and left.observation.visual_class_confirmed and right.observation.visual_class_confirmed):
                compared.append(("visual_class", left.observation.visual_class, right.observation.visual_class))
            if left.incidence_angle_deg is not None and right.incidence_angle_deg is not None and isclose(
                left.incidence_angle_deg, right.incidence_angle_deg, abs_tol=1e-6
            ):
                compared.extend(
                    (field, getattr(left.observation, field), getattr(right.observation, field))
                    for field in ("exterior_vlr_pct", "exterior_vlt_pct")
                )
            for field, first, second in compared:
                if _disagree(first, second):
                    conflicts.append({
                        **left.identity.as_dict(),
                        "field": field,
                        "evidence_ids": [left.evidence_id, right.evidence_id],
                        "source_ids": [left.source_id, right.source_id],
                    })
    return sorted(conflicts, key=lambda row: (row["pane_id"], row["evidence_ids"], row["field"]))


def _disagree(first: str | Measurement | None, second: str | Measurement | None) -> bool:
    if isinstance(first, str) and isinstance(second, str):
        return first != "unknown" and second != "unknown" and first != second
    if not (isinstance(first, Measurement) and first.available
            and isinstance(second, Measurement) and second.available):
        return False
    first_low = first.value if first.lower is None else first.lower
    first_high = first.value if first.upper is None else first.upper
    second_low = second.value if second.lower is None else second.lower
    second_high = second.value if second.upper is None else second.upper
    return first_high < second_low or second_high < first_low
