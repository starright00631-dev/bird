"""Solar geometry and specular-reflection alignment for bird-facing glass.

Coordinates are local East-North-Up (ENU). This module computes the sun
direction and geometric mirror alignment only. It does NOT estimate reflected
radiance, glass BRDF, cloud attenuation, bird recognition, or collision risk.

The compact solar-position approximation follows the NOAA Solar Calculator
algorithm family. Use an ephemeris-grade implementation for final metrology.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import acos, asin, atan2, cos, degrees, floor, radians, sin
from typing import Sequence

import numpy as np


def _unit(vector: Sequence[float]) -> np.ndarray:
    value = np.asarray(vector, dtype=float)
    if value.shape != (3,) or not np.isfinite(value).all():
        raise ValueError("A finite three-dimensional ENU vector is required")
    norm = float(np.linalg.norm(value))
    if norm <= 1e-12:
        raise ValueError("Direction vector cannot be zero")
    return value / norm


@dataclass(frozen=True)
class SolarPosition:
    """Solar position in a local ENU frame.

    Azimuth is degrees clockwise from true north; altitude is degrees above
    the astronomical horizon. The unit vector points from the observer to sun.
    """

    azimuth_deg: float
    altitude_deg: float
    direction_enu: tuple[float, float, float]
    is_above_horizon: bool


def solar_position_enu(when: datetime, latitude_deg: float,
                       longitude_deg: float) -> SolarPosition:
    """Approximate solar azimuth/altitude for an aware timestamp and WGS84 site.

    Longitude is positive east. The timestamp is converted to UTC; no local
    daylight-saving assumptions are made. Elevation, refraction and terrain
    horizon are intentionally omitted.
    """
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("when must be timezone-aware")
    if not (-90.0 <= latitude_deg <= 90.0):
        raise ValueError("latitude must be within [-90, 90]")
    if not (-180.0 <= longitude_deg <= 180.0):
        raise ValueError("longitude must be within [-180, 180]")

    utc = when.astimezone(timezone.utc)
    year = utc.year
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    day_of_year = (utc - start).total_seconds() / 86400.0 + 1.0
    hour = (utc.hour + utc.minute / 60.0 + utc.second / 3600.0
            + utc.microsecond / 3.6e9)

    gamma = 2.0 * np.pi / (366.0 if _is_leap(year) else 365.0) * (
        day_of_year - 1.0 + (hour - 12.0) / 24.0
    )
    eq_time = 229.18 * (
        0.000075 + 0.001868 * cos(gamma) - 0.032077 * sin(gamma)
        - 0.014615 * cos(2 * gamma) - 0.040849 * sin(2 * gamma)
    )
    decl = (
        0.006918 - 0.399912 * cos(gamma) + 0.070257 * sin(gamma)
        - 0.006758 * cos(2 * gamma) + 0.000907 * sin(2 * gamma)
        - 0.002697 * cos(3 * gamma) + 0.00148 * sin(3 * gamma)
    )
    true_solar_minutes = (hour * 60.0 + eq_time + 4.0 * longitude_deg) % 1440.0
    hour_angle_deg = true_solar_minutes / 4.0 - 180.0
    hour_angle = radians(hour_angle_deg)
    latitude = radians(latitude_deg)

    cos_zenith = (sin(latitude) * sin(decl)
                  + cos(latitude) * cos(decl) * cos(hour_angle))
    zenith = acos(float(np.clip(cos_zenith, -1.0, 1.0)))
    altitude = 90.0 - degrees(zenith)

    # Azimuth clockwise from true north. atan2(east, north) is stable at noon.
    east = -cos(decl) * sin(hour_angle)
    north = cos(latitude) * sin(decl) - sin(latitude) * cos(decl) * cos(hour_angle)
    azimuth = degrees(atan2(east, north)) % 360.0

    alt_rad, az_rad = radians(altitude), radians(azimuth)
    direction = (
        cos(alt_rad) * sin(az_rad),
        cos(alt_rad) * cos(az_rad),
        sin(alt_rad),
    )
    return SolarPosition(azimuth, altitude, direction, altitude > 0.0)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


@dataclass(frozen=True)
class ReflectionAlignment:
    """Geometric mirror alignment; not a radiometric reflectance estimate."""

    pane_id: str
    incidence_angle_deg: float
    specular_mismatch_deg: float
    sun_above_horizon: bool
    geometrically_aligned: bool


def specular_reflection_alignment(
    pane_id: str,
    pane_normal_enu: Sequence[float],
    sun_direction_enu: Sequence[float],
    bird_direction_from_pane_enu: Sequence[float],
    angular_tolerance_deg: float = 3.0,
) -> ReflectionAlignment:
    """Compare the mirror-reflected solar direction with a bird's direction.

    All directions are vectors FROM the pane/observer TOWARD the named target.
    The pane normal is unoriented; it is oriented toward the sun side internally.
    A match means the bird lies near the geometric specular direction, not that
    the pane is bright or that the bird perceives the reflection as habitat.
    """
    if not pane_id:
        raise ValueError("pane_id is required")
    if not (0.0 < angular_tolerance_deg <= 30.0):
        raise ValueError("angular tolerance must be in (0, 30] degrees")
    normal = _unit(pane_normal_enu)
    sun = _unit(sun_direction_enu)
    bird = _unit(bird_direction_from_pane_enu)

    dot = float(np.dot(normal, sun))
    if abs(dot) <= 1e-10:
        return ReflectionAlignment(pane_id, 90.0, 90.0, sun[2] > 0.0, False)
    if dot < 0.0:
        normal = -normal
        dot = -dot

    reflected = _unit(2.0 * dot * normal - sun)
    mismatch = degrees(acos(float(np.clip(np.dot(reflected, bird), -1.0, 1.0))))
    incidence = degrees(acos(float(np.clip(dot, 0.0, 1.0))))
    return ReflectionAlignment(
        pane_id, incidence, mismatch, sun[2] > 0.0,
        bool(sun[2] > 0.0 and mismatch <= angular_tolerance_deg),
    )
