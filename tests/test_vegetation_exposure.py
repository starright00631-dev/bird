from __future__ import annotations

import pytest

from birdglass.vegetation_exposure import (
    VegetationBuffer,
    VegetationExposure,
    relative_exposure_band,
)


def test_multiscale_vegetation_summary_flags_reflected_canopy():
    exposure = VegetationExposure(
        facade_id="B1::F1",
        buffers=(
            VegetationBuffer(radius_m=5, tree_canopy_percent=10, shrub_percent=15),
            VegetationBuffer(radius_m=50, tree_canopy_percent=35, shrub_percent=20, porous_surface_percent=55),
            VegetationBuffer(radius_m=1000, tree_canopy_percent=28),
        ),
        facade_porous_cover_50m_percent=55,
        facade_tree_cover_50m_percent=35,
        stories_reflecting_canopy=3,
        building_vegetation_proportion_0_1=0.42,
    )
    summary = exposure.summary()
    assert summary["canopy_reflection_exposure_flag"] is True
    assert set(summary["buffers"]) == {"5", "50", "1000"}
    assert "preserve vegetation" in summary["vegetation_management_default"]


def test_vegetation_buffers_must_have_unique_allowed_radii():
    with pytest.raises(ValueError, match="unique"):
        VegetationExposure(
            facade_id="B1::F1",
            buffers=(VegetationBuffer(radius_m=50), VegetationBuffer(radius_m=50)),
        ).validate()
    with pytest.raises(ValueError, match="Unsupported buffer radius"):
        VegetationBuffer(radius_m=500).validate()


def test_reference_relative_band_does_not_claim_absolute_threshold():
    result = relative_exposure_band(50, [0, 10, 20, 30, 40, 50, 60, 70, 80, 90])
    assert result["band"] == "middle_half_relative_to_reference"
    assert result["absolute_threshold_claimed"] is False


def test_out_of_range_vegetation_percent_is_rejected():
    with pytest.raises(ValueError, match="must be in"):
        VegetationExposure(
            facade_id="B1::F1",
            facade_tree_cover_50m_percent=101,
        ).validate()
