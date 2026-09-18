"""
NEXUS GitHub Integration & Software Delivery REST API Router.
Mounted at /api/v1/github.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from integrations.github import list_known_repositories, get_git_repo_info
from integrations.github_client import (
    get_github_client,
    github_client_manager
)
from orchestrator.github_delivery import (
    github_delivery_engine
)
from models.schemas import (
    GitHubHealthResponse,
    DeliveryRecord,
    DeliveryPublishRequest,
    DeliveryPRCreateRequest,
    DeliveryMergeRequest
)

router = APIRouter(prefix="/github", tags=["GitHub Integration & Delivery"])


class SetModeRequest(BaseModel):
    mode: str  # REAL, MOCK, DRY_RUN


# -----------------------------------------------------------------------------
# GitHub Health & Client Configuration
# -----------------------------------------------------------------------------

@router.get("/health", response_model=GitHubHealthResponse)
def get_github_health():
    """Returns real-time health, configuration status, and mode without token leakage."""
    client = get_github_client()
    return client.health_check()


@router.post("/mode")
def set_github_mode(req: SetModeRequest):
    """Dynamically sets GitHub client operational mode (REAL, MOCK, DRY_RUN)."""
    try:
        new_mode = github_client_manager.set_mode(req.mode)
        return {"status": "UPDATED", "mode": new_mode.value}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------------------------
# Legacy Repository Status Endpoints
# -----------------------------------------------------------------------------

@router.get("/repos")
def get_repos() -> List[Dict[str, Any]]:
    return list_known_repositories()


@router.get("/repos/{project_name}/status")
def get_repo_status(project_name: str) -> Dict[str, Any]:
    path = f"/root/{project_name}"
    return get_git_repo_info(path)


# -----------------------------------------------------------------------------
# Governed Autonomous Software Delivery Endpoints
# -----------------------------------------------------------------------------

@router.post("/delivery/publish", response_model=DeliveryRecord)
def publish_candidate_branch(req: DeliveryPublishRequest):
    """Publishes a local merge candidate branch to governed GitHub remote."""
    try:
        return github_delivery_engine.initiate_delivery(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/pr", response_model=DeliveryRecord)
def create_governed_pr(req: DeliveryPRCreateRequest):
    """Creates a Pull Request with full autonomous provenance and multi-agent review."""
    try:
        return github_delivery_engine.create_pull_request(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/review/{delivery_id}", response_model=DeliveryRecord)
def conduct_pr_review(delivery_id: str):
    """Triggers multi-agent swarm review and governance evaluation on an active PR."""
    try:
        return github_delivery_engine.conduct_automated_review(delivery_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/merge", response_model=DeliveryRecord)
def merge_governed_pr(req: DeliveryMergeRequest):
    """Executes a controlled, risk-gated Pull Request merge on GitHub."""
    try:
        return github_delivery_engine.execute_governed_merge(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/delivery/deliveries", response_model=List[DeliveryRecord])
def list_deliveries(limit: int = 50):
    """Lists all software delivery pipelines."""
    return github_delivery_engine.list_deliveries(limit=limit)


@router.get("/delivery/deliveries/{delivery_id}", response_model=DeliveryRecord)
def get_delivery(delivery_id: str):
    """Retrieves full details of a software delivery pipeline."""
    deliv = github_delivery_engine.get_delivery(delivery_id)
    if not deliv:
        raise HTTPException(status_code=404, detail=f"Delivery '{delivery_id}' not found.")
    return deliv


@router.post("/delivery/deliveries/{delivery_id}/cancel", response_model=DeliveryRecord)
def cancel_delivery(delivery_id: str):
    """Safely cancels an in-flight delivery pipeline."""
    try:
        return github_delivery_engine.cancel_delivery(delivery_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delivery/deliveries/{delivery_id}/resume", response_model=DeliveryRecord)
def resume_delivery(delivery_id: str):
    """Resumes an awaiting-approval or paused delivery pipeline."""
    try:
        return github_delivery_engine.resume_delivery(delivery_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
