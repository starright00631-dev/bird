import pytest

from birdglass.vegetation import VEGETATION_BUFFERS
from birdglass.vegetation_segmentation import summarize_annular_masks, summarize_class_mask

PROVENANCE = {
    "source_image_id": "ortho-2026-01",
    "segmentation_model": "human-reviewed-segmentation",
    "model_revision": "manual-annotation-v1",
    "crs": "EPSG:32650",
    "pixel_resolution_m": "0.25",
    "human_qa_status": "reviewed",
    "qa_reviewer": "reviewer-01",
}


def test_class_mask_summary_separates_canopy_from_porous_ground_cover():
    mask = [
        ["tree_canopy", "tree_canopy", "shrub", "grass"],
        ["impervious", "building", "bare_soil", "water"],
    ]
    result = summarize_class_mask(mask, pixel_area_m2=0.0625)
    assert result["valid_pixels"] == 8
    assert result["tree_canopy_cover_percent"] == 25
    assert result["porous_ground_shrub_cover_percent"] == 37.5
    assert result["valid_area_m2"] == pytest.approx(0.5)


def test_annular_mask_output_preserves_all_five_bands_and_provenance():
    masks = {
        band: [["tree_canopy", "impervious"], ["grass", "water"]]
        for band in VEGETATION_BUFFERS
    }
    result = summarize_annular_masks(masks, provenance=PROVENANCE)
    assert result["mask_geometry"] == "five_non_overlapping_annular_bands"
    assert result["missing_bands"] == []
    assert result["model_ready"] is True
    assert result["provenance"]["source_image_id"] == "ortho-2026-01"
    assert result["band_summaries"]["0_5m"]["tree_canopy_cover_percent"] == 25


def test_missing_annular_bands_remain_missing_not_zero():
    result = summarize_annular_masks(
        {"0_5m": [["tree_canopy", "water"]]},
        provenance={**PROVENANCE, "human_qa_status": "pending", "qa_reviewer": ""},
    )
    assert result["missing_bands"] == [band for band in VEGETATION_BUFFERS if band != "0_5m"]
    assert result["band_summaries"]["5_25m"] is None
    assert result["model_ready"] is False


def test_cumulative_masks_are_not_mislabeled_as_annular():
    with pytest.raises(ValueError, match="non-overlapping annular"):
        summarize_annular_masks(
            {"0_5m": [["tree_canopy"]]},
            provenance=PROVENANCE,
            mask_geometry="cumulative",
        )


def test_reviewed_masks_require_a_reviewer_and_provenance():
    bad = dict(PROVENANCE)
    bad["qa_reviewer"] = ""
    with pytest.raises(ValueError, match="qa_reviewer"):
        summarize_annular_masks({"0_5m": [["tree_canopy"]]}, provenance=bad)


def test_bad_pixel_area_is_rejected():
    with pytest.raises(ValueError, match="finite and positive"):
        summarize_class_mask([["tree_canopy"]], pixel_area_m2=float("nan"))
