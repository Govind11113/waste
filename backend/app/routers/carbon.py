from fastapi import APIRouter
from pydantic import BaseModel
from app.db import log_carbon_calculation

router = APIRouter(prefix="/carbon", tags=["Carbon Calculator"])

# Indian grid intensity (kg CO2 / kWh) — sampled by 6-digit postal code
GRID_INTENSITY = {
    "400001": 0.71, "400002": 0.71, "400003": 0.71, "400004": 0.71, "400005": 0.71,
    "400006": 0.71, "400007": 0.71, "400008": 0.71, "400009": 0.71, "400010": 0.71,
    "411001": 0.72, "411002": 0.72, "411003": 0.72, "411004": 0.72, "411005": 0.72,
    "440001": 0.75, "440002": 0.75, "440003": 0.75, "440004": 0.75, "440005": 0.75,
}

# Aligned with classifier CO2_PROFILES — single source of truth
EMBODIED_CARBON = {
    "Motherboard": 80,
    "Hard Disk / SSD": 40,
    "Monitor": 180,
    "Mouse": 15,
    "Keyboard": 20,
    "Smartphone": 80,
    "Computer": 300,
    "Printer": 120,
    "Projector": 150,
    "Router / Switch": 50,
    "Air Conditioner": 600,
    "Laptop": 200,
    "Television": 220,
    "Microwave": 90,
}

# Suggested base lifespans (years) for operational-emissions integration
DEFAULT_LIFESPAN = {
    "Motherboard": 8,
    "Hard Disk / SSD": 5,
    "Monitor": 7,
    "Mouse": 3,
    "Keyboard": 4,
    "Smartphone": 4,
    "Computer": 6,
    "Printer": 5,
    "Projector": 5,
    "Router / Switch": 6,
    "Air Conditioner": 10,
    "Laptop": 5,
    "Television": 8,
    "Microwave": 8,
}


class CarbonRequest(BaseModel):
    units: int = 1
    device_type: str = "Computer"
    daily_hours: float = 8
    tdp: float = 65
    energy_rating: str = "A"
    zip_code: str = "400001"
    lifespan_years: float | None = None


class CarbonResponse(BaseModel):
    total_tco2e: float
    baseline_avg: float
    trees_planted: int
    embodied_kg: float
    operational_kg: float
    grid_intensity: float
    lifespan_years: float


def _resolve_device(name: str) -> str:
    """Match user input case-insensitively to known device keys."""
    name_lower = name.lower()
    for key in EMBODIED_CARBON.keys():
        if key.lower() == name_lower:
            return key
    return "Computer"  # safe default


@router.post("/calculate", response_model=CarbonResponse)
async def calculate_carbon(request: CarbonRequest):
    grid_intensity = GRID_INTENSITY.get(request.zip_code[:6], 0.71)

    device_key = _resolve_device(request.device_type)
    lifespan = request.lifespan_years if request.lifespan_years and request.lifespan_years > 0 else DEFAULT_LIFESPAN.get(device_key, 5)

    embodied_kg = EMBODIED_CARBON.get(device_key, 200) * request.units

    power_kw = request.tdp / 1000
    annual_energy_kwh = power_kw * request.daily_hours * 365

    rating_factor = {"A": 0.8, "B": 0.9, "C": 1.0, "D": 1.1}.get(request.energy_rating, 1.0)
    annual_energy_kwh *= rating_factor

    operational_kg = annual_energy_kwh * grid_intensity * request.units * lifespan

    total_kg = embodied_kg + operational_kg
    total_tco2e = total_kg / 1000

    baseline_avg = 500 * request.units
    trees_planted = int(total_tco2e * 45)

    # Persist to carbon history (best-effort)
    try:
        log_carbon_calculation(
            device_type=device_key,
            units=request.units,
            daily_hours=request.daily_hours,
            tdp=request.tdp,
            energy_rating=request.energy_rating,
            zip_code=request.zip_code,
            lifespan_years=lifespan,
            total_tco2e=round(total_tco2e, 3),
            embodied_kg=round(embodied_kg, 1),
            operational_kg=round(operational_kg, 1),
            grid_intensity=grid_intensity,
            trees_planted=trees_planted,
        )
    except Exception as e:
        print(f"[carbon] Failed to log carbon history: {e}")

    return CarbonResponse(
        total_tco2e=round(total_tco2e, 3),
        baseline_avg=round(baseline_avg, 1),
        trees_planted=trees_planted,
        embodied_kg=round(embodied_kg, 1),
        operational_kg=round(operational_kg, 1),
        grid_intensity=grid_intensity,
        lifespan_years=lifespan,
    )


@router.get("/devices")
async def get_devices():
    return {"devices": list(EMBODIED_CARBON.keys())}
