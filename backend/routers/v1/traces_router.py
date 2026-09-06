from fastapi import APIRouter, Query
from typing import List, Dict, Any
from core.observability import collector

router = APIRouter(prefix="/traces", tags=["Observability"])

@router.get("", response_model=List[Dict[str, Any]])
def get_recent_traces(limit: int = Query(50, ge=1, le=300)):
    """Returns recent OpenTelemetry-compatible HTTP/system traces."""
    return collector.get_traces(limit=limit)
