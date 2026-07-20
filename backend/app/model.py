"""Three-stage zero-shot e-waste image-classification pipeline.

Stage 0 applies deterministic image-quality heuristics, stage 1 uses a
pre-trained vision-language model as an electronics gate, and stage 2 maps
model prompt scores to 20 canonical device categories with rejection
thresholds. The default preset is ``google/siglip2-base-patch16-224``; larger
SigLIP 2 and CLIP presets can be selected with ``EWASTE_MODEL``.

Preset size labels describe architecture and resource needs only. This project
contains no committed comparative real-image benchmark, so the presets must not
be described as more accurate on this application's target population.
"""

import math
import os
import threading
import time
from typing import Tuple, Optional, Dict, Any

import numpy as np

# NOTE: `torch` is imported lazily inside _load_model() rather than here. It is
# only needed for the CUDA-availability check at model-load time, so deferring
# the import keeps module import cheap (no ~200MB torch load just to import the
# classifier) and lets the pure-logic unit tests run without torch installed.
from PIL import Image
from app.logging_config import get_logger
from app.runtime import classifier_model_path, verify_file_manifest

logger = get_logger("ewaste.model")


# ── Model Configuration ──────────────────────────────────────────
MODEL_PRESETS = {
    # SigLIP 2 So400m presets. Resolution and memory differ; this repository
    # does not contain a comparative target-domain benchmark.
    "siglip2-so400m-512": {
        "model_id": "google/siglip2-so400m-patch16-512",
        "image_size": 512,
        "memory_mb": 4200,       # ~1B params fp32; needs a paid/standard instance
        "is_clip": False,
    },
    "siglip2-so400m-384": {
        "model_id": "google/siglip2-so400m-patch16-384",
        "image_size": 384,
        "memory_mb": 3900,
        "is_clip": False,
    },
    "siglip2-so400m-256": {
        "model_id": "google/siglip2-so400m-patch16-256",
        "image_size": 256,
        "memory_mb": 3600,
        "is_clip": False,
    },
    # SigLIP 2 Giant: largest listed preset and the highest memory requirement.
    "siglip2-giant-384": {
        "model_id": "google/siglip2-giant-opt-patch16-384",
        "image_size": 384,
        "memory_mb": 8500,
        "is_clip": False,
    },
    # SigLIP 2 Large: a separate large-backbone preset.
    "siglip2-large-512": {
        "model_id": "google/siglip2-large-patch16-512",
        "image_size": 512,
        "memory_mb": 3600,
        "is_clip": False,
    },
    # ── SigLIP 2 Base — lightweight fallback for low-memory / CPU-only hosts ──
    "siglip2-base": {
        "model_id": "google/siglip2-base-patch16-224",
        "image_size": 224,
        "memory_mb": 400,        # ~375-400MB est
        "is_clip": False,
    },
    # ── Aliases / legacy presets (retained for backward compatibility) ──
    "siglip2-so400m": {  # alias -> So400m 256
        "model_id": "google/siglip2-so400m-patch16-256",
        "image_size": 256,
        "memory_mb": 3600,
        "is_clip": False,
    },
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

# Default to a CPU-friendly, free-tier-safe model. Normalize the configured
# name first so every derived setting (including family thresholds and metrics)
# describes the model that will actually load.
FALLBACK_MODEL = "siglip2-base"


def _normalize_model_name(configured_name: Optional[str]) -> str:
    """Return a known preset name, falling back to the documented default."""
    normalized = (configured_name or "").strip().lower()
    if normalized in MODEL_PRESETS:
        return normalized
    if normalized:
        logger.warning(
            f"Unknown EWASTE_MODEL={configured_name!r}; using {FALLBACK_MODEL}"
        )
    return FALLBACK_MODEL


REQUESTED_MODEL = os.getenv("EWASTE_MODEL", FALLBACK_MODEL)
DEFAULT_MODEL = _normalize_model_name(REQUESTED_MODEL)
MODEL_PRESET = MODEL_PRESETS[DEFAULT_MODEL]
MODEL_ID = MODEL_PRESET["model_id"]
IMAGE_SIZE = MODEL_PRESET["image_size"]
IS_CLIP_MODEL = MODEL_PRESET["is_clip"]
LOCAL_MODEL_PATH = classifier_model_path(DEFAULT_MODEL)
MODEL_SOURCE = str(LOCAL_MODEL_PATH) if LOCAL_MODEL_PATH is not None else MODEL_ID

# ── Threshold calibration by model family ───────────────────────
# Thresholds are selected by model family because CLIP softmax and SigLIP
# sigmoid scores are not directly comparable. These are rejection heuristics,
# not calibrated probabilities; target-domain evaluation is required before
# changing or interpreting them.
def _model_family(preset_name: str, is_clip: bool) -> str:
    """Return the calibration family for a preset: 'clip', 'siglip2', or 'siglip'."""
    if is_clip:
        return "clip"
    if preset_name.startswith("siglip2"):
        return "siglip2"
    return "siglip"


THRESHOLDS = {
    "clip":    dict(CLASSIFY=0.40, CLASSIFY_LOW=0.25, ELECTRONIC=0.40, ELECTRONIC_MARGIN=0.15, MARGIN=0.15),
    "siglip":  dict(CLASSIFY=0.30, CLASSIFY_LOW=0.15, ELECTRONIC=0.30, ELECTRONIC_MARGIN=0.12, MARGIN=0.10),
    # Larger SigLIP 2 presets (So400m / Large / Giant) produce well-separated,
    # higher sigmoid scores, so they keep firm thresholds.
    "siglip2": dict(CLASSIFY=0.35, CLASSIFY_LOW=0.18, ELECTRONIC=0.33, ELECTRONIC_MARGIN=0.13, MARGIN=0.12),
    # SigLIP 2 *base* emits much lower absolute sigmoid scores (~0.01-0.10),
    # so the firm thresholds above would reject almost everything. We use a low
    # absolute floor and lean on the positive-vs-negative MARGIN instead.
    "siglip2_base": dict(CLASSIFY=0.020, CLASSIFY_LOW=0.010, ELECTRONIC=0.015, ELECTRONIC_MARGIN=0.004, MARGIN=0.004),
}


def _threshold_key(preset_name: str, family: str) -> str:
    """Base SigLIP 2 needs its own low-score calibration; others use family."""
    if family == "siglip2" and "base" in preset_name:
        return "siglip2_base"
    return family


def _threshold_from_env(name: str, default: float) -> float:
    """Read a finite [0, 1] threshold override or retain ``default``."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = float(raw_value)
    except ValueError:
        logger.warning(f"Ignoring invalid {name}={raw_value!r}; using {default}")
        return default
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        logger.warning(f"Ignoring out-of-range {name}={raw_value!r}; using {default}")
        return default
    return value


FAMILY = _model_family(DEFAULT_MODEL, IS_CLIP_MODEL)
_t = THRESHOLDS[_threshold_key(DEFAULT_MODEL, FAMILY)]
CLASSIFY_THRESHOLD = _threshold_from_env("CLASSIFY_THRESHOLD", _t["CLASSIFY"])
CLASSIFY_LOW_THRESHOLD = _t["CLASSIFY_LOW"]
ELECTRONIC_THRESHOLD = _threshold_from_env("ELECTRONIC_THRESHOLD", _t["ELECTRONIC"])
ELECTRONIC_MARGIN = _t["ELECTRONIC_MARGIN"]
MARGIN_THRESHOLD = _threshold_from_env("MARGIN_THRESHOLD", _t["MARGIN"])


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
    "Motherboard":    ["motherboard", "computer circuit board", "GPU graphics card", "RAM memory module", "computer processor", "CPU chip", "processor chip", "microprocessor"],
    "Hard Disk / SSD":["hard disk drive", "solid state drive", "SSD", "HDD", "computer storage"],
    "Air Conditioner":["air conditioner", "split AC", "window AC", "HVAC unit"],
    "Television":     ["television", "TV set", "LED TV", "smart TV"],
    "Microwave":      ["microwave oven", "microwave"],
    "Camera":         ["digital camera", "DSLR camera", "webcam", "action camera"],
    "Smartwatch":     ["smartwatch", "fitness tracker", "wearable device"],
    "Battery":        ["lithium battery", "power bank", "portable charger", "battery pack", "rechargeable battery"],
    "Washing Machine":["washing machine", "clothes washer", "laundry machine"],
    "Refrigerator":   ["refrigerator", "fridge", "mini fridge", "freezer"],
    "Remote Control": ["remote control", "TV remote", "television remote control", "AC remote", "handheld remote"],
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
    "remote control or handheld electronic gadget",
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
# functools.lru_cache protects its dictionary but does not make cache misses
# single-flight: concurrent misses may each construct a multi-GB pipeline. This
# condition owns explicit loading/failure state so exactly one caller loads and
# failures can be retried after a controlled cooldown.
_MODEL_LOAD_RETRY_SECONDS = 30.0
_model_load_condition = threading.Condition()
_model_pipeline = None
_model_load_in_progress = False
_model_load_error: Optional[str] = None
_model_retry_at = 0.0


def model_load_status() -> dict:
    """Return a sanitized snapshot used by readiness and diagnostics."""
    with _model_load_condition:
        if _model_pipeline is not None:
            state = "ready"
        elif _model_load_in_progress:
            state = "loading"
        elif _model_load_error is not None:
            state = "error"
        else:
            state = "not_loaded"
        return {
            "state": state,
            "preset": DEFAULT_MODEL,
            "source": "bundled" if LOCAL_MODEL_PATH is not None else "huggingface",
            "error": "model load failed" if _model_load_error is not None else None,
        }


def _build_model_pipeline():
    """Construct the Hugging Face pipeline from a verified local release asset."""
    if LOCAL_MODEL_PATH is not None:
        if not LOCAL_MODEL_PATH.is_dir():
            raise RuntimeError("Bundled classifier model directory is missing")
        verified, errors = verify_file_manifest(LOCAL_MODEL_PATH)
        if not verified:
            logger.error("Bundled classifier verification failed: %s", "; ".join(errors))
            raise RuntimeError("Bundled classifier model failed integrity verification")
        # A packaged snapshot must never fall back to the network. The local
        # source-development path remains online when LOCAL_MODEL_PATH is None.
        os.environ["HF_HUB_OFFLINE"] = "1"

    import torch  # heavy import — deferred until release assets pass verification
    from transformers import pipeline as hf_pipeline

    logger.info("Loading model: %s", MODEL_SOURCE)
    logger.info("Model type: %s", "CLIP" if IS_CLIP_MODEL else "SigLIP")
    logger.info("Image size: %sx%s", IMAGE_SIZE, IMAGE_SIZE)

    device = 0 if torch.cuda.is_available() else -1
    offline_kwargs = {"local_files_only": True} if LOCAL_MODEL_PATH is not None else {}
    pipeline = hf_pipeline(
        "zero-shot-image-classification",
        model=MODEL_SOURCE,
        device=device,
        **offline_kwargs,
    )
    logger.info("Model loaded on %s", "GPU" if device == 0 else "CPU")
    return pipeline


def _load_model():
    """Lazy-load the model once, with shared waiters and cooldown recovery."""
    global _model_pipeline, _model_load_in_progress
    global _model_load_error, _model_retry_at

    with _model_load_condition:
        while _model_load_in_progress:
            _model_load_condition.wait()

        if _model_pipeline is not None:
            return _model_pipeline

        now = time.monotonic()
        if _model_load_error is not None and now < _model_retry_at:
            wait_seconds = max(0.0, _model_retry_at - now)
            raise RuntimeError(
                f"Model load retry available in {wait_seconds:.1f}s: {_model_load_error}"
            )
        _model_load_in_progress = True

    try:
        pipeline = _build_model_pipeline()
    except Exception as exc:
        logger.error(f"Failed to load {MODEL_ID}: {exc}", exc_info=True)
        with _model_load_condition:
            _model_load_error = f"{type(exc).__name__}: {exc}"
            _model_retry_at = time.monotonic() + _MODEL_LOAD_RETRY_SECONDS
            _model_load_in_progress = False
            _model_load_condition.notify_all()
        raise

    with _model_load_condition:
        _model_pipeline = pipeline
        _model_load_error = None
        _model_retry_at = 0.0
        _model_load_in_progress = False
        _model_load_condition.notify_all()
        return _model_pipeline


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

    # Blur check via Laplacian variance (edge detection)
    # Checked BEFORE contrast because heavy blur reduces contrast,
    # so a blurry image would otherwise fail the contrast check first
    # and the blur gate would never fire.
    # Pure numpy interior Laplacian — avoids PIL FIND_EDGES border artifacts
    # (zero-padded kernel inflates variance ~200x for uniform images).
    lap = pixels[1:-1, 1:-1] * (-4) + pixels[:-2, 1:-1] + pixels[2:, 1:-1] + pixels[1:-1, :-2] + pixels[1:-1, 2:]
    blur_score = lap.var()
    if blur_score < 5.0:
        return {"ok": False, "reason": "image_too_blurry"}

    # Contrast check
    contrast = pixels.std()
    if contrast < 18:
        return {"ok": False, "reason": "image_low_contrast"}

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

        # Transformers returns the formatted candidate label. Include both
        # forms so CLIP's ``a photo of ...`` template still maps to the original
        # positive/negative group.
        formatted_positive = frozenset(
            label.strip().lower()
            for label in all_prompts_formatted[:len(POSITIVE_ELECTRONICS)]
        )
        formatted_negative = frozenset(
            label.strip().lower()
            for label in all_prompts_formatted[len(POSITIVE_ELECTRONICS):]
        )
        positive_labels = _POS_SET | formatted_positive
        negative_labels = _NEG_SET | formatted_negative

        pos_scores = []
        neg_scores = []
        for r in results:
            label = r["label"].strip().lower()
            score = float(r["score"])
            if label in positive_labels:
                pos_scores.append(score)
            elif label in negative_labels:
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
        logger.warning(f"Electronics gate failed: {e}", exc_info=True)
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
        logger.error(f"Device classification failed: {e}", exc_info=True)
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
        self._load_lock = threading.Lock()

    def _ensure_loaded(self):
        """Ensure this wrapper shares the process-wide loaded pipeline."""
        if self._classifier is None:
            with self._load_lock:
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
            # Fallback: the broad electronics gate can miss close-up or
            # partially-disassembled devices (e.g. an opened computer mouse
            # showing its PCB, a bare circuit board). Defer to Stage 2 — if the
            # fine-grained classifier still confidently identifies a specific
            # device (passes both confidence AND margin thresholds), trust it.
            # Genuine non-electronic images won't match a specific device with
            # margin, so they remain correctly rejected.
            fallback = classify_device(image)
            if fallback["model_used"] in ("clip", "siglip"):
                if return_confidence:
                    return (fallback["entity"], fallback["confidence"], fallback["model_used"])
                return fallback["entity"]
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
