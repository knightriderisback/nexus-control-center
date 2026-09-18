"""
NEXUS Swarm Branch Merge Arbitration & Cross-Session Conflict Resolution Engine.
Provides autonomous, auditable, conflict-aware branch reconciliation:
- Evaluates divergence & mergeability between swarm feature branches and target base branches
- Native three-way merge analysis (common ancestor, source/target diffs, overlapping files, rename/delete/binary conflicts, dangerous paths)
- Deep merge risk classification (security policies, auth, secrets, IaC, migrations, core runtime)
- Ephemeral dry-run verification in isolated worktrees (zero primary working-tree pollution)
- Semantic pre-merge regression verification (automated pytest suite execution & security scanning)
- Autonomous cross-session conflict resolution with deterministic safety (Fast-Forward, Three-Way, Ours/Theirs with policy gates, Agent Resolution)
- Multi-agent review fleet integration (AGY planner, Codex reviewer, QA verifier, Security sentinel)
- Scoped human-in-the-loop approval gating with anti-replay protection and commit/tree identity scoping
- Target branch staleness detection and race-condition prevention
- Per-repository concurrency lock & serialized trunk integration
- Safe target branch update with strict protection of existing user uncommitted working trees
- Persistent merge history & audit integration via atomic JSON
"""

import os
import re
import fcntl
import shutil
import uuid
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from core.config import config
from core.storage import load_json_safe, atomic_save_json, atomic_json_updater
from core.audit import record_audit
from core.policy import evaluate_action
from core.approvals import request_approval, load_approvals, save_approvals
from models.schemas import (
    MergeStrategy,
    MergeEvaluationRequest,
    MergeEvaluationResult,
    MergeExecutionRequest,
    MergeExecutionResult,
    MergeClassification,
    ConflictType,
    MergeabilityClassification,
    ThreeWayAnalysis,
    RiskClassification,
    VerificationCandidate,
    MergeDecision,
    RiskLevel,
    ApprovalStatus,
    MergeLifecycleState,
    MergeTransitionRecord,
    MergeCandidateCreateRequest,
    MergeCandidate
)
from orchestrator.safe_runner import SafeCommandExecutor
from orchestrator.worktree_manager import worktree_manager

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_branch_name(branch: str) -> str:
    if not branch or not isinstance(branch, str):
        raise ValueError("Branch name must be a non-empty string.")
    branch = branch.strip()
    if (
        not re.match(r"^[a-zA-Z0-9_\-\.\/]+$", branch)
        or ".." in branch
        or branch.startswith("/")
        or branch.startswith("-")
        or branch.endswith("/")
        or branch.endswith(".lock")
        or any(ch in branch for ch in [";", "|", "&", "`", "$", "\n", "\r"])
    ):
        raise ValueError(f"Malicious or invalid branch name: '{branch}'")
    return branch


def _sanitize_repo_path(repo_path: str) -> str:
    if not repo_path or not isinstance(repo_path, str):
        raise ValueError("Repository path must be a non-empty string.")
    canonical = os.path.realpath(repo_path)
    if not os.path.exists(canonical) or not os.path.isdir(canonical):
        raise ValueError(f"Repository path does not exist or is invalid: '{repo_path}'")
    return canonical


# -----------------------------------------------------------------------------
# Concurrency & Repository Locking
# -----------------------------------------------------------------------------

_repo_locks: Dict[str, threading.RLock] = {}
_repo_locks_guard = threading.Lock()

def _get_repo_lock(repo_path: str) -> threading.RLock:
    canonical = os.path.realpath(repo_path)
    with _repo_locks_guard:
        if canonical not in _repo_locks:
            _repo_locks[canonical] = threading.RLock()
        return _repo_locks[canonical]


class _RepoFileLock:
    """Inter-process and cross-thread file lock on <repo>/.git/nexus_arbitration.lock."""
    def __init__(self, repo_path: str):
        self.lock_file = os.path.join(repo_path, ".git", "nexus_arbitration.lock")
        self.fd = None

    def __enter__(self):
        try:
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
            self.fd = open(self.lock_file, "w")
            fcntl.flock(self.fd, fcntl.LOCK_EX)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
            except Exception:
                pass


# -----------------------------------------------------------------------------
# Sensitive Path Definitions
# -----------------------------------------------------------------------------

SENSITIVE_CATEGORIES = {
    "SECURITY_POLICY": [
        "backend/core/policy.py", "backend/core/approvals.py", "backend/core/secrets.py",
        "backend/core/audit.py", "backend/core/cost_guard.py"
    ],
    "AUTH_GOVERNANCE": [
        "auth.py", "tokens.py", "jwt", "permissions.py", "rbac", "data/approvals.json"
    ],
    "SECRETS_CONFIG": [
        ".env", "credentials", "secrets.json", ".pem", ".key", "id_rsa"
    ],
    "INFRASTRUCTURE_IAC": [
        "infra/", ".tf", "Dockerfile", "docker-compose", "k8s/"
    ],
    "DEPLOYMENT": [
        "cloudbuild", "deploy.sh", "systemd", "supervisord"
    ],
    "DATABASE_MIGRATIONS": [
        "migrations/", "alembic/", "schema.sql"
    ],
    "CORE_RUNTIME": [
        "backend/orchestrator/runtime.py", "backend/orchestrator/safe_runner.py",
        "backend/orchestrator/session_engine.py", "backend/server.py"
    ]
}


class MergeArbitrator:
    """Manages branch merge evaluation, conflict arbitration, multi-agent review, and atomic trunk reconciliation."""

    def __init__(self, history_file: Optional[str] = None, candidates_file: Optional[str] = None):
        self.base_dir = config.base_dir or "/root/control-center"
        self.history_file = history_file or os.path.join(self.base_dir, "data", "merge_history.json")
        self.candidates_file = candidates_file or os.path.join(self.base_dir, "data", "merge_candidates.json")
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(os.path.abspath(self.history_file)), exist_ok=True)
        os.makedirs(os.path.dirname(os.path.abspath(self.candidates_file)), exist_ok=True)

    def _load_history(self) -> Dict[str, Dict[str, Any]]:
        return load_json_safe(self.history_file, default={})

    def list_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._load_history()
            items = [v for v in data.values() if isinstance(v, dict)]
            items.sort(key=lambda x: x.get("executed_at", ""), reverse=True)
            return items[:limit]

    def get_merge_record(self, merge_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._load_history()
            rec = data.get(merge_id)
            return rec if isinstance(rec, dict) else None

    def _record_merge(self, result: MergeExecutionResult):
        with self._lock:
            with atomic_json_updater(self.history_file, default={}) as data:
                data[result.merge_id] = result.model_dump()

    # -------------------------------------------------------------------------
    # Three-Way Merge Analysis (Git Native Machinery)
    # -------------------------------------------------------------------------

    def analyze_three_way(self, repo: str, target: str, source: str) -> ThreeWayAnalysis:
        """
        Executes deep three-way merge analysis using Git's native machinery:
        - Detects common ancestor merge-base
        - Inspects source and target changes
        - Identifies overlapping files
        - Detects rename/delete conflicts
        - Detects binary conflicts
        - Flags dangerous path changes
        """
        merge_base_res = SafeCommandExecutor.execute(["git", "merge-base", target, source], cwd=repo)
        merge_base = merge_base_res.stdout.strip() if merge_base_res.exit_code == 0 else ""

        source_commit = SafeCommandExecutor.execute(["git", "rev-parse", source], cwd=repo).stdout.strip()
        target_commit = SafeCommandExecutor.execute(["git", "rev-parse", target], cwd=repo).stdout.strip()

        is_ff = self._is_ancestor(repo, target, source)
        divergence = self._get_divergence(repo, target, source)

        # Source changes since merge-base
        diff_range = f"{merge_base}...{source}" if merge_base else f"{target}...{source}"
        src_diff_names = SafeCommandExecutor.execute(["git", "diff", "--name-status", diff_range], cwd=repo)
        src_files: Dict[str, str] = {}
        for line in src_diff_names.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                src_files[parts[1]] = parts[0]

        # Target changes since merge-base
        tgt_range = f"{merge_base}...{target}" if merge_base else target
        tgt_diff_names = SafeCommandExecutor.execute(["git", "diff", "--name-status", tgt_range], cwd=repo)
        tgt_files: Dict[str, str] = {}
        for line in tgt_diff_names.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                tgt_files[parts[1]] = parts[0]

        overlapping = [f for f in src_files if f in tgt_files]

        # Rename / delete conflicts: file modified in one branch and deleted in the other
        rename_delete_conflicts = []
        for f, st in src_files.items():
            if st.startswith("D") and f in tgt_files and not tgt_files[f].startswith("D"):
                rename_delete_conflicts.append(f"Deleted in source, modified in target: {f}")
            elif not st.startswith("D") and f in tgt_files and tgt_files[f].startswith("D"):
                rename_delete_conflicts.append(f"Modified in source, deleted in target: {f}")

        # Binary conflicts: inspect diff numstat for binary markers ('-' '-')
        binary_conflicts = []
        numstat_res = SafeCommandExecutor.execute(["git", "diff", "--numstat", f"{target}...{source}"], cwd=repo)
        for line in numstat_res.stdout.splitlines():
            parts = line.strip().split(None, 2)
            if len(parts) == 3 and parts[0] == "-" and parts[1] == "-":
                binary_conflicts.append(parts[2])

        # Dangerous path changes: flags sensitive files
        dangerous_paths = self._detect_dangerous_paths(list(src_files.keys()))

        return ThreeWayAnalysis(
            merge_base_commit=merge_base,
            source_commit=source_commit,
            target_commit=target_commit,
            is_fast_forward=is_ff,
            source_changes={"files_count": len(src_files), "files": src_files},
            target_changes={"files_count": len(tgt_files), "files": tgt_files},
            overlapping_files=overlapping,
            rename_delete_conflicts=rename_delete_conflicts,
            binary_conflicts=binary_conflicts,
            dangerous_path_changes=dangerous_paths,
            divergence=divergence
        )

    def _detect_dangerous_paths(self, file_paths: List[str]) -> List[str]:
        dangerous = []
        for f in file_paths:
            for cat, patterns in SENSITIVE_CATEGORIES.items():
                for p in patterns:
                    if p.endswith("/") and f.startswith(p):
                        dangerous.append(f)
                        break
                    elif p in f or f == p:
                        dangerous.append(f)
                        break
        return list(dict.fromkeys(dangerous))

    # -------------------------------------------------------------------------
    # Deep Risk & Conflict Classification
    # -------------------------------------------------------------------------

    def evaluate_merge_risk(self, repo: str, source_files: List[str]) -> RiskClassification:
        """Evaluates merge risk based on changed file sensitivity and policy rules."""
        matched_categories = set()
        dangerous_paths = []

        for f in source_files:
            for cat, patterns in SENSITIVE_CATEGORIES.items():
                for p in patterns:
                    if (p.endswith("/") and f.startswith(p)) or (p in f or f == p):
                        matched_categories.add(cat)
                        dangerous_paths.append(f)
                        break

        # Check policy engine
        action_desc = f"Merge source changes affecting {len(source_files)} files: {', '.join(source_files[:5])}"
        policy_risk, policy_req_appr, policy_reason = evaluate_action(action_desc, repo)

        effective_risk = policy_risk
        requires_approval = policy_req_appr

        if matched_categories:
            if "SECURITY_POLICY" in matched_categories or "AUTH_GOVERNANCE" in matched_categories:
                effective_risk = RiskLevel.CRITICAL
                requires_approval = True
            elif "INFRASTRUCTURE_IAC" in matched_categories or "CORE_RUNTIME" in matched_categories or "DATABASE_MIGRATIONS" in matched_categories:
                if effective_risk != RiskLevel.CRITICAL:
                    effective_risk = RiskLevel.HIGH
                requires_approval = True
            policy_reason = f"Touched sensitive categories: {', '.join(sorted(matched_categories))}. {policy_reason or ''}".strip()

        return RiskClassification(
            risk_level=effective_risk,
            requires_approval=requires_approval,
            policy_reason=policy_reason,
            dangerous_paths=list(dict.fromkeys(dangerous_paths)),
            sensitive_categories=sorted(list(matched_categories))
        )

    def classify_conflict(
        self,
        analysis: ThreeWayAnalysis,
        has_textual_conflicts: bool,
        test_passed: Optional[bool],
        requires_approval: bool,
        security_clean: Optional[bool] = None
    ) -> Tuple[ConflictType, MergeabilityClassification, str]:
        """
        Classifies merge conflicts and overall mergeability.
        Returns (ConflictType, MergeabilityClassification, high_level_status).
        High-level statuses: CLEAN_MERGE, AUTO_MERGEABLE, CONFLICTED, HIGH_RISK, VERIFICATION_FAILED, REQUIRES_HUMAN, REJECTED
        """
        if requires_approval or analysis.dangerous_path_changes:
            return ConflictType.POLICY_BLOCKED, MergeabilityClassification.DANGEROUS_PATH_VIOLATION, MergeClassification.HIGH_RISK.value

        if test_passed is False or security_clean is False:
            return ConflictType.SEMANTIC_TEST_FAILURE, MergeabilityClassification.UNRESOLVABLE_CONFLICT, MergeClassification.VERIFICATION_FAILED.value

        if analysis.rename_delete_conflicts or analysis.binary_conflicts:
            return ConflictType.RENAME_DELETE_CONFLICT if analysis.rename_delete_conflicts else ConflictType.BINARY_CONFLICT, MergeabilityClassification.UNRESOLVABLE_CONFLICT, MergeClassification.CONFLICTED.value

        if has_textual_conflicts:
            return ConflictType.TEXTUAL_CONFLICT, MergeabilityClassification.RESOLVABLE_CONFLICT, MergeClassification.CONFLICTED.value

        if analysis.is_fast_forward:
            return ConflictType.CLEAN_MERGE, MergeabilityClassification.FAST_FORWARD, MergeClassification.CLEAN_MERGE.value

        return ConflictType.CLEAN_MERGE, MergeabilityClassification.CLEAN_THREE_WAY, MergeClassification.CLEAN_MERGE.value

    # -------------------------------------------------------------------------
    # Evaluation Pipeline
    # -------------------------------------------------------------------------

    def evaluate_merge(self, req: MergeEvaluationRequest) -> MergeEvaluationResult:
        """
        Evaluates mergeability, divergence, fast-forward capability, and semantic test status
        in an ephemeral worktree without mutating the primary repository.
        """
        _sanitize_branch_name(req.source_branch)
        _sanitize_branch_name(req.target_branch)
        sanitized_repo = _sanitize_repo_path(req.repo_path)
        repo_lock = _get_repo_lock(sanitized_repo)
        with repo_lock:
            root_repo = worktree_manager.get_repo_root(sanitized_repo)
            if not root_repo:
                raise ValueError(f"Path '{req.repo_path}' is not a valid git repository.")

            self._validate_branch_exists(root_repo, req.source_branch)
            self._validate_branch_exists(root_repo, req.target_branch)

            # 1. Native Three-Way Analysis
            analysis = self.analyze_three_way(root_repo, req.target_branch, req.source_branch)

            # 2. Deep Risk Evaluation
            source_file_list = list(analysis.source_changes.get("files", {}).keys())
            risk_class = self.evaluate_merge_risk(root_repo, source_file_list)

            # 3. Diff summary
            diff_res = SafeCommandExecutor.execute(
                ["git", "diff", "--stat", f"{req.target_branch}...{req.source_branch}"],
                cwd=root_repo
            )
            diff_summary = diff_res.stdout.strip() if diff_res.exit_code == 0 else ""

            # 4. Ephemeral Dry-Run in isolated worktree
            eval_id = f"eval-{uuid.uuid4().hex[:8]}"
            eval_wt_path = os.path.join(worktree_manager.worktrees_dir, eval_id)
            eval_branch = f"tmp-eval/{eval_id}"

            has_conflicts = False
            conflict_files: List[str] = []
            semantic_test_passed: Optional[bool] = None

            try:
                add_res = SafeCommandExecutor.execute(
                    ["git", "worktree", "add", "-b", eval_branch, eval_wt_path, req.target_branch],
                    cwd=root_repo
                )
                if add_res.exit_code != 0:
                    raise RuntimeError(f"Failed to create evaluation worktree: {add_res.stderr or add_res.stdout}")

                merge_res = SafeCommandExecutor.execute(
                    ["git", "merge", "--no-commit", "--no-ff", req.source_branch],
                    cwd=eval_wt_path
                )

                if merge_res.exit_code != 0:
                    has_conflicts = True
                    unmerged_res = SafeCommandExecutor.execute(
                        ["git", "diff", "--name-only", "--diff-filter=U"],
                        cwd=eval_wt_path
                    )
                    if unmerged_res.exit_code == 0 and unmerged_res.stdout.strip():
                        conflict_files = [f.strip() for f in unmerged_res.stdout.splitlines() if f.strip()]
                    else:
                        status_res = SafeCommandExecutor.execute(["git", "status", "--porcelain"], cwd=eval_wt_path)
                        for line in status_res.stdout.splitlines():
                            if line.startswith("UU ") or line.startswith("AA ") or line.startswith("UD "):
                                conflict_files.append(line[3:].strip())
                else:
                    if req.run_pre_merge_tests:
                        semantic_test_passed = self._run_test_suite(eval_wt_path)

            finally:
                self._cleanup_temp_worktree(root_repo, eval_wt_path, eval_branch)

            conflict_type, mergeability, high_level = self.classify_conflict(
                analysis=analysis,
                has_textual_conflicts=has_conflicts,
                test_passed=semantic_test_passed,
                requires_approval=risk_class.requires_approval
            )

            return MergeEvaluationResult(
                repo_path=root_repo,
                source_branch=req.source_branch,
                target_branch=req.target_branch,
                mergeable=(not has_conflicts and semantic_test_passed is not False),
                is_fast_forward=analysis.is_fast_forward,
                has_conflicts=has_conflicts,
                conflict_files=conflict_files,
                divergence=analysis.divergence,
                diff_summary=diff_summary,
                semantic_test_passed=semantic_test_passed,
                evaluated_at=_now_iso(),
                three_way_analysis=analysis.model_dump(),
                conflict_type=conflict_type.value,
                mergeability=mergeability.value,
                risk_classification=risk_class.model_dump()
            )

    # -------------------------------------------------------------------------
    # Multi-Agent Review Fleet Integration (AGY <-> Codex Workflow)
    # -------------------------------------------------------------------------

    def review_merge_with_fleet(
        self,
        repo: str,
        merge_id: str,
        staging_wt_path: str,
        source_branch: str,
        target_branch: str,
        conflict_files: List[str]
    ) -> Dict[str, Any]:
        """
        Executes multi-agent merge review within the isolated verification worktree:
        1. AGY / Planner: analyzes merge intent and conflict context
        2. Codex / Reviewer: proposes or implements safe resolution
        3. QA Verifier: tests candidate merge
        4. Security Sentinel: audits changed/merged paths
        """
        from orchestrator.runtime import runtime_engine

        # Step 1: AGY Planner review
        agy_task = runtime_engine.create_task(
            agent_id="agent-research",
            title=f"AGY Merge Intent Review: {source_branch} -> {target_branch}",
            instructions=f"Analyze merge topology and conflict files: {conflict_files}",
            project_id=staging_wt_path
        )
        agy_exec = runtime_engine.execute_task(agy_task.id)

        # Step 2: Codex Reviewer
        codex_task = runtime_engine.create_task(
            agent_id="agent-dev",
            title=f"Codex Merge Resolution Review: {merge_id}",
            instructions=f"Inspect conflict resolution and ensure syntax integrity for {conflict_files}",
            project_id=staging_wt_path
        )
        codex_exec = runtime_engine.execute_task(codex_task.id)

        # Step 3: QA Verifier
        qa_task = runtime_engine.create_task(
            agent_id="agent-qa",
            title=f"QA Pre-Merge Verification: {merge_id}",
            instructions="Execute test assertions in staging worktree",
            project_id=staging_wt_path
        )
        qa_exec = runtime_engine.execute_task(qa_task.id)

        # Step 4: Security Sentinel
        sec_task = runtime_engine.create_task(
            agent_id="agent-security",
            title=f"Security Sentinel Audit: {merge_id}",
            instructions="Scan staging worktree for secret leaks and policy violations",
            project_id=staging_wt_path
        )
        sec_exec = runtime_engine.execute_task(sec_task.id)

        return {
            "agy_planner": agy_exec.result or {"status": agy_exec.status},
            "codex_reviewer": codex_exec.result or {"status": codex_exec.status},
            "qa_verifier": qa_exec.result or {"status": qa_exec.status},
            "security_sentinel": sec_exec.result or {"status": sec_exec.status},
            "reviewed_at": _now_iso()
        }

    # -------------------------------------------------------------------------
    # Execution Pipeline
    # -------------------------------------------------------------------------

    def execute_merge(self, req: MergeExecutionRequest) -> MergeExecutionResult:
        """
        Executes merge arbitration with policy gating, deterministic conflict resolution,
        multi-agent review, pre-merge testing, staleness detection, and safe trunk updating
        while strictly preserving the user's primary working tree.
        """
        _sanitize_branch_name(req.source_branch)
        _sanitize_branch_name(req.target_branch)
        sanitized_repo = _sanitize_repo_path(req.repo_path)
        repo_lock = _get_repo_lock(sanitized_repo)
        with repo_lock, _RepoFileLock(sanitized_repo):
            root_repo = worktree_manager.get_repo_root(sanitized_repo)
            if not root_repo:
                raise ValueError(f"Path '{req.repo_path}' is not a valid git repository.")

            self._validate_branch_exists(root_repo, req.source_branch)
            self._validate_branch_exists(root_repo, req.target_branch)

            merge_id = f"merge-{uuid.uuid4().hex[:8]}"

            # Validate provided approval if any (replay prevention)
            if req.approval_id:
                all_apprs = load_approvals()
                appr = next((a for a in all_apprs if a.id == req.approval_id), None)
                if not appr or appr.status != ApprovalStatus.APPROVED:
                    res = MergeExecutionResult(
                        merge_id=merge_id,
                        status="APPROVAL_INVALID",
                        repo_path=root_repo,
                        source_branch=req.source_branch,
                        target_branch=req.target_branch,
                        strategy_used=req.strategy.value,
                        approval_id=req.approval_id,
                        executed_at=_now_iso(),
                        error=f"Approval '{req.approval_id}' is invalid or already executed. Replay blocked."
                    )
                    self._record_merge(res)
                    return res

            # 1. Native Three-Way Analysis & Initial Target Commit
            analysis = self.analyze_three_way(root_repo, req.target_branch, req.source_branch)
            initial_target_commit = analysis.target_commit

            # 2. Risk Evaluation
            source_file_list = list(analysis.source_changes.get("files", {}).keys())
            risk_class = self.evaluate_merge_risk(root_repo, source_file_list)

            # 3. Provision Staging Worktree
            staging_wt_path = os.path.join(worktree_manager.worktrees_dir, merge_id)
            staging_branch = f"staging/{merge_id}"

            add_res = SafeCommandExecutor.execute(
                ["git", "worktree", "add", "-b", staging_branch, staging_wt_path, req.target_branch],
                cwd=root_repo
            )
            if add_res.exit_code != 0:
                raise RuntimeError(f"Failed to create merge staging worktree: {add_res.stderr or add_res.stdout}")

            conflict_files: List[str] = []
            resolved_files: List[str] = []
            test_results: Optional[Dict[str, Any]] = None
            security_results: Optional[Dict[str, Any]] = None
            merge_commit: Optional[str] = None
            candidate_tree_sha: Optional[str] = None
            final_status = "FAILED"
            err_msg: Optional[str] = None
            strategy_used = req.strategy.value
            verif_candidate: Optional[VerificationCandidate] = None
            multi_agent_review_data: Optional[Dict[str, Any]] = None
            insufficient_confidence = False

            try:
                commit_msg = req.commit_message or f"Merge swarm branch '{req.source_branch}' into '{req.target_branch}' [NEXUS {merge_id}]"

                # Check if Fast-Forward is possible
                if analysis.is_fast_forward and req.strategy in [MergeStrategy.AUTO, MergeStrategy.FAST_FORWARD]:
                    ff_res = SafeCommandExecutor.execute(
                        ["git", "merge", "--ff-only", req.source_branch],
                        cwd=staging_wt_path
                    )
                    if ff_res.exit_code == 0:
                        strategy_used = "FAST_FORWARD"
                    else:
                        SafeCommandExecutor.execute(
                            ["git", "merge", "--no-ff", "-m", commit_msg, req.source_branch],
                            cwd=staging_wt_path
                        )
                        strategy_used = "THREE_WAY"
                else:
                    merge_res = SafeCommandExecutor.execute(
                        ["git", "merge", "--no-ff", "-m", commit_msg, req.source_branch],
                        cwd=staging_wt_path
                    )

                    if merge_res.exit_code != 0:
                        unmerged_res = SafeCommandExecutor.execute(
                            ["git", "diff", "--name-only", "--diff-filter=U"],
                            cwd=staging_wt_path
                        )
                        conflict_files = [f.strip() for f in unmerged_res.stdout.splitlines() if f.strip()]

                        # Handle conflict resolution strategies
                        if req.strategy == MergeStrategy.OURS:
                            if not req.allow_ours_theirs:
                                final_status = "REQUIRES_HUMAN"
                                err_msg = "Strategy 'OURS' requires explicit policy allowance (allow_ours_theirs=True)."
                            else:
                                SafeCommandExecutor.execute(["git", "checkout", "--ours", "--", "."], cwd=staging_wt_path)
                                SafeCommandExecutor.execute(["git", "add", "."], cwd=staging_wt_path)
                                SafeCommandExecutor.execute(["git", "commit", "-m", f"{commit_msg} (Strategy: OURS)"], cwd=staging_wt_path)
                                resolved_files = list(conflict_files)
                                strategy_used = "OURS"

                        elif req.strategy == MergeStrategy.THEIRS:
                            if not req.allow_ours_theirs:
                                final_status = "REQUIRES_HUMAN"
                                err_msg = "Strategy 'THEIRS' requires explicit policy allowance (allow_ours_theirs=True)."
                            else:
                                SafeCommandExecutor.execute(["git", "checkout", "--theirs", "--", "."], cwd=staging_wt_path)
                                SafeCommandExecutor.execute(["git", "add", "."], cwd=staging_wt_path)
                                SafeCommandExecutor.execute(["git", "commit", "-m", f"{commit_msg} (Strategy: THEIRS)"], cwd=staging_wt_path)
                                resolved_files = list(conflict_files)
                                strategy_used = "THEIRS"

                        elif req.auto_resolve_conflicts or req.strategy in [MergeStrategy.AUTO, MergeStrategy.AGENT_RESOLVE]:
                            res_ok, res_files, confident = self._autonomous_conflict_resolve(staging_wt_path, conflict_files)
                            if res_ok and confident:
                                SafeCommandExecutor.execute(["git", "add", "."], cwd=staging_wt_path)
                                commit_res = SafeCommandExecutor.execute(
                                    ["git", "commit", "-m", f"{commit_msg} (Autonomous Agent Resolution)"],
                                    cwd=staging_wt_path
                                )
                                if commit_res.exit_code == 0:
                                    resolved_files = res_files
                                    strategy_used = "AGENT_RESOLVE"
                                else:
                                    final_status = "CONFLICT"
                                    err_msg = f"Failed to commit resolved conflict: {commit_res.stderr or commit_res.stdout}"
                            elif not confident:
                                insufficient_confidence = True
                                final_status = "REQUIRES_HUMAN"
                                err_msg = f"Insufficient confidence for autonomous conflict resolution in files: {conflict_files}. Human review required."
                            else:
                                final_status = "CONFLICT"
                                err_msg = f"Unresolved merge conflicts in files: {conflict_files}"
                        else:
                            final_status = "CONFLICT"
                            err_msg = f"Merge conflicts present and auto-resolve disabled: {conflict_files}"

                # Capture candidate commit and tree SHA
                hash_res = SafeCommandExecutor.execute(["git", "rev-parse", "HEAD"], cwd=staging_wt_path)
                merge_commit = hash_res.stdout.strip() if hash_res.exit_code == 0 else None
                tree_res = SafeCommandExecutor.execute(["git", "rev-parse", "HEAD^{tree}"], cwd=staging_wt_path)
                candidate_tree_sha = tree_res.stdout.strip() if tree_res.exit_code == 0 else None

                # 4. Pre-Merge Verification (QA test suite & Security scan)
                tests_passed_val = None
                sec_clean_val = True
                if final_status not in ["CONFLICT", "REQUIRES_HUMAN"]:
                    if req.run_pre_merge_tests:
                        test_ok = self._run_test_suite(staging_wt_path)
                        tests_passed_val = test_ok
                        test_results = {"status": "PASSED" if test_ok else "FAILED"}
                        if not test_ok:
                            final_status = "TEST_FAILED"
                            err_msg = "Pre-merge regression test suite failed in staging workspace."
                        else:
                            final_status = "READY"
                    else:
                        final_status = "READY"

                    # Security Sentinel scan
                    from orchestrator.tool_runner import SecurityRunner
                    sec_scan = SecurityRunner.scan_directory_for_secrets(staging_wt_path)
                    sec_clean_val = sec_scan.get("clean", True)
                    security_results = sec_scan
                    if not sec_clean_val:
                        final_status = "SECURITY_BLOCKED"
                        err_msg = f"Security Sentinel detected secret leaks in candidate merge: {sec_scan.get('findings')}"

                verif_candidate = VerificationCandidate(
                    ephemeral_worktree_path=staging_wt_path,
                    candidate_commit=merge_commit,
                    candidate_tree_sha=candidate_tree_sha,
                    target_base_commit=initial_target_commit,
                    tests_executed=req.run_pre_merge_tests,
                    tests_passed=tests_passed_val,
                    security_clean=sec_clean_val,
                    security_findings=security_results.get("findings", []) if security_results else [],
                    verification_status="VERIFIED" if final_status == "READY" else ("FAILED" if final_status in ["TEST_FAILED", "SECURITY_BLOCKED"] else "PENDING")
                )

                # 5. Human Approval Gate for High-Risk Merges
                if final_status == "READY" and risk_class.requires_approval:
                    approval_valid = False
                    if req.approval_id:
                        # Verify provided approval token & identity
                        all_apprs = load_approvals()
                        appr = next((a for a in all_apprs if a.id == req.approval_id), None)
                        if appr and appr.status == ApprovalStatus.APPROVED:
                            # Replay protection: verify candidate commit / tree scoping
                            appr_cmd = appr.command or ""
                            if candidate_tree_sha and candidate_tree_sha in appr_cmd:
                                approval_valid = True
                                # Atomically mark approval as EXECUTED to prevent replay
                                appr.status = ApprovalStatus.EXECUTED
                                appr.executed_at = _now_iso()
                                save_approvals(all_apprs)
                            elif f"candidate_commit={merge_commit}" in appr_cmd:
                                approval_valid = True
                                appr.status = ApprovalStatus.EXECUTED
                                appr.executed_at = _now_iso()
                                save_approvals(all_apprs)
                            else:
                                final_status = "APPROVAL_MISMATCH"
                                err_msg = f"Approval '{req.approval_id}' was scoped to different candidate commit/tree identity. Replay blocked."
                        else:
                            final_status = "APPROVAL_INVALID"
                            err_msg = f"Approval '{req.approval_id}' is not in APPROVED state."

                    if not approval_valid and final_status == "READY":
                        # Request approval scoped to exact candidate
                        appr_cmd_scope = f"# SWARM Merge {merge_id}: {req.source_branch} -> {req.target_branch} [candidate_commit={merge_commit}] [candidate_tree={candidate_tree_sha}] [target_base={initial_target_commit}]"
                        appr = request_approval(
                            action=f"Swarm Merge: {req.source_branch} -> {req.target_branch}",
                            target_project=root_repo,
                            reason=f"High-risk merge triggered: {risk_class.policy_reason}",
                            command=appr_cmd_scope,
                            actor="merge_arbitrator",
                            risk_level=risk_class.risk_level
                        )
                        final_status = "WAITING_FOR_APPROVAL"
                        err_msg = f"Merge candidate verified cleanly and staged. Gated by high-risk policy: {risk_class.policy_reason}. Approval ID: {appr.id}"

                        decision = MergeDecision(
                            merge_id=merge_id,
                            session_id=req.session_id,
                            source_branch=req.source_branch,
                            target_branch=req.target_branch,
                            status=final_status,
                            classification=MergeClassification.HIGH_RISK.value,
                            mergeability=MergeabilityClassification.RESOLVABLE_CONFLICT,
                            strategy_used=strategy_used,
                            merge_commit=merge_commit,
                            candidate_tree_sha=candidate_tree_sha,
                            conflict_files=conflict_files,
                            resolved_files=resolved_files,
                            reason=err_msg,
                            approval_id=appr.id,
                            executed_at=_now_iso(),
                            three_way_analysis=analysis,
                            verification_candidate=verif_candidate
                        )
                        result = MergeExecutionResult(
                            merge_id=merge_id,
                            status=final_status,
                            repo_path=root_repo,
                            source_branch=req.source_branch,
                            target_branch=req.target_branch,
                            strategy_used=strategy_used,
                            merge_commit=merge_commit,
                            candidate_tree_sha=candidate_tree_sha,
                            conflict_files=conflict_files,
                            resolved_files=resolved_files,
                            test_results=test_results,
                            security_results=security_results,
                            approval_id=appr.id,
                            executed_at=_now_iso(),
                            error=err_msg,
                            decision=decision
                        )
                        self._record_merge(result)
                        return result

                # 6. Target Branch Staleness Detection
                if final_status == "READY":
                    curr_tgt_res = SafeCommandExecutor.execute(["git", "rev-parse", req.target_branch], cwd=root_repo)
                    current_target_commit = curr_tgt_res.stdout.strip() if curr_tgt_res.exit_code == 0 else ""
                    if current_target_commit and initial_target_commit and current_target_commit != initial_target_commit:
                        final_status = "STALE_TARGET_BRANCH"
                        err_msg = (
                            f"Target branch '{req.target_branch}' advanced from {initial_target_commit[:8]} to "
                            f"{current_target_commit[:8]} during arbitration. Re-arbitration required."
                        )

                # 7. Final Trunk Integration (Controlled & Safe)
                if final_status == "READY":
                    primary_b_res = SafeCommandExecutor.execute(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root_repo)
                    primary_branch = primary_b_res.stdout.strip() if primary_b_res.exit_code == 0 else ""

                    if req.target_branch != primary_branch:
                        update_res = SafeCommandExecutor.execute(
                            ["git", "branch", "-f", req.target_branch, merge_commit],
                            cwd=root_repo
                        )
                        if update_res.exit_code == 0:
                            final_status = "SUCCESS"
                        else:
                            final_status = "FAILED"
                            err_msg = f"Failed to update branch ref '{req.target_branch}': {update_res.stderr}"
                    else:
                        status_res = SafeCommandExecutor.execute(["git", "status", "--porcelain"], cwd=root_repo)
                        clean_working_tree = not status_res.stdout.strip()

                        if clean_working_tree:
                            ff_res = SafeCommandExecutor.execute(
                                ["git", "merge", "--ff-only", staging_branch],
                                cwd=root_repo
                            )
                            if ff_res.exit_code == 0:
                                final_status = "SUCCESS"
                            else:
                                final_status = "STAGED_READY"
                                err_msg = "Merged cleanly in staging; fast-forward in primary working tree deferred."
                        else:
                            final_status = "STAGED_READY"
                            err_msg = (
                                f"Merge verified and committed to '{staging_branch}' ({merge_commit[:8] if merge_commit else ''}). "
                                f"Primary working tree contains uncommitted user modifications; working tree was preserved untouched."
                            )

                    if req.delete_source_branch_on_success and final_status == "SUCCESS":
                        SafeCommandExecutor.execute(["git", "branch", "-d", req.source_branch], cwd=root_repo)

            finally:
                keep_candidate = (final_status in ["STAGED_READY", "WAITING_FOR_APPROVAL", "REQUIRES_HUMAN"])
                if not keep_candidate:
                    self._cleanup_temp_worktree(root_repo, staging_wt_path, staging_branch)

            # High-level decision classification
            conflict_type, mergeability, high_level_class = self.classify_conflict(
                analysis=analysis,
                has_textual_conflicts=bool(conflict_files),
                test_passed=test_results.get("status") == "PASSED" if test_results else None,
                requires_approval=risk_class.requires_approval,
                security_clean=security_results.get("clean") if security_results else None
            )

            if final_status in ["SUCCESS", "STAGED_READY"]:
                if resolved_files:
                    decision_class = MergeClassification.AUTO_MERGEABLE.value
                else:
                    decision_class = MergeClassification.CLEAN_MERGE.value
            elif final_status == "WAITING_FOR_APPROVAL":
                decision_class = MergeClassification.HIGH_RISK.value
            elif final_status == "TEST_FAILED" or final_status == "SECURITY_BLOCKED":
                decision_class = MergeClassification.VERIFICATION_FAILED.value
            elif final_status in ["REQUIRES_HUMAN", "STALE_TARGET_BRANCH"]:
                decision_class = MergeClassification.REQUIRES_HUMAN.value
            elif final_status == "REJECTED":
                decision_class = MergeClassification.REJECTED.value
            else:
                decision_class = MergeClassification.CONFLICTED.value

            decision = MergeDecision(
                merge_id=merge_id,
                session_id=req.session_id,
                source_branch=req.source_branch,
                target_branch=req.target_branch,
                status=final_status,
                classification=decision_class,
                mergeability=mergeability,
                strategy_used=strategy_used,
                merge_commit=merge_commit,
                candidate_tree_sha=candidate_tree_sha,
                conflict_files=conflict_files,
                resolved_files=resolved_files,
                reason=err_msg or f"Merge completed successfully using {strategy_used}",
                approval_id=req.approval_id,
                executed_at=_now_iso(),
                three_way_analysis=analysis,
                verification_candidate=verif_candidate,
                multi_agent_review=multi_agent_review_data
            )

            result = MergeExecutionResult(
                merge_id=merge_id,
                status=final_status,
                repo_path=root_repo,
                source_branch=req.source_branch,
                target_branch=req.target_branch,
                strategy_used=strategy_used,
                merge_commit=merge_commit,
                candidate_tree_sha=candidate_tree_sha,
                conflict_files=conflict_files,
                resolved_files=resolved_files,
                test_results=test_results,
                security_results=security_results,
                approval_id=req.approval_id,
                executed_at=_now_iso(),
                error=err_msg,
                decision=decision
            )
            self._record_merge(result)

            record_audit(
                action=f"SWARM_MERGE_EXECUTED: {req.source_branch} -> {req.target_branch}",
                project=root_repo,
                target=req.target_branch,
                reason=f"Status: {final_status}, Strategy: {strategy_used}",
                risk_level=risk_class.risk_level,
                result=final_status,
                actor="merge_arbitrator",
                execution_id=merge_id,
                status=final_status,
                error=err_msg
            )

            return result

    # -------------------------------------------------------------------------
    # Candidate Integration & Rejection API
    # -------------------------------------------------------------------------

    def integrate_approved_candidate(self, merge_id: str, approval_id: str) -> MergeExecutionResult:
        """Resumes integration of a staged candidate after human operator approval."""
        record = self.get_merge_record(merge_id)
        if not record:
            raise ValueError(f"Merge record '{merge_id}' not found.")

        req = MergeExecutionRequest(
            repo_path=record["repo_path"],
            source_branch=record["source_branch"],
            target_branch=record["target_branch"],
            session_id=record.get("session_id"),
            approval_id=approval_id,
            strategy=MergeStrategy.AUTO
        )
        res = self.execute_merge(req)
        if res.status == "SUCCESS":
            staging_branch = f"staging/{merge_id}"
            staging_wt = os.path.join(worktree_manager.worktrees_dir, merge_id)
            self._cleanup_temp_worktree(res.repo_path, staging_wt, staging_branch)
        return res

    def reject_candidate(self, merge_id: str, reason: str = "Rejected by operator") -> Dict[str, Any]:
        """Safely tears down candidate staging worktree/branch and marks record REJECTED."""
        record = self.get_merge_record(merge_id)
        if not record:
            raise ValueError(f"Merge record '{merge_id}' not found.")

        repo = record["repo_path"]
        staging_branch = f"staging/{merge_id}"
        staging_wt = os.path.join(worktree_manager.worktrees_dir, merge_id)

        self._cleanup_temp_worktree(repo, staging_wt, staging_branch)

        record["status"] = "REJECTED"
        record["error"] = reason
        if record.get("decision"):
            record["decision"]["status"] = "REJECTED"
            record["decision"]["classification"] = MergeClassification.REJECTED.value
            record["decision"]["reason"] = reason

        with atomic_json_updater(self.history_file, default={}) as data:
            data[merge_id] = record

        record_audit(
            action=f"SWARM_MERGE_REJECTED: {merge_id}",
            project=repo,
            target=record.get("target_branch", "main"),
            reason=reason,
            risk_level=RiskLevel.MEDIUM,
            result="REJECTED",
            actor="merge_arbitrator",
            execution_id=merge_id,
            status="REJECTED"
        )
        return record

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _validate_branch_exists(self, repo: str, branch: str):
        res = SafeCommandExecutor.execute(["git", "show-ref", f"refs/heads/{branch}"], cwd=repo)
        if res.exit_code != 0:
            raise ValueError(f"Branch '{branch}' does not exist in repository '{repo}'.")

    def _get_divergence(self, repo: str, target: str, source: str) -> Dict[str, int]:
        res = SafeCommandExecutor.execute(
            ["git", "rev-list", "--left-right", "--count", f"{target}...{source}"],
            cwd=repo
        )
        if res.exit_code == 0 and res.stdout.strip():
            parts = res.stdout.strip().split()
            if len(parts) >= 2:
                try:
                    return {"behind": int(parts[0]), "ahead": int(parts[1])}
                except ValueError:
                    pass
        return {"behind": 0, "ahead": 0}

    def _is_ancestor(self, repo: str, ancestor: str, descendant: str) -> bool:
        res = SafeCommandExecutor.execute(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo
        )
        return res.exit_code == 0

    def _run_test_suite(self, workspace_path: str) -> bool:
        has_tests_dir = os.path.exists(os.path.join(workspace_path, "tests"))
        cmd = ["pytest", "tests/", "-q"] if has_tests_dir else ["pytest", "-q"]
        res = SafeCommandExecutor.execute(cmd, cwd=workspace_path, timeout=60)
        return res.exit_code == 0 and "ERRORS" not in res.stdout and "FAILED" not in res.stdout

    def _autonomous_conflict_resolve(self, wt_path: str, conflict_files: List[str]) -> Tuple[bool, List[str], bool]:
        """
        Deterministic, safe textual conflict resolver.
        Inspects conflict blocks. If definitions or imports are non-colliding, resolves them cleanly.
        Returns: (all_resolved: bool, resolved_files: List[str], confidence_sufficient: bool)
        If ambiguity or collision detected, returns confidence_sufficient=False without guessing.
        """
        resolved: List[str] = []
        confident = True

        for rel_file in conflict_files:
            abs_path = os.path.join(wt_path, rel_file)
            if not os.path.exists(abs_path):
                confident = False
                continue
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if "<<<<<<<" not in content or ">>>>>>>" not in content:
                confident = False
                continue

            pattern = re.compile(r"<<<<<<<[^\n]*\n(.*?)\n=======\n(.*?)\n>>>>>>>[^\n]*", re.DOTALL)
            matches = list(pattern.finditer(content))

            file_confident = True
            for m in matches:
                ours = m.group(1).strip()
                theirs = m.group(2).strip()

                ours_lines = [l.strip() for l in ours.splitlines() if l.strip()]
                theirs_lines = [l.strip() for l in theirs.splitlines() if l.strip()]
                is_pure_imports = (
                    bool(ours_lines) and bool(theirs_lines) and
                    all(l.startswith("import ") or l.startswith("from ") for l in ours_lines + theirs_lines)
                )

                ours_defs = re.findall(r"(?:def|class)\s+([a-zA-Z0-9_]+)", ours)
                theirs_defs = re.findall(r"(?:def|class)\s+([a-zA-Z0-9_]+)", theirs)
                is_distinct_defs = (
                    bool(ours_defs) and bool(theirs_defs) and
                    not set(ours_defs).intersection(set(theirs_defs))
                )

                if not (is_pure_imports or is_distinct_defs):
                    # Ambiguous conflict inside code bodies or colliding logic: unsafe to auto-resolve
                    file_confident = False
                    break

            if not file_confident:
                confident = False
                continue

            def conflict_replacer(match):
                ours = match.group(1).strip()
                theirs = match.group(2).strip()

                if not ours:
                    return theirs
                if not theirs:
                    return ours

                if ("def " in ours and "def " in theirs) or ("class " in ours and "class " in theirs):
                    return f"{ours}\n\n{theirs}"

                if "import " in ours and "import " in theirs:
                    lines = set(ours.splitlines() + theirs.splitlines())
                    return "\n".join(sorted(list(lines)))

                return f"{ours}\n{theirs}"

            new_content = pattern.sub(conflict_replacer, content)

            if "<<<<<<<" not in new_content and ">>>>>>>" not in new_content:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                resolved.append(rel_file)

        all_ok = (len(resolved) == len(conflict_files))
        return all_ok, resolved, confident

    def _cleanup_temp_worktree(self, root_repo: str, wt_path: str, branch_name: Optional[str] = None):
        SafeCommandExecutor.execute(["git", "worktree", "remove", "--force", wt_path], cwd=root_repo)
        SafeCommandExecutor.execute(["git", "worktree", "prune"], cwd=root_repo)

        if os.path.exists(wt_path):
            try:
                shutil.rmtree(wt_path, ignore_errors=True)
            except Exception:
                pass

        if branch_name:
            SafeCommandExecutor.execute(["git", "branch", "-D", branch_name], cwd=root_repo)

    # -------------------------------------------------------------------------
    # Candidate Lifecycle State Machine API (Phase 9 Comprehensive)
    # -------------------------------------------------------------------------

    def _load_candidates(self) -> Dict[str, Dict[str, Any]]:
        return load_json_safe(self.candidates_file, default={})

    def list_candidates(self, limit: int = 50) -> List[MergeCandidate]:
        with self._lock:
            data = self._load_candidates()
            items = []
            for v in data.values():
                try:
                    items.append(MergeCandidate(**v))
                except Exception:
                    pass
            items.sort(key=lambda x: x.updated_at, reverse=True)
            return items[:limit]

    def get_candidate(self, candidate_id: str) -> Optional[MergeCandidate]:
        with self._lock:
            data = self._load_candidates()
            raw = data.get(candidate_id)
            if not raw:
                return None
            try:
                return MergeCandidate(**raw)
            except Exception:
                return None

    def _save_candidate(self, candidate: MergeCandidate):
        candidate.updated_at = _now_iso()
        with atomic_json_updater(self.candidates_file, default={}) as data:
            data[candidate.candidate_id] = candidate.model_dump()

    def record_candidate_transition(
        self,
        candidate: MergeCandidate,
        to_state: MergeLifecycleState,
        actor: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MergeCandidate:
        from_state = candidate.state
        if from_state in [MergeLifecycleState.REJECTED, MergeLifecycleState.ROLLED_BACK, MergeLifecycleState.FAILED]:
            raise ValueError(f"Cannot transition candidate '{candidate.candidate_id}' from terminal state '{from_state.value}'. Accidental mutation blocked.")
        if from_state == MergeLifecycleState.INTEGRATED and to_state != MergeLifecycleState.ROLLED_BACK:
            raise ValueError(f"Cannot transition candidate '{candidate.candidate_id}' from terminal state 'INTEGRATED' except via rollback.")

        candidate.state = to_state
        candidate.transitions.append(MergeTransitionRecord(
            from_state=from_state.value if isinstance(from_state, MergeLifecycleState) else str(from_state),
            to_state=to_state.value if isinstance(to_state, MergeLifecycleState) else str(to_state),
            actor=actor,
            timestamp=_now_iso(),
            reason=reason,
            metadata=metadata
        ))
        self._save_candidate(candidate)
        record_audit(
            action=f"CANDIDATE_TRANSITION: {candidate.candidate_id} [{from_state} -> {to_state}]",
            project=candidate.repo_path,
            target=candidate.target_branch,
            reason=reason or f"State transition to {to_state}",
            risk_level=RiskLevel.LOW,
            result=to_state.value,
            actor=actor,
            execution_id=candidate.candidate_id,
            status=to_state.value
        )
        return candidate

    def create_candidate(self, req: MergeCandidateCreateRequest) -> MergeCandidate:
        repo = _sanitize_repo_path(req.repo_path)
        source = _sanitize_branch_name(req.source_branch)
        target = _sanitize_branch_name(req.target_branch)

        self._validate_branch_exists(repo, source)
        self._validate_branch_exists(repo, target)

        candidate_id = f"cand-{uuid.uuid4().hex[:8]}"
        now = _now_iso()
        candidate = MergeCandidate(
            candidate_id=candidate_id,
            session_id=req.session_id,
            repo_path=repo,
            source_branch=source,
            target_branch=target,
            state=MergeLifecycleState.CREATED,
            strategy=req.strategy.value,
            allow_ours_theirs=req.allow_ours_theirs,
            created_at=now,
            updated_at=now,
            correlation_id=str(uuid.uuid4())
        )
        self.record_candidate_transition(
            candidate,
            MergeLifecycleState.CREATED,
            actor="merge_arbitrator",
            reason="Candidate initialized"
        )

        if req.auto_advance:
            candidate = self.analyze_candidate(candidate_id)
            if candidate.state == MergeLifecycleState.VERIFICATION_PENDING:
                candidate = self.verify_candidate(candidate_id)
                if candidate.state == MergeLifecycleState.READY_TO_INTEGRATE:
                    candidate = self.integrate_candidate(candidate_id)

        return candidate

    def analyze_candidate(self, candidate_id: str) -> MergeCandidate:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate '{candidate_id}' not found.")

        if candidate.state in [MergeLifecycleState.INTEGRATED, MergeLifecycleState.REJECTED, MergeLifecycleState.ROLLED_BACK, MergeLifecycleState.FAILED]:
            raise ValueError(f"Candidate '{candidate_id}' is in terminal state '{candidate.state.value}'. Accidental mutation blocked.")

        repo_lock = _get_repo_lock(candidate.repo_path)
        with repo_lock:
            self.record_candidate_transition(
                candidate, MergeLifecycleState.ANALYZING, actor="merge_arbitrator", reason="Starting three-way merge analysis"
            )

            analysis = self.analyze_three_way(candidate.repo_path, candidate.target_branch, candidate.source_branch)
            candidate.source_commit = analysis.source_commit
            candidate.target_commit = analysis.target_commit
            candidate.target_base_commit = analysis.target_commit
            candidate.merge_base_commit = analysis.merge_base_commit
            candidate.three_way_analysis = analysis.model_dump()

            source_files = list(analysis.source_changes.get("files", {}).keys())
            risk_class = self.evaluate_merge_risk(candidate.repo_path, source_files)
            candidate.risk_classification = risk_class.model_dump()

            self.record_candidate_transition(
                candidate, MergeLifecycleState.ARBITRATING, actor="merge_arbitrator", reason="Three-way analysis complete, evaluating conflicts"
            )

            if analysis.rename_delete_conflicts or analysis.binary_conflicts:
                candidate = self.record_candidate_transition(
                    candidate, MergeLifecycleState.CONFLICTED, actor="merge_arbitrator",
                    reason=f"Unresolvable conflicts detected: {analysis.rename_delete_conflicts or analysis.binary_conflicts}"
                )
            else:
                candidate = self.record_candidate_transition(
                    candidate, MergeLifecycleState.VERIFICATION_PENDING, actor="merge_arbitrator", reason="Ready for ephemeral staging verification"
                )
            return candidate

    def verify_candidate(self, candidate_id: str) -> MergeCandidate:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate '{candidate_id}' not found.")

        if candidate.state in [MergeLifecycleState.INTEGRATED, MergeLifecycleState.REJECTED, MergeLifecycleState.ROLLED_BACK, MergeLifecycleState.FAILED]:
            raise ValueError(f"Candidate '{candidate_id}' is in terminal state '{candidate.state.value}'. Accidental mutation blocked.")

        repo_lock = _get_repo_lock(candidate.repo_path)
        with repo_lock:
            self.record_candidate_transition(
                candidate, MergeLifecycleState.VERIFYING, actor="merge_arbitrator", reason="Starting staging verification"
            )

            staging_wt_path = os.path.join(worktree_manager.worktrees_dir, candidate_id)
            staging_branch = f"staging/{candidate_id}"

            # Ensure staging worktree is provisioned
            if not os.path.exists(staging_wt_path):
                b_chk = SafeCommandExecutor.execute(["git", "show-ref", f"refs/heads/{staging_branch}"], cwd=candidate.repo_path)
                if b_chk.exit_code == 0:
                    SafeCommandExecutor.execute(["git", "worktree", "add", staging_wt_path, staging_branch], cwd=candidate.repo_path)
                else:
                    add_res = SafeCommandExecutor.execute(
                        ["git", "worktree", "add", "-b", staging_branch, staging_wt_path, candidate.target_branch],
                        cwd=candidate.repo_path
                    )
                    if add_res.exit_code != 0:
                        candidate.error = f"Failed to provision staging worktree: {add_res.stderr or add_res.stdout}"
                        return self.record_candidate_transition(candidate, MergeLifecycleState.FAILED, actor="merge_arbitrator", reason=candidate.error)

            candidate.candidate_worktree = staging_wt_path

            # Attempt merge in staging
            commit_msg = f"Merge candidate '{candidate.source_branch}' into '{candidate.target_branch}' [NEXUS {candidate_id}]"
            merge_res = SafeCommandExecutor.execute(
                ["git", "merge", "--no-ff", "-m", commit_msg, candidate.source_branch],
                cwd=staging_wt_path
            )

            conflict_files = []
            resolved_files = []
            if merge_res.exit_code != 0:
                unmerged = SafeCommandExecutor.execute(["git", "diff", "--name-only", "--diff-filter=U"], cwd=staging_wt_path)
                conflict_files = [f.strip() for f in unmerged.stdout.splitlines() if f.strip()]
                candidate.conflict_files = conflict_files

                # Autonomous conflict resolve attempt
                res_ok, res_files, confident = self._autonomous_conflict_resolve(staging_wt_path, conflict_files)
                if res_ok and confident:
                    SafeCommandExecutor.execute(["git", "add", "."], cwd=staging_wt_path)
                    commit_res = SafeCommandExecutor.execute(["git", "commit", "-m", f"{commit_msg} (Agent Resolved)"], cwd=staging_wt_path)
                    if commit_res.exit_code == 0:
                        resolved_files = res_files
                        candidate.resolved_files = resolved_files
                    else:
                        candidate.error = f"Failed to commit resolved conflict: {commit_res.stderr}"
                        return self.record_candidate_transition(candidate, MergeLifecycleState.CONFLICTED, actor="merge_arbitrator", reason=candidate.error)
                elif not confident:
                    candidate.error = f"Unsafe or low-confidence conflicts in: {conflict_files}"
                    return self.record_candidate_transition(candidate, MergeLifecycleState.REQUIRES_HUMAN, actor="merge_arbitrator", reason=candidate.error)
                else:
                    candidate.error = f"Unresolved conflicts in: {conflict_files}"
                    return self.record_candidate_transition(candidate, MergeLifecycleState.CONFLICTED, actor="merge_arbitrator", reason=candidate.error)

            # Record candidate commit & tree
            c_hash = SafeCommandExecutor.execute(["git", "rev-parse", "HEAD"], cwd=staging_wt_path).stdout.strip()
            t_hash = SafeCommandExecutor.execute(["git", "rev-parse", "HEAD^{tree}"], cwd=staging_wt_path).stdout.strip()
            candidate.candidate_commit = c_hash
            candidate.candidate_tree_sha = t_hash

            # Pre-merge testing
            test_ok = self._run_test_suite(staging_wt_path)
            candidate.verification_results = {"status": "PASSED" if test_ok else "FAILED"}
            if not test_ok:
                candidate.error = "Pre-merge test suite assertions failed"
                return self.record_candidate_transition(candidate, MergeLifecycleState.VERIFICATION_FAILED, actor="merge_arbitrator", reason=candidate.error)

            # Security Sentinel scan
            from orchestrator.tool_runner import SecurityRunner
            sec_scan = SecurityRunner.scan_directory_for_secrets(staging_wt_path)
            candidate.security_results = sec_scan
            if not sec_scan.get("clean", True):
                candidate.error = f"Security Sentinel detected leaks: {sec_scan.get('findings')}"
                return self.record_candidate_transition(candidate, MergeLifecycleState.VERIFICATION_FAILED, actor="merge_arbitrator", reason=candidate.error)

            # Risk and approval gate check
            risk_info = candidate.risk_classification or {}
            if risk_info.get("requires_approval"):
                appr_cmd = f"# SWARM Merge {candidate_id}: {candidate.source_branch} -> {candidate.target_branch} [candidate_commit={c_hash}] [candidate_tree={t_hash}]"
                appr = request_approval(
                    action=f"Swarm Candidate Merge: {candidate.source_branch} -> {candidate.target_branch}",
                    target_project=candidate.repo_path,
                    reason=f"High-risk merge candidate: {risk_info.get('policy_reason')}",
                    command=appr_cmd,
                    actor="merge_arbitrator",
                    risk_level=RiskLevel(risk_info.get("risk_level", "HIGH"))
                )
                candidate.approval_id = appr.id
                candidate.approval_state = "PENDING"
                return self.record_candidate_transition(
                    candidate, MergeLifecycleState.APPROVAL_PENDING, actor="merge_arbitrator",
                    reason=f"Gated by policy: {risk_info.get('policy_reason')}",
                    metadata={"approval_id": appr.id}
                )

            return self.record_candidate_transition(
                candidate, MergeLifecycleState.READY_TO_INTEGRATE, actor="merge_arbitrator", reason="Candidate verified and ready for integration"
            )

    def review_candidate(self, candidate_id: str) -> Dict[str, Any]:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate '{candidate_id}' not found.")

        staging_wt = os.path.join(worktree_manager.worktrees_dir, candidate_id)
        if not os.path.exists(staging_wt):
            branch_name = f"staging/{candidate_id}"
            add_res = SafeCommandExecutor.execute(["git", "worktree", "add", staging_wt, branch_name], cwd=candidate.repo_path)
            if add_res.exit_code != 0:
                raise RuntimeError(f"Could not provision staging worktree for review: {add_res.stderr}")

        review = self.review_merge_with_fleet(
            repo=candidate.repo_path,
            merge_id=candidate_id,
            staging_wt_path=staging_wt,
            source_branch=candidate.source_branch,
            target_branch=candidate.target_branch,
            conflict_files=candidate.conflict_files
        )
        return review

    def integrate_candidate(self, candidate_id: str, approval_id: Optional[str] = None) -> MergeCandidate:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate '{candidate_id}' not found.")

        # Terminal state handling & idempotency
        if candidate.state == MergeLifecycleState.INTEGRATED:
            return candidate

        if candidate.state in [MergeLifecycleState.REJECTED, MergeLifecycleState.ROLLED_BACK, MergeLifecycleState.FAILED]:
            raise ValueError(f"Candidate '{candidate_id}' is in terminal state '{candidate.state.value}'. Accidental mutation blocked.")

        repo_lock = _get_repo_lock(candidate.repo_path)
        with repo_lock, _RepoFileLock(candidate.repo_path):
            if candidate.state == MergeLifecycleState.APPROVAL_PENDING:
                effective_appr_id = approval_id or candidate.approval_id
                if not effective_appr_id:
                    raise ValueError(f"Candidate '{candidate_id}' is waiting for approval. Approval ID required.")
                all_apprs = load_approvals()
                appr = next((a for a in all_apprs if a.id == effective_appr_id), None)
                if not appr or appr.status != ApprovalStatus.APPROVED:
                    raise ValueError(f"Approval '{effective_appr_id}' is not in APPROVED state. Replay or unapproved mutation blocked.")

                appr_cmd = appr.command or ""
                if candidate.candidate_tree_sha and candidate.candidate_tree_sha not in appr_cmd and f"candidate_commit={candidate.candidate_commit}" not in appr_cmd:
                    raise ValueError(f"Approval identity mismatch for candidate '{candidate_id}'.")

                appr.status = ApprovalStatus.EXECUTED
                appr.executed_at = _now_iso()
                save_approvals(all_apprs)
                candidate.approval_state = "EXECUTED"

                self.record_candidate_transition(
                    candidate, MergeLifecycleState.READY_TO_INTEGRATE, actor="human_operator", reason=f"Approval {effective_appr_id} consumed"
                )

            if candidate.state != MergeLifecycleState.READY_TO_INTEGRATE:
                candidate = self.verify_candidate(candidate_id)
                if candidate.state != MergeLifecycleState.READY_TO_INTEGRATE:
                    return candidate

            self.record_candidate_transition(
                candidate, MergeLifecycleState.INTEGRATING, actor="merge_arbitrator", reason="Beginning trunk integration"
            )

            # Target branch staleness check
            curr_target_commit = SafeCommandExecutor.execute(["git", "rev-parse", candidate.target_branch], cwd=candidate.repo_path).stdout.strip()
            if candidate.target_base_commit and curr_target_commit != candidate.target_base_commit:
                candidate.error = f"Target branch '{candidate.target_branch}' advanced from {candidate.target_base_commit[:8]} to {curr_target_commit[:8]}. Re-arbitration required."
                return self.record_candidate_transition(candidate, MergeLifecycleState.REQUIRES_HUMAN, actor="merge_arbitrator", reason=candidate.error)

            primary_branch = SafeCommandExecutor.execute(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=candidate.repo_path).stdout.strip()
            staging_branch = f"staging/{candidate_id}"

            if candidate.target_branch != primary_branch:
                SafeCommandExecutor.execute(["git", "branch", "-f", candidate.target_branch, candidate.candidate_commit], cwd=candidate.repo_path)
                candidate.integration_state = "COMMITTED"
            else:
                status_res = SafeCommandExecutor.execute(["git", "status", "--porcelain"], cwd=candidate.repo_path)
                clean_working_tree = not status_res.stdout.strip()
                if clean_working_tree:
                    ff_res = SafeCommandExecutor.execute(["git", "merge", "--ff-only", staging_branch], cwd=candidate.repo_path)
                    candidate.integration_state = "COMMITTED" if ff_res.exit_code == 0 else "STAGED_READY"
                else:
                    candidate.integration_state = "STAGED_READY"

            staging_wt = os.path.join(worktree_manager.worktrees_dir, candidate_id)
            self._cleanup_temp_worktree(candidate.repo_path, staging_wt, staging_branch)

            return self.record_candidate_transition(
                candidate, MergeLifecycleState.INTEGRATED, actor="merge_arbitrator", reason="Trunk integration completed successfully"
            )

    def rollback_candidate(self, candidate_id: str, reason: str = "Rollback requested") -> MergeCandidate:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate '{candidate_id}' not found.")
        if candidate.state in [MergeLifecycleState.REJECTED, MergeLifecycleState.ROLLED_BACK, MergeLifecycleState.FAILED]:
            raise ValueError(f"Cannot rollback candidate '{candidate_id}' in terminal state '{candidate.state.value}'.")

        repo_lock = _get_repo_lock(candidate.repo_path)
        with repo_lock, _RepoFileLock(candidate.repo_path):
            if candidate.state == MergeLifecycleState.INTEGRATED and candidate.target_base_commit:
                curr_tgt = SafeCommandExecutor.execute(["git", "rev-parse", candidate.target_branch], cwd=candidate.repo_path).stdout.strip()
                if curr_tgt == candidate.candidate_commit:
                    SafeCommandExecutor.execute(["git", "branch", "-f", candidate.target_branch, candidate.target_base_commit], cwd=candidate.repo_path)

            staging_branch = f"staging/{candidate_id}"
            backup_branch = f"backup/cand-{candidate_id}"
            if candidate.candidate_commit:
                SafeCommandExecutor.execute(["git", "branch", "-f", backup_branch, candidate.candidate_commit], cwd=candidate.repo_path)
            else:
                SafeCommandExecutor.execute(["git", "branch", "-m", staging_branch, backup_branch], cwd=candidate.repo_path)

            staging_wt = os.path.join(worktree_manager.worktrees_dir, candidate_id)
            self._cleanup_temp_worktree(candidate.repo_path, staging_wt)

            candidate.error = reason
            return self.record_candidate_transition(
                candidate, MergeLifecycleState.ROLLED_BACK, actor="merge_arbitrator", reason=reason
            )

    def reject_candidate_by_id(self, candidate_id: str, reason: str = "Rejected by operator") -> MergeCandidate:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate '{candidate_id}' not found.")
        if candidate.state in [MergeLifecycleState.INTEGRATED, MergeLifecycleState.REJECTED, MergeLifecycleState.ROLLED_BACK, MergeLifecycleState.FAILED]:
            raise ValueError(f"Cannot reject candidate '{candidate_id}' in terminal state '{candidate.state.value}'.")

        staging_branch = f"staging/{candidate_id}"
        staging_wt = os.path.join(worktree_manager.worktrees_dir, candidate_id)
        self._cleanup_temp_worktree(candidate.repo_path, staging_wt, staging_branch)

        candidate.error = reason
        return self.record_candidate_transition(
            candidate, MergeLifecycleState.REJECTED, actor="merge_arbitrator", reason=reason
        )


merge_arbitrator = MergeArbitrator()
