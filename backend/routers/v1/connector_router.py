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
    ProjectRegistryItem,
    AutoSyncConfig,
    AutoSyncStatusResponse,
    ReconcileFleetResponse
)
from orchestrator.local_connector import local_connector_engine
from orchestrator.external_source_sync import discover_github, discover_vercel, sync_external_sources

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


@router.get("/external/sources", response_model=Dict[str, Any])
def get_external_sources():
    """Returns the live GitHub and Vercel inventories available to the authenticated local CLIs."""
    github, github_errors = discover_github()
    vercel, vercel_errors = discover_vercel()
    return {
        "github": github,
        "vercel": vercel,
        "errors": github_errors + vercel_errors,
    }


@router.post("/external/sync", response_model=Dict[str, Any])
def sync_external_source_projects():
    """Immediately merges live GitHub + Vercel inventories into the NEXUS registry."""
    try:
        return sync_external_sources()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto-sync/status", response_model=AutoSyncStatusResponse)
def get_auto_sync_status():
    """Returns the live status, cycle metrics, and configuration of Universal Auto-Sync."""
    try:
        return local_connector_engine.get_auto_sync_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-sync/config", response_model=AutoSyncStatusResponse)
def update_auto_sync_config(cfg: AutoSyncConfig):
    """Updates Universal Auto-Sync configuration settings."""
    try:
        return local_connector_engine.update_auto_sync_config(cfg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-sync/trigger", response_model=Dict[str, Any])
def trigger_auto_sync():
    """Manually triggers an immediate Universal Discovery & Auto-Sync cycle."""
    try:
        return local_connector_engine.run_auto_sync_cycle(force=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reconcile-all", response_model=ReconcileFleetResponse)
def reconcile_all_projects():
    """Reconciles all registered projects against current disk and Git state."""
    try:
        return local_connector_engine.reconcile_fleet()
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

