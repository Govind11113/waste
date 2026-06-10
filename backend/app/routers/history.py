from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.db import (
    query_history, query_stats, clear_history,
    query_lifespan_history, query_lifespan_stats, clear_lifespan_history,
    query_carbon_history, query_carbon_stats, clear_carbon_history,
)

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


class LifespanHistoryEntry(BaseModel):
    id: int
    timestamp: str
    device_type: str
    age: float
    base_lifespan: int
    health_score: float
    remaining_years: float
    remaining_min: float
    remaining_max: float
    co2_avoided_kg: float
    repair_savings_inr: float
    usage_hours_per_day: float
    temperature: str
    environment: str
    power: str
    maintenance: str


class LifespanHistoryResponse(BaseModel):
    items: list[LifespanHistoryEntry]
    total: int
    page: int
    per_page: int


class LifespanStatsResponse(BaseModel):
    total_predictions: int
    avg_health_score: float
    avg_remaining_years: float
    total_co2_avoided_kg: float
    total_repair_savings_inr: float
    top_devices: list


class CarbonHistoryEntry(BaseModel):
    id: int
    timestamp: str
    device_type: str
    units: int
    daily_hours: float
    tdp: float
    energy_rating: str
    zip_code: str
    lifespan_years: float
    total_tco2e: float
    embodied_kg: float
    operational_kg: float
    grid_intensity: float
    trees_planted: int


class CarbonHistoryResponse(BaseModel):
    items: list[CarbonHistoryEntry]
    total: int
    page: int
    per_page: int


class CarbonStatsResponse(BaseModel):
    total_calculations: int
    avg_total_tco2e: float
    total_tco2e: float
    total_trees_planted: int
    total_embodied_kg: float
    total_operational_kg: float


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


# ─── Lifespan history ────────────────────────────────────────────────────────
@router.get("/lifespan", response_model=LifespanHistoryResponse)
async def get_lifespan_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    device_type: Optional[str] = Query(None),
):
    items, total = query_lifespan_history(page=page, per_page=per_page, device_type=device_type)
    return LifespanHistoryResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/lifespan/stats", response_model=LifespanStatsResponse)
async def get_lifespan_stats():
    return LifespanStatsResponse(**query_lifespan_stats())


@router.delete("/lifespan")
async def delete_lifespan_history():
    clear_lifespan_history()
    return {"ok": True}


# ─── Carbon history ─────────────────────────────────────────────────────────
@router.get("/carbon", response_model=CarbonHistoryResponse)
async def get_carbon_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    device_type: Optional[str] = Query(None),
):
    items, total = query_carbon_history(page=page, per_page=per_page, device_type=device_type)
    return CarbonHistoryResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/carbon/stats", response_model=CarbonStatsResponse)
async def get_carbon_stats():
    return CarbonStatsResponse(**query_carbon_stats())


@router.delete("/carbon")
async def delete_carbon_history():
    clear_carbon_history()
    return {"ok": True}
