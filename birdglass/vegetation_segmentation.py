"""Convert semantic land-cover masks into auditable vegetation exposure metrics.

The function accepts masks produced by any segmentation model (including a
DINOv2-based/Kaggle-style segmenter). It does not assume the segmentation model
is correct; image source, resolution and model version should be retained.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping, Optional, Sequence

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
    """Return class pixel counts and percentages for one spatial buffer."""
    height, width = _validate_rectangular(class_mask)
    if valid_mask is not None:
        vh, vw = _validate_rectangular(valid_mask)
        if (vh, vw) != (height, width):
            raise ValueError("valid_mask shape must match class_mask")
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
    percentages = {name: 100.0 * counts.get(name, 0) / valid_pixels for name in sorted(allowed)}
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
        "interpretation": "segmentation-derived cover; accuracy depends on mask model, image resolution and annotation quality",
    }


def summarize_multiscale_masks(
    masks_by_radius: Mapping[int, Sequence[Sequence[str]]],
    *,
    valid_masks_by_radius: Optional[Mapping[int, Sequence[Sequence[bool]]]] = None,
    pixel_area_by_radius_m2: Optional[Mapping[int, float]] = None,
) -> dict:
    """Summarize independent clipped masks for multiple buffer radii."""
    if not masks_by_radius:
        raise ValueError("masks_by_radius cannot be empty")
    output = {}
    for radius, mask in sorted(masks_by_radius.items()):
        if radius not in {5, 25, 50, 100, 1000, 10000}:
            raise ValueError(f"Unsupported buffer radius: {radius}")
        valid_mask = valid_masks_by_radius.get(radius) if valid_masks_by_radius else None
        pixel_area = pixel_area_by_radius_m2.get(radius) if pixel_area_by_radius_m2 else None
        output[str(radius)] = summarize_class_mask(
            mask, valid_mask=valid_mask, pixel_area_m2=pixel_area
        )
    return {
        "buffer_summaries": output,
        "buffer_radii_m": sorted(masks_by_radius),
        "cross_scale_warning": "Do not add percentages across buffers; each buffer has a different spatial denominator.",
    }
