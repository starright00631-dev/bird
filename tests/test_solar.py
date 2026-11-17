from datetime import datetime, timezone

import numpy as np
import pytest

from birdglass.solar import solar_position_enu, specular_reflection_alignment


def test_solar_position_is_unit_enu_and_south_at_northern_solar_noon():
    # Near the December solstice at 40 N, the sun is due south at solar noon.
    pos = solar_position_enu(
        datetime(2026, 12, 21, 12, 0, tzinfo=timezone.utc), 40.0, 0.0
    )
    assert np.linalg.norm(pos.direction_enu) == pytest.approx(1.0)
    assert pos.is_above_horizon
    assert pos.azimuth_deg == pytest.approx(180.0, abs=1.5)
    assert pos.altitude_deg > 20.0


def test_timezone_conversion_preserves_solar_position():
    utc = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    local = datetime.fromisoformat("2026-06-21T08:00:00-04:00")
    a = solar_position_enu(utc, 35.0, -75.0)
    b = solar_position_enu(local, 35.0, -75.0)
    assert a.azimuth_deg == pytest.approx(b.azimuth_deg)
    assert a.altitude_deg == pytest.approx(b.altitude_deg)


def test_sun_below_horizon_is_not_marked_as_daylight():
    pos = solar_position_enu(
        datetime(2026, 6, 21, 3, 0, tzinfo=timezone.utc), 35.0, -75.0
    )
    assert not pos.is_above_horizon
    assert pos.altitude_deg < 0.0


def test_specular_alignment_uses_vector_reflection_law():
    # Mirror normal is +z; sun ray from pane is (0.6, 0, 0.8).
    result = specular_reflection_alignment(
        "pane-1", (0, 0, 1), (0.6, 0, 0.8), (-0.6, 0, 0.8)
    )
    assert result.incidence_angle_deg == pytest.approx(36.8698976)
    assert result.specular_mismatch_deg == pytest.approx(0.0, abs=1e-6)
    assert result.geometrically_aligned


def test_misaligned_bird_is_not_flagged_as_specular():
    result = specular_reflection_alignment(
        "pane-2", (0, 0, 1), (0.6, 0, 0.8), (0.6, 0, 0.8)
    )
    assert result.specular_mismatch_deg > 60.0
    assert not result.geometrically_aligned


def test_invalid_timezone_and_tolerance_are_rejected():
    with pytest.raises(ValueError):
        solar_position_enu(datetime(2026, 1, 1), 22.0, 113.0)
    with pytest.raises(ValueError):
        specular_reflection_alignment("p", (0, 0, 1), (1, 0, 1), (0, 1, 0),
                                      angular_tolerance_deg=0.0)
