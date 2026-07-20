from math import ceil
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.auth import get_current_user
from app.db import log_carbon_calculation
from app.device_profiles import DEVICE_PROFILES, default_lifespan, embodied_carbon
from app.logging_config import get_logger

logger = get_logger("ewaste.carbon")

router = APIRouter(prefix="/carbon", tags=["Carbon Calculator"])

# ─────────────────────────────────────────────────────────────────────────────
# India electricity grid carbon intensity (kg CO2e / kWh)
# ─────────────────────────────────────────────────────────────────────────────
# Sources (see README "Data Sources & Citations"):
#   [1] CEA CO2 Baseline Database for the Indian Power Sector, Govt. of India,
#       Ministry of Power / Central Electricity Authority. India operates a
#       single national grid; the combined-margin grid emission factor is
#       ~0.71-0.82 kg CO2/kWh in recent versions.
#   [2] Ember — India electricity data (per-state carbon intensity, gCO2/kWh,
#       2019-present): https://ember-energy.org/data/india-electricity-data/
GRID_INTENSITY_DEFAULT = 0.79

# A mature tree sequesters approximately 22 kg CO2/year. Tree equivalents are
# rounded upward because a fractional tree cannot meet the stated offset.
KG_CO2_PER_TREE_PER_YEAR = 22.0

GRID_INTENSITY_BY_PREFIX = {
    "400": 0.71,
    "401": 0.71,
    "402": 0.72,
    "403": 0.72,
    "410": 0.72,
    "411": 0.72,
    "412": 0.72,
    "413": 0.74,
    "414": 0.75,
    "415": 0.73,
    "416": 0.73,
    "421": 0.72,
    "422": 0.74,
    "423": 0.75,
    "424": 0.76,
    "425": 0.78,
    "431": 0.82,
    "440": 0.84,
    "441": 0.84,
    "442": 0.85,
    "444": 0.83,
}

GRID_INTENSITY = {
    "400001": 0.71,
    "400002": 0.71,
    "400003": 0.71,
    "400004": 0.71,
    "400005": 0.71,
    "411001": 0.72,
    "411002": 0.72,
    "411003": 0.72,
    "440001": 0.84,
    "440002": 0.84,
    "440003": 0.84,
}

RATING_FACTORS = {"A": 0.8, "B": 0.9, "C": 1.0, "D": 1.1}
MAX_UNITS = 100_000
MAX_TDP_WATTS = 10_000.0
MAX_LIFESPAN_YEARS = 50.0
MIN_MAHARASHTRA_PIN = 400_000
MAX_MAHARASHTRA_PIN = 445_999


def resolve_grid_intensity(zip_code: str) -> float:
    """Resolve exact PIN, then prefix, then the documented state average."""
    code = (zip_code or "").strip()
    if code in GRID_INTENSITY:
        return GRID_INTENSITY[code]
    prefix = code[:3]
    if prefix in GRID_INTENSITY_BY_PREFIX:
        return GRID_INTENSITY_BY_PREFIX[prefix]
    return GRID_INTENSITY_DEFAULT


EMBODIED_CARBON = embodied_carbon()
DEFAULT_LIFESPAN = default_lifespan()


def _resolve_device(name: object) -> str:
    """Return a canonical known device name or reject the value."""
    if not isinstance(name, str):
        raise ValueError("device_type must be a string")
    cleaned = name.strip()
    for key in DEVICE_PROFILES:
        if key.casefold() == cleaned.casefold():
            return key
    raise ValueError(
        f"unknown device_type {name!r}; expected one of: {', '.join(DEVICE_PROFILES)}"
    )


MaharashtraPin = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^\d{6}$"),
]
EnergyRating = Literal["A", "B", "C", "D"]


class CarbonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    units: int = Field(default=1, strict=True, ge=1, le=MAX_UNITS)
    device_type: str = "Computer"
    daily_hours: float = Field(
        default=8.0, strict=True, ge=0.0, le=24.0, allow_inf_nan=False
    )
    # None means use the selected device profile. Explicit zero remains valid
    # for passive devices (for example batteries and remote controls).
    tdp: Optional[float] = Field(
        default=None,
        strict=True,
        ge=0.0,
        le=MAX_TDP_WATTS,
        allow_inf_nan=False,
    )
    energy_rating: EnergyRating = "A"
    zip_code: MaharashtraPin = "400001"
    lifespan_years: Optional[float] = Field(
        default=None,
        strict=True,
        gt=0.0,
        le=MAX_LIFESPAN_YEARS,
        allow_inf_nan=False,
    )

    @field_validator("device_type", mode="before")
    @classmethod
    def validate_device_type(cls, value: object) -> str:
        return _resolve_device(value)

    @field_validator("zip_code")
    @classmethod
    def validate_maharashtra_pin(cls, value: str) -> str:
        numeric_pin = int(value)
        if not MIN_MAHARASHTRA_PIN <= numeric_pin <= MAX_MAHARASHTRA_PIN:
            raise ValueError(
                "zip_code must be a six-digit Maharashtra PIN between 400000 and 445999"
            )
        return value


class CarbonResponse(BaseModel):
    total_tco2e: float
    total_kg: float
    baseline_avg: float
    trees_planted: int
    embodied_kg: float
    embodied_kg_per_unit: float
    operational_kg: float
    grid_intensity: float
    lifespan_years: float
    power_w: float
    rating_factor: float
    annual_energy_kwh_per_unit: float
    formula_text: str


@router.post("/calculate", response_model=CarbonResponse)
def calculate_carbon(
    request: CarbonRequest, user_id: str = Depends(get_current_user)
):
    """Calculate lifecycle emissions using explicit, inspectable units.

    annual kWh/unit = (power W / 1000) × hours/day × 365 × rating factor
    operational kg = annual kWh/unit × kg/kWh × units × lifespan years
    total kg = embodied kg/unit × units + operational kg
    """
    device_key = request.device_type
    profile = DEVICE_PROFILES[device_key]
    grid_intensity = resolve_grid_intensity(request.zip_code)
    lifespan = (
        request.lifespan_years
        if request.lifespan_years is not None
        else float(DEFAULT_LIFESPAN[device_key])
    )
    power_w = request.tdp if request.tdp is not None else float(profile["default_tdp"])
    rating_factor = RATING_FACTORS[request.energy_rating]

    embodied_kg_per_unit = float(EMBODIED_CARBON[device_key])
    embodied_kg = embodied_kg_per_unit * request.units

    power_kw = power_w / 1000.0
    annual_energy_kwh_per_unit = (
        power_kw * request.daily_hours * 365.0 * rating_factor
    )
    operational_kg = (
        annual_energy_kwh_per_unit
        * grid_intensity
        * request.units
        * lifespan
    )

    total_kg = embodied_kg + operational_kg
    total_tco2e = total_kg / 1000.0

    # Indicative 500 kg CO2e lifetime reference per device for the UI's
    # comparison bar. It is not part of the lifecycle sum above.
    baseline_avg = 500.0 * request.units
    trees_planted = ceil(total_kg / KG_CO2_PER_TREE_PER_YEAR)

    try:
        log_carbon_calculation(
            device_type=device_key,
            units=request.units,
            daily_hours=request.daily_hours,
            tdp=power_w,
            energy_rating=request.energy_rating,
            zip_code=request.zip_code,
            lifespan_years=lifespan,
            total_tco2e=round(total_tco2e, 3),
            embodied_kg=round(embodied_kg, 1),
            operational_kg=round(operational_kg, 1),
            grid_intensity=grid_intensity,
            trees_planted=trees_planted,
            user_id=user_id,
        )
    except Exception as exc:
        logger.error("Failed to log carbon history: %s", exc)

    return CarbonResponse(
        total_tco2e=round(total_tco2e, 3),
        total_kg=round(total_kg, 1),
        baseline_avg=round(baseline_avg, 1),
        trees_planted=trees_planted,
        embodied_kg=round(embodied_kg, 1),
        embodied_kg_per_unit=embodied_kg_per_unit,
        operational_kg=round(operational_kg, 1),
        grid_intensity=grid_intensity,
        lifespan_years=lifespan,
        power_w=power_w,
        rating_factor=rating_factor,
        annual_energy_kwh_per_unit=round(annual_energy_kwh_per_unit, 3),
        formula_text=(
            "total_kg = embodied_kg_per_unit × units + "
            "((power_w ÷ 1000) × daily_hours × 365 × rating_factor × "
            "grid_intensity × units × lifespan_years)"
        ),
    )


@router.get("/devices")
async def get_devices():
    return {
        "devices": list(EMBODIED_CARBON.keys()),
        "default_power_w": {
            name: float(profile["default_tdp"])
            for name, profile in DEVICE_PROFILES.items()
        },
    }
