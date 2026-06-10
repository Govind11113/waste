import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

# Local SQLite store — single source of truth for scan history.
# Lives next to the backend so it survives restarts and works offline.
DB_PATH = Path(__file__).resolve().parent.parent / "scan_history.db"

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
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


def init_db():
    """Create all tables if missing — scan + lifespan + carbon history."""
    with _cursor() as conn:
        # Original scan history (unchanged)
        conn.execute("""
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
                model_used TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_history_timestamp ON scan_history(timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_history_status ON scan_history(waste_status)")

        # Lifespan prediction history
        conn.execute("""
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
                maintenance TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lifespan_history_timestamp ON lifespan_history(timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lifespan_history_device ON lifespan_history(device_type)")

        # Carbon calculation history
        conn.execute("""
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
                trees_planted INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_carbon_history_timestamp ON carbon_history(timestamp DESC)")

        # Best-effort migration for existing DBs that pre-date the new columns
        try:
            existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(scan_history)").fetchall()}
            if "recyclability" not in existing_cols:
                conn.execute("ALTER TABLE scan_history ADD COLUMN recyclability TEXT")
            if "model_used" not in existing_cols:
                conn.execute("ALTER TABLE scan_history ADD COLUMN model_used TEXT")
        except Exception as e:
            print(f"DB migration check failed: {e}")

    print(f"Local scan history DB ready at {DB_PATH}")


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
):
    try:
        with _cursor() as conn:
            conn.execute(
                """
                INSERT INTO scan_history
                (timestamp, filename, waste_status, hazard_level, confidence,
                 entity, group_name, condition, co2_delta, processing_time,
                 recyclability, model_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
    except Exception as e:
        print(f"Error logging scan: {e}")


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
):
    try:
        with _cursor() as conn:
            conn.execute(
                """
                INSERT INTO lifespan_history
                (timestamp, device_type, age, base_lifespan, health_score,
                 remaining_years, remaining_min, remaining_max,
                 co2_avoided_kg, repair_savings_inr,
                 usage_hours_per_day, temperature, environment, power, maintenance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
    except Exception as e:
        print(f"Error logging lifespan prediction: {e}")


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
):
    try:
        with _cursor() as conn:
            conn.execute(
                """
                INSERT INTO carbon_history
                (timestamp, device_type, units, daily_hours, tdp, energy_rating,
                 zip_code, lifespan_years, total_tco2e, embodied_kg, operational_kg,
                 grid_intensity, trees_planted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
    except Exception as e:
        print(f"Error logging carbon calculation: {e}")


def query_history(
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
):
    where = []
    params: list = []
    if search:
        where.append("(filename LIKE ? OR entity LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if status:
        where.append("waste_status = ?")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    offset = (page - 1) * per_page
    with _cursor() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM scan_history {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT * FROM scan_history {clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        ).fetchall()
    return [dict(r) for r in rows], total


def query_lifespan_history(
    page: int = 1,
    per_page: int = 10,
    device_type: Optional[str] = None,
):
    where = []
    params: list = []
    if device_type:
        where.append("device_type = ?")
        params.append(device_type)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    offset = (page - 1) * per_page
    with _cursor() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM lifespan_history {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT * FROM lifespan_history {clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()
    return [dict(r) for r in rows], total


def query_carbon_history(
    page: int = 1,
    per_page: int = 10,
    device_type: Optional[str] = None,
):
    where = []
    params: list = []
    if device_type:
        where.append("device_type = ?")
        params.append(device_type)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    offset = (page - 1) * per_page
    with _cursor() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM carbon_history {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT * FROM carbon_history {clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()
    return [dict(r) for r in rows], total


def query_lifespan_stats():
    with _cursor() as conn:
        total = conn.execute("SELECT COUNT(*) FROM lifespan_history").fetchone()[0]
        avg_health = conn.execute("SELECT COALESCE(AVG(health_score), 0) FROM lifespan_history").fetchone()[0]
        avg_remaining = conn.execute("SELECT COALESCE(AVG(remaining_years), 0) FROM lifespan_history").fetchone()[0]
        total_co2 = conn.execute("SELECT COALESCE(SUM(co2_avoided_kg), 0) FROM lifespan_history").fetchone()[0]
        total_savings = conn.execute("SELECT COALESCE(SUM(repair_savings_inr), 0) FROM lifespan_history").fetchone()[0]
        by_device = conn.execute(
            "SELECT device_type, COUNT(*) c FROM lifespan_history GROUP BY device_type ORDER BY c DESC LIMIT 5"
        ).fetchall()
    return {
        "total_predictions": total,
        "avg_health_score": round(float(avg_health or 0), 3),
        "avg_remaining_years": round(float(avg_remaining or 0), 2),
        "total_co2_avoided_kg": round(float(total_co2 or 0), 2),
        "total_repair_savings_inr": round(float(total_savings or 0), 2),
        "top_devices": [dict(r) for r in by_device],
    }


def query_carbon_stats():
    with _cursor() as conn:
        total = conn.execute("SELECT COUNT(*) FROM carbon_history").fetchone()[0]
        avg_tco2e = conn.execute("SELECT COALESCE(AVG(total_tco2e), 0) FROM carbon_history").fetchone()[0]
        total_tco2e = conn.execute("SELECT COALESCE(SUM(total_tco2e), 0) FROM carbon_history").fetchone()[0]
        total_trees = conn.execute("SELECT COALESCE(SUM(trees_planted), 0) FROM carbon_history").fetchone()[0]
        total_embodied = conn.execute("SELECT COALESCE(SUM(embodied_kg), 0) FROM carbon_history").fetchone()[0]
        total_operational = conn.execute("SELECT COALESCE(SUM(operational_kg), 0) FROM carbon_history").fetchone()[0]
    return {
        "total_calculations": total,
        "avg_total_tco2e": round(float(avg_tco2e or 0), 3),
        "total_tco2e": round(float(total_tco2e or 0), 3),
        "total_trees_planted": int(total_trees or 0),
        "total_embodied_kg": round(float(total_embodied or 0), 2),
        "total_operational_kg": round(float(total_operational or 0), 2),
    }


def query_stats():
    with _cursor() as conn:
        total_scans = conn.execute("SELECT COUNT(*) FROM scan_history").fetchone()[0]
        total_co2 = conn.execute("SELECT COALESCE(SUM(co2_delta), 0) FROM scan_history").fetchone()[0]
        rows = conn.execute(
            "SELECT waste_status, COUNT(*) c FROM scan_history GROUP BY waste_status"
        ).fetchall()
    distribution = {r["waste_status"]: r["c"] for r in rows}
    return {
        "total_scans": total_scans,
        "total_co2_tracked": round(float(total_co2 or 0), 2),
        "status_distribution": distribution,
    }


def clear_history():
    with _cursor() as conn:
        conn.execute("DELETE FROM scan_history")


def clear_lifespan_history():
    with _cursor() as conn:
        conn.execute("DELETE FROM lifespan_history")


def clear_carbon_history():
    with _cursor() as conn:
        conn.execute("DELETE FROM carbon_history")


# Initialize on import so the table exists before the first request
init_db()
