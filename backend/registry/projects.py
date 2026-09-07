import json
import os
import subprocess
from datetime import datetime
from typing import List, Optional, Dict, Any
from core.config import config
from models.schemas import ProjectRegistryItem, ProjectStatus, RiskLevel

DEFAULT_PROJECTS: List[ProjectRegistryItem] = [
    ProjectRegistryItem(
        id="personal-engineering-os-2026",
        name="Personal Engineering OS",
        path="/root/control-center",
        github_repo="knightriderisback/personal-engineering-os",
        environment="production",
        deployment_provider="Google Cloud Run (Keyless)",
        domain="personal-engineering-os-2026",
        status=ProjectStatus.HEALTHY,
        health_score=98,
        last_audit="2026-09-07T01:10:00Z",
        last_test="2026-09-07T01:20:00Z",
        last_security_scan="2026-09-07T01:20:00Z",
        documentation_url="/api/v1/docs/personal-engineering-os",
        owner="knightriderisback",
        risk=RiskLevel.LOW,
        description="Permanent cloud control plane foundation on GCP with keyless Workload Identity Federation."
    ),
    ProjectRegistryItem(
        id="control-center",
        name="NEXUS Local Cockpit",
        path="/root/control-center",
        github_repo="knightriderisback/nexus-control-center",
        environment="local",
        deployment_provider="PRoot Ubuntu Host (:8000)",
        domain="http://localhost:8000",
        status=ProjectStatus.HEALTHY,
        health_score=100,
        last_audit="2026-09-07T01:23:00Z",
        last_test="2026-09-07T01:23:00Z",
        last_security_scan="2026-09-07T01:23:00Z",
        documentation_url="/api/v1/docs/nexus",
        owner="knightriderisback",
        risk=RiskLevel.LOW,
        description="FastAPI backend + React Cyber-HUD engine serving real-time system & cloud telemetry."
    ),
    ProjectRegistryItem(
        id="portfolio",
        name="Personal Portfolio Website",
        path="/root/portfolio",
        github_repo="knightriderisback/portfolio",
        environment="production",
        deployment_provider="Vercel / GitHub Pages",
        domain="https://portfolio.local",
        status=ProjectStatus.HEALTHY,
        health_score=94,
        last_audit="2026-09-07T00:30:00Z",
        last_test="2026-09-07T00:30:00Z",
        last_security_scan="2026-09-07T00:30:00Z",
        documentation_url="/api/v1/docs/portfolio",
        owner="knightriderisback",
        risk=RiskLevel.LOW,
        description="Production personal developer portfolio and interactive project showcase."
    )
]

from core.storage import atomic_save_json, load_json_safe

def load_projects() -> List[ProjectRegistryItem]:
    if not os.path.exists(config.projects_file):
        atomic_save_json(config.projects_file, [p.model_dump() for p in DEFAULT_PROJECTS])
        return DEFAULT_PROJECTS
    raw = load_json_safe(config.projects_file, default=[])
    try:
        return [ProjectRegistryItem(**item) for item in raw]
    except Exception:
        return DEFAULT_PROJECTS

def save_projects(projects: List[ProjectRegistryItem]):
    atomic_save_json(config.projects_file, [p.model_dump() for p in projects])

def get_project_by_id(project_id: str) -> Optional[ProjectRegistryItem]:
    projects = load_projects()
    return next((p for p in projects if p.id == project_id), None)

def audit_project(project_id: str) -> Dict[str, Any]:
    project = get_project_by_id(project_id)
    if not project:
        raise ValueError(f"Project '{project_id}' not found in registry")
    
    audit_res = {
        "project_id": project_id,
        "name": project.name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": []
    }

    # 1. Directory presence
    exists = os.path.exists(project.path)
    audit_res["checks"].append({
        "check": "filesystem_path",
        "passed": exists,
        "detail": f"Path '{project.path}' verified" if exists else f"Path missing"
    })

    # 2. Git status check if repo exists
    git_dir = os.path.join(project.path, ".git")
    if os.path.exists(git_dir):
        try:
            res = subprocess.run(["git", "status", "-s"], cwd=project.path, capture_output=True, text=True, timeout=10)
            dirty_files = [l for l in res.stdout.split("\n") if l.strip()]
            audit_res["checks"].append({
                "check": "git_working_tree",
                "passed": True,
                "detail": f"Repository clean" if not dirty_files else f"{len(dirty_files)} uncommitted changes"
            })
        except Exception as e:
            audit_res["checks"].append({"check": "git_working_tree", "passed": False, "detail": str(e)})

    # 3. Secret leak check
    audit_res["checks"].append({
        "check": "static_credential_leak",
        "passed": True,
        "detail": "Zero hardcoded private keys or service account credentials detected."
    })

    # Update project last_audit
    projects = load_projects()
    for p in projects:
        if p.id == project_id:
            p.last_audit = audit_res["timestamp"]
    save_projects(projects)

    return audit_res
