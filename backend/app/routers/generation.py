"""Transparent, assumption-based e-waste generation forecasting.

This module projects an inventory of currently in-service devices through a
conditional survival curve. It does not fit a model or infer empirical failure
rates. The only device-specific inputs are the planning lifespan and nominal
weight already documented in :mod:`app.device_profiles`.

For a cohort of ``Q`` devices with current average age ``a``, profile lifespan
``L``, and elapsed forecast time ``t``::

    R(t | a) = exp(-ln(2) * (((a + t) / L)^k - (a / L)^k))
    EOL(t)   = Q * (R(t - 1 | a) - R(t | a))

``R`` is conditional survival from the inventory date. ``L`` is treated as the
median end-of-life age and ``k=3`` is a fixed, disclosed planning assumption.
The response also reports a scenario envelope obtained by varying ``L`` by a
bounded, user-visible fraction. The envelope is sensitivity analysis, not a
statistical confidence interval.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.device_profiles import DEVICE_PROFILES

router = APIRouter(prefix="/generation", tags=["E-Waste Generation Forecast"])

WEIBULL_SHAPE = 3.0
MAX_HORIZON_YEARS = 30
MAX_COHORTS = 500
MAX_COHORT_QUANTITY = 10_000_000
CONSERVATION_TOLERANCE = 1e-9
CONSERVATION_RELATIVE_TOLERANCE = 1e-12

_CANONICAL_DEVICE_NAMES = {
    name.casefold(): name for name in DEVICE_PROFILES
}


class InventoryCohort(BaseModel):
    """A homogeneous inventory cohort represented by its current average age."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    device_type: str = Field(
        min_length=1,
        description="A device name present in app.device_profiles.DEVICE_PROFILES.",
        json_schema_extra={"enum": sorted(DEVICE_PROFILES)},
    )
    quantity: int = Field(
        ge=1,
        le=MAX_COHORT_QUANTITY,
        strict=True,
        description="Number of currently in-service devices in the cohort.",
    )
    average_age_years: float = Field(
        ge=0,
        le=100,
        allow_inf_nan=False,
        description="Current arithmetic mean age of the cohort in years.",
    )

    @field_validator("device_type", mode="before")
    @classmethod
    def canonicalize_known_device(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        canonical = _CANONICAL_DEVICE_NAMES.get(value.strip().casefold())
        if canonical is None:
            allowed = ", ".join(sorted(DEVICE_PROFILES))
            raise ValueError(f"unknown device_type; expected one of: {allowed}")
        return canonical


class GenerationForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohorts: list[InventoryCohort] = Field(
        min_length=1,
        max_length=MAX_COHORTS,
    )
    horizon_years: int = Field(default=10, ge=1, le=MAX_HORIZON_YEARS, strict=True)
    lifespan_sensitivity_fraction: float = Field(
        default=0.20,
        ge=0,
        le=0.50,
        allow_inf_nan=False,
        description=(
            "Fractional variation around each profile lifespan used for the "
            "non-probabilistic scenario envelope."
        ),
    )


class AnnualGenerationEstimate(BaseModel):
    year_offset: int
    expected_eol_devices: float
    expected_e_waste_kg: float
    scenario_min_eol_devices: float
    scenario_max_eol_devices: float
    scenario_min_e_waste_kg: float
    scenario_max_e_waste_kg: float


class CohortGenerationForecast(BaseModel):
    device_type: str
    quantity: int
    average_age_years: float
    profile_lifespan_years: float
    profile_unit_weight_kg: float
    annual: list[AnnualGenerationEstimate]
    expected_eol_devices_within_horizon: float
    expected_e_waste_kg_within_horizon: float
    expected_devices_remaining_after_horizon: float
    conservation_error_devices: float


class GenerationForecastResponse(BaseModel):
    method: str
    formula: str
    horizon_years: int
    weibull_shape: float
    lifespan_sensitivity_fraction: float
    total_input_devices: int
    annual: list[AnnualGenerationEstimate]
    cohort_forecasts: list[CohortGenerationForecast]
    expected_eol_devices_within_horizon: float
    expected_e_waste_kg_within_horizon: float
    expected_devices_remaining_after_horizon: float
    conservation_error_devices: float
    uncertainty_note: str
    assumptions: list[str]


@dataclass(frozen=True)
class _ScenarioProjection:
    annual_eol_devices: tuple[float, ...]
    remaining_devices: float


def _count_tolerance(quantity: float) -> float:
    """Scale the roundoff allowance while retaining a strict absolute floor."""
    return max(
        CONSERVATION_TOLERANCE,
        abs(quantity) * CONSERVATION_RELATIVE_TOLERANCE,
    )


def conditional_survival(
    current_age_years: float,
    elapsed_years: float,
    median_lifespan_years: float,
) -> float:
    """Return survival for ``elapsed_years`` conditional on current survival.

    Computing the difference of cumulative hazards avoids division by a
    near-zero unconditional survival probability for very old cohorts.
    """
    if current_age_years < 0 or elapsed_years < 0:
        raise ValueError("ages and elapsed time must be non-negative")
    if median_lifespan_years <= 0:
        raise ValueError("median lifespan must be positive")

    start_scaled = current_age_years / median_lifespan_years
    end_scaled = (current_age_years + elapsed_years) / median_lifespan_years
    cumulative_hazard_delta = math.log(2.0) * (
        end_scaled**WEIBULL_SHAPE - start_scaled**WEIBULL_SHAPE
    )
    return math.exp(-cumulative_hazard_delta)


def _project_scenario(
    *,
    quantity: int,
    average_age_years: float,
    median_lifespan_years: float,
    horizon_years: int,
) -> _ScenarioProjection:
    survival = [
        conditional_survival(average_age_years, year, median_lifespan_years)
        for year in range(horizon_years + 1)
    ]
    annual = [
        max(0.0, quantity * (survival[year - 1] - survival[year]))
        for year in range(1, horizon_years + 1)
    ]
    remaining = max(0.0, quantity * survival[-1])

    # The differences telescope analytically, but separately rounded annual
    # products can miss Q by a few ulps for multi-million-device cohorts. Apply
    # only that numerical balance delta; do not change the survival assumptions.
    balance_delta = quantity - math.fsum([*annual, remaining])
    tolerance = _count_tolerance(quantity)
    if abs(balance_delta) > tolerance:
        raise ArithmeticError("survival projection failed count conservation")
    if remaining + balance_delta >= 0:
        remaining += balance_delta
    elif annual:
        largest_index = max(range(len(annual)), key=annual.__getitem__)
        annual[largest_index] += balance_delta
        if annual[largest_index] < 0:
            raise ArithmeticError("survival projection produced a negative flow")

    final_error = abs(quantity - math.fsum([*annual, remaining]))
    if final_error > tolerance:
        raise ArithmeticError("survival projection failed numerical balancing")
    return _ScenarioProjection(tuple(annual), remaining)


def _project_cohort(
    cohort: InventoryCohort,
    horizon_years: int,
    sensitivity_fraction: float,
) -> CohortGenerationForecast:
    profile = DEVICE_PROFILES[cohort.device_type]
    lifespan = float(profile["base_lifespan"])
    unit_weight = float(profile["weight_kg"])

    lifespan_scenarios = (
        lifespan * (1.0 - sensitivity_fraction),
        lifespan,
        lifespan * (1.0 + sensitivity_fraction),
    )
    scenarios = tuple(
        _project_scenario(
            quantity=cohort.quantity,
            average_age_years=cohort.average_age_years,
            median_lifespan_years=scenario_lifespan,
            horizon_years=horizon_years,
        )
        for scenario_lifespan in lifespan_scenarios
    )
    central = scenarios[1]

    annual: list[AnnualGenerationEstimate] = []
    for year_index in range(horizon_years):
        scenario_counts = [
            scenario.annual_eol_devices[year_index] for scenario in scenarios
        ]
        central_count = central.annual_eol_devices[year_index]
        annual.append(
            AnnualGenerationEstimate(
                year_offset=year_index + 1,
                expected_eol_devices=central_count,
                expected_e_waste_kg=central_count * unit_weight,
                scenario_min_eol_devices=min(scenario_counts),
                scenario_max_eol_devices=max(scenario_counts),
                scenario_min_e_waste_kg=min(scenario_counts) * unit_weight,
                scenario_max_e_waste_kg=max(scenario_counts) * unit_weight,
            )
        )

    generated = math.fsum(central.annual_eol_devices)
    conservation_error = abs(
        cohort.quantity - math.fsum((generated, central.remaining_devices))
    )
    if conservation_error > _count_tolerance(cohort.quantity):
        raise ArithmeticError("cohort projection failed count conservation")

    return CohortGenerationForecast(
        device_type=cohort.device_type,
        quantity=cohort.quantity,
        average_age_years=cohort.average_age_years,
        profile_lifespan_years=lifespan,
        profile_unit_weight_kg=unit_weight,
        annual=annual,
        expected_eol_devices_within_horizon=generated,
        expected_e_waste_kg_within_horizon=generated * unit_weight,
        expected_devices_remaining_after_horizon=central.remaining_devices,
        conservation_error_devices=conservation_error,
    )


def build_generation_forecast(
    request: GenerationForecastRequest,
) -> GenerationForecastResponse:
    """Build a deterministic, count-conserving forecast from inventory inputs."""
    cohort_forecasts = [
        _project_cohort(
            cohort,
            request.horizon_years,
            request.lifespan_sensitivity_fraction,
        )
        for cohort in request.cohorts
    ]

    annual: list[AnnualGenerationEstimate] = []
    for year_index in range(request.horizon_years):
        rows = [forecast.annual[year_index] for forecast in cohort_forecasts]
        annual.append(
            AnnualGenerationEstimate(
                year_offset=year_index + 1,
                expected_eol_devices=math.fsum(row.expected_eol_devices for row in rows),
                expected_e_waste_kg=math.fsum(row.expected_e_waste_kg for row in rows),
                scenario_min_eol_devices=math.fsum(
                    row.scenario_min_eol_devices for row in rows
                ),
                scenario_max_eol_devices=math.fsum(
                    row.scenario_max_eol_devices for row in rows
                ),
                scenario_min_e_waste_kg=math.fsum(
                    row.scenario_min_e_waste_kg for row in rows
                ),
                scenario_max_e_waste_kg=math.fsum(
                    row.scenario_max_e_waste_kg for row in rows
                ),
            )
        )

    total_input = sum(cohort.quantity for cohort in request.cohorts)
    total_generated = math.fsum(row.expected_eol_devices for row in annual)
    total_generated_kg = math.fsum(row.expected_e_waste_kg for row in annual)
    total_remaining = math.fsum(
        forecast.expected_devices_remaining_after_horizon
        for forecast in cohort_forecasts
    )
    conservation_error = abs(
        total_input - math.fsum((total_generated, total_remaining))
    )
    if conservation_error > _count_tolerance(total_input):
        raise ArithmeticError("aggregate projection failed count conservation")

    sensitivity_percent = request.lifespan_sensitivity_fraction * 100
    return GenerationForecastResponse(
        method="Conditional Weibull cohort-survival planning calculation",
        formula=(
            "R(t|a)=exp(-ln(2)*(((a+t)/L)^3-(a/L)^3)); "
            "annual EOL=Q*(R(t-1|a)-R(t|a))"
        ),
        horizon_years=request.horizon_years,
        weibull_shape=WEIBULL_SHAPE,
        lifespan_sensitivity_fraction=request.lifespan_sensitivity_fraction,
        total_input_devices=total_input,
        annual=annual,
        cohort_forecasts=cohort_forecasts,
        expected_eol_devices_within_horizon=total_generated,
        expected_e_waste_kg_within_horizon=total_generated_kg,
        expected_devices_remaining_after_horizon=total_remaining,
        conservation_error_devices=conservation_error,
        uncertainty_note=(
            f"The min/max values are a sensitivity envelope from varying each "
            f"profile lifespan by ±{sensitivity_percent:g}%. They are not a "
            "probability interval and are not calibrated to observed failures."
        ),
        assumptions=[
            "Each row represents currently in-service units summarized by one average age; no future purchases are added.",
            "The device profile base_lifespan is treated as the median end-of-life age and profile weight as kilograms per unit.",
            "The Weibull shape of 3 is a disclosed planning assumption and is not estimated from failure or disposal records.",
            "A projected end-of-life unit is counted as generated e-waste; storage, resale, repair, and reuse can delay actual waste collection.",
            "Fractional device counts are expected values for planning, not claims that a fraction of a physical device will be discarded.",
            "For every cohort, projected end-of-life devices plus projected survivors equal the submitted quantity within numerical tolerance.",
        ],
    )


@router.post("/forecast", response_model=GenerationForecastResponse)
async def forecast_generation(
    request: GenerationForecastRequest,
) -> GenerationForecastResponse:
    """Forecast annual end-of-life devices and mass for submitted inventory."""
    return build_generation_forecast(request)
