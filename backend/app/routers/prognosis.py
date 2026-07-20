"""
Corrected E-Waste Lifespan Predictor
====================================
True weighted-average formula with full transparency:

    Health_Score = Σ(wᵢ × fᵢ)        where Σwᵢ = 1.0
    Remaining_Life = max(0, (Base_Lifespan × Health_Score) − Current_Age)
    Confidence_Range = ±(Base_Lifespan × 0.15 × (1 − Health_Score))

CO₂ Avoided = (Device_Weight_kg × 0.05) × (Remaining_Life / Base_Lifespan) × 1000
Repair Savings = Base_Repair_Cost × Health_Score
"""

from datetime import datetime
import hashlib
import hmac
import io
import json
import math
import os as _os
from pathlib import Path
import pickle
from typing import Dict, List, Literal, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth import get_current_user
from app.db import log_lifespan_prediction
from app.device_profiles import DEVICE_PROFILES as _SHARED_PROFILES
from app.logging_config import get_logger
from app.runtime import lifespan_model_path

logger = get_logger("ewaste.prognosis")

router = APIRouter(prefix="/predict", tags=["Prognosis"])

# Device profiles are the single source of truth shared by all routers.
DEVICE_PROFILES: Dict[str, Dict] = _SHARED_PROFILES

# ─── Lazy-loaded ML model cache ────────────────────────────────────────────
_ML_CACHE: Dict[str, object] = {}
MODEL_DIR = lifespan_model_path()
_MODEL_MANIFEST: Optional[Dict[str, str]] = None


def _load_manifest() -> Dict[str, str]:
    """Load and validate the SHA-256 manifest.

    An absent, malformed, or non-dict manifest is treated as empty. Artifacts
    are never trusted merely because the manifest cannot be read.
    """
    global _MODEL_MANIFEST
    if _MODEL_MANIFEST is not None:
        return _MODEL_MANIFEST

    manifest_path = MODEL_DIR / "model_manifest.json"
    try:
        with manifest_path.open("r", encoding="utf-8") as manifest_file:
            raw_manifest = json.load(manifest_file)
        if not isinstance(raw_manifest, dict):
            raise ValueError("manifest root must be an object")

        validated: Dict[str, str] = {}
        for filename, digest in raw_manifest.items():
            if (
                isinstance(filename, str)
                and isinstance(digest, str)
                and len(digest) == 64
                and all(char in "0123456789abcdefABCDEF" for char in digest)
            ):
                validated[filename] = digest.lower()
            else:
                logger.error("Ignoring invalid model manifest entry for %r", filename)
        _MODEL_MANIFEST = validated
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.error("Model manifest is unavailable or invalid: %s", exc)
        _MODEL_MANIFEST = {}
    return _MODEL_MANIFEST


def _read_verified_artifact(path: Path) -> Optional[bytes]:
    """Return artifact bytes only when a manifest entry exists and matches.

    The exact bytes that are hashed are passed to ``pickle.load`` through an
    in-memory stream. This avoids a verify/re-open race and guarantees hash
    verification occurs before any unpickling.
    """
    expected_hash = _load_manifest().get(path.name)
    if expected_hash is None:
        logger.error("Refusing unmanifested model artifact: %s", path.name)
        return None
    try:
        data = path.read_bytes()
    except OSError as exc:
        logger.error("Model artifact %s is unavailable: %s", path.name, exc)
        return None

    actual_hash = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(actual_hash, expected_hash):
        logger.error("Refusing model artifact with SHA-256 mismatch: %s", path.name)
        return None
    return data


def _verify_model_hash(path: Path) -> bool:
    """Return whether a pickle is present in the manifest and hash-valid."""
    return _read_verified_artifact(path) is not None


def _load_ml_artifact(name: str):
    """Load a hash-verified pickle, or return ``None`` without unpickling."""
    if name in _ML_CACHE:
        return _ML_CACHE[name]

    path = MODEL_DIR / f"{name}.pkl"
    verified_bytes = _read_verified_artifact(path)
    if verified_bytes is None:
        return None

    try:
        obj = pickle.load(io.BytesIO(verified_bytes))
    except Exception as exc:
        logger.error("Verified model artifact %s could not be loaded: %s", path.name, exc)
        return None
    _ML_CACHE[name] = obj
    return obj


def _ml_predict(model_name: str, row_dict: dict) -> Optional[float]:
    """Run a saved sklearn pipeline on one row, returning no silent fallback."""
    pipe = _load_ml_artifact(model_name)
    if pipe is None:
        return None
    feature_columns = _load_ml_artifact("feature_columns")
    if feature_columns is None:
        return None

    try:
        row = {key: row_dict.get(key) for key in feature_columns}
        prediction = float(pipe.predict(pd.DataFrame([row]))[0])
        if not math.isfinite(prediction):
            raise ValueError("model returned a non-finite prediction")
        return max(0.0, prediction)
    except Exception as exc:
        logger.error("ML prediction (%s) failed: %s", model_name, exc)
        return None


def preload_models() -> None:
    """Warm hash-verified ML artifacts at startup."""
    for name in ("feature_columns", "xgboost_model", "rf_model", "lightgbm_model"):
        try:
            if _load_ml_artifact(name) is None:
                logger.error("Model preload unavailable: %s", name)
            else:
                logger.info("Preloaded %s", name)
        except Exception as exc:
            logger.error("Failed to preload %s: %s", name, exc)


# Tests set this before importing the module so pure math/API validation never
# opens large native ML artifacts. Production preserves eager preload behavior.
if _os.getenv("EWASTE_SKIP_MODEL_PRELOAD") != "1":
    preload_models()


# ─── Default weights (must sum to 1.0) ──────────────────────────────────────
DEFAULT_WEIGHTS: Dict[str, float] = {
    "age": 0.25,
    "usage": 0.20,
    "temperature": 0.15,
    "power": 0.13,
    "environment": 0.10,
    "service": 0.05,
    "software": 0.12,
}
WEIGHT_NAMES = frozenset(DEFAULT_WEIGHTS)
MIN_MANUFACTURING_YEAR = 1970

TemperatureStress = Literal["Cool", "Normal", "Hot"]
Environment = Literal["Clean", "Normal", "Harsh"]
PowerQuality = Literal["UPS Protected", "Direct Grid", "Frequent Outages"]
Maintenance = Literal[
    "Regular", "Occasional", "None", "No Service", "Never", "No Maintenance"
]
SoftwareLoad = Literal["Light", "Office", "Heavy"]
WeightName = Literal[
    "age", "usage", "temperature", "power", "environment", "service", "software"
]
ModelChoice = Literal["formula", "xgboost", "random_forest", "lightgbm", "best"]


def _canonical_device_type(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("device_type must be a string")
    cleaned = value.strip()
    for known_device in DEVICE_PROFILES:
        if known_device.casefold() == cleaned.casefold():
            return known_device
    raise ValueError(
        f"unknown device_type {value!r}; expected one of: {', '.join(DEVICE_PROFILES)}"
    )


def _normalize_weights(custom: Optional[Dict[str, float]]) -> Dict[str, float]:
    """Validate overrides and return all seven finite weights normalized to 1."""
    if custom is None or len(custom) == 0:
        return dict(DEFAULT_WEIGHTS)

    unknown = set(custom) - WEIGHT_NAMES
    if unknown:
        raise ValueError(
            "unknown weight names: " + ", ".join(sorted(map(str, unknown)))
        )

    overrides: Dict[str, float] = {}
    for name, value in custom.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"weight {name!r} must be a number")
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(f"weight {name!r} must be finite")
        if numeric_value < 0:
            raise ValueError(f"weight {name!r} must be nonnegative")
        overrides[name] = numeric_value

    merged = {**DEFAULT_WEIGHTS, **overrides}
    total = math.fsum(merged.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("at least one lifespan weight must be positive")

    normalized = {name: merged[name] / total for name in DEFAULT_WEIGHTS}
    # Correct harmless floating-point drift so math.fsum is exactly 1.0 in the
    # serialized audit record while retaining nonnegative values.
    last_name = next(reversed(normalized))
    normalized[last_name] += 1.0 - math.fsum(normalized.values())
    return normalized


# ─── Request / Response models ──────────────────────────────────────────────
class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_type: str
    manufacturing_year: int = Field(strict=True)
    usage_hours_per_day: float = Field(
        default=8.0, strict=True, ge=0.0, le=24.0, allow_inf_nan=False
    )
    temperature_stress: TemperatureStress = "Normal"
    environment: Environment = "Normal"
    power_outage_freq: PowerQuality = "Direct Grid"
    maintenance_frequency: Maintenance = "Occasional"
    software_load: SoftwareLoad = "Office"
    weights: Optional[Dict[WeightName, float]] = None
    model_choice: ModelChoice = "formula"

    @field_validator("device_type", mode="before")
    @classmethod
    def validate_device_type(cls, value: object) -> str:
        return _canonical_device_type(value)

    @field_validator("manufacturing_year")
    @classmethod
    def validate_manufacturing_year(cls, value: int) -> int:
        current_year = datetime.now().year
        if not MIN_MANUFACTURING_YEAR <= value <= current_year:
            raise ValueError(
                f"manufacturing_year must be between {MIN_MANUFACTURING_YEAR} and {current_year}"
            )
        return value

    @field_validator("weights", mode="before")
    @classmethod
    def validate_and_normalize_weights(cls, value: object):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("weights must be an object")
        # Validate before Pydantic coercion so strings and booleans are not
        # silently converted to numeric weights.
        return _normalize_weights(value)


class FactorDetail(BaseModel):
    name: str
    raw: float
    weight: float
    weighted: float
    label: Optional[str] = None


class PredictResponse(BaseModel):
    device_type: str
    age: float
    base_lifespan: int
    factors: List[FactorDetail]
    normalized_weights: Dict[str, float]
    health_score: float
    remaining_years: float
    remaining_min: float
    remaining_max: float
    end_of_life: bool
    co2_avoided_kg: float
    repair_savings_inr: float
    base_repair_cost_inr: float
    base_replace_cost_inr: float
    device_weight_kg: float
    manufacturing_co2_kg: float
    annual_co2_kg: float
    model_requested: ModelChoice
    model_used: str
    formula_text: str
    ensemble: Dict[str, float] = Field(default_factory=dict)


# ─── Pure math helpers (testable) ───────────────────────────────────────────
def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def f_age(current_age: float, base_lifespan: int) -> float:
    """1.0 at year 0, linear decay to 0.0 at base lifespan."""
    if base_lifespan <= 0:
        return 0.0
    return _clamp(1.0 - (current_age / base_lifespan))


def f_usage(usage_hours_per_day: float) -> float:
    """0–4 = 1.0, 4–8 = 0.85, 8–12 = 0.70, 12+ = 0.50."""
    hours = float(usage_hours_per_day)
    if hours <= 4:
        return 1.0
    if hours <= 8:
        return 0.85
    if hours <= 12:
        return 0.70
    return 0.50


_TEMPERATURE_SCORES = {"Cool": 0.90, "Normal": 0.75, "Hot": 0.50}
_ENVIRONMENT_SCORES = {"Clean": 0.90, "Normal": 0.70, "Harsh": 0.40}
_POWER_SCORES = {"UPS Protected": 0.90, "Direct Grid": 0.70, "Frequent Outages": 0.45}
_MAINTENANCE_SCORES = {
    "Regular": 0.90,
    "Occasional": 0.70,
    "None": 0.50,
    "No Service": 0.50,
    "Never": 0.50,
    "No Maintenance": 0.50,
}
_SOFTWARE_SCORES = {"Light": 0.92, "Office": 0.78, "Heavy": 0.55}


def f_temperature(label: str) -> float:
    return _TEMPERATURE_SCORES.get(label, 0.75)


def f_environment(label: str) -> float:
    return _ENVIRONMENT_SCORES.get(label, 0.70)


def f_power(label: str) -> float:
    return _POWER_SCORES.get(label, 0.70)


def f_service(label: str) -> float:
    return _MAINTENANCE_SCORES.get(label, 0.70)


def f_software(label: str) -> float:
    """The S factor: heavier software/workload shortens device life."""
    return _SOFTWARE_SCORES.get(label, 0.78)


_ML_ARTIFACTS = {
    "xgboost": "xgboost_model",
    "random_forest": "rf_model",
    "lightgbm": "lightgbm_model",
}


# ─── Main endpoint ──────────────────────────────────────────────────────────
@router.post("/", response_model=PredictResponse)
def predict_lifespan(request: PredictRequest, user_id: str = Depends(get_current_user)):
    # Pydantic validates this first; retain a defensive 422 for direct calls.
    if request.device_type not in DEVICE_PROFILES:
        raise HTTPException(status_code=422, detail="Unknown device type")

    profile = DEVICE_PROFILES[request.device_type]
    base_lifespan = int(profile["base_lifespan"])
    current_age = float(datetime.now().year - request.manufacturing_year)

    raw_factors = {
        "age": f_age(current_age, base_lifespan),
        "usage": f_usage(request.usage_hours_per_day),
        "temperature": f_temperature(request.temperature_stress),
        "power": f_power(request.power_outage_freq),
        "environment": f_environment(request.environment),
        "service": f_service(request.maintenance_frequency),
        "software": f_software(request.software_load),
    }
    labels = {
        "age": f"{current_age:.1f} / {base_lifespan} yr",
        "usage": f"{request.usage_hours_per_day:.1f} h/day",
        "temperature": request.temperature_stress,
        "power": request.power_outage_freq,
        "environment": request.environment,
        "service": request.maintenance_frequency,
        "software": request.software_load,
    }
    weights = _normalize_weights(request.weights)

    factors: List[FactorDetail] = []
    health = 0.0
    for name, raw in raw_factors.items():
        weight = weights[name]
        weighted = weight * raw
        health += weighted
        factors.append(
            FactorDetail(
                name=name,
                raw=round(raw, 4),
                weight=round(weight, 6),
                weighted=round(weighted, 6),
                label=labels[name],
            )
        )
    health = _clamp(health)

    end_of_life = current_age >= base_lifespan
    max_remaining = max(0.0, base_lifespan - current_age)
    if end_of_life:
        formula_remaining = 0.0
    else:
        formula_remaining = max(
            0.0, min((base_lifespan * health) - current_age, max_remaining)
        )

    ensemble: Dict[str, float] = {"formula": round(formula_remaining, 4)}
    model_requested: ModelChoice = request.model_choice
    model_used = "formula"
    remaining_years = formula_remaining

    ml_input = {
        "device_type": request.device_type,
        "manufacturer": "Unknown",
        "region": "Maharashtra",
        "base_lifespan_yrs": base_lifespan,
        "current_age_yrs": current_age,
        "daily_usage_hrs": request.usage_hours_per_day,
        "temperature": request.temperature_stress,
        "environment": request.environment,
        "power_quality": request.power_outage_freq,
        "maintenance": request.maintenance_frequency,
        "software_load": request.software_load,
    }

    if model_requested in _ML_ARTIFACTS:
        prediction = _ml_predict(_ML_ARTIFACTS[model_requested], ml_input)
        if prediction is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Requested lifespan model '{model_requested}' is unavailable, "
                    "failed integrity verification, or could not predict"
                ),
            )
        prediction = min(prediction, max_remaining)
        ensemble[model_requested] = round(prediction, 4)
        remaining_years = prediction
        model_used = model_requested
    elif model_requested == "best":
        available_predictions: List[float] = [formula_remaining]
        used_engines = ["formula"]
        for engine, artifact_name in _ML_ARTIFACTS.items():
            prediction = _ml_predict(artifact_name, ml_input)
            if prediction is not None:
                prediction = min(prediction, max_remaining)
                ensemble[engine] = round(prediction, 4)
                available_predictions.append(prediction)
                used_engines.append(engine)
        if len(available_predictions) == 1:
            raise HTTPException(
                status_code=503,
                detail="Requested 'best' ensemble has no verified ML models available",
            )
        remaining_years = math.fsum(available_predictions) / len(available_predictions)
        model_used = "ensemble:" + "+".join(used_engines)

    remaining_years = max(0.0, min(remaining_years, max_remaining))
    if end_of_life:
        remaining_years = remaining_min = remaining_max = 0.0
    else:
        band = base_lifespan * 0.15 * (1.0 - health)
        remaining_min = max(0.0, remaining_years - band)
        remaining_max = min(max_remaining, remaining_years + band)

    weight_kg = float(profile["weight_kg"])
    base_repair = float(profile["base_repair_cost"])
    co2_avoided_kg = (
        (weight_kg * 0.05) * (remaining_years / base_lifespan) * 1000.0
    )
    repair_savings = base_repair * health

    response = PredictResponse(
        device_type=request.device_type,
        age=current_age,
        base_lifespan=base_lifespan,
        factors=factors,
        normalized_weights=weights,
        health_score=round(health, 4),
        remaining_years=round(remaining_years, 2),
        remaining_min=round(remaining_min, 2),
        remaining_max=round(remaining_max, 2),
        end_of_life=end_of_life,
        co2_avoided_kg=round(co2_avoided_kg, 2),
        repair_savings_inr=round(repair_savings, 2),
        base_repair_cost_inr=base_repair,
        base_replace_cost_inr=float(profile["base_replace_cost"]),
        device_weight_kg=weight_kg,
        manufacturing_co2_kg=float(profile["manufacturing_co2"]),
        annual_co2_kg=float(profile["annual_co2"]),
        model_requested=model_requested,
        model_used=model_used,
        formula_text=(
            "H = Σ(wᵢ × fᵢ(A, U, T, P, E, M, S)); "
            "remaining = clamp(base_lifespan × H − age, 0, base_lifespan − age)"
        ),
        ensemble=ensemble,
    )

    # History remains best-effort, but every successful prediction supplies a
    # complete audit record including the normalized inputs and model choice.
    try:
        log_lifespan_prediction(
            device_type=request.device_type,
            age=current_age,
            base_lifespan=base_lifespan,
            health_score=response.health_score,
            remaining_years=response.remaining_years,
            co2_avoided_kg=response.co2_avoided_kg,
            repair_savings_inr=response.repair_savings_inr,
            remaining_min=response.remaining_min,
            remaining_max=response.remaining_max,
            usage_hours_per_day=request.usage_hours_per_day,
            temperature=request.temperature_stress,
            environment=request.environment,
            power=request.power_outage_freq,
            maintenance=request.maintenance_frequency,
            user_id=user_id,
            software_load=request.software_load,
            normalized_weights=response.normalized_weights,
            model_requested=response.model_requested,
            model_used=response.model_used,
        )
    except Exception as exc:
        logger.error("Failed to log lifespan history: %s", exc)

    return response


@router.get("/device-types")
async def get_device_types():
    return {
        "device_types": list(DEVICE_PROFILES.keys()),
        "default_weights": DEFAULT_WEIGHTS,
    }


@router.get("/profile/{device_type}")
async def get_device_profile(device_type: str):
    try:
        canonical_name = _canonical_device_type(device_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unknown device type") from exc
    return DEVICE_PROFILES[canonical_name]
