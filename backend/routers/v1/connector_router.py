"""
NEXUS Local Connector & Operations Bridge REST API Router.
Mounted under /api/v1/connector.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body

from models.schemas import (
    ConnectorStatusResponse,
    ProjectOnboardRequest,
    ProjectDashboardResponse,
    ProjectActionRequest,
    ProjectActionResult,
    ConnectorSyncRequest,
    ConnectorSyncResponse,
    ProjectDiscoveryResponse,
    ProjectRegistryItem
)
from orchestrator.local_connector import local_connector_engine

router = APIRouter(prefix="/connector", tags=["NEXUS Local Connector & Project Operations Bridge"])


@router.get("/status", response_model=ConnectorStatusResponse)
def get_connector_status():
    """Returns real-time host environment, Termux detection, uptime, and connected counts."""
    return local_connector_engine.get_status()


@router.get("/roots", response_model=List[str])
def get_scan_roots():
    """Returns list of allowed and detected workspace roots for discovery."""
    return local_connector_engine.get_scan_roots()


@router.get("/discover", response_model=ProjectDiscoveryResponse)
@router.post("/discover", response_model=ProjectDiscoveryResponse)
def discover_local_projects(roots: Optional[List[str]] = None):
    """Scans configured workspace roots for Git repositories and project manifests."""
    try:
        return local_connector_engine.discover_projects(roots)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-all", response_model=ConnectorSyncResponse)
def sync_all_discovered_projects(req: Optional[ConnectorSyncRequest] = None):
    """Bulk registers and synchronizes discovered projects into the persistent control plane."""
    request = req or ConnectorSyncRequest()
    try:
        return local_connector_engine.sync_discovered_projects(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/onboard", response_model=ProjectRegistryItem, status_code=201)
def onboard_project(req: ProjectOnboardRequest):
    """Onboards a new project from a local workspace path, GitHub repository URL, or existing directory."""
    try:
        return local_connector_engine.onboard_project(req)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/dashboard", response_model=ProjectDashboardResponse)
def get_project_dashboard(project_id: str):
    """Retrieves full interactive project dashboard (Git, Operations, Missions, Tests, Security, Deployments)."""
    try:
        return local_connector_engine.get_project_dashboard(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/action", response_model=ProjectActionResult)
def execute_project_action(project_id: str, req: ProjectActionRequest):
    """Executes an operational action on the project (AUDIT, TEST, SECURITY_SCAN, RUN_MISSION, RECONCILE_DRIFT)."""
    try:
        return local_connector_engine.execute_project_action(project_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
