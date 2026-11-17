"""Optional zero-shot visual appearance triage for façade glass photos.

CLIP scores are relative image/text similarities, not calibrated probabilities.
Every result is explicitly marked for human review and must not be used as an
optical specification or as a collision-risk probability.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

PROMPTS = {
    "transparent": "a clear transparent glass building facade with a view through the glass",
    "reflective": "a reflective glass building facade reflecting trees, sky and surrounding landscape",
    "mirrored": "a mirror-like highly reflective glass building facade",
    "tinted": "a tinted or colored glass building facade",
    "fritted": "a glass building facade with ceramic frit dots or a fritted pattern",
    "patterned": "a patterned or textured glass building facade with visible lines or dots",
    "frosted_translucent": "a frosted translucent glass building facade with obscured visibility",
}


def rank_visual_class_scores(scores: Mapping[str, float]) -> dict:
    if not scores:
        raise ValueError("scores cannot be empty")
    unknown = set(scores) - set(PROMPTS)
    if unknown:
        raise ValueError(f"Unknown visual classes: {sorted(unknown)}")
    normalized = {}
    for key, value in scores.items():
        value = float(value)
        if not (value == value and abs(value) != float("inf")):
            raise ValueError(f"Non-finite similarity for {key}")
        normalized[key] = value
    ranked = sorted(normalized.items(), key=lambda item: item[1], reverse=True)
    margin = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else None
    return {
        "visual_class": ranked[0][0],
        "relative_scores": dict(ranked),
        "top_score_margin": margin,
        "score_semantics": "relative CLIP similarity; not a calibrated probability",
        "requires_human_review": True,
        "recommended_next_step": "Confirm with façade photo from multiple angles and manufacturer/optical specification.",
    }


def classify_glass_image(
    image_path: str | Path,
    *,
    model_name: str = "openai/clip-vit-base-patch32",
    device: str = "cpu",
) -> dict:
    """Run optional CLIP zero-shot triage; requires glass-vision extras."""
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
    image = Image.open(path).convert("RGB")
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name).to(device)
    model.eval()
    labels = list(PROMPTS)
    texts = [PROMPTS[label] for label in labels]
    inputs = processor(text=texts, images=image, return_tensors="pt", padding=True)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        similarities = outputs.logits_per_image[0].detach().cpu().tolist()
    result = rank_visual_class_scores(dict(zip(labels, similarities)))
    result.update({
        "image_path": str(path),
        "model_name": model_name,
        "evidence_source": "zero_shot_image_model",
        "limitations": [
            "Photo appearance does not determine spectral reflectance or transmittance.",
            "Reflections vary with time, weather, camera angle and surrounding scene.",
            "Do not use this result without human review and, where possible, manufacturer specifications or instrument measurements.",
        ],
    })
    return result
