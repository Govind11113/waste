from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.db import get_db

router = APIRouter(prefix="/history", tags=["History"])


class HistoryEntry(BaseModel):
    id: int
    timestamp: str
    filename: Optional[str]
    waste_status: str
    hazard_level: str
    confidence: float
    entity: str
    group_name: str
    condition: str
    co2_delta: float
    processing_time: float


class HistoryResponse(BaseModel):
    items: list[HistoryEntry]
    total: int
    page: int
    per_page: int


class StatsResponse(BaseModel):
    total_scans: int
    total_co2_tracked: float
    status_distribution: dict


@router.get("/", response_model=HistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM scan_history WHERE 1=1"
    params = []

    if search:
        query += " AND (filename LIKE ? OR entity LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if status:
        query += " AND waste_status = ?"
        params.append(status)

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    items = [HistoryEntry(**dict(row)) for row in rows]

    return HistoryResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM scan_history")
    total_scans = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(co2_delta) FROM scan_history")
    total_co2 = cursor.fetchone()[0] or 0

    cursor.execute("SELECT waste_status, COUNT(*) FROM scan_history GROUP BY waste_status")
    status_rows = cursor.fetchall()
    status_distribution = {row[0]: row[1] for row in status_rows}

    conn.close()

    return StatsResponse(
        total_scans=total_scans,
        total_co2_tracked=round(total_co2, 2),
        status_distribution=status_distribution
    )
