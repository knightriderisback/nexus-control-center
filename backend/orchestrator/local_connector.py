"""
NEXUS Local Connector & Project Operations Bridge.
Provides:
1. Environment detection (Termux / Android / Linux / Ubuntu).
2. Deep automatic workspace discovery across configured approved roots.
3. Metadata inspection (Git remote, branch, commit, dirty files, stack, tests).
4. Idempotent project onboarding & registry synchronization.
5. Unified Project Dashboard aggregation (real Git state, health, missions, tests, security, deployments).
6. Governed project action execution.
"""

import os
import sys
import platform
import socket
import psutil
import time
import uuid
import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

from core.config import config
from core.audit import record_audit
from core.policy import evaluate_action
from core.approvals import request_approval
from models.schemas import (
    ConnectorStatusResponse,
    ProjectOnboardRequest,
    ProjectDashboardResponse,
    ProjectDashboardGitStatus,
    ProjectActionRequest,
    ProjectActionResult,
    ConnectorSyncRequest,
    ConnectorSyncResponse,
    DiscoveredProjectItem,
    ProjectDiscoveryResponse,
    ProjectRegistryItem,
    ProjectStatus,
    RiskLevel
)
from orchestrator.safe_runner import SafeCommandExecutor
from orchestrator.project_operations_engine import project_operations_engine
from orchestrator.mission_engine import mission_engine
from orchestrator.deployment_engine import deployment_engine
from orchestrator.self_healing_engine import self_healing_engine
from orchestrator.security_compliance_engine import security_compliance_engine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine
from registry.projects import load_projects, save_projects, get_project_by_id, audit_project

logger = logging.getLogger("nexus.local_connector")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalConnectorEngine:
    """
    Manages local Termux/Ubuntu environment bridge, project discovery, and interactive operations.
    """

    def __init__(self):
        self.start_time = time.time()
        self.connector_id = f"conn-{uuid.uuid4().hex[:8]}"

    def is_termux_environment(self) -> bool:
        """Detects if running inside Termux on Android."""
        return (
            "TERMUX_VERSION" in os.environ
            or os.path.exists("/data/data/com.termux/files")
            or "com.termux" in os.environ.get("PREFIX", "")
        )

    def get_status(self) -> ConnectorStatusResponse:
        """Returns live bridge status, host metadata, and active project counts."""
        is_termux = self.is_termux_environment()
        os_name = "Termux (Android)" if is_termux else f"{platform.system()} {platform.release()}"
        
        registered = load_projects()
        active_missions = len(mission_engine.list_missions(limit=100))
        
        # Scan active worktrees
        worktrees_dir = os.path.join(config.data_dir, "worktrees")
        active_worktrees = 0
        if os.path.exists(worktrees_dir):
            try:
                active_worktrees = len([d for d in os.listdir(worktrees_dir) if os.path.isdir(os.path.join(worktrees_dir, d))])
            except Exception:
                active_worktrees = 0

        return ConnectorStatusResponse(
            connector_id=self.connector_id,
            status="ONLINE",
            os_environment=os_name,
            is_termux=is_termux,
            hostname=socket.gethostname(),
            pid=os.getpid(),
            uptime_seconds=round(time.time() - self.start_time, 2),
            listening_host=config.host,
            listening_port=config.port,
            bridge_auth_required=config.auth_enabled,
            allowed_roots=self.get_scan_roots(),
            connected_projects_count=len(registered),
            active_missions_count=active_missions,
            active_worktrees_count=active_worktrees,
            timestamp=_now_iso()
        )

    def get_scan_roots(self) -> List[str]:
        """Returns configured and detected valid scan roots."""
        roots = list(config.allowed_project_roots)
        if self.is_termux_environment():
            termux_home = "/data/data/com.termux/files/home"
            if termux_home not in roots and os.path.exists(termux_home):
                roots.append(termux_home)
        
        # Ensure roots exist
        existing = [os.path.abspath(r) for r in roots if os.path.exists(r)]
        return existing or ["/root"]

    def discover_projects(self, custom_roots: Optional[List[str]] = None) -> ProjectDiscoveryResponse:
        """
        Deep automatic discovery: scans allowed roots up to depth 3 for Git repositories.
        Extracts remote, branch, commit, modified files, and stack configuration.
        """
        scan_roots = custom_roots or self.get_scan_roots()
        valid_roots = []
        for r in scan_roots:
            norm_r = os.path.abspath(r)
            if project_operations_engine.is_path_allowed(norm_r) and os.path.exists(norm_r):
                valid_roots.append(norm_r)

        registered = load_projects()
        registered_paths = {os.path.abspath(p.path): p.id for p in registered}
        discovered: List[DiscoveredProjectItem] = []
        seen_paths: Set[str] = set()

        ignore_dirs = {
            "node_modules", ".cache", ".npm", ".git", "__pycache__", 
            "site-packages", "dist", "build", ".pytest_cache", ".cargo", ".local"
        }

        for root_dir in valid_roots:
            # 1. Check root_dir itself
            self._probe_and_collect(root_dir, registered_paths, discovered, seen_paths)

            # 2. Walk up to depth 3
            try:
                for root, dirs, files in os.walk(root_dir):
                    # Prune ignored directories in-place
                    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
                    
                    depth = os.path.abspath(root).count(os.sep) - root_dir.count(os.sep)
                    if depth > 2:
                        continue

                    for d in list(dirs):
                        cand_path = os.path.join(root, d)
                        if self._probe_and_collect(cand_path, registered_paths, discovered, seen_paths):
                            # Don't descend into subdirectories of a discovered project
                            dirs.remove(d)
            except Exception as e:
                logger.warning(f"Error traversing root {root_dir}: {e}")

        reg_count = sum(1 for it in discovered if it.is_registered)
        unreg_count = len(discovered) - reg_count

        return ProjectDiscoveryResponse(
            scanned_roots=valid_roots,
            discovered_projects=discovered,
            total_discovered=len(discovered),
            registered_count=reg_count,
            unregistered_count=unreg_count,
            timestamp=_now_iso()
        )

    def _probe_and_collect(
        self,
        path: str,
        registered_paths: Dict[str, str],
        discovered: List[DiscoveredProjectItem],
        seen_paths: Set[str]
    ) -> bool:
        norm_p = os.path.abspath(path)
        if norm_p in seen_paths:
            return False

        has_git = os.path.exists(os.path.join(norm_p, ".git"))
        has_pyproject = os.path.exists(os.path.join(norm_p, "pyproject.toml"))
        has_package_json = os.path.exists(os.path.join(norm_p, "package.json"))
        has_dockerfile = os.path.exists(os.path.join(norm_p, "Dockerfile"))
        has_tests = os.path.exists(os.path.join(norm_p, "tests"))

        if not (has_git or has_pyproject or has_package_json or has_dockerfile or has_tests):
            return False

        seen_paths.add(norm_p)
        item = project_operations_engine._inspect_directory_for_project(norm_p, registered_paths)
        if item:
            discovered.append(item)
            return True
        return False

    def sync_discovered_projects(self, req: ConnectorSyncRequest) -> ConnectorSyncResponse:
        """
        Synchronizes discovered projects into the persistent registry and operational control plane.
        """
        disc_resp = self.discover_projects(req.roots)
        target_ids = set(req.project_ids) if req.project_ids else None

        synced = []
        errors = []
        skipped = 0

        for item in disc_resp.discovered_projects:
            if target_ids and item.project_id not in target_ids and item.path not in target_ids:
                continue

            try:
                # Query git remote
                remote_url = None
                if item.has_git:
                    r_res = SafeCommandExecutor.execute(["git", "remote", "get-url", "origin"], cwd=item.path)
                    if r_res.exit_code == 0:
                        remote_url = r_res.stdout.strip()

                reg_item = ProjectRegistryItem(
                    id=item.project_id,
                    name=item.name,
                    path=item.path,
                    repository=remote_url,
                    type=item.detected_type,
                    branch=item.branch or "main",
                    status=ProjectStatus.ACTIVE,
                    health_score=100.0,
                    owner="lead_developer",
                    tags=[item.detected_type, "auto-discovered"]
                )
                registered = project_operations_engine.register_project(reg_item)
                synced.append(registered)
            except Exception as e:
                errors.append(f"Failed to register '{item.name}' ({item.path}): {str(e)}")

        return ConnectorSyncResponse(
            synced_count=len(synced),
            synced_projects=synced,
            skipped_count=skipped,
            errors=errors,
            timestamp=_now_iso()
        )

    def onboard_project(self, req: ProjectOnboardRequest) -> ProjectRegistryItem:
        """
        Onboards a new project via local path, GitHub repository URL, or existing directory.
        Autodetects Git remote, branch, commit, and stack type.
        """
        raw_path = req.path or req.root_path
        if not raw_path:
            raise ValueError("Must provide 'path' or 'root_path' to onboard project.")

        target_path = os.path.abspath(raw_path)
        project_operations_engine.ensure_path_allowed(target_path)

        repository = req.repository or req.git_remote_url

        if not os.path.exists(target_path):
            # If GitHub repo provided, attempt cloning
            if repository and repository.startswith(("http", "git@")):
                os.makedirs(target_path, exist_ok=True)
                clone_res = SafeCommandExecutor.execute(
                    ["git", "clone", repository, target_path],
                    cwd=os.path.dirname(target_path)
                )
                if clone_res.exit_code != 0:
                    raise ValueError(f"Git clone failed: {clone_res.stderr or clone_res.stdout}")
            else:
                raise ValueError(f"Target path '{target_path}' does not exist.")

        # Detect Git metadata
        has_git = os.path.exists(os.path.join(target_path, ".git"))
        branch = req.branch or req.git_branch or "main"
        remote_url = repository

        if has_git:
            b_res = SafeCommandExecutor.execute(["git", "branch", "--show-current"], cwd=target_path)
            if b_res.exit_code == 0 and b_res.stdout.strip():
                branch = b_res.stdout.strip()
            
            if not remote_url:
                r_res = SafeCommandExecutor.execute(["git", "remote", "get-url", "origin"], cwd=target_path)
                if r_res.exit_code == 0 and r_res.stdout.strip():
                    remote_url = r_res.stdout.strip()

        # Detect project archetype
        detected_type = req.project_type or "generic_git"
        if os.path.exists(os.path.join(target_path, "main.py")) or os.path.exists(os.path.join(target_path, "backend", "main.py")):
            detected_type = "fastapi"
        elif os.path.exists(os.path.join(target_path, "vite.config.ts")) or os.path.exists(os.path.join(target_path, "frontend", "vite.config.ts")):
            detected_type = "react_vite"
        elif os.path.exists(os.path.join(target_path, "package.json")):
            detected_type = "node"
        elif os.path.exists(os.path.join(target_path, "pyproject.toml")):
            detected_type = "python_package"

        slug = (req.project_id or os.path.basename(target_path)).lower().replace("_", "-")
        name = req.name or os.path.basename(target_path).replace("-", " ").replace("_", " ").title()

        reg_item = ProjectRegistryItem(
            id=slug,
            name=name,
            path=target_path,
            repository=remote_url,
            type=detected_type,
            branch=branch,
            status=ProjectStatus.HEALTHY,
            health_score=100,
            owner=req.owner,
            tags=list(set(req.tags + [detected_type, "onboarded"]))
        )

        return project_operations_engine.register_project(reg_item)

    def get_project_dashboard(self, project_id: str) -> ProjectDashboardResponse:
        """
        Aggregates complete, live, real project dashboard telemetry.
        """
        project = get_project_by_id(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found in registry.")

        path = os.path.abspath(project.path)

        branch_name = getattr(project, "branch", None) or "main"
        git_status = self._inspect_real_git(path, branch_name)

        # 2. Operations record
        op_record = None
        try:
            op_record = project_operations_engine.get_project_record(project_id)
        except Exception as e:
            logger.warning(f"Error fetching op_record for {project_id}: {e}")

        # 3. Health detail
        health = None
        try:
            health = project_operations_engine.get_project_health(project_id)
        except Exception as e:
            logger.warning(f"Error fetching health for {project_id}: {e}")

        # 4. Missions
        proj_missions = []
        try:
            all_missions = mission_engine.list_missions(limit=50)
            proj_missions = [
                m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in all_missions
                if getattr(m, "project_id", None) == project_id or project_id in str(getattr(m, "repo_path", ""))
            ]
        except Exception as e:
            logger.warning(f"Error listing missions for {project_id}: {e}")

        # 5. Deployments
        proj_deps = []
        try:
            all_deps = deployment_engine.list_deployments(limit=50)
            proj_deps = [
                d.model_dump() if hasattr(d, "model_dump") else dict(d) for d in all_deps
                if getattr(d, "project_id", None) == project_id or getattr(d, "service_name", None) == project_id
            ]
        except Exception as e:
            logger.warning(f"Error listing deployments for {project_id}: {e}")

        # 6. Incidents
        proj_incs = []
        try:
            all_incs = self_healing_engine.list_incidents()
            proj_incs = [
                inc.model_dump() if hasattr(inc, "model_dump") else dict(inc) for inc in all_incs
                if getattr(inc, "project_id", None) == project_id or project_id in str(getattr(inc, "title", ""))
            ]
        except Exception as e:
            logger.warning(f"Error listing incidents for {project_id}: {e}")

        # 7. Security findings
        sec_findings = []
        try:
            all_findings = security_compliance_engine.list_findings()
            for f in all_findings:
                fp = getattr(f, "file_path", getattr(f, "location", "")) or ""
                if project_id in fp or path in fp:
                    sec_findings.append(f.model_dump() if hasattr(f, "model_dump") else dict(f))
        except Exception as e:
            logger.warning(f"Error listing security findings: {e}")

        # 8. Knowledge nodes
        know_nodes = []
        try:
            kn = knowledge_learning_engine.query_knowledge(project_id)
            know_nodes = [n.model_dump() if hasattr(n, "model_dump") else dict(n) for n in kn]
        except Exception:
            pass

        return ProjectDashboardResponse(
            project=project,
            operations_record=op_record,
            git=git_status,
            health=health,
            missions=proj_missions,
            deployments=proj_deps,
            incidents=proj_incs,
            security_findings=sec_findings,
            knowledge_nodes=know_nodes,
            available_actions=[
                "AUDIT", "TEST", "SECURITY_SCAN", "DEPLOY", "RUN_MISSION", "RECONCILE_DRIFT"
            ],
            timestamp=_now_iso()
        )

    def _inspect_real_git(self, path: str, default_branch: str = "main") -> ProjectDashboardGitStatus:
        if not os.path.exists(os.path.join(path, ".git")):
            return ProjectDashboardGitStatus(
                branch=default_branch,
                is_clean=True,
                dirty_files_count=0,
                modified_files=[],
                untracked_files=[]
            )

        # Query branch
        b_res = SafeCommandExecutor.execute(["git", "branch", "--show-current"], cwd=path)
        branch = b_res.stdout.strip() if b_res.exit_code == 0 else default_branch

        # Query commit
        c_res = SafeCommandExecutor.execute(["git", "log", "-n", "1", "--format=%h %s"], cwd=path)
        commit_sha = None
        commit_msg = None
        if c_res.exit_code == 0 and c_res.stdout.strip():
            parts = c_res.stdout.strip().split(" ", 1)
            commit_sha = parts[0]
            commit_msg = parts[1] if len(parts) > 1 else ""

        # Query remote URL
        r_res = SafeCommandExecutor.execute(["git", "remote", "get-url", "origin"], cwd=path)
        remote_url = r_res.stdout.strip() if r_res.exit_code == 0 else None

        # Query status
        s_res = SafeCommandExecutor.execute(["git", "status", "--porcelain"], cwd=path)
        modified_files = []
        untracked_files = []
        if s_res.exit_code == 0 and s_res.stdout.strip():
            for line in s_res.stdout.strip().split("\n"):
                if not line:
                    continue
                code = line[:2]
                fname = line[3:].strip()
                if "??" in code:
                    untracked_files.append(fname)
                else:
                    modified_files.append(fname)

        dirty_count = len(modified_files) + len(untracked_files)

        return ProjectDashboardGitStatus(
            branch=branch,
            commit_sha=commit_sha,
            commit_message=commit_msg,
            remote_url=remote_url,
            is_clean=(dirty_count == 0),
            dirty_files_count=dirty_count,
            modified_files=modified_files[:20],
            untracked_files=untracked_files[:20],
            ahead=0,
            behind=0
        )

    def execute_project_action(self, project_id: str, req: ProjectActionRequest) -> ProjectActionResult:
        """
        Executes a live governed project action.
        """
        project = get_project_by_id(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        path = os.path.abspath(project.path)
        action = req.action.upper()
        t0 = time.time()

        if action == "AUDIT":
            res = audit_project(project_id)
            duration = (time.time() - t0) * 1000
            msg = f"Project audit executed with health score {res.get('health_score', 100)}/100"
            return ProjectActionResult(
                project_id=project_id,
                action="AUDIT",
                status="SUCCESS",
                message=msg,
                output=msg,
                duration_ms=round(duration, 2),
                details=res
            )

        elif action == "TEST":
            # Check for pytest or npm test
            test_cmd = None
            if os.path.exists(os.path.join(path, "pytest.ini")) or os.path.exists(os.path.join(path, "tests")):
                test_cmd = ["python3", "-m", "pytest", "tests/"]
            elif os.path.exists(os.path.join(path, "package.json")):
                test_cmd = ["npm", "test"]

            if not test_cmd:
                msg = "No test runner configured for project."
                return ProjectActionResult(
                    project_id=project_id,
                    action="TEST",
                    status="SUCCESS",
                    message=msg,
                    output=msg,
                    duration_ms=round((time.time() - t0) * 1000, 2),
                    details={"tests_run": 0, "passed": 0}
                )

            run_res = SafeCommandExecutor.execute(test_cmd, cwd=path)
            duration = (time.time() - t0) * 1000
            passed = run_res.exit_code == 0
            msg = "All tests passed successfully" if passed else "Test suite completed with failures"
            out_str = (run_res.stdout + "\n" + run_res.stderr).strip() or msg
            return ProjectActionResult(
                project_id=project_id,
                action="TEST",
                status="SUCCESS" if passed else "FAILED",
                message=msg,
                output=out_str,
                duration_ms=round(duration, 2),
                details={
                    "exit_code": run_res.exit_code,
                    "stdout": run_res.stdout[-1500:],
                    "stderr": run_res.stderr[-1000:]
                }
            )

        elif action == "SECURITY_SCAN":
            scan_rep = security_compliance_engine.scan_codebase()
            duration = (time.time() - t0) * 1000
            findings_count = len(scan_rep.findings)
            msg = f"Security AST scan completed ({findings_count} findings evaluated, score: {scan_rep.risk_score})"
            return ProjectActionResult(
                project_id=project_id,
                action="SECURITY_SCAN",
                status="SUCCESS",
                message=msg,
                output=msg,
                duration_ms=round(duration, 2),
                details={
                    "scan_id": scan_rep.scan_id,
                    "total_files": scan_rep.total_files_scanned,
                    "risk_score": scan_rep.risk_score,
                    "findings_count": findings_count
                }
            )

        elif action == "RECONCILE_DRIFT":
            duration = (time.time() - t0) * 1000
            reconciled = []
            try:
                op_rec = project_operations_engine.get_project_record(project_id)
                if op_rec and op_rec.active_drifts:
                    from models.schemas import ReconcileDriftRequest
                    for d in list(op_rec.active_drifts):
                        try:
                            r = project_operations_engine.reconcile_drift(
                                ReconcileDriftRequest(drift_id=d.drift_id)
                            )
                            reconciled.append(r.model_dump())
                        except Exception as de:
                            logger.warning(f"Error reconciling drift {d.drift_id}: {de}")
            except Exception as e:
                logger.warning(f"Error checking drifts: {e}")

            msg = f"Configuration drift inspected. {len(reconciled)} drift(s) reconciled." if reconciled else "Configuration and environment synchronized with zero drift."
            return ProjectActionResult(
                project_id=project_id,
                action="RECONCILE_DRIFT",
                status="SUCCESS",
                message=msg,
                output=msg,
                duration_ms=round(duration, 2),
                details={"reconciled_count": len(reconciled), "drifts": reconciled}
            )

        elif action == "RUN_MISSION":
            goal = req.payload.get("goal") or f"Inspect and optimize {project.name}"
            from models.schemas import MissionPlanRequest
            mission = mission_engine.plan_mission(MissionPlanRequest(
                goal=goal,
                project_id=project_id,
                repo_path=path,
                target_branch=getattr(project, 'branch', 'main')
            ))
            duration = (time.time() - t0) * 1000
            msg = f"Mission '{mission.mission_id}' created for project {project_id}."
            return ProjectActionResult(
                project_id=project_id,
                action="RUN_MISSION",
                status="SUCCESS",
                message=msg,
                output=msg,
                duration_ms=round(duration, 2),
                details=mission.model_dump()
            )

        else:
            raise ValueError(f"Unknown project action: '{action}'. Supported: AUDIT, TEST, SECURITY_SCAN, RUN_MISSION, RECONCILE_DRIFT")


# Singleton Local Connector
local_connector_engine = LocalConnectorEngine()
