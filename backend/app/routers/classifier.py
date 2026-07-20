import hashlib
import os
import time
import uuid
import io
import threading
import warnings
from collections import OrderedDict
from typing import Optional

import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError

from app.auth import get_current_user
from app.db import log_scan
from app.device_profiles import co2_profiles, DEVICE_PROFILES
from app.model import EWasteClassifier, DEFAULT_MODEL
from app.logging_config import get_logger

logger = get_logger("ewaste.classifier")

router = APIRouter(prefix="/classifier", tags=["Classifier"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MiB
UPLOAD_CHUNK_SIZE = 64 * 1024
MAX_DECODED_PIXELS = 25_000_000
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": frozenset({"JPEG"}),
    "image/jpg": frozenset({"JPEG"}),
    "image/pjpeg": frozenset({"JPEG"}),
    "image/png": frozenset({"PNG"}),
    "image/x-png": frozenset({"PNG"}),
    "image/webp": frozenset({"WEBP"}),
}
SUPPORTED_IMAGE_FORMATS = frozenset(
    image_format
    for formats in SUPPORTED_IMAGE_TYPES.values()
    for image_format in formats
)

# ── Per-user scan rate limiting (Req 11) ────────────────────────────────────
SCAN_RATE_LIMIT = int(os.getenv("SCAN_RATE_LIMIT", "30"))  # requests per window
RATE_WINDOW_SECONDS = 60


class RateLimiter:
    """Per-user fixed-window counter. Thread-safe, in-process, zero deps."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, user_id: str) -> bool:
        """Return True if allowed, False if the user is over the limit."""
        now = time.time()
        with self._lock:
            bucket = [t for t in self._hits.get(user_id, []) if now - t < self.window]
            if len(bucket) >= self.limit:
                self._hits[user_id] = bucket
                return False
            bucket.append(now)
            self._hits[user_id] = bucket
            return True

    def remaining(self, user_id: str) -> int:
        """Return how many requests the user has left in the current window."""
        now = time.time()
        with self._lock:
            used = len([t for t in self._hits.get(user_id, []) if now - t < self.window])
            return max(0, self.limit - used)


scan_limiter = RateLimiter(SCAN_RATE_LIMIT, RATE_WINDOW_SECONDS)

# Lazy initialization is single-flight. Although EWasteClassifier itself is
# lightweight, keeping construction coordinated avoids duplicate wrappers and
# permits recovery if initialization ever fails.
_MODEL_INIT_RETRY_SECONDS = 5.0
_model_condition = threading.Condition()
_model = None
_model_initializing = False
_model_load_failed = False
_model_retry_at = 0.0


def get_model():
    """Get one shared classifier, retrying initialization after a cooldown."""
    global _model, _model_initializing, _model_load_failed, _model_retry_at

    with _model_condition:
        while _model_initializing:
            _model_condition.wait()
        if _model is not None:
            return _model
        if _model_load_failed and time.monotonic() < _model_retry_at:
            return None
        _model_initializing = True

    try:
        candidate = EWasteClassifier()
    except Exception as exc:
        logger.error(f"Failed to initialize classifier: {exc}", exc_info=True)
        with _model_condition:
            _model_load_failed = True
            _model_retry_at = time.monotonic() + _MODEL_INIT_RETRY_SECONDS
            _model_initializing = False
            _model_condition.notify_all()
        return None

    with _model_condition:
        _model = candidate
        _model_load_failed = False
        _model_retry_at = 0.0
        _model_initializing = False
        _model_condition.notify_all()
        return _model


def warm_model():
    """Preload model weights and run one tiny forward pass so the first real
    scan doesn't pay the cold-start cost (weight loading + graph warmup).

    Safe to call in a background thread at startup; failures are non-fatal."""
    try:
        from app.model import _load_model

        clf = _load_model()  # loads weights — the slow, one-time cost
        dummy = Image.new("RGB", (64, 64), (120, 120, 120))
        clf(dummy, candidate_labels=["electronic device", "background"])
        logger.info("Classifier model warmed up and ready")
    except Exception as e:
        logger.warning(f"Classifier warmup skipped: {e}")


E_WASTE_CLASSES = sorted(DEVICE_PROFILES.keys())

# Derived from shared device_profiles — {device: {manufacturing, annual, recycling}}
CO2_PROFILES = co2_profiles()

# All e-waste devices contain hazardous components under E-Waste (Management) Rules, 2022.
# Lead (solder/PCBs), Mercury (CCFL backlights), Cadmium (batteries/chips),
# Lithium (batteries — fire hazard), Brominated Flame Retardants (plastics).
E_WASTE_HAZARD = [
    "Motherboard", "Smartphone", "Computer", "Printer", "Monitor",
    "Television", "Air Conditioner", "Laptop", "Hard Disk / SSD",
    "Keyboard", "Mouse", "Projector", "Router / Switch",
    "Microwave", "Camera", "Smartwatch", "Battery",
    "Washing Machine", "Refrigerator", "Remote Control",
]

# Recyclability tier per device — High = standard e-waste recycling recovers most materials.
# Medium = needs specialized handling (refrigerants, toner, lamps). Low = limited recovery (burnt/composite).
RECYCLABILITY = {
    "Motherboard": "High",
    "Hard Disk / SSD": "High",
    "Monitor": "Medium",
    "Mouse": "High",
    "Keyboard": "High",
    "Smartphone": "High",
    "Computer": "High",
    "Printer": "Medium",
    "Projector": "Medium",
    "Router / Switch": "High",
    "Air Conditioner": "Medium",
    "Microwave": "Medium",
    "Television": "Medium",
    "Camera": "High",
    "Smartwatch": "High",
    "Laptop": "High",
    "Battery": "Medium",
    "Washing Machine": "Medium",
    "Refrigerator": "Medium",
    "Remote Control": "Medium",
}

# ── Map expanded zero-shot model labels → canonical CO2_PROFILES entity ───
LABEL_TO_ENTITY = {
    # Computing
    "laptop": "Laptop",
    "desktop computer": "Computer",
    "computer": "Computer",
    "motherboard": "Motherboard",
    "computer processor": "Motherboard",
    "cpu chip": "Motherboard",
    "processor chip": "Motherboard",
    "microprocessor": "Motherboard",
    "cpu": "Motherboard",
    "processor": "Motherboard",
    "ram module": "Motherboard",
    "graphics card": "Motherboard",
    "solid state drive": "Hard Disk / SSD",
    "hard disk drive": "Hard Disk / SSD",
    "hdd": "Hard Disk / SSD",
    "ssd": "Hard Disk / SSD",
    # Peripherals
    "computer mouse": "Mouse",
    "mouse": "Mouse",
    "mechanical keyboard": "Keyboard",
    "keyboard": "Keyboard",
    "computer monitor": "Monitor",
    "monitor": "Monitor",
    "display": "Monitor",
    "computer printer": "Printer",
    "printer": "Printer",
    "3d printer": "Printer",
    "computer projector": "Projector",
    "projector": "Projector",
    "webcam": "Camera",
    # Audio accessories: no dedicated Audio profile exists, so they map to the
    # small-wearable Smartwatch proxy for e-waste coverage (all contain PCBs +
    # small batteries/magnets). Add a proper Audio profile later for accuracy.
    "computer speakers": "Smartwatch",
    "headphones": "Smartwatch",
    "computer headset": "Smartwatch",
    # Networking
    "wireless router": "Router / Switch",
    "router": "Router / Switch",
    "network switch": "Router / Switch",
    "modem": "Router / Switch",
    "network cable": "Router / Switch",
    # Mobile & Wearables
    "smartphone": "Smartphone",
    "mobile phone": "Smartphone",
    "phone": "Smartphone",
    "tablet": "Smartphone",
    "smartwatch": "Smartwatch",
    "fitness tracker": "Smartwatch",
    # Earbuds are small wearable lithium-battery devices; the Smartwatch profile
    # (0.05 kg, small battery) is the closest e-waste proxy until a dedicated
    # Audio profile exists.
    "wireless earbuds": "Smartwatch",
    "bluetooth earbuds": "Smartwatch",
    "earbuds": "Smartwatch",
    # Home Electronics
    "television": "Television",
    "led tv": "Television",
    "smart tv": "Television",
    "tv": "Television",
    "microwave oven": "Microwave",
    "microwave": "Microwave",
    "air conditioner": "Air Conditioner",
    "ac": "Air Conditioner",
    "washing machine": "Washing Machine",
    "clothes washer": "Washing Machine",
    "laundry machine": "Washing Machine",
    "refrigerator": "Refrigerator",
    "fridge": "Refrigerator",
    "mini fridge": "Refrigerator",
    "freezer": "Refrigerator",
    "camera": "Camera",
    "digital camera": "Camera",
    "dslr camera": "Camera",
    "action camera": "Camera",
    # Power & Accessories
    "power bank": "Battery",
    "portable charger": "Battery",
    "battery pack": "Battery",
    "lithium battery": "Battery",
    "rechargeable battery": "Battery",
    "battery": "Battery",
    "remote control": "Remote Control",
    "tv remote": "Remote Control",
    "television remote control": "Remote Control",
    "ac remote": "Remote Control",
    "handheld remote": "Remote Control",
    "usb cable": "Router / Switch",
    "power adapter": "Router / Switch",
    "extension cord": "Router / Switch",
    "power strip": "Router / Switch",
    # Components
    "circuit board": "Motherboard",
    "electronic cable": "Router / Switch",
    "hdmi cable": "Router / Switch",
}


CACHE_MAX_SIZE = 500
CACHE_MAX_MEMORY_MB = int(os.getenv("CACHE_MAX_MEMORY_MB", "256"))


class LRUCache(OrderedDict):
    """Thread-safe LRU cache with both count and memory limits."""

    def __init__(self, maxsize=CACHE_MAX_SIZE, max_memory_mb=CACHE_MAX_MEMORY_MB):
        super().__init__()
        self.maxsize = maxsize
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_bytes = 0
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _estimate_size(self, value: dict) -> int:
        """Estimate memory size of cached result in bytes."""
        # Rough estimate: dict overhead + string values
        size = 500  # Base dict overhead
        for k, v in value.items():
            size += len(str(k)) + len(str(v)) + 100
        return size

    def get_item(self, key):
        with self._lock:
            if key not in self:
                self.misses += 1
                if (self.hits + self.misses) % 100 == 0:
                    logger.info(f"Cache stats: hits={self.hits}, misses={self.misses}, "
                              f"size={len(self)}, memory={self.current_memory_bytes / (1024*1024):.1f}MB")
                return None
            self.hits += 1
            self.move_to_end(key)
            return self[key]

    def set_item(self, key, value):
        with self._lock:
            value_size = self._estimate_size(value)

            # If key exists, update memory accounting
            if key in self:
                old_size = self[key].get('_cache_size', 0)
                self.current_memory_bytes -= old_size
                self.move_to_end(key)

            # Evict LRU items until we have space
            while len(self) > 0 and (
                len(self) >= self.maxsize or
                self.current_memory_bytes + value_size > self.max_memory_bytes
            ):
                evicted_key, evicted_val = self.popitem(last=False)
                evicted_size = evicted_val.get('_cache_size', 0)
                self.current_memory_bytes -= evicted_size
                logger.debug(f"Evicted cache entry: {evicted_key[:16]}... "
                           f"(freed {evicted_size / 1024:.1f}KB)")

            # Store value with size metadata
            value['_cache_size'] = value_size
            self[key] = value
            self.current_memory_bytes += value_size


cache = LRUCache()


class ScanResponse(BaseModel):
    analysis_id: str
    waste_status: str
    hazard_level: str
    recyclable: bool
    recyclability: str
    confidence: float
    entity: str
    group: str
    condition: str
    co2_delta: float
    processing_time: float
    model_used: str
    disposal_advice: str
    rejection_reason: Optional[str] = None


def _validate_claimed_content_type(content_type: Optional[str]) -> Optional[str]:
    """Normalize and validate the upload's declared media type."""
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized and normalized not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format. Use JPEG, PNG, or WebP.",
        )
    return normalized or None


def _read_upload_limited(file: UploadFile) -> bytes:
    """Stream an upload in bounded chunks without retaining more than 10 MiB."""
    contents = bytearray()
    while True:
        remaining = MAX_UPLOAD_SIZE - len(contents)
        # Once exactly at the limit, read one byte to distinguish EOF from an
        # oversized upload without appending that byte.
        read_size = min(UPLOAD_CHUNK_SIZE, remaining + 1)
        chunk = file.file.read(read_size)
        if not chunk:
            break
        if not isinstance(chunk, (bytes, bytearray)):
            raise HTTPException(status_code=400, detail="Invalid upload stream.")
        if len(chunk) > remaining:
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum size is 10MB.",
            )
        contents.extend(chunk)

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    return bytes(contents)


def _decode_uploaded_image(
    contents: bytes,
    content_type: Optional[str],
) -> Image.Image:
    """Validate format and dimensions, then return a fully decoded image.

    Pillow's decompression-bomb warning is promoted to an exception. The lower
    application pixel cap is checked before decoding pixel data.
    """
    claimed_type = _validate_claimed_content_type(content_type)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as probe:
                image_format = (probe.format or "").upper()
                if image_format not in SUPPORTED_IMAGE_FORMATS:
                    raise HTTPException(
                        status_code=415,
                        detail="Unsupported image format. Use JPEG, PNG, or WebP.",
                    )
                if (
                    claimed_type is not None
                    and image_format not in SUPPORTED_IMAGE_TYPES[claimed_type]
                ):
                    raise HTTPException(
                        status_code=415,
                        detail="Uploaded content does not match its image type.",
                    )

                width, height = probe.size
                if width <= 0 or height <= 0:
                    raise HTTPException(status_code=400, detail="Invalid image dimensions.")
                if width * height > MAX_DECODED_PIXELS:
                    raise HTTPException(
                        status_code=413,
                        detail="Image dimensions exceed the safe pixel limit.",
                    )
                probe.verify()

            # ``verify`` intentionally invalidates the first decoder, so reopen
            # and force a full decode to catch truncation/corruption now.
            with Image.open(io.BytesIO(contents)) as decoded:
                if decoded.width * decoded.height > MAX_DECODED_PIXELS:
                    raise HTTPException(
                        status_code=413,
                        detail="Image dimensions exceed the safe pixel limit.",
                    )
                decoded.load()
                return decoded.copy()
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(
            status_code=413,
            detail="Image dimensions exceed the safe pixel limit.",
        )
    except MemoryError:
        raise HTTPException(
            status_code=413,
            detail="Image is too large to decode safely.",
        )
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image file.",
        )


def detect_condition(image: Image.Image) -> str:
    """Heuristic physical-condition estimate from cheap image statistics.

    Combines brightness (mean), contrast (std), and edge energy (Laplacian
    variance). Conservative: returns "good" unless multiple signals agree on
    damage. NOTE: this infers condition from global image statistics, not
    actual physical damage detection.
    """
    try:
        gray = np.asarray(image.convert("L"), dtype=np.float64)
        brightness = gray.mean()
        contrast = gray.std()
        lap = (gray[1:-1, 1:-1] * -4 + gray[:-2, 1:-1] + gray[2:, 1:-1]
               + gray[1:-1, :-2] + gray[1:-1, 2:])
        edge_energy = lap.var()

        # "burnt": very dark AND low edge/contrast (charred, featureless)
        if brightness < 45 and contrast < 35 and edge_energy < 80:
            return "burnt"
        # "damaged": moderately dark with low contrast (only when both agree)
        if brightness < 95 and contrast < 30:
            return "damaged"
        return "good"
    except Exception:
        return "good"


def get_recyclability(entity: str, condition: str) -> tuple[bool, str]:
    """Return (is_recyclable, tier). Burnt items drop one tier."""
    if entity == "Unrecognized":
        return False, "Unknown"
    base = RECYCLABILITY.get(entity, "Medium")
    if condition == "burnt":
        downgrade = {"High": "Medium", "Medium": "Low", "Low": "Low"}
        base = downgrade.get(base, "Low")
    return True, base


def get_disposal_advice(entity: str, hazard_level: str, condition: str, recyclability: str) -> str:
    if entity == "Unrecognized":
        return "Image was not clear enough to identify the device. Please upload a clearer photo."

    if recyclability == "High":
        recover = " Most materials can be recovered through standard e-waste recycling."
    elif recyclability == "Medium":
        recover = " Requires specialized handling (e.g., refrigerants, toner, lamps) — use a certified recycler."
    else:
        recover = " Material recovery is limited; ensure hazardous components are isolated."

    base = f"This {entity} contains hazardous components (lead, mercury, cadmium, lithium, or flame retardants). Hand it over to a certified e-waste recycler authorized under E-Waste (Management) Rules, 2022."

    if condition == "burnt":
        return base + recover + " Note: The device appears burnt — handle with care during transport."
    if condition == "damaged":
        return base + recover + " Note: The device appears damaged — repair may not be feasible."
    return base + recover


def real_classification(
    contents: bytes,
    image: Optional[Image.Image] = None,
) -> dict:
    model = get_model()

    if model is None:
        return {
            "entity": "Unrecognized",
            "group": "Unknown",
            "condition": "model unavailable",
            "confidence": 0.0,
            "waste_status": "Unknown",
            "hazard_level": "Unknown",
            "co2_delta": 0.0,
            "model_used": "none",
            "rejection_reason": "model_unavailable",
        }

    owns_image = False
    try:
        if image is None:
            image = _decode_uploaded_image(contents, None)
            owns_image = True
        entity, confidence, model_used = model.predict(image, return_confidence=True)

        # Handle 3-stage pipeline rejections
        if entity == "Unrecognized" or model_used.startswith("rejected_"):
            rejection_messages = {
                "rejected_image_too_small": "Image is too small to analyze. Please upload a larger photo.",
                "rejected_image_too_dark": "Image is too dark. Please upload a brighter photo.",
                "rejected_image_too_blurry": "Image is too blurry. Please upload a clearer photo.",
                "rejected_image_low_contrast": "Image has very low contrast. Please upload a clearer photo.",
                "rejected_non_electronic": "This image does not appear to contain an electronic device or e-waste item.",
                "siglip_low_confidence": "Could not identify the device with enough confidence. Please upload a clearer photo of the device.",
                "siglip_ambiguous": "The image is ambiguous — could not confidently determine the device type. Please try a different angle.",
                "clip_low_confidence": "Could not identify the device with enough confidence. Please upload a clearer photo of the device.",
                "clip_ambiguous": "The image is ambiguous — could not confidently determine the device type. Please try a different angle.",
                "none": "Image could not be processed. Please upload a valid image.",
                "error": "An error occurred during classification. Please try again.",
            }
            # Normalize the rejection reason for the frontend (non_electronic / low_confidence / etc.)
            if model_used.startswith("rejected_"):
                rejection_reason = model_used.replace("rejected_", "")
            else:
                rejection_reason = model_used
            return {
                "entity": "Unrecognized",
                "group": "Unknown",
                "condition": rejection_messages.get(model_used, "Image could not be classified."),
                "confidence": round(float(confidence), 3),
                "waste_status": "Unknown",
                "hazard_level": "Unknown",
                "co2_delta": 0.0,
                "model_used": model_used,
                "rejection_reason": rejection_reason,
            }

        # Successful classification — normalize entity
        entity = LABEL_TO_ENTITY.get(entity.lower(), entity)
        entity_map = {k.lower(): k for k in CO2_PROFILES.keys()}
        normalized_entity = entity_map.get(entity.lower(), entity)

        condition = detect_condition(image)
        confidence = round(float(confidence), 3)

        co2_profile = CO2_PROFILES.get(normalized_entity, {"recycling": 10})
        co2_delta = co2_profile.get("recycling", 10)

        waste_status = "E-Waste" if normalized_entity in CO2_PROFILES else "Non-E-Waste"
        hazard_level = "Hazardous" if normalized_entity in E_WASTE_HAZARD else "Non-Hazardous"

        return {
            "entity": normalized_entity,
            "group": "Electronics",
            "condition": condition,
            "confidence": confidence,
            "waste_status": waste_status,
            "hazard_level": hazard_level,
            "co2_delta": co2_delta,
            "model_used": model_used,
            "rejection_reason": None,
        }
    except Exception as e:
        logger.error(f"Model prediction failed: {e}", exc_info=True)
        return {
            "entity": "Unrecognized",
            "group": "Unknown",
            "condition": "An error occurred during classification.",
            "confidence": 0.0,
            "waste_status": "Unknown",
            "hazard_level": "Unknown",
            "co2_delta": 0.0,
            "model_used": "error",
            "rejection_reason": "error",
        }
    finally:
        if owns_image and image is not None:
            image.close()


def _is_cacheable_classification(result: dict) -> bool:
    """Exclude transient model availability/prediction failures from cache."""
    model_used = str(result.get("model_used", "")).lower()
    rejection_reason = str(result.get("rejection_reason", "")).lower()
    return (
        model_used not in {"none", "error"}
        and rejection_reason not in {"model_unavailable", "error"}
    )


@router.post("/scan", response_model=ScanResponse)
def scan_image(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    if not scan_limiter.check(user_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {SCAN_RATE_LIMIT} scans per minute. Please wait and try again.",
        )

    start_time = time.time()
    claimed_type = _validate_claimed_content_type(file.content_type)
    contents = _read_upload_limited(file)
    image = _decode_uploaded_image(contents, claimed_type)

    file_hash = hashlib.sha256(contents).hexdigest()

    cached = cache.get_item(file_hash)
    if cached is not None:
        image.close()
        result = cached.copy()
        result.pop('_cache_size', None)  # Remove internal metadata
        result["analysis_id"] = str(uuid.uuid4())
        result["processing_time"] = round(time.time() - start_time, 3)
        if result.get("entity") and result["entity"] != "Unrecognized":
            log_scan(
                filename=file.filename,
                waste_status=result["waste_status"],
                hazard_level=result["hazard_level"],
                confidence=result["confidence"],
                entity=result["entity"],
                group_name=result["group"],
                condition=result["condition"],
                co2_delta=result["co2_delta"],
                processing_time=result["processing_time"],
                recyclability=result.get("recyclability"),
                model_used=result.get("model_used"),
                user_id=user_id,
            )

        # Calculate remaining scans
        remaining = scan_limiter.remaining(user_id)

        response = JSONResponse(content=result)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + RATE_WINDOW_SECONDS)
        return response

    try:
        cls = real_classification(contents, image=image)
    finally:
        image.close()

    if cls.get("rejection_reason") in {"model_unavailable", "error"}:
        raise HTTPException(
            status_code=503,
            detail="Classifier model is not ready. Check /health/ready or run diagnostics.",
        )

    recyclable, recyclability = get_recyclability(cls["entity"], cls["condition"])
    advice = get_disposal_advice(cls["entity"], cls["hazard_level"], cls["condition"], recyclability)

    result = {
        "analysis_id": str(uuid.uuid4()),
        "waste_status": cls["waste_status"],
        "hazard_level": cls["hazard_level"],
        "recyclable": recyclable,
        "recyclability": recyclability,
        "confidence": cls["confidence"],
        "entity": cls["entity"],
        "group": cls["group"],
        "condition": cls["condition"],
        "co2_delta": cls["co2_delta"],
        "processing_time": round(time.time() - start_time, 3),
        "model_used": cls["model_used"],
        "disposal_advice": advice,
        "rejection_reason": cls.get("rejection_reason"),
    }

    if _is_cacheable_classification(cls):
        cache.set_item(file_hash, result.copy())

    if cls["entity"] != "Unrecognized":
        log_scan(
            filename=file.filename,
            waste_status=cls["waste_status"],
            hazard_level=cls["hazard_level"],
            confidence=cls["confidence"],
            entity=cls["entity"],
            group_name=cls["group"],
            condition=cls["condition"],
            co2_delta=cls["co2_delta"],
            processing_time=result["processing_time"],
            recyclability=recyclability,
            model_used=cls["model_used"],
            user_id=user_id,
        )

    # Calculate remaining scans
    remaining = scan_limiter.remaining(user_id)

    response = JSONResponse(content=result)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + RATE_WINDOW_SECONDS)
    return response


@router.get("/classes")
async def get_classes():
    return {"classes": E_WASTE_CLASSES}


@router.get("/metrics")
async def get_metrics(user_id: str = Depends(get_current_user)):
    """Performance metrics for the classifier (auth required)."""
    return {
        "cache_size": len(cache),
        "cache_hits": cache.hits,
        "cache_misses": cache.misses,
        "cache_hit_rate": round(cache.hits / max(1, cache.hits + cache.misses), 3),
        "cache_memory_mb": round(cache.current_memory_bytes / (1024 * 1024), 2),
        "cache_memory_limit_mb": CACHE_MAX_MEMORY_MB,
        "model_preset": DEFAULT_MODEL,
        "rate_limit": SCAN_RATE_LIMIT,
    }
