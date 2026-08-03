"""
GET /health  — liveness probe.
GET /metrics — lightweight runtime counters (stub, expand as needed).
"""
import time
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["ops"])

# Record the process start time once at import.
_START_TIME = time.time()


class HealthResponse(BaseModel):
    status: str = "ok"
    uptime_seconds: float


class MetricsResponse(BaseModel):
    uptime_seconds: float
    # Extend with Prometheus-style counters once the pipeline is wired.


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    return HealthResponse(uptime_seconds=round(time.time() - _START_TIME, 2))


@router.get("/metrics", response_model=MetricsResponse, summary="Runtime counters (stub)")
async def metrics() -> MetricsResponse:
    return MetricsResponse(uptime_seconds=round(time.time() - _START_TIME, 2))
