"""Unit and API tests for the transparent lifespan predictor."""

from datetime import datetime
import hashlib
import json
import math
import pickle

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth import get_current_user
from app.routers import prognosis as p


@pytest.fixture
def prognosis_client(temp_db):  # noqa: ARG001
    app = FastAPI()
    app.include_router(p.router)
    app.dependency_overrides[get_current_user] = lambda: "user-prognosis"
    with TestClient(app) as client:
        yield client


def _valid_payload(**overrides):
    payload = {
        "device_type": "Laptop",
        "manufacturing_year": datetime.now().year - 2,
        "usage_hours_per_day": 8.0,
        "temperature_stress": "Normal",
        "environment": "Normal",
        "power_outage_freq": "Direct Grid",
        "maintenance_frequency": "Occasional",
        "software_load": "Office",
        "model_choice": "formula",
    }
    payload.update(overrides)
    return payload


# ── Pure factor math ────────────────────────────────────────────────────────
def test_f_age_new_device_is_full_health():
    assert p.f_age(0, 5) == 1.0


def test_f_age_at_base_lifespan_is_zero():
    assert p.f_age(5, 5) == 0.0


def test_f_age_midlife_is_half():
    assert abs(p.f_age(4, 8) - 0.5) < 1e-9


def test_f_age_beyond_lifespan_clamps_to_zero():
    assert p.f_age(12, 5) == 0.0


def test_f_age_zero_base_lifespan_is_safe():
    assert p.f_age(3, 0) == 0.0


def test_f_usage_is_monotonic_non_increasing():
    scores = [p.f_usage(hours) for hours in (2, 6, 10, 16)]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 1.0
    assert scores[-1] == 0.50


def test_temperature_scores():
    assert p.f_temperature("Cool") > p.f_temperature("Normal") > p.f_temperature("Hot")
    assert p.f_temperature("Unknown") == 0.75


def test_power_scores_order():
    assert p.f_power("UPS Protected") > p.f_power("Direct Grid") > p.f_power(
        "Frequent Outages"
    )


def test_software_workload_order():
    assert p.f_software("Light") > p.f_software("Office") > p.f_software("Heavy")


def test_maintenance_no_service_scores_at_or_below_none():
    none_score = p.f_service("None")
    assert p.f_service("No Service") <= none_score
    assert p.f_service("Never") <= none_score
    assert p.f_service("No Maintenance") <= none_score
    assert p.f_service("Regular") > none_score


# ── Weight validation and normalization ────────────────────────────────────
def test_default_weights_sum_to_one():
    assert math.fsum(p.DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)


def test_custom_weights_are_renormalized_and_complete():
    result = p._normalize_weights({"age": 10, "usage": 10})
    assert set(result) == set(p.DEFAULT_WEIGHTS)
    assert math.fsum(result.values()) == pytest.approx(1.0)
    assert all(math.isfinite(value) and value >= 0 for value in result.values())


def test_empty_weights_fall_back_to_defaults():
    assert p._normalize_weights(None) == p.DEFAULT_WEIGHTS
    assert p._normalize_weights({}) == p.DEFAULT_WEIGHTS


@pytest.mark.parametrize(
    "weights",
    [
        {"unknown": 1.0},
        {1: 1.0},
        {"age": -0.1},
        {"age": float("nan")},
        {"age": float("inf")},
        {"age": True},
        {"age": "1.0"},
        {name: 0.0 for name in p.DEFAULT_WEIGHTS},
    ],
)
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):
        p._normalize_weights(weights)


# ── Request/API validation ─────────────────────────────────────────────────
@pytest.mark.parametrize(
    "overrides",
    [
        {"device_type": "Flux Capacitor"},
        {"manufacturing_year": 1969},
        {"manufacturing_year": datetime.now().year + 1},
        {"usage_hours_per_day": -0.1},
        {"usage_hours_per_day": 24.1},
        {"temperature_stress": "Warm"},
        {"environment": "Dusty"},
        {"power_outage_freq": "Sometimes"},
        {"maintenance_frequency": "Monthly"},
        {"software_load": "Gaming"},
        {"model_choice": "auto"},
        {"weights": {"mystery": 1.0}},
        {"weights": {"age": -1.0}},
        {"weights": {"age": "1.0"}},
        {"unexpected": "field"},
    ],
)
def test_invalid_prediction_inputs_return_422(prognosis_client, overrides):
    response = prognosis_client.post("/predict/", json=_valid_payload(**overrides))
    assert response.status_code == 422, response.text


def test_formula_request_never_touches_ml_and_returns_audit_fields(
    prognosis_client, monkeypatch
):
    def fail_if_called(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("formula prediction must not access ML artifacts")

    monkeypatch.setattr(p, "_ml_predict", fail_if_called)
    response = prognosis_client.post(
        "/predict/",
        json=_valid_payload(
            device_type="laptop",
            weights={"age": 2.0, "usage": 1.0},
        ),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["device_type"] == "Laptop"
    assert body["model_requested"] == "formula"
    assert body["model_used"] == "formula"
    assert math.fsum(body["normalized_weights"].values()) == pytest.approx(1.0)
    assert set(body["normalized_weights"]) == set(p.DEFAULT_WEIGHTS)


@pytest.mark.parametrize("model_choice", ["xgboost", "random_forest", "lightgbm"])
def test_unavailable_explicit_model_returns_503(
    prognosis_client, monkeypatch, model_choice
):
    monkeypatch.setattr(p, "_ml_predict", lambda *args, **kwargs: None)
    response = prognosis_client.post(
        "/predict/", json=_valid_payload(model_choice=model_choice)
    )
    assert response.status_code == 503
    assert model_choice in response.json()["detail"]


def test_best_without_any_verified_ml_model_returns_503(
    prognosis_client, monkeypatch
):
    monkeypatch.setattr(p, "_ml_predict", lambda *args, **kwargs: None)
    response = prognosis_client.post(
        "/predict/", json=_valid_payload(model_choice="best")
    )
    assert response.status_code == 503


# ── Pickle integrity gate ──────────────────────────────────────────────────
@pytest.mark.parametrize("manifest_contents", [None, {}, {"rf_model.pkl": "0" * 64}])
def test_pickle_is_not_loaded_when_manifest_missing_entry_or_hash_mismatches(
    tmp_path, monkeypatch, manifest_contents
):
    artifact = tmp_path / "rf_model.pkl"
    artifact.write_bytes(pickle.dumps({"trusted": False}))
    if manifest_contents is not None:
        (tmp_path / "model_manifest.json").write_text(
            json.dumps(manifest_contents), encoding="utf-8"
        )

    monkeypatch.setattr(p, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(p, "_MODEL_MANIFEST", None)
    monkeypatch.setattr(p, "_ML_CACHE", {})
    calls = []

    def record_pickle_load(stream):  # noqa: ARG001
        calls.append(True)
        raise AssertionError("unverified bytes reached pickle.load")

    monkeypatch.setattr(p.pickle, "load", record_pickle_load)
    assert p._load_ml_artifact("rf_model") is None
    assert calls == []


def test_manifested_matching_pickle_loads_after_hash_verification(tmp_path, monkeypatch):
    artifact = tmp_path / "rf_model.pkl"
    payload = pickle.dumps({"trusted": True})
    artifact.write_bytes(payload)
    (tmp_path / "model_manifest.json").write_text(
        json.dumps({"rf_model.pkl": hashlib.sha256(payload).hexdigest()}),
        encoding="utf-8",
    )

    monkeypatch.setattr(p, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(p, "_MODEL_MANIFEST", None)
    monkeypatch.setattr(p, "_ML_CACHE", {})

    assert p._load_ml_artifact("rf_model") == {"trusted": True}


# ── Generic helper ─────────────────────────────────────────────────────────
def test_clamp_bounds():
    assert p._clamp(-1) == 0.0
    assert p._clamp(2) == 1.0
    assert p._clamp(0.5) == 0.5
