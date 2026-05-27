from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.db import query_history, query_stats, clear_history

router = APIRouter(prefix="/history", tags=["History"])


class HistoryEntry(BaseModel):
    id: int
    timestamp: str
    filename: Optional[str] = None
    waste_status: str
    hazard_level: str
    confidence: float
    entity: str
    group_name: str
    condition: str
    co2_delta: float
    processing_time: float
    recyclability: Optional[str] = None
    model_used: Optional[str] = None


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
    status: Optional[str] = Query(None),
):
    items, total = query_history(page=page, per_page=per_page, search=search, status=status)
    return HistoryResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    return StatsResponse(**query_stats())


@router.delete("/")
async def delete_history():
    clear_history()
    return {"ok": True}
