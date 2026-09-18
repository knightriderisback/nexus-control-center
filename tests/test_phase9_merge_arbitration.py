"""
NEXUS Phase 9: Swarm Branch Merge Arbitration & Cross-Session Conflict Resolution Suite.
Comprehensive verification covering:
1. Merge divergence & fast-forward evaluation
2. Syntactic conflict detection via ephemeral dry-run worktrees
3. Semantic pre-merge test regression gating (blocking broken code even if git merge is clean)
4. Clean three-way merge execution and branch pointer reconciliation
5. Autonomous conflict arbitration (OURS, THEIRS, and Agent Resolution)
6. Primary working tree preservation when target branch has uncommitted modifications
7. Swarm session auto-merge on completion lifecycle
8. REST API endpoints (/merge/evaluate, /merge/execute, /merge/history)
"""

import os
import shutil
import subprocess
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from server import app
from core.storage import load_json_safe
from models.schemas import (
    MergeStrategy,
    MergeEvaluationRequest,
    MergeExecutionRequest,
    AgyCodexSessionRequest,
    SessionState
)
from orchestrator.merge_arbitrator import MergeArbitrator, merge_arbitrator
from orchestrator.worktree_manager import WorktreeManager, worktree_manager
from orchestrator.session_engine import SessionEngine, session_engine

client = TestClient(app)


def _init_test_git_repo(path: Path) -> str:
    """Helper to initialize an isolated git repository with test fixtures."""
    repo_str = str(path)
    os.makedirs(repo_str, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_str, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "NEXUS Tester"], cwd=repo_str, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@nexus.local"], cwd=repo_str, check=True, capture_output=True)

    with open(os.path.join(repo_str, "calculator.py"), "w", encoding="utf-8") as f:
        f.write("def calculate(a, b):\n    return a + b\n")

    with open(os.path.join(repo_str, "test_calculator.py"), "w", encoding="utf-8") as f:
        f.write("from calculator import calculate\n\ndef test_calculate():\n    assert calculate(2, 3) == 5\n")

    subprocess.run(["git", "add", "."], cwd=repo_str, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial baseline commit"], cwd=repo_str, check=True, capture_output=True)
    return repo_str


# =============================================================================
# 1. Merge Evaluation (Dry-Run, Divergence & Conflict Detection)
# =============================================================================

def test_merge_evaluator_clean_fast_forward(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    # Create feature branch with a clean commit
    subprocess.run(["git", "checkout", "-b", "swarm/feature-ff"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "new_module.py"), "w") as f:
        f.write("def helper(): return True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add helper"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeEvaluationRequest(
        repo_path=repo,
        source_branch="swarm/feature-ff",
        target_branch="main",
        run_pre_merge_tests=True
    )
    res = merge_arbitrator.evaluate_merge(req)

    assert res.mergeable is True
    assert res.is_fast_forward is True
    assert res.has_conflicts is False
    assert res.conflict_files == []
    assert res.divergence.get("ahead", 0) >= 1
    assert res.semantic_test_passed is True


def test_merge_evaluator_conflict_detection(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")

    # Diverge on main
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b):\n    # Main version\n    return (a + b) * 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit calculate on main"], cwd=repo, check=True, capture_output=True)

    # Branch from initial commit or diverge on feature branch
    subprocess.run(["git", "checkout", "-b", "swarm/conflict-branch", "HEAD~1"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b):\n    # Feature version\n    return (a + b) + 0\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "edit calculate on feature"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeEvaluationRequest(
        repo_path=repo,
        source_branch="swarm/conflict-branch",
        target_branch="main",
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.evaluate_merge(req)

    assert res.mergeable is False
    assert res.has_conflicts is True
    assert "calculator.py" in res.conflict_files


# =============================================================================
# 2. Merge Execution Strategies & Atomic Reconciliation
# =============================================================================

def test_merge_execute_clean_fast_forward(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "integration"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "swarm/ff-test"], cwd=repo, check=True, capture_output=True)

    with open(os.path.join(repo, "feature.py"), "w") as f:
        f.write("FEATURE_ENABLED = True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "enable feature"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/ff-test",
        target_branch="integration",
        strategy=MergeStrategy.FAST_FORWARD,
        run_pre_merge_tests=True
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "SUCCESS"
    assert res.merge_commit is not None
    assert res.strategy_used in ["FAST_FORWARD", "THREE_WAY"]

    # Verify integration branch was updated
    show_res = subprocess.run(["git", "show", "integration:feature.py"], cwd=repo, capture_output=True, text=True)
    assert "FEATURE_ENABLED = True" in show_res.stdout


def test_merge_execute_three_way_clean(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-b"], cwd=repo, check=True, capture_output=True)

    # Commit A on target-b
    subprocess.run(["git", "checkout", "target-b"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "target_file.py"), "w") as f:
        f.write("TARGET = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "target commit"], cwd=repo, check=True, capture_output=True)

    # Commit B on source-b from baseline
    subprocess.run(["git", "checkout", "-b", "swarm/source-b", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "source_file.py"), "w") as f:
        f.write("SOURCE = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "source commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/source-b",
        target_branch="target-b",
        strategy=MergeStrategy.THREE_WAY,
        run_pre_merge_tests=True
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "SUCCESS"
    assert res.strategy_used in ["THREE_WAY", "FAST_FORWARD"]
    assert res.merge_commit is not None

    # Verify target-b has both files
    assert subprocess.run(["git", "show", "target-b:target_file.py"], cwd=repo, capture_output=True).returncode == 0
    assert subprocess.run(["git", "show", "target-b:source_file.py"], cwd=repo, capture_output=True).returncode == 0


def test_merge_execute_conflict_resolution_theirs(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-conflict"], cwd=repo, check=True, capture_output=True)

    # Edit on target-conflict
    subprocess.run(["git", "checkout", "target-conflict"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b):\n    return a + b + 100\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "ours edit"], cwd=repo, check=True, capture_output=True)

    # Edit on swarm branch
    subprocess.run(["git", "checkout", "-b", "swarm/theirs-branch", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b):\n    return a + b + 200\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "theirs edit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/theirs-branch",
        target_branch="target-conflict",
        strategy=MergeStrategy.THEIRS,
        allow_ours_theirs=True,
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "SUCCESS"
    assert res.strategy_used == "THEIRS"
    show_res = subprocess.run(["git", "show", "target-conflict:calculator.py"], cwd=repo, capture_output=True, text=True)
    assert "+ 200" in show_res.stdout


def test_merge_execute_autonomous_agent_resolution(tmp_path):
    """Verify autonomous conflict resolver synthesizes clean union of two non-colliding function additions."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-multi"], cwd=repo, check=True, capture_output=True)

    # Target branch adds subtract()
    subprocess.run(["git", "checkout", "target-multi"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "a") as f:
        f.write("\ndef subtract(a, b):\n    return a - b\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add subtract"], cwd=repo, check=True, capture_output=True)

    # Swarm branch adds multiply() at same location
    subprocess.run(["git", "checkout", "-b", "swarm/add-multiply", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "a") as f:
        f.write("\ndef multiply(a, b):\n    return a * b\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add multiply"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/add-multiply",
        target_branch="target-multi",
        strategy=MergeStrategy.AUTO,
        auto_resolve_conflicts=True,
        run_pre_merge_tests=True
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "SUCCESS"
    assert res.strategy_used == "AGENT_RESOLVE"
    assert "calculator.py" in res.resolved_files

    # Verify target-multi contains both functions and zero conflict markers
    calc_content = subprocess.run(["git", "show", "target-multi:calculator.py"], cwd=repo, capture_output=True, text=True).stdout
    assert "def subtract" in calc_content
    assert "def multiply" in calc_content
    assert "<<<<<<<" not in calc_content
    assert "=======" not in calc_content
    assert ">>>>>>>" not in calc_content


def test_merge_pre_merge_test_failure_blocks_merge(tmp_path):
    """Verify pre-merge test failure prevents corrupt code from being integrated into target branch."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-stable"], cwd=repo, check=True, capture_output=True)

    # Swarm branch breaks calculator tests
    subprocess.run(["git", "checkout", "-b", "swarm/broken-code", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b):\n    return a - b  # Breaks test_calculate which asserts 2+3==5\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "broken calculation"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/broken-code",
        target_branch="target-stable",
        run_pre_merge_tests=True
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "TEST_FAILED"
    assert "Pre-merge regression test suite failed" in (res.error or "")

    # Target stable branch was NOT updated with broken code
    stable_calc = subprocess.run(["git", "show", "target-stable:calculator.py"], cwd=repo, capture_output=True, text=True).stdout
    assert "return a + b" in stable_calc


def test_merge_preserves_dirty_primary_working_tree(tmp_path):
    """Verify that when the target branch is checked out with uncommitted changes, working tree is preserved."""
    repo = _init_test_git_repo(tmp_path / "repo")

    # Create feature branch
    subprocess.run(["git", "checkout", "-b", "swarm/feat-staged"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "feat.txt"), "w") as f:
        f.write("feat\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # Dirty the primary working tree intentionally
    with open(os.path.join(repo, "user_uncommitted.txt"), "w") as f:
        f.write("USER UNCOMMITTED WORK DO NOT TOUCH\n")

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/feat-staged",
        target_branch="main",
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.execute_merge(req)

    # Must be marked STAGED_READY without overwriting or resetting user uncommitted file
    assert res.status == "STAGED_READY"
    assert os.path.exists(os.path.join(repo, "user_uncommitted.txt"))
    with open(os.path.join(repo, "user_uncommitted.txt"), "r") as f:
        assert "USER UNCOMMITTED WORK" in f.read()


# =============================================================================
# 3. Session Engine Auto-Merge Integration
# =============================================================================

def test_session_engine_auto_merge_on_completion(tmp_path):
    """Verify SessionEngine automatically merges worktree branch upon COMPLETED."""
    storage_file = str(tmp_path / "sessions_automerge.json")
    engine = SessionEngine(storage_file=storage_file)
    repo = _init_test_git_repo(tmp_path / "repo")

    # Target branch for auto-merge
    subprocess.run(["git", "branch", "integration"], cwd=repo, check=True, capture_output=True)

    req = AgyCodexSessionRequest(
        session_name="Auto Merge Test Session",
        directive="Add multiply feature with automated merge",
        target_workspace=repo,
        isolate_worktree=True,
        auto_cleanup_worktree=True,
        auto_merge_on_completion=True,
        merge_target_branch="integration"
    )

    session = engine.create_session(req)
    completed = engine.execute_session(session.session_id)

    assert completed.status == "COMPLETED"
    assert completed.auto_merge_on_completion is True
    assert completed.merge_result is not None
    assert completed.merge_result.get("status") in ["SUCCESS", "STAGED_READY"]

    # Verify integration branch has the committed changes
    int_calc = subprocess.run(["git", "show", "integration:calculator.py"], cwd=repo, capture_output=True, text=True).stdout
    assert "def multiply" in int_calc


# =============================================================================
# 4. REST API Merge Endpoints
# =============================================================================

def test_rest_api_merge_endpoints(tmp_path):
    repo = _init_test_git_repo(tmp_path / "api_merge_repo")
    subprocess.run(["git", "branch", "target-api"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "swarm/api-feat"], cwd=repo, check=True, capture_output=True)

    with open(os.path.join(repo, "api_feat.txt"), "w") as f:
        f.write("api feature\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "api commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # 1. POST /api/v1/agents/merge/evaluate
    eval_resp = client.post("/api/v1/agents/merge/evaluate", json={
        "repo_path": repo,
        "source_branch": "swarm/api-feat",
        "target_branch": "target-api",
        "run_pre_merge_tests": False
    })
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["mergeable"] is True
    assert eval_data["has_conflicts"] is False

    # 2. POST /api/v1/agents/merge/execute
    exec_resp = client.post("/api/v1/agents/merge/execute", json={
        "repo_path": repo,
        "source_branch": "swarm/api-feat",
        "target_branch": "target-api",
        "strategy": "AUTO",
        "run_pre_merge_tests": False
    })
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["status"] == "SUCCESS"
    merge_id = exec_data["merge_id"]

    # 3. GET /api/v1/agents/merge/history
    hist_resp = client.get("/api/v1/agents/merge/history")
    assert hist_resp.status_code == 200
    assert any(m["merge_id"] == merge_id for m in hist_resp.json())

    # 4. GET /api/v1/agents/merge/{merge_id}
    single_resp = client.get(f"/api/v1/agents/merge/{merge_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["merge_id"] == merge_id


# =============================================================================
# 5. Advanced Autonomous Governance, Risk & Approval Gating Tests
# =============================================================================

def test_merge_theirs_blocked_without_explicit_allowance(tmp_path):
    """Verify that using THEIRS without allow_ours_theirs=True halts and classifies as REQUIRES_HUMAN."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-blind"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "target-blind"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b): return a + b + 10\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "target change"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "-b", "swarm/blind-theirs", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b): return a + b + 20\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "swarm change"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/blind-theirs",
        target_branch="target-blind",
        strategy=MergeStrategy.THEIRS,
        allow_ours_theirs=False,
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "REQUIRES_HUMAN"
    assert "requires explicit policy allowance" in (res.error or "")


def test_merge_low_confidence_conflict_requires_human(tmp_path):
    """Verify colliding edits in same function cannot be safely auto-resolved and trigger REQUIRES_HUMAN."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-ambig"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "target-ambig"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b):\n    # Conflicting target logic\n    return a * 10 + b\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "target logic"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "-b", "swarm/ambig-logic", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "calculator.py"), "w") as f:
        f.write("def calculate(a, b):\n    # Conflicting swarm logic\n    return a * 20 + b\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "swarm logic"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/ambig-logic",
        target_branch="target-ambig",
        strategy=MergeStrategy.AUTO,
        auto_resolve_conflicts=True,
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "REQUIRES_HUMAN"
    assert "Insufficient confidence" in (res.error or "")


def test_merge_high_risk_policy_triggers_human_approval_gate(tmp_path):
    """Verify modification of security policy file halts integration and enters WAITING_FOR_APPROVAL."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-gov"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "-b", "swarm/touch-policy", "main"], cwd=repo, check=True, capture_output=True)
    os.makedirs(os.path.join(repo, "backend", "core"), exist_ok=True)
    with open(os.path.join(repo, "backend", "core", "policy.py"), "w") as f:
        f.write("# Modified security policy\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "modify policy"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/touch-policy",
        target_branch="target-gov",
        strategy=MergeStrategy.AUTO,
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.execute_merge(req)

    assert res.status == "WAITING_FOR_APPROVAL"
    assert res.approval_id is not None
    assert res.decision.classification in ["HIGH_RISK", "REQUIRES_HUMAN"]
    assert res.candidate_tree_sha is not None


def test_merge_approval_scoped_identity_and_replay_prevention(tmp_path):
    """Verify approving the scoped approval allows integration, but replaying the approval fails."""
    from core.approvals import decide_approval, load_approvals

    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-scoped"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "-b", "swarm/scoped-feat", "main"], cwd=repo, check=True, capture_output=True)
    os.makedirs(os.path.join(repo, "infra"), exist_ok=True)
    with open(os.path.join(repo, "infra", "service.tf"), "w") as f:
        f.write("# New IaC config\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add iac"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # 1. Execute merge -> Triggers WAITING_FOR_APPROVAL due to infra/ category
    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/scoped-feat",
        target_branch="target-scoped",
        strategy=MergeStrategy.AUTO,
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.execute_merge(req)
    assert res.status == "WAITING_FOR_APPROVAL"
    appr_id = res.approval_id
    merge_id = res.merge_id

    # 2. Operator decides approval
    decide_approval(approval_id=appr_id, decision="APPROVED", user="operator")

    # 3. Resume integration via integrate_approved_candidate
    res_integrated = merge_arbitrator.integrate_approved_candidate(merge_id=merge_id, approval_id=appr_id)
    assert res_integrated.status == "SUCCESS"

    # Verify target branch now has infra/service.tf
    assert subprocess.run(["git", "show", "target-scoped:infra/service.tf"], cwd=repo, capture_output=True).returncode == 0

    # 4. Attempt to replay the same approval on another request -> Must fail!
    req_replay = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/scoped-feat",
        target_branch="target-scoped",
        strategy=MergeStrategy.AUTO,
        approval_id=appr_id,
        run_pre_merge_tests=False
    )
    res_replay = merge_arbitrator.execute_merge(req_replay)
    assert res_replay.status == "APPROVAL_INVALID"


def test_merge_staleness_detection_aborts_integration(tmp_path):
    """Verify that if target branch advances between analysis and merge, integration halts with STALE_TARGET_BRANCH."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-stale"], cwd=repo, check=True, capture_output=True)

    # Swarm branch
    subprocess.run(["git", "checkout", "-b", "swarm/stale-branch", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "stale_feat.py"), "w") as f:
        f.write("STALE_FEAT = True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "stale commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/stale-branch",
        target_branch="target-stale",
        strategy=MergeStrategy.AUTO,
        run_pre_merge_tests=False
    )

    original_analyze = merge_arbitrator.analyze_three_way
    def mock_analyze(r, t, s):
        analysis = original_analyze(r, t, s)
        # Advance target-stale behind arbitrator's back
        subprocess.run(["git", "checkout", "target-stale"], cwd=repo, check=True, capture_output=True)
        with open(os.path.join(repo, "concurrent.txt"), "w") as f:
            f.write("concurrent commit on target\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "concurrent target advance"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
        return analysis

    merge_arbitrator.analyze_three_way = mock_analyze
    try:
        res = merge_arbitrator.execute_merge(req)
        assert res.status == "STALE_TARGET_BRANCH"
        assert "advanced from" in (res.error or "")
    finally:
        merge_arbitrator.analyze_three_way = original_analyze


def test_multi_agent_review_and_candidate_rejection(tmp_path):
    """Verify fleet review in staging worktree and clean candidate rejection."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-fleet"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "-b", "swarm/fleet-branch", "main"], cwd=repo, check=True, capture_output=True)
    os.makedirs(os.path.join(repo, "infra"), exist_ok=True)
    with open(os.path.join(repo, "infra", "db.tf"), "w") as f:
        f.write("# DB config\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add db iac"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    req = MergeExecutionRequest(
        repo_path=repo,
        source_branch="swarm/fleet-branch",
        target_branch="target-fleet",
        strategy=MergeStrategy.AUTO,
        run_pre_merge_tests=False
    )
    res = merge_arbitrator.execute_merge(req)
    assert res.status == "WAITING_FOR_APPROVAL"
    merge_id = res.merge_id

    # Test fleet review via REST API
    rev_resp = client.post(f"/api/v1/agents/merge/{merge_id}/review")
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["status"] == "REVIEW_COMPLETED"
    assert "agy_planner" in rev_data["review"]
    assert "codex_reviewer" in rev_data["review"]
    assert "qa_verifier" in rev_data["review"]
    assert "security_sentinel" in rev_data["review"]

    # Test candidate rejection via REST API
    rej_resp = client.post(f"/api/v1/agents/merge/{merge_id}/reject", params={"reason": "Denied by operator security review"})
    assert rej_resp.status_code == 200
    rej_data = rej_resp.json()
    assert rej_data["status"] == "REJECTED"
    assert rej_data["error"] == "Denied by operator security review"

    # Verify staging branch was deleted
    show_staging = subprocess.run(["git", "show-ref", f"refs/heads/staging/{merge_id}"], cwd=repo, capture_output=True)
    assert show_staging.returncode != 0
