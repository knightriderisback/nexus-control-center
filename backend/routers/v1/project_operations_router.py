"""
NEXUS Phase 22: Autonomous Project Operations & Lifecycle Control REST Router.

Mounted under /api/v1/project-operations (with /api/v1/lifecycle aliases).
Provides fleet-wide lifecycle control, canary promotion, SLA governance,
drift detection/reconciliation, autonomous maintenance, and tombstone archival.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body

from models.schemas import (
    FleetOverviewResponse,
    ProjectOperationsRecord,
    ProjectRelease,
    ProjectDriftRecord,
    MaintenanceTask,
    ProjectSLA,
    CreateReleaseRequest,
    PromoteReleaseRequest,
    RollbackReleaseRequest,
    DetectDriftRequest,
    ReconcileDriftRequest,
    ScheduleMaintenanceRequest,
    ExecuteMaintenanceRequest,
    DecommissionProjectRequest,
    ArchiveProjectRequest
)
from orchestrator.project_operations_engine import project_operations_engine

router = APIRouter(prefix="/project-operations", tags=["Autonomous Project Operations & Lifecycle"])


@router.get("/fleet", response_model=FleetOverviewResponse)
def get_fleet_overview():
    """Returns aggregated fleet operational metrics, health, and SLA status."""
    return project_operations_engine.get_fleet_overview()


@router.post("/sync", response_model=FleetOverviewResponse)
def sync_fleet_inventory():
    """Synchronizes registry projects into active operational lifecycle governance."""
    return project_operations_engine.sync_fleet()


@router.get("/projects", response_model=List[ProjectOperationsRecord])
def list_managed_projects():
    """Lists all projects managed under autonomous operations."""
    return project_operations_engine.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectOperationsRecord)
def get_project_lifecycle_record(project_id: str):
    """Retrieves detailed operational and release lifecycle record for a project."""
    try:
        return project_operations_engine.get_project_record(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/releases", response_model=ProjectRelease, status_code=201)
def create_project_release(request: CreateReleaseRequest):
    """Initiates a new autonomous release candidate (Canary/Blue-Green/Direct)."""
    try:
        return project_operations_engine.create_release(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/releases/promote", response_model=ProjectRelease)
def promote_project_release(request: PromoteReleaseRequest):
    """Promotes active canary release traffic weight (10% -> 50% -> 100% / STABLE)."""
    try:
        return project_operations_engine.promote_release(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/releases/rollback", response_model=ProjectOperationsRecord)
def rollback_project_release(request: RollbackReleaseRequest):
    """Rolls back to previous stable release and drains unstable canary traffic."""
    try:
        return project_operations_engine.rollback_release(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drift/detect", response_model=List[ProjectDriftRecord])
def detect_runtime_drift(request: Optional[DetectDriftRequest] = None):
    """Executes live configuration, dependency, and workspace drift detection."""
    req = request or DetectDriftRequest()
    return project_operations_engine.detect_drift(req)


@router.post("/drift/reconcile", response_model=ProjectDriftRecord)
def reconcile_runtime_drift(request: ReconcileDriftRequest):
    """Autonomously reconciles detected drift without cloud cost."""
    try:
        return project_operations_engine.reconcile_drift(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sla/{project_id}", response_model=ProjectSLA)
def evaluate_project_sla(
    project_id: str,
    sample_latency_ms: Optional[float] = Query(None),
    sample_error_rate: Optional[float] = Query(None)
):
    """Evaluates project SLA compliance, error budget remaining, and burn rate."""
    try:
        return project_operations_engine.evaluate_project_sla(
            project_id=project_id,
            sample_latency_ms=sample_latency_ms,
            sample_error_rate=sample_error_rate
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/maintenance/schedule", response_model=MaintenanceTask, status_code=201)
def schedule_maintenance_task(request: ScheduleMaintenanceRequest):
    """Schedules an autonomous maintenance task (dependency scan, patch, log rotate, backup)."""
    return project_operations_engine.schedule_maintenance(request)


@router.post("/maintenance/execute", response_model=MaintenanceTask)
def execute_maintenance_task(request: ExecuteMaintenanceRequest):
    """Executes a scheduled maintenance task immediately."""
    try:
        return project_operations_engine.execute_maintenance(request.task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projects/{project_id}/decommission", response_model=ProjectOperationsRecord)
def decommission_project(project_id: str, request: Optional[DecommissionProjectRequest] = None):
    """Drains traffic and marks a project as DECOMMISSIONED."""
    req = request or DecommissionProjectRequest(project_id=project_id)
    req.project_id = project_id
    try:
        return project_operations_engine.decommission_project(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projects/{project_id}/archive")
def archive_project(project_id: str, request: Optional[ArchiveProjectRequest] = None):
    """Archives project into tombstone vault with cryptographic SHA-256 provenance."""
    req = request or ArchiveProjectRequest(project_id=project_id)
    req.project_id = project_id
    try:
        return project_operations_engine.archive_project(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
