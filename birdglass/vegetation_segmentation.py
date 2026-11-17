"""Summarize supplied land-cover masks; this module does not run segmentation.

Masks must already be clipped to the five non-overlapping annular bands used
by birdglass.vegetation. Source image, model revision, CRS, pixel resolution
and human-QA state are retained with every output.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Mapping, Optional, Sequence

from .vegetation import VEGETATION_BUFFERS

DEFAULT_CLASSES = {
    "tree_canopy", "shrub", "grass", "bare_soil", "bark_mulch",
    "impervious", "building", "water", "other",
}
POROUS_GROUND_CLASSES = {"shrub", "grass", "bare_soil", "bark_mulch"}


def _validate_rectangular(mask: Sequence[Sequence[str]]) -> tuple[int, int]:
    if not mask or not mask[0]:
        raise ValueError("class_mask cannot be empty")
    width = len(mask[0])
    if any(len(row) != width for row in mask):
        raise ValueError("class_mask must be rectangular")
    return len(mask), width


def summarize_class_mask(
    class_mask: Sequence[Sequence[str]],
    *,
    valid_mask: Optional[Sequence[Sequence[bool]]] = None,
    allowed_classes: Iterable[str] = DEFAULT_CLASSES,
    pixel_area_m2: Optional[float] = None,
) -> dict:
    height, width = _validate_rectangular(class_mask)
    if valid_mask is not None:
        vh, vw = _validate_rectangular(valid_mask)
        if (vh, vw) != (height, width):
            raise ValueError("valid_mask shape must match class_mask")
    if pixel_area_m2 is not None and (
        not math.isfinite(float(pixel_area_m2)) or pixel_area_m2 <= 0
    ):
        raise ValueError("pixel_area_m2 must be finite and positive")
    allowed = set(allowed_classes)
    counts: Counter[str] = Counter()
    valid_pixels = 0
    for y, row in enumerate(class_mask):
        for x, label in enumerate(row):
            if valid_mask is not None and not bool(valid_mask[y][x]):
                continue
            if label not in allowed:
                raise ValueError(f"Unknown land-cover class: {label!r}")
            counts[label] += 1
            valid_pixels += 1
    if valid_pixels == 0:
        raise ValueError("No valid pixels in mask")
    percentages = {
        name: 100.0 * counts.get(name, 0) / valid_pixels
        for name in sorted(allowed)
    }
    porous = sum(percentages.get(name, 0.0) for name in POROUS_GROUND_CLASSES)
    tree = percentages.get("tree_canopy", 0.0)
    return {
        "height_pixels": height,
        "width_pixels": width,
        "valid_pixels": valid_pixels,
        "pixel_area_m2": pixel_area_m2,
        "valid_area_m2": valid_pixels * pixel_area_m2 if pixel_area_m2 is not None else None,
        "class_pixel_counts": {name: counts.get(name, 0) for name in sorted(allowed)},
        "class_cover_percent": percentages,
        "tree_canopy_cover_percent": tree,
        "porous_ground_shrub_cover_percent": porous,
        "interpretation": "mask-derived cover; accuracy depends on source imagery, segmentation model and human QA",
    }


def summarize_annular_masks(
    masks_by_band: Mapping[str, Sequence[Sequence[str]]],
    *,
    provenance: Mapping[str, str],
    valid_masks_by_band: Optional[Mapping[str, Sequence[Sequence[bool]]]] = None,
    pixel_area_by_band_m2: Optional[Mapping[str, float]] = None,
    mask_geometry: str = "annular",
) -> dict:
    """Summarize five separate non-overlapping masks; never accept cumulative buffers."""
    if mask_geometry != "annular":
        raise ValueError("Masks must be clipped to non-overlapping annular bands")
    if not masks_by_band:
        raise ValueError("masks_by_band cannot be empty")
    unknown = set(masks_by_band) - set(VEGETATION_BUFFERS)
    if unknown:
        raise ValueError(f"Unsupported vegetation bands: {sorted(unknown)}")
    required_provenance = {
        "source_image_id", "segmentation_model", "model_revision",
        "crs", "pixel_resolution_m", "human_qa_status",
    }
    missing = required_provenance - set(provenance)
    if missing:
        raise ValueError(f"Missing mask provenance: {sorted(missing)}")
    if any(not str(provenance[key]).strip() for key in required_provenance):
        raise ValueError("Mask provenance values cannot be empty")
    if provenance["human_qa_status"] not in {"pending", "reviewed", "rejected"}:
        raise ValueError("human_qa_status must be pending, reviewed or rejected")
    if provenance["human_qa_status"] == "reviewed" and not provenance.get("qa_reviewer", "").strip():
        raise ValueError("Reviewed masks require qa_reviewer")
    try:
        resolution = float(provenance["pixel_resolution_m"])
    except ValueError as exc:
        raise ValueError("pixel_resolution_m must be numeric") from exc
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError("pixel_resolution_m must be finite and positive")

    output = {}
    for band in VEGETATION_BUFFERS:
        if band not in masks_by_band:
            output[band] = None
            continue
        valid_mask = valid_masks_by_band.get(band) if valid_masks_by_band else None
        pixel_area = pixel_area_by_band_m2.get(band) if pixel_area_by_band_m2 else resolution ** 2
        output[band] = summarize_class_mask(
            masks_by_band[band],
            valid_mask=valid_mask,
            pixel_area_m2=pixel_area,
        )
    return {
        "mask_geometry": "five_non_overlapping_annular_bands",
        "band_summaries": output,
        "missing_bands": [band for band in VEGETATION_BUFFERS if output[band] is None],
        "provenance": dict(provenance),
        "model_ready": (
            provenance["human_qa_status"] == "reviewed"
            and all(output[band] is not None for band in VEGETATION_BUFFERS)
        ),
        "not_a_segmentation_model": True,
        "cross_band_warning": "Each band has its own denominator; never sum or average cover percentages across bands without area weighting.",
    }
