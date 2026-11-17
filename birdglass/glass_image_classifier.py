"""Optional pinned CLIP photo triage; output is never a calibrated probability."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Mapping

from .evidence import EvidenceTier

PROMPTS = {
    "transparent": "a clear transparent glass building facade with a view through the glass",
    "reflective": "a reflective glass building facade reflecting trees, sky and surrounding landscape",
    "mirrored": "a mirror-like highly reflective glass building facade",
    "tinted": "a tinted or colored glass building facade",
    "fritted": "a glass building facade with ceramic frit dots or a fritted pattern",
    "patterned": "a patterned or textured glass building facade with visible lines or dots",
    "frosted_translucent": "a frosted translucent glass building facade with obscured visibility",
    "opaque_spandrel": "an opaque spandrel panel on a glass building facade",
}
IMMUTABLE_REVISION = re.compile(r"^[0-9a-f]{40}$")


def rank_visual_class_scores(scores: Mapping[str, float], *, model_name: str, model_revision: str) -> dict:
    if not scores:
        raise ValueError("scores cannot be empty")
    if not model_name.strip() or not IMMUTABLE_REVISION.fullmatch(model_revision or ""):
        raise ValueError("model_name and an immutable 40-character model_revision are required")
    unknown = set(scores) - set(PROMPTS)
    if unknown:
        raise ValueError(f"Unknown visual classes: {sorted(unknown)}")
    normalized = {}
    for key, value in scores.items():
        number = float(value)
        if not (number == number and abs(number) != float("inf")):
            raise ValueError(f"Non-finite similarity for {key}")
        normalized[key] = number
    ranked = sorted(normalized.items(), key=lambda item: item[1], reverse=True)
    margin = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else None
    return {
        "visual_class": ranked[0][0],
        "relative_scores": dict(ranked),
        "top_score_margin": margin,
        "score_semantics": "raw CLIP similarity logits; not calibrated class probabilities",
        "model_name": model_name,
        "model_revision": model_revision,
        "prompt_version": "birdglass-glass-prompts-v1",
        "requires_human_review": True,
        "recommended_next_step": "Confirm from multiple bird-side views and manufacturer/instrument optical evidence.",
    }


def classify_glass_image(
    image_path: str | Path,
    *,
    model_revision: str,
    model_name: str = "openai/clip-vit-base-patch32",
    device: str = "cpu",
    source_image_id: str | None = None,
) -> dict:
    """Run optional CLIP triage; install requirements-glass-vision.txt first."""
    if not IMMUTABLE_REVISION.fullmatch(model_revision or ""):
        raise ValueError("An immutable 40-character model_revision is required")
    try:
        import torch
        from PIL import Image
        from transformers import CLIPModel, CLIPProcessor
    except ImportError as exc:
        raise RuntimeError(
            "Install optional dependencies from requirements-glass-vision.txt to run image triage"
        ) from exc

    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_bytes()
    image_hash = hashlib.sha256(raw).hexdigest()
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    processor = CLIPProcessor.from_pretrained(model_name, revision=model_revision)
    model = CLIPModel.from_pretrained(model_name, revision=model_revision).to(device)
    model.eval()
    labels = list(PROMPTS)
    inputs = processor(
        text=[PROMPTS[label] for label in labels],
        images=image,
        return_tensors="pt",
        padding=True,
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        similarities = outputs.logits_per_image[0].detach().cpu().tolist()
    result = rank_visual_class_scores(
        dict(zip(labels, similarities)),
        model_name=model_name,
        model_revision=model_revision,
    )
    result.update({
        "source_image_id": source_image_id,
        "source_image_sha256": image_hash,
        "evidence_tier": EvidenceTier.PROXY.value,
        "evidence_source": "zero_shot_image_model",
        "human_review_required": True,
        "limitations": [
            "Photo appearance does not determine spectral reflectance or transmittance.",
            "Reflections vary with time, weather and bird approach angle.",
            "This result must not enter the scientific feature table until a human reviewer confirms it.",
        ],
    })
    return result

