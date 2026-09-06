from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from core.automations import automations_engine

router = APIRouter(prefix="/automations", tags=["Automations"])

@router.get("/jobs")
def list_jobs():
    """Lists all registered automated routines and schedules."""
    return automations_engine.list_jobs()

@router.post("/run/{job_id}")
def run_job(job_id: str):
    """Manually triggers a scheduled automation routine."""
    res = automations_engine.execute_job(job_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@router.get("/brief")
def get_engineering_brief():
    """Generates the real-time engineering executive morning brief."""
    return automations_engine.generate_morning_brief()
