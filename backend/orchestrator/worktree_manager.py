"""
NEXUS Isolated Git Worktree Swarm Execution Manager.
Provides isolated, concurrent multi-agent git worktree workspaces:
- Native `git worktree add -b <branch>` per swarm session
- Full isolation for concurrent agents operating on the same base repository
- Prevents working-tree collisions and uncommitted file contamination
- Safe teardown, branch retention, and dead worktree pruning
- Full auditability and persistent metadata tracking via atomic JSON
"""

import os
import re
import shutil
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from core.config import config
from core.storage import load_json_safe, atomic_save_json, atomic_json_updater
from core.audit import record_audit
from models.schemas import WorktreeInfo, RiskLevel
from orchestrator.safe_runner import SafeCommandExecutor

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class WorktreeManager:
    """Manages isolated git worktree environments for multi-agent swarm sessions."""

    def __init__(self, registry_file: Optional[str] = None, worktrees_dir: Optional[str] = None):
        self.base_dir = config.base_dir or "/root/control-center"
        self.worktrees_dir = worktrees_dir or os.path.join(self.base_dir, "data", "worktrees")
        self.registry_file = registry_file or os.path.join(self.base_dir, "data", "worktrees_registry.json")
        self._lock = threading.RLock()
        os.makedirs(self.worktrees_dir, exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(self.registry_file)), exist_ok=True)

    def is_git_repo(self, path: str) -> bool:
        """Checks whether a directory is inside a valid git repository."""
        if not path or not os.path.exists(path):
            return False
        res = SafeCommandExecutor.execute(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
        return res.exit_code == 0 and res.stdout.strip().lower() == "true"

    def get_repo_root(self, path: str) -> Optional[str]:
        """Resolves the root directory of a git repository."""
        if not self.is_git_repo(path):
            return None
        res = SafeCommandExecutor.execute(["git", "rev-parse", "--show-toplevel"], cwd=path)
        if res.exit_code == 0 and res.stdout.strip():
            return res.stdout.strip()
        return None

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        return load_json_safe(self.registry_file, default={})

    def _save_registry(self, data: Dict[str, Dict[str, Any]]):
        atomic_save_json(self.registry_file, data)

    def get_worktree(self, session_id: str) -> Optional[WorktreeInfo]:
        reg = self._load_registry()
        raw = reg.get(session_id)
        if raw and isinstance(raw, dict):
            try:
                return WorktreeInfo(**raw)
            except Exception:
                return None
        return None

    def list_worktrees(self, repo_path: Optional[str] = None) -> List[WorktreeInfo]:
        """Lists active worktrees from the registry, optionally filtered by repo."""
        reg = self._load_registry()
        results: List[WorktreeInfo] = []
        target_root = self.get_repo_root(repo_path) if repo_path else None

        for s_id, raw in reg.items():
            if isinstance(raw, dict) and raw.get("status") == "ACTIVE":
                try:
                    info = WorktreeInfo(**raw)
                    if not os.path.exists(info.repo_path) or not os.path.exists(info.worktree_path):
                        continue
                    if target_root:
                        if info.repo_path == target_root:
                            results.append(info)
                    else:
                        results.append(info)
                except Exception:
                    pass
        return results

    def provision_worktree(
        self,
        repo_path: str,
        session_id: str,
        branch_name: Optional[str] = None
    ) -> WorktreeInfo:
        """
        Provisions a new isolated git worktree on a dedicated branch for the swarm session.
        Enforces strict path traversal defenses, branch safety, and thread concurrency protection.
        """
        with self._lock:
            # 1. Path traversal & input validation
            if not session_id or not isinstance(session_id, str):
                raise ValueError("session_id must be a non-empty string.")
            if not re.match(r"^[a-zA-Z0-9_\-]+$", session_id):
                raise ValueError(f"Invalid session_id '{session_id}': contains illegal characters or path traversal elements.")

            root_repo = self.get_repo_root(repo_path)
            if not root_repo:
                raise ValueError(f"Path '{repo_path}' is not a valid git repository.")

            # Ensure repository is not a dangerous root directory
            canonical_root = os.path.realpath(root_repo)
            if canonical_root in ["/", "/root", "/etc", "/var", "/usr"]:
                raise ValueError(f"Repository root '{canonical_root}' is a protected system directory.")

            # 2. Resolve worktree target path & assert inside worktrees_dir
            worktree_path = os.path.realpath(os.path.join(self.worktrees_dir, session_id))
            canonical_wts_dir = os.path.realpath(self.worktrees_dir)
            if not Path(worktree_path).resolve().is_relative_to(Path(canonical_wts_dir).resolve()):
                raise ValueError(f"Worktree path traversal attempt blocked: {worktree_path}")

            # Check existing active worktree for this session
            existing = self.get_worktree(session_id)
            if existing and existing.status == "ACTIVE" and os.path.exists(existing.worktree_path):
                if self.is_git_repo(existing.worktree_path):
                    return existing

            # 3. Branch resolution and base branch protection
            curr_branch_res = SafeCommandExecutor.execute(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root_repo)
            current_branch = curr_branch_res.stdout.strip() if curr_branch_res.exit_code == 0 else "main"

            branch = branch_name or f"swarm/{session_id}"
            if not re.match(r"^[a-zA-Z0-9_\-/\.]+$", branch):
                raise ValueError(f"Invalid branch name '{branch}'.")

            if branch == current_branch:
                raise ValueError(f"Cannot checkout current active branch '{branch}' as isolated worktree.")

            # Clean existing directory if stale
            if os.path.exists(worktree_path):
                self.teardown_worktree(session_id, force=True)

            # Ensure branch does not collide; if it exists and is not base branch, delete stale
            branch_check = SafeCommandExecutor.execute(["git", "show-ref", f"refs/heads/{branch}"], cwd=root_repo)
            if branch_check.exit_code == 0 and branch != current_branch:
                SafeCommandExecutor.execute(["git", "branch", "-D", branch], cwd=root_repo)

            # Create isolated worktree with branch checked out from HEAD
            cmd_res = SafeCommandExecutor.execute(
                ["git", "worktree", "add", "-b", branch, worktree_path, "HEAD"],
                cwd=root_repo
            )
            if cmd_res.exit_code != 0:
                raise RuntimeError(f"Failed to create git worktree at {worktree_path}: {cmd_res.stderr or cmd_res.stdout}")

            # Capture initial commit hash
            hash_res = SafeCommandExecutor.execute(["git", "rev-parse", "HEAD"], cwd=worktree_path)
            commit_hash = hash_res.stdout.strip() if hash_res.exit_code == 0 else None

            info = WorktreeInfo(
                session_id=session_id,
                repo_path=root_repo,
                worktree_path=worktree_path,
                branch_name=branch,
                created_at=_now_iso(),
                status="ACTIVE",
                commit_hash=commit_hash
            )

            with atomic_json_updater(self.registry_file, default={}) as reg:
                reg[session_id] = info.model_dump()

            record_audit(
                action=f"WORKTREE_PROVISIONED: {session_id}",
                project=root_repo,
                target=worktree_path,
                reason=f"Spawned isolated worktree on branch '{branch}'",
                risk_level=RiskLevel.LOW,
                result="PROVISIONED",
                actor="worktree_manager",
                execution_id=session_id,
                status="ACTIVE"
            )
            return info

    def teardown_worktree(
        self,
        session_id: str,
        force: bool = True,
        delete_branch: bool = False
    ) -> Dict[str, Any]:
        """
        Safely removes an isolated worktree and prunes git tracking.
        Optionally deletes or retains the session feature branch.
        """
        with self._lock:
            info = self.get_worktree(session_id)
            worktree_path = info.worktree_path if info else os.path.realpath(os.path.join(self.worktrees_dir, session_id))
            repo_path = info.repo_path if info else self.base_dir
            branch_name = info.branch_name if info else f"swarm/{session_id}"

            # 1. git worktree remove
            if self.is_git_repo(repo_path):
                SafeCommandExecutor.execute(
                    ["git", "worktree", "remove", "--force", worktree_path],
                    cwd=repo_path
                )
                SafeCommandExecutor.execute(["git", "worktree", "prune"], cwd=repo_path)

                if delete_branch:
                    curr_branch_res = SafeCommandExecutor.execute(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
                    curr_b = curr_branch_res.stdout.strip() if curr_branch_res.exit_code == 0 else "main"
                    if branch_name != curr_b:
                        SafeCommandExecutor.execute(["git", "branch", "-D", branch_name], cwd=repo_path)

            # 2. Filesystem fallback cleanup if directory still remains
            if os.path.exists(worktree_path):
                try:
                    shutil.rmtree(worktree_path, ignore_errors=True)
                except Exception:
                    pass

            with atomic_json_updater(self.registry_file, default={}) as reg:
                if session_id in reg:
                    reg[session_id]["status"] = "TEARDOWN"
                    reg[session_id]["torn_down_at"] = _now_iso()

            record_audit(
                action=f"WORKTREE_TEARDOWN: {session_id}",
                project=repo_path,
                target=worktree_path,
                reason=f"Tore down isolated worktree (delete_branch={delete_branch})",
                risk_level=RiskLevel.LOW,
                result="TEARDOWN",
                actor="worktree_manager",
                execution_id=session_id,
                status="TEARDOWN"
            )

            return {
                "status": "TEARDOWN",
                "session_id": session_id,
                "worktree_path": worktree_path,
                "branch_name": branch_name,
                "branch_deleted": delete_branch
            }

    def prune_stale_worktrees(self) -> int:
        """Prunes any dead or untracked worktrees from disk and registry."""
        import tempfile
        pruned_count = 0
        if not os.path.exists(self.worktrees_dir):
            return 0

        # 1. First, tear down any lingering worktrees whose repo_path is in temporary test dirs
        reg_snapshot = self._load_registry()
        for sid, entry in list(reg_snapshot.items()):
            if isinstance(entry, dict) and entry.get("status") == "ACTIVE":
                rp = entry.get("repo_path", "")
                if rp.startswith("/tmp") or rp.startswith(tempfile.gettempdir()):
                    try:
                        self.teardown_worktree(sid, force=True)
                        pruned_count += 1
                    except Exception:
                        pass

        with self._lock:
            with atomic_json_updater(self.registry_file, default={}) as reg:
                # 2. Clean registry entries whose worktree_path or repo_path no longer exists
                for sid, entry in list(reg.items()):
                    if isinstance(entry, dict) and entry.get("status") == "ACTIVE":
                        wt_p = entry.get("worktree_path")
                        rp = entry.get("repo_path")
                        if (wt_p and not os.path.exists(wt_p)) or (rp and not os.path.exists(rp)):
                            entry["status"] = "TEARDOWN"
                            entry["torn_down_at"] = _now_iso()
                            pruned_count += 1

                # 3. Remove untracked or torn down directories from worktrees_dir
                for item in os.listdir(self.worktrees_dir):
                    wt_path = os.path.join(self.worktrees_dir, item)
                    if os.path.isdir(wt_path):
                        entry = reg.get(item)
                        if not entry or entry.get("status") == "TEARDOWN":
                            shutil.rmtree(wt_path, ignore_errors=True)
                            pruned_count += 1

            if self.is_git_repo(self.base_dir):
                SafeCommandExecutor.execute(["git", "worktree", "prune"], cwd=self.base_dir)

            return pruned_count

    @contextmanager
    def isolated_worktree_context(
        self,
        repo_path: str,
        session_id: str,
        branch_name: Optional[str] = None,
        delete_branch_on_teardown: bool = False
    ):
        """Context manager for ephemeral worktree execution."""
        wt_info = self.provision_worktree(repo_path, session_id, branch_name=branch_name)
        try:
            yield wt_info
        finally:
            self.teardown_worktree(session_id, force=True, delete_branch=delete_branch_on_teardown)

worktree_manager = WorktreeManager()
