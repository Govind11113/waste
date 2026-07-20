"""Unit and API tests for the carbon calculator's validation and math."""

import math

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth import get_current_user
from app.routers import carbon as c


@pytest.fixture
def carbon_client(temp_db):  # noqa: ARG001
    app = FastAPI()
    app.include_router(c.router)
    app.dependency_overrides[get_current_user] = lambda: "user-carbon"
    with TestClient(app) as client:
        yield client


def _valid_payload(**overrides):
    payload = {
        "units": 1,
        "device_type": "Computer",
        "daily_hours": 8.0,
        "tdp": 200.0,
        "energy_rating": "A",
        "zip_code": "400001",
        "lifespan_years": 5.0,
    }
    payload.update(overrides)
    return payload


# ── Grid intensity resolution ──────────────────────────────────────────────
def test_grid_intensity_exact_code_wins():
    assert c.resolve_grid_intensity("400001") == 0.71


def test_grid_intensity_prefix_fallback():
    assert c.resolve_grid_intensity("400050") == 0.71


def test_grid_intensity_coal_belt_prefix():
    assert c.resolve_grid_intensity("440022") == 0.84


def test_grid_intensity_unknown_uses_state_default():
    assert c.resolve_grid_intensity("999999") == c.GRID_INTENSITY_DEFAULT


def test_grid_intensity_blank_is_safe_for_direct_helper_use():
    assert c.resolve_grid_intensity("") == c.GRID_INTENSITY_DEFAULT
    assert c.resolve_grid_intensity(None) == c.GRID_INTENSITY_DEFAULT


def test_coal_belt_dirtier_than_mumbai():
    assert c.resolve_grid_intensity("440001") > c.resolve_grid_intensity("400001")


# ── Known devices ──────────────────────────────────────────────────────────
def test_resolve_device_case_insensitive():
    assert c._resolve_device("laptop") == "Laptop"
    assert c._resolve_device("LAPTOP") == "Laptop"


def test_resolve_device_unknown_is_rejected():
    with pytest.raises(ValueError, match="unknown device_type"):
        c._resolve_device("flux capacitor")


# ── Strict request validation ──────────────────────────────────────────────
@pytest.mark.parametrize(
    "overrides",
    [
        {"device_type": "Flux Capacitor"},
        {"units": 0},
        {"units": c.MAX_UNITS + 1},
        {"units": "1"},
        {"units": True},
        {"daily_hours": -0.1},
        {"daily_hours": 24.1},
        {"daily_hours": "8"},
        {"tdp": -0.1},
        {"tdp": c.MAX_TDP_WATTS + 0.1},
        {"tdp": "65"},
        {"energy_rating": "E"},
        {"energy_rating": "a"},
        {"zip_code": "40001"},
        {"zip_code": "ABCDEF"},
        {"zip_code": " 400001 "},
        {"zip_code": "110001"},
        {"zip_code": 400001},
        {"lifespan_years": 0.0},
        {"lifespan_years": c.MAX_LIFESPAN_YEARS + 0.1},
        {"lifespan_years": "5"},
        {"unexpected": "field"},
    ],
)
def test_invalid_carbon_inputs_return_422(carbon_client, overrides):
    response = carbon_client.post(
        "/carbon/calculate", json=_valid_payload(**overrides)
    )
    assert response.status_code == 422, response.text


def test_device_name_is_canonicalized(carbon_client):
    response = carbon_client.post(
        "/carbon/calculate", json=_valid_payload(device_type="laptop")
    )
    assert response.status_code == 200, response.text


# ── Transparent carbon math ────────────────────────────────────────────────
def test_omitted_tdp_uses_profile_default(carbon_client):
    payload = _valid_payload(device_type="Laptop")
    payload.pop("tdp")
    payload.pop("lifespan_years")
    response = carbon_client.post("/carbon/calculate", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["power_w"] == 65.0
    assert body["lifespan_years"] == 5.0
    expected_annual_kwh = (65.0 / 1000.0) * 8.0 * 365.0 * 0.8
    assert body["annual_energy_kwh_per_unit"] == pytest.approx(
        expected_annual_kwh, abs=0.001
    )


def test_zero_profile_tdp_is_valid_when_omitted(carbon_client):
    payload = _valid_payload(device_type="Battery", daily_hours=24.0)
    payload.pop("tdp")
    response = carbon_client.post("/carbon/calculate", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["power_w"] == 0.0
    assert response.json()["operational_kg"] == 0.0


def test_formula_fields_reproduce_lifecycle_math(carbon_client):
    response = carbon_client.post(
        "/carbon/calculate",
        json=_valid_payload(
            device_type="Laptop",
            daily_hours=1.0,
            tdp=1000.0,
            energy_rating="C",
            lifespan_years=1.0,
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    annual_kwh = 1.0 * 1.0 * 365.0 * 1.0
    operational_kg = annual_kwh * 0.71
    total_kg = 200.0 + operational_kg
    assert body["rating_factor"] == 1.0
    assert body["annual_energy_kwh_per_unit"] == annual_kwh
    assert body["embodied_kg_per_unit"] == 200.0
    assert body["operational_kg"] == pytest.approx(round(operational_kg, 1))
    assert body["total_kg"] == pytest.approx(round(total_kg, 1))
    assert body["total_tco2e"] == pytest.approx(round(total_kg / 1000.0, 3))
    assert body["trees_planted"] == math.ceil(
        total_kg / c.KG_CO2_PER_TREE_PER_YEAR
    )
    assert "power_w" in body["formula_text"]


def test_tree_equivalents_are_rounded_up(carbon_client):
    response = carbon_client.post(
        "/carbon/calculate",
        json=_valid_payload(daily_hours=0.0, lifespan_years=1.0),
    )
    assert response.status_code == 200, response.text
    # Computer embodied carbon alone is 300 kg: 300 / 22 = 13.64 -> 14.
    assert response.json()["trees_planted"] == 14


def test_one_tonne_uses_ceiling_tree_equivalent():
    assert math.ceil(1000.0 / c.KG_CO2_PER_TREE_PER_YEAR) == 46


def test_tree_constant_in_published_estimate_range():
    assert 10.0 <= c.KG_CO2_PER_TREE_PER_YEAR <= 40.0
