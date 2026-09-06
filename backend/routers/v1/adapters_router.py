from fastapi import APIRouter
from typing import Dict, Any, List
from integrations.adapters.termux_adapter import termux_adapter
from integrations.adapters.vercel_adapter import vercel_adapter
from integrations.adapters.gcp_isolation_adapter import gcp_isolation_adapter

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.get("/termux")
def get_termux_status():
    """Returns Android Termux node connection and telemetry status."""
    return termux_adapter.get_device_status()

@router.post("/termux/heartbeat")
def post_termux_heartbeat(payload: dict):
    """Receives mobile node telemetry heartbeat."""
    return termux_adapter.record_heartbeat(payload)

@router.get("/vercel/{project_name}")
def get_vercel_status(project_name: str = "portfolio"):
    """Returns Vercel deployment status."""
    return vercel_adapter.get_deployment_status(project_name)

@router.get("/isolated-projects")
def get_isolated_projects():
    """Returns absolute isolation boundaries for protected legacy projects."""
    return gcp_isolation_adapter.get_isolation_manifest()
