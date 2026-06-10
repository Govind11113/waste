"""
E-Waste Image Classifier — 3-stage zero-shot pipeline
=====================================================

Stage 0: Image quality gate (reject blurry/dark/small images)
Stage 1: Electronics gate (reject non-electronic images)
Stage 2: Fine-grained device classification with confidence/margin rejection

Default Model: google/siglip-base-patch16-224 (~350MB)
- Better zero-shot accuracy than CLIP
- Sigmoid-based loss (better calibration)
- CPU-friendly

Optional Models (set EWASTE_MODEL env var):
- clip-base:       openai/clip-vit-base-patch32      (~1.1GB)
- siglip-so400m:   google/siglip-so400m-patch14-384  (~900MB, best accuracy)
"""

import os
from typing import Tuple, Optional, Dict, Any
from functools import lru_cache
import numpy as np

import torch
from PIL import Image, ImageFilter


# ── Model Configuration ──────────────────────────────────────────
MODEL_PRESETS = {
    "siglip-base": {
        "model_id": "google/siglip-base-patch16-224",
        "image_size": 224,
        "memory_mb": 350,
        "is_clip": False,
    },
    "clip-base": {
        "model_id": "openai/clip-vit-base-patch32",
        "image_size": 224,
        "memory_mb": 1100,
        "is_clip": True,
    },
    "siglip-so400m": {
        "model_id": "google/siglip-so400m-patch14-384",
        "image_size": 384,
        "memory_mb": 900,
        "is_clip": False,
    },
}

DEFAULT_MODEL = os.getenv("EWASTE_MODEL", "siglip-base")
MODEL_PRESET = MODEL_PRESETS.get(DEFAULT_MODEL, MODEL_PRESETS["siglip-base"])
MODEL_ID = MODEL_PRESET["model_id"]
IMAGE_SIZE = MODEL_PRESET["image_size"]
IS_CLIP_MODEL = MODEL_PRESET["is_clip"]

# Thresholds (SigLIP uses sigmoid, CLIP uses softmax — different calibration)
if IS_CLIP_MODEL:
    CLASSIFY_THRESHOLD = 0.30
    CLASSIFY_LOW_THRESHOLD = 0.15
    ELECTRONIC_THRESHOLD = 0.28
    ELECTRONIC_MARGIN = 0.08
    MARGIN_THRESHOLD = 0.07
else:
    CLASSIFY_THRESHOLD = 0.20
    CLASSIFY_LOW_THRESHOLD = 0.10
    ELECTRONIC_THRESHOLD = 0.18
    ELECTRONIC_MARGIN = 0.05
    MARGIN_THRESHOLD = 0.04


# ── Canonical entity prompt groups ──────────────────────────────
# Each entity has multiple aliases for more robust classification.
# The model scores each alias and we take the max per entity.
ENTITY_PROMPTS: Dict[str, list] = {
    "Laptop":         ["laptop", "notebook computer", "portable computer"],
    "Computer":       ["desktop computer", "personal computer", "computer tower", "PC"],
    "Smartphone":     ["smartphone", "mobile phone", "cell phone", "phone"],
    "Monitor":        ["computer monitor", "display screen", "desktop monitor", "computer display"],
    "Keyboard":       ["computer keyboard", "mechanical keyboard", "typing keyboard"],
    "Mouse":          ["computer mouse", "wired mouse", "wireless mouse"],
    "Printer":        ["computer printer", "inkjet printer", "laser printer", "3D printer"],
    "Projector":      ["projector", "video projector", "data projector"],
    "Router / Switch":["wireless router", "network switch", "modem", "networking device"],
    "Motherboard":    ["motherboard", "computer circuit board", "GPU graphics card", "RAM memory module"],
    "Hard Disk / SSD":["hard disk drive", "solid state drive", "SSD", "HDD", "computer storage"],
    "Air Conditioner":["air conditioner", "split AC", "window AC", "HVAC unit"],
    "Television":     ["television", "TV set", "LED TV", "smart TV"],
    "Microwave":      ["microwave oven", "microwave"],
    "Camera":         ["digital camera", "DSLR camera", "webcam", "action camera"],
    "Smartwatch":     ["smartwatch", "fitness tracker", "wearable device"],
    "Battery":        ["lithium battery", "power bank", "portable charger"],
}


# ── Electronics gate prompts ─────────────────────────────────────
POSITIVE_ELECTRONICS = [
    "electronic device",
    "consumer electronics",
    "household appliance",
    "computer accessory",
    "phone or tablet",
    "monitor or screen",
    "computer component",
    "IT equipment",
    "digital device",
    "battery or power supply",
]

NEGATIVE_ELECTRONICS = [
    "person",
    "animal",
    "food",
    "plant",
    "vehicle",
    "clothing",
    "furniture",
    "paper document",
    "toy",
    "outdoor landscape",
    "indoor room scene",
    "book",
    "building",
]

# Pre-computed sets for O(1) lookup (rebuilt once at import, not per request)
_POS_SET = frozenset(p.lower() for p in POSITIVE_ELECTRONICS)
_NEG_SET = frozenset(p.lower() for p in NEGATIVE_ELECTRONICS)

# Pre-built prompt list + entity map for classify_device (computed once)
_ALL_CLASSIFY_PROMPTS: list = []
_PROMPT_ENTITY_MAP: Dict[str, str] = {}
for _entity, _aliases in ENTITY_PROMPTS.items():
    for _alias in _aliases:
        _prompt = f"a photo of a {_alias}, electronic device" if IS_CLIP_MODEL else _alias
        _PROMPT_ENTITY_MAP[_prompt] = _entity
        _ALL_CLASSIFY_PROMPTS.append(_prompt)


# ── Model loading ────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_model():
    """Lazy-load the zero-shot image classification model."""
    try:
        from transformers import pipeline as hf_pipeline

        print(f"[model] Loading: {MODEL_ID}")
        print(f"[model] Type: {'CLIP' if IS_CLIP_MODEL else 'SigLIP'}")
        print(f"[model] Image size: {IMAGE_SIZE}x{IMAGE_SIZE}")

        device = 0 if torch.cuda.is_available() else -1

        classifier = hf_pipeline(
            "zero-shot-image-classification",
            model=MODEL_ID,
            device=device,
        )

        print(f"[model] Loaded on {'GPU' if device == 0 else 'CPU'}")
        return classifier

    except Exception as e:
        print(f"[model] Failed to load {MODEL_ID}: {e}")
        raise


# ── Stage 0: Image quality gate ──────────────────────────────────
def assess_image_quality(image: Image.Image) -> dict:
    """
    Check image quality before classification.
    Returns dict with 'ok' bool and 'reason' str if rejected.
    """
    w, h = image.size

    # Minimum size check
    if min(w, h) < 160:
        return {"ok": False, "reason": "image_too_small"}

    # Convert to grayscale for analysis
    gray = image.convert("L")
    pixels = np.array(gray, dtype=np.float64)

    # Brightness check
    brightness = pixels.mean()
    if brightness < 30:
        return {"ok": False, "reason": "image_too_dark"}

    # Contrast check
    contrast = pixels.std()
    if contrast < 18:
        return {"ok": False, "reason": "image_low_contrast"}

    # Blur check via Laplacian variance (edge detection)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_pixels = np.array(edges, dtype=np.float64)
    blur_score = edge_pixels.var()
    if blur_score < 45:
        return {"ok": False, "reason": "image_too_blurry"}

    return {"ok": True, "reason": None}


# ── Stage 1: Electronics gate ────────────────────────────────────
def gate_electronics(image: Image.Image) -> dict:
    """
    Broad zero-shot check: is this image an electronic device?
    Returns dict with 'is_electronic', 'electronic_score', 'non_electronic_score'.
    """
    classifier = _load_model()

    try:
        # Combine positive + negative prompts for a single pass
        all_prompts = POSITIVE_ELECTRONICS + NEGATIVE_ELECTRONICS

        if IS_CLIP_MODEL:
            all_prompts_formatted = [
                f"a photo of {p}" if not p.startswith("a ") else p
                for p in all_prompts
            ]
        else:
            all_prompts_formatted = all_prompts

        results = classifier(
            image,
            candidate_labels=all_prompts_formatted,
            multi_label=True,
        )

        # Separate scores using pre-computed frozensets
        pos_scores = []
        neg_scores = []
        for r in results:
            label = r["label"].strip().lower()
            score = float(r["score"])
            if label in _POS_SET:
                pos_scores.append(score)
            elif label in _NEG_SET:
                neg_scores.append(score)

        electronic_score = max(pos_scores) if pos_scores else 0.0
        non_electronic_score = max(neg_scores) if neg_scores else 0.0
        margin = electronic_score - non_electronic_score

        is_electronic = (
            electronic_score >= ELECTRONIC_THRESHOLD
            and margin >= ELECTRONIC_MARGIN
        )

        return {
            "is_electronic": is_electronic,
            "electronic_score": round(electronic_score, 4),
            "non_electronic_score": round(non_electronic_score, 4),
            "margin": round(margin, 4),
        }

    except Exception as e:
        print(f"[model] Electronics gate failed: {e}")
        # On error, allow classification to proceed (fail open)
        return {"is_electronic": True, "electronic_score": 0.5, "non_electronic_score": 0.0, "margin": 0.5}


# ── Stage 2: Fine-grained device classification ──────────────────
def classify_device(image: Image.Image) -> dict:
    """
    Classify into a specific electronic device category.
    Batches ALL aliases into a single model call for speed.
    Returns dict with 'entity', 'confidence', 'top2_entity', 'top2_confidence', 'model_used'.
    """
    classifier = _load_model()

    try:
        # Use pre-built prompt list + O(1) entity lookup (computed once at module import)
        results = classifier(
            image,
            candidate_labels=_ALL_CLASSIFY_PROMPTS,
            multi_label=False,
        )

        if not results:
            return {"entity": "Unrecognized", "confidence": 0.0, "top2_entity": None, "top2_confidence": 0.0, "model_used": "none"}

        # Aggregate scores by canonical entity (take max across aliases)
        entity_scores: Dict[str, float] = {}
        for r in results:
            prompt_label = r["label"].strip()
            score = float(r["score"])
            entity = _PROMPT_ENTITY_MAP.get(prompt_label)
            if entity:
                if entity not in entity_scores or score > entity_scores[entity]:
                    entity_scores[entity] = score

        if not entity_scores:
            return {"entity": "Unrecognized", "confidence": 0.0, "top2_entity": None, "top2_confidence": 0.0, "model_used": "none"}

        # Sort by score
        sorted_entities = sorted(entity_scores.items(), key=lambda x: x[1], reverse=True)
        top1_entity, top1_score = sorted_entities[0]
        top2_entity = sorted_entities[1][0] if len(sorted_entities) > 1 else None
        top2_score = sorted_entities[1][1] if len(sorted_entities) > 1 else 0.0

        model_used = "clip" if IS_CLIP_MODEL else "siglip"
        margin = top1_score - top2_score

        # Apply confidence + margin thresholds
        if top1_score < CLASSIFY_THRESHOLD:
            return {
                "entity": "Unrecognized",
                "confidence": round(top1_score, 4),
                "top2_entity": top2_entity,
                "top2_confidence": round(top2_score, 4),
                "model_used": f"{model_used}_low_confidence",
            }

        if margin < MARGIN_THRESHOLD:
            return {
                "entity": "Unrecognized",
                "confidence": round(top1_score, 4),
                "top2_entity": top2_entity,
                "top2_confidence": round(top2_score, 4),
                "model_used": f"{model_used}_ambiguous",
            }

        return {
            "entity": top1_entity,
            "confidence": round(top1_score, 4),
            "top2_entity": top2_entity,
            "top2_confidence": round(top2_score, 4),
            "model_used": model_used,
        }

    except Exception as e:
        print(f"[model] Device classification failed: {e}")
        return {"entity": "Unrecognized", "confidence": 0.0, "top2_entity": None, "top2_confidence": 0.0, "model_used": "error"}


# ── Main classifier class ────────────────────────────────────────
class EWasteClassifier:
    """
    3-stage e-waste image classifier:
      Stage 0: Image quality gate
      Stage 1: Electronics gate (reject non-electronic images)
      Stage 2: Fine-grained device classification with rejection
    """

    def __init__(self):
        self._classifier = None

    def _ensure_loaded(self):
        """Ensure the model is loaded (lazy initialization)."""
        if self._classifier is None:
            self._classifier = _load_model()

    def predict(self, image: Image.Image, return_confidence: bool = True) -> Tuple[str, float, str]:
        """
        Classify an electronic device from an image through the 3-stage pipeline.

        Returns:
            If return_confidence=True: (label, confidence, model_used)
            If return_confidence=False: label only
        """
        if image.mode != "RGB":
            image = image.convert("RGB")

        self._ensure_loaded()

        # ── Stage 0: Quality gate ──
        quality = assess_image_quality(image)
        if not quality["ok"]:
            reason = quality["reason"]
            return ("Unrecognized", 0.0, f"rejected_{reason}") if return_confidence else "Unrecognized"

        # ── Stage 1: Electronics gate ──
        gate = gate_electronics(image)
        if not gate["is_electronic"]:
            return ("Unrecognized", gate["electronic_score"], "rejected_non_electronic") if return_confidence else "Unrecognized"

        # ── Stage 2: Fine-grained device classification ──
        result = classify_device(image)
        entity = result["entity"]
        confidence = result["confidence"]
        model_used = result["model_used"]

        if return_confidence:
            return (entity, confidence, model_used)
        return entity


# Module-level instance for easy import
classifier = EWasteClassifier()
