"""API and migration tests for persisted history audit data."""

from datetime import datetime
import inspect
import json
import math
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth import get_current_user
from app.routers import carbon, history, prognosis


@pytest.fixture
def history_client(temp_db):
    app = FastAPI()
    app.include_router(prognosis.router)
    app.include_router(history.router)
    app.dependency_overrides[get_current_user] = lambda: "user-history"
    with TestClient(app) as client:
        yield client, temp_db


def test_prediction_audit_fields_round_trip_through_history_api(history_client):
    client, db = history_client
    response = client.post(
        "/predict/",
        json={
            "device_type": "Laptop",
            "manufacturing_year": datetime.now().year - 1,
            "usage_hours_per_day": 6.0,
            "temperature_stress": "Hot",
            "environment": "Harsh",
            "power_outage_freq": "Frequent Outages",
            "maintenance_frequency": "None",
            "software_load": "Heavy",
            "weights": {"age": 2.0, "software": 3.0},
            "model_choice": "formula",
        },
    )
    assert response.status_code == 200, response.text
    prediction = response.json()

    # A row for another user must never appear in this authenticated response.
    db.log_lifespan_prediction(
        device_type="Computer",
        age=1.0,
        base_lifespan=6,
        health_score=0.8,
        remaining_years=3.8,
        co2_avoided_kg=10.0,
        repair_savings_inr=1000.0,
        remaining_min=3.0,
        remaining_max=4.0,
        usage_hours_per_day=8.0,
        temperature="Normal",
        environment="Normal",
        power="Direct Grid",
        maintenance="Occasional",
        user_id="other-user",
        software_load="Office",
        normalized_weights=prognosis.DEFAULT_WEIGHTS,
        model_requested="formula",
        model_used="formula",
    )

    history_response = client.get("/history/lifespan")
    assert history_response.status_code == 200, history_response.text
    body = history_response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1

    item = body["items"][0]
    assert item["device_type"] == "Laptop"
    assert item["software_load"] == "Heavy"
    assert item["model_requested"] == "formula"
    assert item["model_used"] == "formula"
    assert item["normalized_weights"] == prediction["normalized_weights"]
    assert math.fsum(item["normalized_weights"].values()) == pytest.approx(1.0)

    # The DB stores portable JSON, while query/history layers expose an object.
    with sqlite3.connect(db.DB_PATH) as conn:
        stored = conn.execute(
            "SELECT normalized_weights FROM lifespan_history WHERE user_id = ?",
            ("user-history",),
        ).fetchone()[0]
    assert json.loads(stored) == prediction["normalized_weights"]


def test_lifespan_migration_is_idempotent_and_preserves_legacy_rows(temp_db):
    legacy_path = temp_db.DB_PATH
    legacy_path.unlink()
    with sqlite3.connect(legacy_path) as conn:
        conn.execute(
            """
            CREATE TABLE lifespan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_type TEXT NOT NULL,
                age REAL NOT NULL,
                base_lifespan INTEGER NOT NULL,
                health_score REAL NOT NULL,
                remaining_years REAL NOT NULL,
                remaining_min REAL NOT NULL,
                remaining_max REAL NOT NULL,
                co2_avoided_kg REAL NOT NULL,
                repair_savings_inr REAL NOT NULL,
                usage_hours_per_day REAL NOT NULL,
                temperature TEXT NOT NULL,
                environment TEXT NOT NULL,
                power TEXT NOT NULL,
                maintenance TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO lifespan_history
            (timestamp, device_type, age, base_lifespan, health_score,
             remaining_years, remaining_min, remaining_max, co2_avoided_kg,
             repair_savings_inr, usage_hours_per_day, temperature, environment,
             power, maintenance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2025-01-01T00:00:00",
                "Laptop",
                2.0,
                5,
                0.7,
                1.5,
                1.0,
                2.0,
                5.0,
                500.0,
                8.0,
                "Normal",
                "Normal",
                "Direct Grid",
                "Occasional",
            ),
        )

    temp_db.init_db()
    temp_db.init_db()

    with sqlite3.connect(legacy_path) as conn:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(lifespan_history)")
        }
        row = conn.execute(
            """SELECT device_type, software_load, normalized_weights,
                      model_requested, model_used
               FROM lifespan_history"""
        ).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM lifespan_history").fetchone()[0]

    assert {
        "software_load",
        "normalized_weights",
        "model_requested",
        "model_used",
        "user_id",
    } <= columns
    assert count == 1
    assert row == ("Laptop", None, None, None, None)

    items, total = temp_db.query_lifespan_history(user_id=None)
    assert total == 1
    assert items[0]["device_type"] == "Laptop"
    assert items[0]["normalized_weights"] is None


def test_all_sqlite_route_handlers_are_synchronous():
    handlers = [
        prognosis.predict_lifespan,
        carbon.calculate_carbon,
        history.get_history,
        history.get_stats,
        history.delete_history,
        history.get_lifespan_history,
        history.get_lifespan_stats,
        history.delete_lifespan_history,
        history.get_carbon_history,
        history.get_carbon_stats,
        history.delete_carbon_history,
    ]
    assert all(not inspect.iscoroutinefunction(handler) for handler in handlers)
