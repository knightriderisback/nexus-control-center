"""
NEXUS Phase 16: Production Deployment Engine REST API Router.
Mounted under /api/v1/deployments.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from models.schemas import (
    DeploymentRecord,
    DeploymentRequest,
    RollbackRequest,
    CanaryPromoteRequest,
    DORAMetrics,
    EnvironmentStatus,
    DeploymentOverallStatus,
)
from orchestrator.deployment_engine import deployment_engine
from core.approvals import approvals_manager

router = APIRouter(prefix="/deployments", tags=["Production Deployments"])


@router.get("", response_model=List[DeploymentRecord])
def list_deployments(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    environment: Optional[str] = Query(None, description="Filter by environment (LOCAL, PREVIEW, STAGING, PRODUCTION)"),
    status: Optional[str] = Query(None, description="Filter by status (BUILDING, LIVE, FAILED, ROLLED_BACK, etc.)")
):
    """Lists all deployment records with optional filtering."""
    return deployment_engine.list_deployments(
        project_id=project_id,
        environment=environment,
        status=status
    )


@router.post("/deploy", response_model=DeploymentRecord)
def trigger_deployment(request: DeploymentRequest):
    """Triggers an end-to-end multi-target deployment pipeline."""
    try:
        return deployment_engine.deploy(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/environments", response_model=List[EnvironmentStatus])
def list_environments():
    """Lists all managed environments and active versions."""
    return deployment_engine.list_environments()


@router.get("/targets", response_model=List[Dict[str, Any]])
def list_supported_targets():
    """Lists supported multi-target deployment dispatchers."""
    return deployment_engine.list_targets()


@router.get("/dora", response_model=DORAMetrics)
def get_dora_telemetry():
    """Returns DevOps Research and Assessment (DORA) operational metrics."""
    return deployment_engine.get_dora_metrics()


@router.get("/{deployment_id}", response_model=DeploymentRecord)
def get_deployment(deployment_id: str):
    """Retrieves full deployment record with stage-by-stage progression."""
    dep = deployment_engine.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found.")
    return dep


@router.post("/{deployment_id}/rollback", response_model=DeploymentRecord)
def rollback_deployment(deployment_id: str, request: Optional[RollbackRequest] = None):
    """Executes an instant atomic rollback to a previous stable release."""
    req = request or RollbackRequest(deployment_id=deployment_id)
    req.deployment_id = deployment_id
    try:
        return deployment_engine.rollback(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/promote", response_model=DeploymentRecord)
def promote_canary(deployment_id: str, request: CanaryPromoteRequest):
    """Promotes canary traffic allocation for an active deployment."""
    request.deployment_id = deployment_id
    try:
        return deployment_engine.promote_canary(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/approve", response_model=DeploymentRecord)
def approve_and_resume_deployment(deployment_id: str):
    """Approves a pending deployment and resumes pipeline execution."""
    dep = deployment_engine.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail=f"Deployment '{deployment_id}' not found.")

    if dep.status != DeploymentOverallStatus.APPROVAL_PENDING:
        raise HTTPException(status_code=400, detail=f"Deployment is not in APPROVAL_PENDING state (current: {dep.status.value}).")

    if dep.approval_id:
        approvals_manager.approve(dep.approval_id, approved_by="operator")

    # Resume pipeline execution
    dep.requires_approval = False
    return deployment_engine._execute_pipeline(dep)
