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
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import pickle
from pathlib import Path
import pandas as pd
from app.db import log_lifespan_prediction

router = APIRouter(prefix="/predict", tags=["Prognosis"])

# ─── Lazy-loaded ML model cache ────────────────────────────────────────────
_ML_CACHE: Dict[str, object] = {}
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "lifespan"


def _load_ml_artifact(name: str):
    if name in _ML_CACHE:
        return _ML_CACHE[name]
    path = MODEL_DIR / f"{name}.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        obj = pickle.load(f)
    _ML_CACHE[name] = obj
    return obj


def _ml_predict(model_name: str, row_dict: dict) -> Optional[float]:
    """Run a saved sklearn pipeline (preprocessor + model) on a single row."""
    pipe = _load_ml_artifact(model_name)
    if pipe is None:
        return None
    feat_cols = _load_ml_artifact("feature_columns")
    if feat_cols is None:
        return None
    row = {k: row_dict.get(k) for k in feat_cols}
    df_row = pd.DataFrame([row])
    try:
        pred = float(pipe.predict(df_row)[0])
        return max(0.0, pred)
    except Exception as e:
        print(f"[prognosis] ML prediction ({model_name}) failed: {e}")
        return None


def preload_models() -> None:
    """Warm the ML model cache at startup.

    Unpickling the saved sklearn/xgboost Pipelines inside a request handler
    segfaults the uvicorn worker on macOS (likely due to native code init
    interacting badly with the ASGI server's event loop). Loading them once
    at process start avoids the crash.
    """
    for name in ("feature_columns", "xgboost_model", "rf_model"):
        try:
            _load_ml_artifact(name)
            print(f"[prognosis] preloaded {name}", flush=True)
        except Exception as e:
            print(f"[prognosis] failed to preload {name}: {e}", flush=True)


# Preload at module import. The first request would otherwise unpickle the
# saved sklearn/xgboost Pipelines lazily, which segfaults the uvicorn
# worker on macOS. main.py pins OMP_NUM_THREADS=1 to keep the native
# thread pools from colliding during load.
for _n in ("feature_columns", "xgboost_model", "rf_model"):
    _load_ml_artifact(_n)
    print(f"[prognosis] preloaded {_n}", flush=True)


# ─── Single source of truth: device profiles ────────────────────────────────
DEVICE_PROFILES: Dict[str, Dict] = {
    "Motherboard":    {"base_lifespan": 8, "weight_kg": 0.5,  "manufacturing_co2": 80,  "annual_co2": 10, "base_repair_cost": 2500, "base_replace_cost": 8000},
    "Hard Disk / SSD":{"base_lifespan": 5, "weight_kg": 0.2,  "manufacturing_co2": 40,  "annual_co2": 5,  "base_repair_cost": 800,  "base_replace_cost": 4000},
    "Monitor":        {"base_lifespan": 7, "weight_kg": 6.0,  "manufacturing_co2": 180, "annual_co2": 40, "base_repair_cost": 1500, "base_replace_cost": 9000},
    "Mouse":          {"base_lifespan": 3, "weight_kg": 0.15, "manufacturing_co2": 15,  "annual_co2": 1,  "base_repair_cost": 100,  "base_replace_cost": 500},
    "Keyboard":       {"base_lifespan": 4, "weight_kg": 0.5,  "manufacturing_co2": 20,  "annual_co2": 2,  "base_repair_cost": 200,  "base_replace_cost": 1000},
    "Smartphone":     {"base_lifespan": 4, "weight_kg": 0.2,  "manufacturing_co2": 80,  "annual_co2": 20, "base_repair_cost": 3000, "base_replace_cost": 15000},
    "Computer":       {"base_lifespan": 6, "weight_kg": 10.0, "manufacturing_co2": 300, "annual_co2": 80, "base_repair_cost": 5000, "base_replace_cost": 35000},
    "Printer":        {"base_lifespan": 5, "weight_kg": 8.0,  "manufacturing_co2": 120, "annual_co2": 30, "base_repair_cost": 2500, "base_replace_cost": 12000},
    "Projector":      {"base_lifespan": 5, "weight_kg": 3.5,  "manufacturing_co2": 150, "annual_co2": 40, "base_repair_cost": 6000, "base_replace_cost": 25000},
    "Router / Switch":{"base_lifespan": 6, "weight_kg": 1.0,  "manufacturing_co2": 50,  "annual_co2": 15, "base_repair_cost": 500,  "base_replace_cost": 3000},
    "Air Conditioner":{"base_lifespan": 10,"weight_kg": 50.0, "manufacturing_co2": 600, "annual_co2": 250,"base_repair_cost": 5000, "base_replace_cost": 40000},
    "Laptop":         {"base_lifespan": 5, "weight_kg": 2.0,  "manufacturing_co2": 200, "annual_co2": 50, "base_repair_cost": 6000, "base_replace_cost": 50000},
    "Television":     {"base_lifespan": 8, "weight_kg": 25.0, "manufacturing_co2": 220, "annual_co2": 60, "base_repair_cost": 8000, "base_replace_cost": 30000},
    "Battery":        {"base_lifespan": 3, "weight_kg": 2.0,  "manufacturing_co2": 30,  "annual_co2": 5,  "base_repair_cost": 1500, "base_replace_cost": 4500},
    "Microwave":      {"base_lifespan": 8, "weight_kg": 12.0, "manufacturing_co2": 90,  "annual_co2": 80, "base_repair_cost": 2500, "base_replace_cost": 12000},
}


# ─── Default weights (must sum to 1.0) ──────────────────────────────────────
DEFAULT_WEIGHTS: Dict[str, float] = {
    "age": 0.30,
    "usage": 0.25,
    "temperature": 0.15,
    "power": 0.15,
    "environment": 0.10,
    "service": 0.05,
}


# ─── Request / Response models ──────────────────────────────────────────────
class PredictRequest(BaseModel):
    device_type: str
    manufacturing_year: int
    usage_hours_per_day: float = 8.0
    temperature_stress: str = "Normal"   # "Cool" | "Normal" | "Hot"
    environment: str = "Normal"          # "Clean" | "Normal" | "Harsh"
    power_outage_freq: str = "Direct Grid"  # "UPS Protected" | "Direct Grid" | "Frequent Outages"
    maintenance_frequency: str = "Occasional"  # "Regular" | "Occasional" | "None" | "No Service"
    # Optional advanced-mode weight overrides (must sum to ~1.0)
    weights: Dict[str, float] | None = None
    # Which engine to use: "formula" (default) | "xgboost" | "random_forest" | "best"
    # "best" picks the highest-confidence among available models
    model_choice: str = "formula"


class FactorDetail(BaseModel):
    name: str
    raw: float             # fᵢ ∈ [0, 1]
    weight: float          # wᵢ
    weighted: float        # wᵢ × fᵢ
    label: str | None = None  # categorical label for display


class PredictResponse(BaseModel):
    device_type: str
    age: float
    base_lifespan: int

    # The actual math
    factors: List[FactorDetail]
    health_score: float         # Σ(wᵢ × fᵢ)
    remaining_years: float
    remaining_min: float        # lower bound of confidence range
    remaining_max: float        # upper bound of confidence range
    end_of_life: bool

    # Derived
    co2_avoided_kg: float
    repair_savings_inr: float
    base_repair_cost_inr: float
    base_replace_cost_inr: float
    device_weight_kg: float
    manufacturing_co2_kg: float
    annual_co2_kg: float

    # Meta
    model_used: str
    formula_text: str
    # All engine predictions (formula + ML) for comparison
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
    h = float(usage_hours_per_day)
    if h <= 4:
        return 1.0
    if h <= 8:
        return 0.85
    if h <= 12:
        return 0.70
    return 0.50


_TEMPERATURE_SCORES = {"Cool": 0.90, "Normal": 0.75, "Hot": 0.50}
_ENVIRONMENT_SCORES = {"Clean": 0.90, "Normal": 0.70, "Harsh": 0.40}
_POWER_SCORES = {"UPS Protected": 0.90, "Direct Grid": 0.70, "Frequent Outages": 0.45}
_MAINTENANCE_SCORES = {"Regular": 0.90, "Occasional": 0.70, "None": 0.50}


def f_temperature(label: str) -> float:
    return _TEMPERATURE_SCORES.get(label, 0.75)


def f_environment(label: str) -> float:
    return _ENVIRONMENT_SCORES.get(label, 0.70)


def f_power(label: str) -> float:
    return _POWER_SCORES.get(label, 0.70)


def f_service(label: str) -> float:
    return _MAINTENANCE_SCORES.get(label, 0.70)


def _normalize_weights(custom: Dict[str, float] | None) -> Dict[str, float]:
    """If user provided weights, validate and re-normalize so Σwᵢ = 1.0."""
    if not custom:
        return dict(DEFAULT_WEIGHTS)
    merged = {**DEFAULT_WEIGHTS, **{k: float(v) for k, v in custom.items()}}
    total = sum(merged.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: v / total for k, v in merged.items()}


# ─── Main endpoint ──────────────────────────────────────────────────────────
@router.post("/", response_model=PredictResponse)
def predict_lifespan(request: PredictRequest):
    if request.device_type not in DEVICE_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown device type '{request.device_type}'. Valid: {list(DEVICE_PROFILES.keys())}",
        )

    profile = DEVICE_PROFILES[request.device_type]
    base_lifespan = int(profile["base_lifespan"])

    current_year = datetime.now().year
    current_age = max(0.0, float(current_year - request.manufacturing_year))

    # Build factor list (display name, raw fᵢ, weight wᵢ, weighted wᵢ×fᵢ)
    raw_factors = {
        "age":         f_age(current_age, base_lifespan),
        "usage":       f_usage(request.usage_hours_per_day),
        "temperature": f_temperature(request.temperature_stress),
        "power":       f_power(request.power_outage_freq),
        "environment": f_environment(request.environment),
        "service":     f_service(request.maintenance_frequency),
    }
    labels = {
        "age":         f"{current_age:.1f} / {base_lifespan} yr",
        "usage":       f"{request.usage_hours_per_day:.0f} h/day",
        "temperature": request.temperature_stress,
        "power":       request.power_outage_freq,
        "environment": request.environment,
        "service":     request.maintenance_frequency,
    }
    weights = _normalize_weights(request.weights)

    factors: List[FactorDetail] = []
    health = 0.0
    for name, raw in raw_factors.items():
        w = weights[name]
        wd = w * raw
        health += wd
        factors.append(FactorDetail(
            name=name, raw=round(raw, 4), weight=round(w, 4),
            weighted=round(wd, 4), label=labels[name],
        ))

    health = _clamp(health)

    # End-of-life guard
    end_of_life = current_age >= base_lifespan
    if end_of_life:
        remaining_years = 0.0
        remaining_min = 0.0
        remaining_max = 0.0
    else:
        # Remaining life formula per spec
        raw_remaining = (base_lifespan * health) - current_age
        # Clamp upper bound to (Base_Lifespan − Current_Age) so we never over-promise
        max_remaining = base_lifespan - current_age
        remaining_years = max(0.0, min(raw_remaining, max_remaining))
        # Confidence range ±(Base_Lifespan × 0.15 × (1 − Health_Score))
        band = base_lifespan * 0.15 * (1.0 - health)
        remaining_min = max(0.0, remaining_years - band)
        remaining_max = min(max_remaining, remaining_years + band)

    # Derived metrics
    weight_kg = float(profile["weight_kg"])
    base_repair = float(profile["base_repair_cost"])

    co2_avoided_kg = (weight_kg * 0.05) * (remaining_years / base_lifespan) * 1000.0
    repair_savings = base_repair * health

    # ─── Optional ML predictions (xgboost / random_forest) ──────────────────
    ensemble: Dict[str, float] = {"formula": round(remaining_years, 4)}

    ml_input = {
        "device_type": request.device_type,
        "manufacturer": "Unknown",  # not supplied by API user; ML will use most-frequent
        "region": "Maharashtra",
        "base_lifespan_yrs": base_lifespan,
        "current_age_yrs": current_age,
        "daily_usage_hrs": request.usage_hours_per_day,
        "temperature": request.temperature_stress,
        "environment": request.environment,
        "power_quality": request.power_outage_freq,
        "maintenance": request.maintenance_frequency,
    }
    xgb_pred = _ml_predict("xgboost_model", ml_input)
    rf_pred = _ml_predict("rf_model", ml_input)
    if xgb_pred is not None:
        ensemble["xgboost"] = round(xgb_pred, 4)
    if rf_pred is not None:
        ensemble["random_forest"] = round(rf_pred, 4)

    # Resolve which prediction to surface
    choice = (request.model_choice or "formula").lower()
    if choice == "xgboost" and xgb_pred is not None:
        remaining_years = xgb_pred
        model_used = "XGBoost (trained on 500-row corrected dataset)"
    elif choice == "random_forest" and rf_pred is not None:
        remaining_years = rf_pred
        model_used = "Random Forest (trained on 500-row corrected dataset)"
    elif choice == "best":
        # Use the average of available predictions (ensemble) for robustness
        available = [remaining_years]
        if xgb_pred is not None:
            available.append(xgb_pred)
        if rf_pred is not None:
            available.append(rf_pred)
        remaining_years = sum(available) / len(available)
        model_used = f"Ensemble (avg of {len(available)} models)"
    else:
        # Default: formula
        model_used = "Weighted-Average (v2 — transparent)"

    # Re-clamp final value and re-derive confidence range around the chosen point
    max_remaining = max(0.0, base_lifespan - current_age)
    remaining_years = max(0.0, min(remaining_years, max_remaining))
    if end_of_life:
        remaining_years = 0.0
        remaining_min = 0.0
        remaining_max = 0.0
    else:
        band = base_lifespan * 0.15 * (1.0 - health)
        remaining_min = max(0.0, remaining_years - band)
        remaining_max = min(max_remaining, remaining_years + band)

    # Re-derive CO₂ and savings for the chosen prediction
    co2_avoided_kg = (weight_kg * 0.05) * (remaining_years / base_lifespan) * 1000.0

    response = PredictResponse(
        device_type=request.device_type,
        age=current_age,
        base_lifespan=base_lifespan,
        factors=factors,
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
        model_used=model_used,
        formula_text="L = Σ(wᵢ × fᵢ(M, T, E, U, P, S))",
        ensemble=ensemble,
    )

    # Persist to history (best-effort, never break the response)
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
        )
    except Exception as e:
        print(f"[prognosis] Failed to log lifespan history: {e}")

    return response


@router.get("/device-types")
async def get_device_types():
    return {
        "device_types": list(DEVICE_PROFILES.keys()),
        "default_weights": DEFAULT_WEIGHTS,
    }


@router.get("/profile/{device_type}")
async def get_device_profile(device_type: str):
    if device_type not in DEVICE_PROFILES:
        raise HTTPException(status_code=404, detail="Unknown device type")
    return DEVICE_PROFILES[device_type]
