import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "history.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Existing scan_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            filename TEXT,
            waste_status TEXT,
            hazard_level TEXT,
            confidence REAL,
            entity TEXT,
            group_name TEXT,
            condition TEXT,
            co2_delta REAL,
            processing_time REAL
        )
    """)

    # New users table for institutional login
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            institution_name TEXT,
            region TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Temporary OTP store
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_store (
            email TEXT PRIMARY KEY,
            otp TEXT NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def log_scan(
    filename: Optional[str],
    waste_status: str,
    hazard_level: str,
    confidence: float,
    entity: str,
    group_name: str,
    condition: str,
    co2_delta: float,
    processing_time: float
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scan_history
        (timestamp, filename, waste_status, hazard_level, confidence, entity, group_name, condition, co2_delta, processing_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        filename,
        waste_status,
        hazard_level,
        confidence,
        entity,
        group_name,
        condition,
        co2_delta,
        processing_time
    ))
    conn.commit()
    conn.close()
