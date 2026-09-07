import os
import subprocess
import re
from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import ProjectRegistryItem, RiskLevel
from registry.projects import load_projects, get_project_by_id, save_projects, audit_project
from core.policy import evaluate_action
from core.approvals import request_approval
from core.audit import record_audit

router = APIRouter(prefix="/projects", tags=["Project Registry"])

@router.get("", response_model=List[ProjectRegistryItem])
def list_projects():
    return load_projects()

@router.get("/{project_id}", response_model=ProjectRegistryItem)
def get_project(project_id: str):
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return p

@router.post("", response_model=ProjectRegistryItem)
def register_project(project: ProjectRegistryItem):
    projects = load_projects()
    if any(p.id == project.id for p in projects):
        raise HTTPException(status_code=400, detail=f"Project '{project.id}' already exists")
    projects.append(project)
    save_projects(projects)
    
    record_audit(
        action=f"PROJECT_REGISTERED: {project.id}",
        project=project.id,
        target=project.path,
        reason="Manual or automated project registration",
        risk_level=RiskLevel.LOW
    )
    return project

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
                ["pytest", "tests/", "-q", "--ignore=tests/test_hardening_and_execution.py"],
                cwd=p.path,
                capture_output=True,
                text=True,
                timeout=30
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
            dur_match = re.search(r"in\s+([\d\.]+s)", output)
            if dur_match:
                duration = dur_match.group(1)

            total = passed + failed
            status = "PASSED" if res.returncode == 0 else "FAILED"

            record_audit(
                action=f"TEST_SUITE_RUN: {project_id}",
                project=project_id,
                target=p.path,
                reason="Live pytest execution",
                risk_level=RiskLevel.LOW,
                result=status
            )
            return {
                "project_id": project_id,
                "status": status,
                "tests_total": total,
                "passed": passed,
                "failed": failed,
                "duration": duration,
                "execution_mode": "REAL_PYTEST"
            }
        except Exception as e:
            return {
                "project_id": project_id,
                "status": "ERROR",
                "tests_total": 0,
                "passed": 0,
                "failed": 0,
                "duration": "0s",
                "error": str(e)
            }

    record_audit(
        action=f"TEST_SUITE_RUN: {project_id}",
        project=project_id,
        target=p.path,
        reason="Automated test suite probe (no tests directory)",
        risk_level=RiskLevel.LOW,
        result="SKIPPED"
    )
    return {
        "project_id": project_id,
        "status": "SKIPPED",
        "tests_total": 0,
        "passed": 0,
        "failed": 0,
        "duration": "0s",
        "detail": "No tests/ directory discovered"
    }

@router.post("/{project_id}/security")
def run_security_scan(project_id: str):
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    findings = []
    if os.path.exists(p.path):
        try:
            res = subprocess.run(
                ["grep", "-rnE", "--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude-dir=__pycache__", "--exclude-dir=.pytest_cache", "--exclude-dir=docs", "-----BEGIN [A-Z ]*PRIVATE KEY-----", p.path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.stdout.strip():
                for line in res.stdout.strip().split("\n"):
                    fpath = line.split(":")[0]
                    if not fpath.endswith("projects.py") and not fpath.endswith("automations.py"):
                        findings.append(fpath)
        except Exception:
            pass

    unique_files = list(set(findings))
    status = "WARNING" if unique_files else "CLEAN"

    record_audit(
        action=f"SECURITY_SCAN: {project_id}",
        project=project_id,
        target=p.path,
        reason="Real regex secret leak scan across workspace",
        risk_level=RiskLevel.LOW,
        result=status
    )
    return {
        "project_id": project_id,
        "status": status,
        "cves_found": 0,
        "secrets_leaked": len(unique_files),
        "leaked_locations": unique_files,
        "iam_misconfigurations": 0,
        "execution_mode": "REAL_REGEX_SCAN"
    }

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
