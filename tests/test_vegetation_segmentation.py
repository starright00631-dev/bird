from __future__ import annotations

import pytest

from birdglass.vegetation_segmentation import summarize_class_mask, summarize_multiscale_masks


def test_mask_summary_separates_tree_canopy_from_porous_ground_cover():
    mask = [
        ["tree_canopy", "tree_canopy", "shrub", "grass"],
        ["impervious", "building", "bare_soil", "water"],
    ]
    result = summarize_class_mask(mask, pixel_area_m2=1.0)
    assert result["valid_pixels"] == 8
    assert result["tree_canopy_cover_percent"] == 25
    assert result["porous_ground_shrub_cover_percent"] == 37.5
    assert result["valid_area_m2"] == 8


def test_mask_summary_respects_valid_mask_and_rejects_unknown_class():
    mask = [["tree_canopy", "impervious"], ["grass", "water"]]
    valid = [[True, False], [True, True]]
    result = summarize_class_mask(mask, valid_mask=valid)
    assert result["valid_pixels"] == 3
    assert result["tree_canopy_cover_percent"] == pytest.approx(100 / 3)
    with pytest.raises(ValueError, match="Unknown land-cover class"):
        summarize_class_mask([["tree", "water"]])


def test_multiscale_summary_does_not_sum_across_different_denominators():
    masks = {
        5: [["tree_canopy", "impervious"], ["grass", "water"]],
        50: [["tree_canopy", "tree_canopy"], ["shrub", "grass"]],
    }
    result = summarize_multiscale_masks(masks)
    assert result["buffer_radii_m"] == [5, 50]
    assert "different spatial denominator" in result["cross_scale_warning"]
