"""Deterministic tests for the assumption-based generation forecast."""

import math

import pytest
from pydantic import ValidationError

from app.routers.generation import (
    CONSERVATION_TOLERANCE,
    GenerationForecastRequest,
    InventoryCohort,
    build_generation_forecast,
)


def test_inventory_cohort_accepts_only_constrained_known_devices():
    cohort = InventoryCohort(
        device_type=" laptop ", quantity=12, average_age_years=2.5
    )
    assert cohort.device_type == "Laptop"

    with pytest.raises(ValidationError, match="unknown device_type"):
        InventoryCohort(
            device_type="Imaginary Device", quantity=1, average_age_years=0
        )
    with pytest.raises(ValidationError):
        InventoryCohort(device_type="Laptop", quantity=0, average_age_years=0)
    with pytest.raises(ValidationError):
        InventoryCohort(device_type="Laptop", quantity=1, average_age_years=-0.1)


def test_request_horizon_is_bounded_and_extra_fields_are_forbidden():
    cohort = {"device_type": "Laptop", "quantity": 1, "average_age_years": 0}
    with pytest.raises(ValidationError):
        GenerationForecastRequest(cohorts=[cohort], horizon_years=31)
    with pytest.raises(ValidationError):
        GenerationForecastRequest(
            cohorts=[{**cohort, "unobserved_failure_rate": 0.25}],
            horizon_years=5,
        )


def test_first_year_matches_documented_conditional_survival_formula():
    request = GenerationForecastRequest(
        cohorts=[
            InventoryCohort(
                device_type="Laptop", quantity=100, average_age_years=0
            )
        ],
        horizon_years=1,
        lifespan_sensitivity_fraction=0.2,
    )
    result = build_generation_forecast(request)

    expected_survival = math.exp(-math.log(2.0) * (1.0 / 5.0) ** 3)
    expected_eol = 100.0 * (1.0 - expected_survival)
    year_one = result.annual[0]
    assert year_one.expected_eol_devices == pytest.approx(expected_eol)
    assert year_one.expected_e_waste_kg == pytest.approx(expected_eol * 2.0)
    assert year_one.scenario_min_eol_devices <= year_one.expected_eol_devices
    assert year_one.scenario_max_eol_devices >= year_one.expected_eol_devices


def test_mixed_inventory_conserves_each_cohort_and_aggregate_counts():
    request = GenerationForecastRequest(
        cohorts=[
            InventoryCohort(
                device_type="Laptop", quantity=137, average_age_years=2.25
            ),
            InventoryCohort(
                device_type="Refrigerator", quantity=41, average_age_years=8.5
            ),
            InventoryCohort(
                device_type="Mouse", quantity=503, average_age_years=1.0
            ),
        ],
        horizon_years=30,
    )
    result = build_generation_forecast(request)

    for cohort in result.cohort_forecasts:
        generated = math.fsum(row.expected_eol_devices for row in cohort.annual)
        assert generated + cohort.expected_devices_remaining_after_horizon == pytest.approx(
            cohort.quantity, abs=CONSERVATION_TOLERANCE
        )
        assert cohort.conservation_error_devices <= CONSERVATION_TOLERANCE

    generated = math.fsum(row.expected_eol_devices for row in result.annual)
    assert generated == pytest.approx(result.expected_eol_devices_within_horizon)
    assert generated + result.expected_devices_remaining_after_horizon == pytest.approx(
        result.total_input_devices, abs=CONSERVATION_TOLERANCE
    )
    assert result.conservation_error_devices <= CONSERVATION_TOLERANCE
    assert "not a probability interval" in result.uncertainty_note
    assert any("not estimated" in note for note in result.assumptions)


def test_maximum_quantity_cohort_balances_floating_point_residual():
    request = GenerationForecastRequest(
        cohorts=[
            InventoryCohort(
                device_type="Laptop",
                quantity=10_000_000,
                average_age_years=0,
            )
        ],
        horizon_years=30,
    )
    result = build_generation_forecast(request)
    cohort = result.cohort_forecasts[0]

    assert cohort.conservation_error_devices <= CONSERVATION_TOLERANCE
    assert result.conservation_error_devices <= CONSERVATION_TOLERANCE
    assert math.fsum(row.expected_eol_devices for row in cohort.annual) + (
        cohort.expected_devices_remaining_after_horizon
    ) == pytest.approx(cohort.quantity, abs=CONSERVATION_TOLERANCE)


def test_forecast_api_is_registered_under_shared_authenticated_v1_router(monkeypatch):
    # Avoid unrelated lifespan artifact loading while importing the application.
    monkeypatch.setenv("EWASTE_SKIP_MODEL_PRELOAD", "1")
    from fastapi.testclient import TestClient
    from app.auth import get_current_user
    from app.main import app

    payload = {
        "cohorts": [
            {"device_type": "Laptop", "quantity": 10, "average_age_years": 2}
        ],
        "horizon_years": 3,
    }
    client = TestClient(app)

    # The generation handler has no duplicate local auth dependency. This 401
    # therefore proves the dependency supplied by app.include_router applies.
    assert client.post("/api/v1/generation/forecast", json=payload).status_code == 401

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: "test_user"
    try:
        response = client.post("/api/v1/generation/forecast", json=payload)
    finally:
        app.dependency_overrides = original_overrides

    assert response.status_code == 200
    body = response.json()
    assert body["total_input_devices"] == 10
    assert len(body["annual"]) == 3


def test_skip_model_preload_disables_classifier_warmup(monkeypatch):
    import asyncio
    from app import main as main_module

    calls = []
    monkeypatch.setenv("EWASTE_SKIP_MODEL_PRELOAD", "1")
    monkeypatch.setattr(
        main_module.classifier,
        "warm_model",
        lambda: calls.append("warmed"),
    )

    async def exercise_lifespan():
        async with main_module.lifespan(main_module.app):
            pass

    asyncio.run(exercise_lifespan())
    assert calls == []
