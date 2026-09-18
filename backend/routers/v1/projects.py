"""
NEXUS Phase 22: Unified Project Registry & Operations REST Router.

Mounted under /api/v1/projects.
Provides complete project discovery, registration, real health evaluation,
governed operations, mission routing, deployments, incidents, and dependency graphs.
"""

import os
import subprocess
import re
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any

from models.schemas import (
    ProjectRegistryItem,
    RiskLevel,
    ProjectDiscoveryResponse,
    ProjectHealthDetail,
    ProjectOperationRequest,
    ProjectOperationResult,
    ProjectDependencyGraph,
    ProjectMissionRoutingResult,
    DiscoveredProjectItem
)
from registry.projects import load_projects, get_project_by_id, save_projects, audit_project
from orchestrator.project_operations_engine import project_operations_engine
from orchestrator.self_healing_engine import self_healing_engine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine
from orchestrator.mission_engine import mission_engine
from orchestrator.deployment_engine import deployment_engine
from core.policy import evaluate_action
from core.approvals import request_approval
from core.audit import record_audit

router = APIRouter(prefix="/projects", tags=["Project Registry & Operations"])


# -----------------------------------------------------------------------------
# 1. Project Discovery & Registration
# -----------------------------------------------------------------------------

@router.get("", response_model=List[ProjectRegistryItem])
def list_projects():
    """Lists all registered projects."""
    return load_projects()


@router.post("/discover", response_model=ProjectDiscoveryResponse)
def discover_projects(roots: Optional[List[str]] = Body(None, embed=True)):
    """Discovers eligible projects strictly within allowed project roots."""
    return project_operations_engine.discover_projects(roots)


@router.post("", response_model=ProjectRegistryItem)
@router.post("/register", response_model=ProjectRegistryItem)
def register_project(project: ProjectRegistryItem):
    """Registers a project into the persistent registry and operations control plane."""
    try:
        return project_operations_engine.register_project(project)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/route-mission", response_model=ProjectMissionRoutingResult)
def route_mission_goal(
    goal: str = Body(..., embed=True),
    target_project_ids: Optional[List[str]] = Body(None, embed=True)
):
    """Resolves natural-language goal to an existing, new, or multi-project targets."""
    return project_operations_engine.route_mission_goal(goal, target_project_ids)


# -----------------------------------------------------------------------------
# 2. Individual Project Endpoints
# -----------------------------------------------------------------------------

@router.get("/{project_id}", response_model=ProjectRegistryItem)
def get_project(project_id: str):
    """Retrieves project registry item by project_id."""
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return p


@router.get("/{project_id}/health", response_model=ProjectHealthDetail)
def get_project_real_health(project_id: str):
    """Inspects and returns real project health (Git, Tests, Runtime, Security, Incidents)."""
    try:
        return project_operations_engine.get_project_health(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{project_id}/operations", response_model=ProjectOperationResult)
def execute_project_operation(project_id: str, request: ProjectOperationRequest):
    """Executes a governed operation on a project (inspect, test, build, deploy, rollback, etc.)."""
    try:
        return project_operations_engine.execute_project_operation(project_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/missions")
def get_project_missions(project_id: str):
    """Retrieves all missions executed against this project."""
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    all_missions = mission_engine.list_missions()
    project_missions = [
        m.model_dump() for m in all_missions
        if getattr(m, "project_id", "") == project_id or project_id in getattr(m, "title", "")
    ]
    return {"project_id": project_id, "missions": project_missions}


@router.get("/{project_id}/deployments")
def get_project_deployments(project_id: str):
    """Retrieves deployments associated with this project."""
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    all_deps = deployment_engine.list_deployments()
    project_deps = [
        d.model_dump() for d in all_deps
        if getattr(d, "project_id", "") == project_id or getattr(d, "service_name", "") == project_id
    ]
    return {"project_id": project_id, "deployments": project_deps}


@router.get("/{project_id}/incidents")
def get_project_incidents(project_id: str):
    """Retrieves self-healing incidents associated with this project."""
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    all_incs = self_healing_engine.list_incidents()
    project_incs = [
        inc.model_dump() for inc in all_incs
        if getattr(inc, "project_id", "") == project_id or project_id in getattr(inc, "title", "")
    ]
    return {"project_id": project_id, "incidents": project_incs}


@router.get("/{project_id}/knowledge")
def get_project_knowledge(project_id: str):
    """Retrieves knowledge and optimization nodes linked to this project."""
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    nodes = knowledge_learning_engine.query_knowledge(project_id)
    return {"project_id": project_id, "knowledge_nodes": [n.model_dump() for n in nodes]}


@router.get("/{project_id}/dependencies", response_model=ProjectDependencyGraph)
def get_project_dependencies(project_id: str):
    """Builds and returns the dependency graph for a specific project."""
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project_operations_engine.detect_dependencies(project_id)


# -----------------------------------------------------------------------------
# 3. Legacy project endpoints for backwards compatibility
# -----------------------------------------------------------------------------

@router.post("/{project_id}/audit")
def run_audit(project_id: str):
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    res = audit_project(project_id)
    record_audit(
        action=f"AUDIT_EXECUTED: {project_id}",
        project=project_id,
        target=p.path,
        reason="Autonomous project health audit",
        risk_level=RiskLevel.LOW,
        result="SUCCESS"
    )
    return res


@router.post("/{project_id}/test")
def run_tests(project_id: str):
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    test_dir = os.path.join(p.path, "tests")
    if os.path.exists(test_dir):
        try:
            res = subprocess.run(
                ["pytest", "tests/", "-q"],
                cwd=p.path,
                capture_output=True,
                text=True,
                timeout=60
            )
            output = res.stdout.strip()
            passed = 0
            failed = 0
            duration = "0s"
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                passed = int(match.group(1))
            fail_match = re.search(r"(\d+)\s+failed", output)
            if fail_match:
                failed = int(fail_match.group(1))

            status = "PASSED" if res.returncode == 0 else "FAILED"
            return {
                "project_id": project_id,
                "status": status,
                "tests_total": passed + failed,
                "passed": passed,
                "failed": failed,
                "execution_mode": "REAL_PYTEST"
            }
        except Exception as e:
            return {"project_id": project_id, "status": "ERROR", "error": str(e)}

    return {"project_id": project_id, "status": "SKIPPED", "detail": "No tests/ directory discovered"}


@router.post("/{project_id}/security")
def run_security_scan(project_id: str):
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    from orchestrator.tool_runner import SecurityRunner
    scan_res = SecurityRunner.scan_directory_for_secrets(p.path)
    scan_res["project_id"] = project_id
    return scan_res


@router.post("/{project_id}/deploy")
def trigger_deployment(project_id: str):
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    
    risk, req_appr, desc = evaluate_action("deploy production", project_id)
    if req_appr:
        appr = request_approval(
            action=f"Deploy {project_id} to {p.deployment_provider}",
            target_project=project_id,
            reason=f"Operator requested deployment of {project_id}",
            command=f"# Deployment script for {project_id}"
        )
        return {
            "status": "AWAITING_APPROVAL",
            "approval_required": True,
            "approval_id": appr.id,
            "risk_level": risk,
            "message": f"Deployment is a {risk.value} risk action. Approval request {appr.id} logged."
        }

    return {"status": "DEPLOYING", "project_id": project_id}
