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
    """Create the scan_history table if missing."""
    with _cursor() as conn:
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


# Initialize on import so the table exists before the first request
init_db()
