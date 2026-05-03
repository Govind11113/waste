from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/carbon", tags=["Carbon Calculator"])

GRID_INTENSITY = {
    "400001": 0.71, "400002": 0.71, "400003": 0.71, "400004": 0.71, "400005": 0.71,
    "400006": 0.71, "400007": 0.71, "400008": 0.71, "400009": 0.71, "400010": 0.71,
    "411001": 0.72, "411002": 0.72, "411003": 0.72, "411004": 0.72, "411005": 0.72,
    "440001": 0.75, "440002": 0.75, "440003": 0.75, "440004": 0.75, "440005": 0.75,
}

EMBODIED_CARBON = {
    "laptop": 200,
    "desktop": 300,
    "server": 500,
    "smartphone": 80,
    "tablet": 100,
    "printer": 120,
    "monitor": 180,
    "router": 50
}


class CarbonRequest(BaseModel):
    units: int = 1
    device_type: str = "laptop"
    daily_hours: float = 8
    tdp: float = 65
    screen_size: float = 15.6
    energy_rating: str = "A"
    zip_code: str = "400001"


class CarbonResponse(BaseModel):
    total_tco2e: float
    baseline_avg: float
    trees_planted: int
    embodied_kg: float
    operational_kg: float
    grid_intensity: float


@router.post("/calculate", response_model=CarbonResponse)
async def calculate_carbon(request: CarbonRequest):
    grid_intensity = GRID_INTENSITY.get(request.zip_code[:6], 0.71)

    embodied_kg = EMBODIED_CARBON.get(request.device_type.lower(), 200) * request.units

    power_kw = request.tdp / 1000
    annual_energy_kwh = power_kw * request.daily_hours * 365

    rating_factor = {"A": 0.8, "B": 0.9, "C": 1.0, "D": 1.1}.get(request.energy_rating, 1.0)
    annual_energy_kwh *= rating_factor

    operational_kg = annual_energy_kwh * grid_intensity * request.units

    total_kg = embodied_kg + operational_kg
    total_tco2e = total_kg / 1000

    baseline_avg = 500 * request.units
    trees_planted = int(total_tco2e * 45)

    return CarbonResponse(
        total_tco2e=round(total_tco2e, 3),
        baseline_avg=round(baseline_avg, 1),
        trees_planted=trees_planted,
        embodied_kg=round(embodied_kg, 1),
        operational_kg=round(operational_kg, 1),
        grid_intensity=grid_intensity
    )
