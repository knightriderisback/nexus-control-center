from fastapi import APIRouter
from core.observability import collector

router = APIRouter(prefix="/metrics", tags=["Observability"])

@router.get("")
def get_system_metrics():
    """Returns real-time telemetry metrics, latency stats, and agent runs."""
    return collector.get_metrics()
