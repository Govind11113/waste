"""
Lifespan prediction using the formula:
  L = (1/N) * Σ f_i(M, T, E, U, P, S)
where each f_i returns a normalized health score in [0, 1].
"""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/predict", tags=["Prognosis"])


# Carbon and lifespan profiles per device — single source of truth
CO2_PROFILES = {
    "Motherboard": {"manufacturing": 80, "annual": 10, "recycling": 5, "base_lifespan": 8},
    "Hard Disk / SSD": {"manufacturing": 40, "annual": 5, "recycling": 2, "base_lifespan": 5},
    "Monitor": {"manufacturing": 180, "annual": 40, "recycling": 18, "base_lifespan": 7},
    "Mouse": {"manufacturing": 15, "annual": 1, "recycling": 1, "base_lifespan": 3},
    "Keyboard": {"manufacturing": 20, "annual": 2, "recycling": 2, "base_lifespan": 4},
    "Smartphone": {"manufacturing": 80, "annual": 20, "recycling": 10, "base_lifespan": 4},
    "Computer": {"manufacturing": 300, "annual": 80, "recycling": 25, "base_lifespan": 6},
    "Printer": {"manufacturing": 120, "annual": 30, "recycling": 15, "base_lifespan": 5},
    "Projector": {"manufacturing": 150, "annual": 40, "recycling": 20, "base_lifespan": 5},
    "Router / Switch": {"manufacturing": 50, "annual": 15, "recycling": 5, "base_lifespan": 6},
    "Air Conditioner": {"manufacturing": 600, "annual": 250, "recycling": 60, "base_lifespan": 10},
    "Laptop": {"manufacturing": 200, "annual": 50, "recycling": 18, "base_lifespan": 5},
}

COST_PROFILES = {
    "Motherboard": {"replace": 8000, "repair": 2500},
    "Hard Disk / SSD": {"replace": 4000, "repair": 800},
    "Monitor": {"replace": 9000, "repair": 1500},
    "Mouse": {"replace": 500, "repair": 100},
    "Keyboard": {"replace": 1000, "repair": 200},
    "Smartphone": {"replace": 15000, "repair": 3000},
    "Computer": {"replace": 35000, "repair": 4000},
    "Printer": {"replace": 12000, "repair": 2500},
    "Projector": {"replace": 25000, "repair": 6000},
    "Router / Switch": {"replace": 3000, "repair": 500},
    "Air Conditioner": {"replace": 40000, "repair": 5000},
    "Laptop": {"replace": 50000, "repair": 6000},
}

POWER_QUALITY_SCORE = {"UPS Protected": 1.0, "Direct Grid": 0.7, "Frequent Outages": 0.3}
MAINTENANCE_SCORE = {"Regular": 1.0, "Occasional": 0.6, "None": 0.2}


class PredictRequest(BaseModel):
    device_type: str
    manufacturing_year: int
    usage_hours_per_day: float = 8.0
    temperature_stress: float = 0.5  # 0 = optimal, 1 = severe
    humidity_index: float = 0.5      # 0 = dry/optimal, 1 = saturated
    dust_index: float = 0.5          # 0 = clean, 1 = heavy dust
    power_outage_freq: str = "Direct Grid"
    maintenance_frequency: str = "Occasional"


class PredictResponse(BaseModel):
    remaining_years: float
    health_percentage: float
    co2_avoided: float
    manufacturing_co2: float
    annual_co2: float
    recycling_co2: float
    age: float
    base_lifespan: int
    model_used: str
    repair_cost: float
    replace_cost: float
    factor_breakdown: dict


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def f_age(current_age: float, base_lifespan: int) -> float:
    return _clamp(1.0 - current_age / base_lifespan)


def f_temperature(temperature_stress: float) -> float:
    return _clamp(1.0 - temperature_stress)


def f_environment(humidity_index: float, dust_index: float) -> float:
    return _clamp(1.0 - (humidity_index + dust_index) / 2.0)


def f_usage(usage_hours_per_day: float) -> float:
    """Optimal at 0–8 hours; degrades linearly beyond 8h, zero at 24h+."""
    excess = max(0.0, usage_hours_per_day - 8.0)
    return _clamp(1.0 - excess / 16.0)


def f_power(power_outage_freq: str) -> float:
    return POWER_QUALITY_SCORE.get(power_outage_freq, 0.7)


def f_service(maintenance_frequency: str) -> float:
    return MAINTENANCE_SCORE.get(maintenance_frequency, 0.6)


@router.post("/", response_model=PredictResponse)
def predict_lifespan(request: PredictRequest):
    current_year = datetime.now().year
    current_age = float(max(0, current_year - request.manufacturing_year))

    profile = CO2_PROFILES.get(request.device_type, CO2_PROFILES["Computer"])
    base_lifespan = profile["base_lifespan"]

    # L = (1/N) * Σ f_i(M, T, E, U, P, S)
    factors = {
        "age": f_age(current_age, base_lifespan),
        "temperature": f_temperature(request.temperature_stress),
        "environment": f_environment(request.humidity_index, request.dust_index),
        "usage": f_usage(request.usage_hours_per_day),
        "power": f_power(request.power_outage_freq),
        "service": f_service(request.maintenance_frequency),
    }
    L = sum(factors.values()) / len(factors)

    # Remaining years: scale base lifespan by health, then subtract age already lived
    remaining_years = max(0.0, round(base_lifespan * L - current_age, 1))
    health_percentage = round(L * 100, 1)
    co2_avoided = profile["manufacturing"] * (remaining_years / base_lifespan)

    cost_profile = COST_PROFILES.get(request.device_type, {"repair": 1000, "replace": 5000})

    return PredictResponse(
        remaining_years=remaining_years,
        health_percentage=health_percentage,
        co2_avoided=round(co2_avoided, 1),
        manufacturing_co2=profile["manufacturing"],
        annual_co2=profile["annual"],
        recycling_co2=profile["recycling"],
        age=current_age,
        base_lifespan=base_lifespan,
        model_used="Formula (Weighted Average)",
        repair_cost=float(cost_profile["repair"]),
        replace_cost=float(cost_profile["replace"]),
        factor_breakdown={k: round(v, 3) for k, v in factors.items()},
    )


@router.get("/device-types")
async def get_device_types():
    return {"device_types": list(CO2_PROFILES.keys())}
