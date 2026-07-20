"""Unit tests for the classifier router's pure logic (no model inference).

Covers recyclability tiering, disposal advice, the per-user rate limiter, the
memory-aware LRU cache, and the label→entity mapping we corrected. These do not
load the vision model — they exercise the plain-Python decision code only.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import threading

import pytest
from fastapi import HTTPException
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app import model as model_module
from app.routers import classifier as clf


# ── Recyclability tiering ───────────────────────────────────────────────────
def test_unrecognized_is_not_recyclable():
    recyclable, tier = clf.get_recyclability("Unrecognized", "good")
    assert recyclable is False
    assert tier == "Unknown"


def test_known_device_recyclable_tier():
    recyclable, tier = clf.get_recyclability("Laptop", "good")
    assert recyclable is True
    assert tier in ("High", "Medium", "Low")


def test_burnt_condition_downgrades_one_tier():
    # Laptop is normally "High"; burnt drops it to "Medium".
    _, good_tier = clf.get_recyclability("Laptop", "good")
    _, burnt_tier = clf.get_recyclability("Laptop", "burnt")
    order = {"High": 3, "Medium": 2, "Low": 1}
    assert order[burnt_tier] < order[good_tier]


# ── Disposal advice ─────────────────────────────────────────────────────────
def test_disposal_advice_mentions_certified_recycler():
    advice = clf.get_disposal_advice("Smartphone", "Hazardous", "good", "High")
    assert "certified" in advice.lower()


def test_disposal_advice_flags_burnt_handling():
    advice = clf.get_disposal_advice("Battery", "Hazardous", "burnt", "Medium")
    assert "burnt" in advice.lower()


def test_disposal_advice_unrecognized_asks_for_clearer_photo():
    advice = clf.get_disposal_advice("Unrecognized", "Unknown", "good", "Unknown")
    assert "clearer" in advice.lower()


# ── Label → entity mapping (regression on the mappings we reviewed) ─────────
def test_core_label_mappings_are_correct():
    assert clf.LABEL_TO_ENTITY["laptop"] == "Laptop"
    assert clf.LABEL_TO_ENTITY["smartphone"] == "Smartphone"
    assert clf.LABEL_TO_ENTITY["refrigerator"] == "Refrigerator"
    assert clf.LABEL_TO_ENTITY["washing machine"] == "Washing Machine"


def test_battery_maps_to_battery_not_smartphone():
    # Regression: Battery previously mis-mapped to Smartphone.
    assert clf.LABEL_TO_ENTITY["lithium battery"] == "Battery"
    assert clf.LABEL_TO_ENTITY["power bank"] == "Battery"


def test_all_mapping_targets_are_known_devices():
    # Every mapping target must be a real device profile key, otherwise the
    # carbon/hazard lookups downstream silently fall back to defaults.
    valid = set(clf.DEVICE_PROFILES.keys())
    for label, entity in clf.LABEL_TO_ENTITY.items():
        assert entity in valid, f"'{label}' maps to unknown device '{entity}'"


# ── Rate limiter ────────────────────────────────────────────────────────────
def test_rate_limiter_allows_up_to_limit_then_blocks():
    rl = clf.RateLimiter(limit=3, window=60)
    uid = "user-a"
    assert rl.check(uid) is True   # 1
    assert rl.check(uid) is True   # 2
    assert rl.check(uid) is True   # 3
    assert rl.check(uid) is False  # 4 — over the limit


def test_rate_limiter_remaining_counts_down():
    rl = clf.RateLimiter(limit=5, window=60)
    uid = "user-b"
    assert rl.remaining(uid) == 5
    rl.check(uid)
    rl.check(uid)
    assert rl.remaining(uid) == 3


def test_rate_limiter_is_per_user():
    rl = clf.RateLimiter(limit=1, window=60)
    assert rl.check("alice") is True
    assert rl.check("bob") is True     # bob has his own bucket
    assert rl.check("alice") is False  # alice already used hers


# ── LRU cache (memory-aware) ────────────────────────────────────────────────
def test_cache_hit_and_miss_accounting():
    cache = clf.LRUCache(maxsize=10, max_memory_mb=1)
    assert cache.get_item("missing") is None
    cache.set_item("k1", {"entity": "Laptop"})
    got = cache.get_item("k1")
    assert got is not None
    assert got["entity"] == "Laptop"
    assert cache.hits >= 1
    assert cache.misses >= 1


def test_cache_evicts_when_over_count_limit():
    cache = clf.LRUCache(maxsize=2, max_memory_mb=100)
    cache.set_item("a", {"v": 1})
    cache.set_item("b", {"v": 2})
    cache.set_item("c", {"v": 3})  # should evict the oldest ("a")
    assert cache.get_item("a") is None
    assert cache.get_item("c") is not None
# ── Upload streaming and decoded-image validation ───────────────────────────
class _SizedStream:
    def __init__(self, size):
        self.remaining = size
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        count = self.remaining if size < 0 else min(size, self.remaining)
        self.remaining -= count
        return b"x" * count


def _image_bytes(image_format="PNG", size=(16, 16)):
    output = io.BytesIO()
    Image.new("RGB", size, (100, 120, 140)).save(output, format=image_format)
    return output.getvalue()


def _upload(contents, content_type="image/png"):
    headers = Headers({"content-type": content_type}) if content_type else Headers()
    return UploadFile(
        io.BytesIO(contents),
        filename="device.png",
        headers=headers,
    )


def test_upload_reader_uses_bounded_chunks_and_stops_before_retaining_overflow(
    monkeypatch,
):
    limit = clf.UPLOAD_CHUNK_SIZE * 2
    monkeypatch.setattr(clf, "MAX_UPLOAD_SIZE", limit)
    stream = _SizedStream(limit + 1)
    upload = type("Upload", (), {"file": stream})()

    with pytest.raises(HTTPException) as exc_info:
        clf._read_upload_limited(upload)

    assert exc_info.value.status_code == 413
    assert max(stream.read_sizes) <= clf.UPLOAD_CHUNK_SIZE
    assert stream.remaining == 0


def test_invalid_and_unsupported_image_formats_are_rejected():
    with pytest.raises(HTTPException) as invalid:
        clf._decode_uploaded_image(b"not an image", "image/png")
    assert invalid.value.status_code == 400

    with pytest.raises(HTTPException) as unsupported:
        clf._decode_uploaded_image(_image_bytes("GIF"), None)
    assert unsupported.value.status_code == 415


def test_declared_type_must_match_decoded_format():
    with pytest.raises(HTTPException) as exc_info:
        clf._decode_uploaded_image(_image_bytes("PNG"), "image/jpeg")
    assert exc_info.value.status_code == 415


def test_decoded_pixel_limit_is_enforced_before_full_decode(monkeypatch):
    monkeypatch.setattr(clf, "MAX_DECODED_PIXELS", 3)
    with pytest.raises(HTTPException) as exc_info:
        clf._decode_uploaded_image(_image_bytes("PNG", (2, 2)), "image/png")
    assert exc_info.value.status_code == 413


def test_pillow_decompression_bomb_warning_is_rejected(monkeypatch):
    contents = _image_bytes("PNG", (2, 1))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)

    with pytest.raises(HTTPException) as exc_info:
        clf._decode_uploaded_image(contents, "image/png")

    assert exc_info.value.status_code == 413


# ── Cache key and transient-error policy ────────────────────────────────────
def _successful_classification(contents, image=None):
    return {
        "entity": "Laptop",
        "group": "Electronics",
        "condition": "good",
        "confidence": 0.91,
        "waste_status": "E-Waste",
        "hazard_level": "Hazardous",
        "co2_delta": 8.0,
        "model_used": "siglip",
        "rejection_reason": None,
    }


def _transient_classification(contents, image=None):
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


def test_scan_cache_uses_sha256_key(monkeypatch):
    contents = _image_bytes()
    local_cache = clf.LRUCache(maxsize=10, max_memory_mb=1)
    monkeypatch.setattr(clf, "cache", local_cache)
    monkeypatch.setattr(clf, "scan_limiter", clf.RateLimiter(limit=10, window=60))
    monkeypatch.setattr(clf, "real_classification", _successful_classification)
    monkeypatch.setattr(clf, "log_scan", lambda **kwargs: None)

    clf.scan_image(_upload(contents), user_id="sha-user")

    assert list(local_cache.keys()) == [hashlib.sha256(contents).hexdigest()]
    assert len(next(iter(local_cache.keys()))) == 64


def test_transient_model_errors_are_not_cached(monkeypatch):
    contents = _image_bytes()
    calls = {"count": 0}

    def transient(contents, image=None):
        calls["count"] += 1
        return _transient_classification(contents, image=image)

    local_cache = clf.LRUCache(maxsize=10, max_memory_mb=1)
    monkeypatch.setattr(clf, "cache", local_cache)
    monkeypatch.setattr(clf, "scan_limiter", clf.RateLimiter(limit=10, window=60))
    monkeypatch.setattr(clf, "real_classification", transient)

    for _ in range(2):
        with pytest.raises(HTTPException) as raised:
            clf.scan_image(_upload(contents), user_id="error-user")
        assert raised.value.status_code == 503

    assert calls["count"] == 2
    assert len(local_cache) == 0


# ── Model preset, threshold, and CLIP gate regressions ──────────────────────
def test_unknown_model_name_normalizes_to_actual_fallback_preset():
    resolved = model_module._normalize_model_name("definitely-not-a-model")
    assert resolved == model_module.FALLBACK_MODEL
    preset = model_module.MODEL_PRESETS[resolved]
    family = model_module._model_family(resolved, preset["is_clip"])
    assert model_module._threshold_key(resolved, family) == "siglip2_base"


def test_numeric_threshold_override_accepts_only_finite_unit_interval(monkeypatch):
    monkeypatch.setenv("CLASSIFY_THRESHOLD", "0.73")
    assert model_module._threshold_from_env("CLASSIFY_THRESHOLD", 0.2) == 0.73

    for invalid in ("not-a-number", "nan", "inf", "-0.1", "1.1"):
        monkeypatch.setenv("CLASSIFY_THRESHOLD", invalid)
        assert model_module._threshold_from_env("CLASSIFY_THRESHOLD", 0.2) == 0.2


def test_clip_electronics_gate_compares_formatted_labels(monkeypatch):
    def fake_classifier(image, candidate_labels, multi_label):
        assert "a photo of electronic device" in candidate_labels
        assert "a photo of person" in candidate_labels
        return [
            {"label": "a photo of electronic device", "score": 0.92},
            {"label": "a photo of person", "score": 0.10},
        ]

    monkeypatch.setattr(model_module, "IS_CLIP_MODEL", True)
    monkeypatch.setattr(model_module, "ELECTRONIC_THRESHOLD", 0.4)
    monkeypatch.setattr(model_module, "ELECTRONIC_MARGIN", 0.1)
    monkeypatch.setattr(model_module, "_load_model", lambda: fake_classifier)

    result = model_module.gate_electronics(Image.new("RGB", (224, 224)))

    assert result["is_electronic"] is True
    assert result["electronic_score"] == 0.92
    assert result["non_electronic_score"] == 0.10


# ── Single-flight model/classifier initialization ──────────────────────────
def _reset_pipeline_state(monkeypatch):
    monkeypatch.setattr(model_module, "_model_pipeline", None)
    monkeypatch.setattr(model_module, "_model_load_in_progress", False)
    monkeypatch.setattr(model_module, "_model_load_error", None)
    monkeypatch.setattr(model_module, "_model_retry_at", 0.0)


def test_huggingface_pipeline_load_is_single_flight(monkeypatch):
    _reset_pipeline_state(monkeypatch)
    sentinel = object()
    started = threading.Event()
    release = threading.Event()
    calls = {"count": 0}
    calls_lock = threading.Lock()

    def build():
        with calls_lock:
            calls["count"] += 1
        started.set()
        assert release.wait(timeout=2)
        return sentinel

    monkeypatch.setattr(model_module, "_build_model_pipeline", build)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(model_module._load_model) for _ in range(16)]
        assert started.wait(timeout=2)
        release.set()
        results = [future.result(timeout=2) for future in futures]

    assert calls["count"] == 1
    assert all(result is sentinel for result in results)


def test_model_loader_recovers_after_failure_cooldown(monkeypatch):
    _reset_pipeline_state(monkeypatch)
    clock = {"now": 50.0}
    sentinel = object()
    attempts = {"count": 0}

    def build():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary load failure")
        return sentinel

    monkeypatch.setattr(model_module.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(model_module, "_build_model_pipeline", build)

    with pytest.raises(RuntimeError, match="temporary load failure"):
        model_module._load_model()
    with pytest.raises(RuntimeError, match="retry available"):
        model_module._load_model()
    assert attempts["count"] == 1

    clock["now"] += model_module._MODEL_LOAD_RETRY_SECONDS + 1
    assert model_module._load_model() is sentinel
    assert attempts["count"] == 2


def test_classifier_wrapper_initialization_is_single_flight(monkeypatch):
    monkeypatch.setattr(clf, "_model", None)
    monkeypatch.setattr(clf, "_model_initializing", False)
    monkeypatch.setattr(clf, "_model_load_failed", False)
    monkeypatch.setattr(clf, "_model_retry_at", 0.0)
    started = threading.Event()
    release = threading.Event()
    calls = {"count": 0}
    calls_lock = threading.Lock()

    class FakeClassifier:
        def __init__(self):
            with calls_lock:
                calls["count"] += 1
            started.set()
            assert release.wait(timeout=2)

    monkeypatch.setattr(clf, "EWasteClassifier", FakeClassifier)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(clf.get_model) for _ in range(16)]
        assert started.wait(timeout=2)
        release.set()
        results = [future.result(timeout=2) for future in futures]

    assert calls["count"] == 1
    assert all(result is results[0] for result in results)
