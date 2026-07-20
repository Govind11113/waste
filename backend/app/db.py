import json
import math
import os
import sqlite3
import threading
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.logging_config import get_logger
from app.runtime import database_path

logger = get_logger("ewaste.db")

# Tests and deployments can explicitly select a database path. Packaged Windows
# runs default to the per-user LOCALAPPDATA directory resolved by app.runtime.
DB_PATH = database_path()

_lock = threading.Lock()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


@contextmanager
def _cursor():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _add_missing_columns(
    conn: sqlite3.Connection, table: str, columns: Mapping[str, str]
) -> None:
    """Idempotently add columns without replacing or copying existing rows."""
    existing = {
        row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    }
    for column_name, declaration in columns.items():
        if column_name not in existing:
            conn.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{column_name}" {declaration}'
            )
            existing.add(column_name)


def init_db():
    """Create and migrate all history tables without deleting existing data."""
    with _cursor() as conn:
        # WAL allows readers to continue while the single packaged server writes.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                filename TEXT,
                waste_status TEXT NOT NULL,
                hazard_level TEXT NOT NULL,
                confidence REAL NOT NULL,
                entity TEXT NOT NULL,
                group_name TEXT NOT NULL,
                condition TEXT NOT NULL,
                co2_delta REAL NOT NULL,
                processing_time REAL NOT NULL,
                recyclability TEXT,
                model_used TEXT,
                user_id TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lifespan_history (
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
                maintenance TEXT NOT NULL,
                software_load TEXT,
                normalized_weights TEXT,
                model_requested TEXT,
                model_used TEXT,
                user_id TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS carbon_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_type TEXT NOT NULL,
                units INTEGER NOT NULL,
                daily_hours REAL NOT NULL,
                tdp REAL NOT NULL,
                energy_rating TEXT NOT NULL,
                zip_code TEXT NOT NULL,
                lifespan_years REAL NOT NULL,
                total_tco2e REAL NOT NULL,
                embodied_kg REAL NOT NULL,
                operational_kg REAL NOT NULL,
                grid_intensity REAL NOT NULL,
                trees_planted INTEGER NOT NULL,
                user_id TEXT
            )
            """
        )

        # Each ALTER is guarded by PRAGMA table_info, so repeated startup is
        # safe. New columns are nullable because historical rows cannot be
        # truthfully backfilled with inputs/model choices they never recorded.
        _add_missing_columns(
            conn,
            "scan_history",
            {
                "recyclability": "TEXT",
                "model_used": "TEXT",
                "user_id": "TEXT",
            },
        )
        _add_missing_columns(
            conn,
            "lifespan_history",
            {
                "software_load": "TEXT",
                "normalized_weights": "TEXT",
                "model_requested": "TEXT",
                "model_used": "TEXT",
                "user_id": "TEXT",
            },
        )
        _add_missing_columns(conn, "carbon_history", {"user_id": "TEXT"})

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scan_history_timestamp "
            "ON scan_history(timestamp DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scan_history_status "
            "ON scan_history(waste_status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scan_history_user "
            "ON scan_history(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lifespan_history_timestamp "
            "ON lifespan_history(timestamp DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lifespan_history_device "
            "ON lifespan_history(device_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lifespan_history_user "
            "ON lifespan_history(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_carbon_history_timestamp "
            "ON carbon_history(timestamp DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_carbon_history_user "
            "ON carbon_history(user_id)"
        )

    logger.info("Local scan history DB ready at %s", DB_PATH)


def database_healthcheck() -> tuple[bool, str | None]:
    """Return a sanitized readiness result without exposing filesystem paths."""
    try:
        with _cursor() as conn:
            value = conn.execute("SELECT 1").fetchone()[0]
        return value == 1, None if value == 1 else "database query failed"
    except (OSError, sqlite3.Error):
        logger.exception("Database readiness check failed")
        return False, "database unavailable"


def log_scan(
    filename: Optional[str],
    waste_status: str,
    hazard_level: str,
    confidence: float,
    entity: str,
    group_name: str,
    condition: str,
    co2_delta: float,
    processing_time: float,
    recyclability: Optional[str] = None,
    model_used: Optional[str] = None,
    user_id: Optional[str] = None,
):
    try:
        with _cursor() as conn:
            conn.execute(
                """
                INSERT INTO scan_history
                (timestamp, filename, waste_status, hazard_level, confidence,
                 entity, group_name, condition, co2_delta, processing_time,
                 recyclability, model_used, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    filename,
                    waste_status,
                    hazard_level,

                    confidence,
                    entity,
                    group_name,
                    condition,
                    co2_delta,
                    processing_time,
                    recyclability,
                    model_used,
                    user_id,
                ),
            )
    except Exception as exc:
        logger.error("Error logging scan: %s", exc, exc_info=True)


def log_lifespan_prediction(
    device_type: str,
    age: float,
    base_lifespan: int,
    health_score: float,
    remaining_years: float,
    co2_avoided_kg: float,
    repair_savings_inr: float,
    remaining_min: float,
    remaining_max: float,
    usage_hours_per_day: float,
    temperature: str,
    environment: str,
    power: str,
    maintenance: str,
    user_id: Optional[str] = None,
    software_load: Optional[str] = None,
    normalized_weights: Optional[Mapping[str, float]] = None,
    model_requested: Optional[str] = None,
    model_used: Optional[str] = None,
):
    try:
        weights_json = (
            json.dumps(
                {name: float(value) for name, value in normalized_weights.items()},
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            if normalized_weights is not None
            else None
        )
        with _cursor() as conn:
            conn.execute(
                """
                INSERT INTO lifespan_history
                (timestamp, device_type, age, base_lifespan, health_score,
                 remaining_years, remaining_min, remaining_max,
                 co2_avoided_kg, repair_savings_inr,
                 usage_hours_per_day, temperature, environment, power,
                 maintenance, software_load, normalized_weights,
                 model_requested, model_used, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    device_type,
                    age,
                    base_lifespan,
                    health_score,
                    remaining_years,
                    remaining_min,
                    remaining_max,
                    co2_avoided_kg,
                    repair_savings_inr,
                    usage_hours_per_day,
                    temperature,
                    environment,
                    power,
                    maintenance,
                    software_load,
                    weights_json,
                    model_requested,
                    model_used,
                    user_id,
                ),
            )
    except Exception as exc:
        logger.error("Error logging lifespan prediction: %s", exc, exc_info=True)


def log_carbon_calculation(
    device_type: str,
    units: int,
    daily_hours: float,
    tdp: float,
    energy_rating: str,
    zip_code: str,
    lifespan_years: float,
    total_tco2e: float,
    embodied_kg: float,
    operational_kg: float,
    grid_intensity: float,
    trees_planted: int,
    user_id: Optional[str] = None,
):
    try:
        with _cursor() as conn:
            conn.execute(
                """
                INSERT INTO carbon_history
                (timestamp, device_type, units, daily_hours, tdp, energy_rating,
                 zip_code, lifespan_years, total_tco2e, embodied_kg, operational_kg,
                 grid_intensity, trees_planted, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    device_type,
                    units,
                    daily_hours,
                    tdp,
                    energy_rating,
                    zip_code,
                    lifespan_years,
                    total_tco2e,
                    embodied_kg,
                    operational_kg,
                    grid_intensity,
                    trees_planted,
                    user_id,
                ),
            )
    except Exception:
        logger.exception("Error logging carbon calculation")


def query_history(
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
):
    where = []
    params: list = []
    if user_id is not None:
        where.append("user_id = ?")
        params.append(user_id)
    if search:
        where.append("(filename LIKE ? OR entity LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if status:
        where.append("waste_status = ?")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    offset = (page - 1) * per_page
    with _cursor() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM scan_history {clause}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT * FROM scan_history {clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        ).fetchall()
    return [dict(row) for row in rows], total


def _decode_normalized_weights(value: object) -> Optional[dict[str, float]]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return None
        decoded: dict[str, float] = {}
        for name, weight in parsed.items():
            if not isinstance(name, str) or isinstance(weight, bool):
                return None
            numeric_weight = float(weight)
            if not math.isfinite(numeric_weight) or numeric_weight < 0:
                return None
            decoded[name] = numeric_weight
        return decoded
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def query_lifespan_history(
    page: int = 1,
    per_page: int = 10,
    device_type: Optional[str] = None,
    user_id: Optional[str] = None,
):
    where = []
    params: list = []
    if user_id is not None:
        where.append("user_id = ?")
        params.append(user_id)
    if device_type:
        where.append("device_type = ?")
        params.append(device_type)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    offset = (page - 1) * per_page
    with _cursor() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM lifespan_history {clause}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT * FROM lifespan_history {clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

    items = []
    for row in rows:
        item = dict(row)
        item["normalized_weights"] = _decode_normalized_weights(
            item.get("normalized_weights")
        )
        items.append(item)
    return items, total


def query_carbon_history(
    page: int = 1,
    per_page: int = 10,
    device_type: Optional[str] = None,
    user_id: Optional[str] = None,
):
    where = []
    params: list = []
    if user_id is not None:
        where.append("user_id = ?")
        params.append(user_id)
    if device_type:
        where.append("device_type = ?")
        params.append(device_type)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    offset = (page - 1) * per_page
    with _cursor() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM carbon_history {clause}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT * FROM carbon_history {clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()
    return [dict(row) for row in rows], total


def query_lifespan_stats(user_id: Optional[str] = None):
    clause = "WHERE user_id = ?" if user_id is not None else ""
    params: list = [user_id] if user_id is not None else []
    with _cursor() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM lifespan_history {clause}", params
        ).fetchone()[0]
        avg_health = conn.execute(
            f"SELECT COALESCE(AVG(health_score), 0) FROM lifespan_history {clause}",
            params,
        ).fetchone()[0]
        avg_remaining = conn.execute(
            f"SELECT COALESCE(AVG(remaining_years), 0) FROM lifespan_history {clause}",
            params,
        ).fetchone()[0]
        total_co2 = conn.execute(
            f"SELECT COALESCE(SUM(co2_avoided_kg), 0) FROM lifespan_history {clause}",
            params,
        ).fetchone()[0]
        total_savings = conn.execute(
            f"SELECT COALESCE(SUM(repair_savings_inr), 0) FROM lifespan_history {clause}",
            params,
        ).fetchone()[0]
        by_device = conn.execute(
            f"SELECT device_type, COUNT(*) c FROM lifespan_history {clause} "
            "GROUP BY device_type ORDER BY c DESC LIMIT 5",
            params,
        ).fetchall()
    return {
        "total_predictions": total,
        "avg_health_score": round(float(avg_health or 0), 3),
        "avg_remaining_years": round(float(avg_remaining or 0), 2),
        "total_co2_avoided_kg": round(float(total_co2 or 0), 2),
        "total_repair_savings_inr": round(float(total_savings or 0), 2),
        "top_devices": [dict(row) for row in by_device],
    }


def query_carbon_stats(user_id: Optional[str] = None):
    clause = "WHERE user_id = ?" if user_id is not None else ""
    params: list = [user_id] if user_id is not None else []
    with _cursor() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM carbon_history {clause}", params
        ).fetchone()[0]
        avg_tco2e = conn.execute(
            f"SELECT COALESCE(AVG(total_tco2e), 0) FROM carbon_history {clause}",
            params,
        ).fetchone()[0]
        total_tco2e = conn.execute(
            f"SELECT COALESCE(SUM(total_tco2e), 0) FROM carbon_history {clause}",
            params,
        ).fetchone()[0]
        total_trees = conn.execute(
            f"SELECT COALESCE(SUM(trees_planted), 0) FROM carbon_history {clause}",
            params,
        ).fetchone()[0]
        total_embodied = conn.execute(
            f"SELECT COALESCE(SUM(embodied_kg), 0) FROM carbon_history {clause}",
            params,
        ).fetchone()[0]
        total_operational = conn.execute(
            f"SELECT COALESCE(SUM(operational_kg), 0) FROM carbon_history {clause}",
            params,
        ).fetchone()[0]
    return {
        "total_calculations": total,
        "avg_total_tco2e": round(float(avg_tco2e or 0), 3),
        "total_tco2e": round(float(total_tco2e or 0), 3),
        "total_trees_planted": int(total_trees or 0),
        "total_embodied_kg": round(float(total_embodied or 0), 2),
        "total_operational_kg": round(float(total_operational or 0), 2),
    }


def query_stats(user_id: Optional[str] = None):
    clause = "WHERE user_id = ?" if user_id is not None else ""
    params: list = [user_id] if user_id is not None else []
    with _cursor() as conn:
        total_scans = conn.execute(
            f"SELECT COUNT(*) FROM scan_history {clause}", params
        ).fetchone()[0]
        total_co2 = conn.execute(
            f"SELECT COALESCE(SUM(co2_delta), 0) FROM scan_history {clause}",
            params,
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT waste_status, COUNT(*) c FROM scan_history {clause} "
            "GROUP BY waste_status",
            params,
        ).fetchall()
    distribution = {row["waste_status"]: row["c"] for row in rows}
    return {
        "total_scans": total_scans,
        "total_co2_tracked": round(float(total_co2 or 0), 2),
        "status_distribution": distribution,
    }


def clear_history(user_id: Optional[str] = None):
    with _cursor() as conn:
        if user_id is not None:
            conn.execute("DELETE FROM scan_history WHERE user_id = ?", [user_id])
        else:
            conn.execute("DELETE FROM scan_history")


def clear_lifespan_history(user_id: Optional[str] = None):
    with _cursor() as conn:
        if user_id is not None:
            conn.execute(
                "DELETE FROM lifespan_history WHERE user_id = ?", [user_id]
            )
        else:
            conn.execute("DELETE FROM lifespan_history")


def clear_carbon_history(user_id: Optional[str] = None):
    with _cursor() as conn:
        if user_id is not None:
            conn.execute("DELETE FROM carbon_history WHERE user_id = ?", [user_id])
        else:
            conn.execute("DELETE FROM carbon_history")


# Initialize on import so tables and idempotent migrations exist before routes.
init_db()
