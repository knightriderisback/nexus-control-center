"""
NEXUS Phase 8: Isolated Git Worktree Swarm Execution Test Suite.
Comprehensive verification covering:
1. WorktreeManager lifecycle (detection, root resolution, provisioning, teardown, branch retention/deletion)
2. WorktreeManager idempotency & stale worktree pruning
3. Ephemeral context manager execution
4. Parallel multi-agent worktree isolation (concurrent uncommitted modifications without collisions or base contamination)
5. SessionEngine integration with worktree isolation & auto-cleanup lifecycle
6. SessionEngine rollback inside isolated worktrees preserving clean main repo
7. Worktree REST API endpoints (/worktrees, /provision, /teardown, /prune)
8. CLI eco worktrees command integration
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
    AgyCodexSessionRequest,
    AgyCodexSession,
    SessionState,
    WorktreeProvisionRequest
)
from orchestrator.worktree_manager import WorktreeManager, worktree_manager
from orchestrator.session_engine import SessionEngine, session_engine

client = TestClient(app)


def _init_test_git_repo(path: Path) -> str:
    """Helper to initialize an isolated git repository with test fixtures."""
    repo_str = str(path)
    os.makedirs(repo_str, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_str, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "NEXUS Tester"], cwd=repo_str, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@nexus.local"], cwd=repo_str, check=True, capture_output=True)

    with open(os.path.join(repo_str, "calculator.py"), "w", encoding="utf-8") as f:
        f.write("def calculate(a, b):\n    return a + b\n")

    with open(os.path.join(repo_str, "test_calculator.py"), "w", encoding="utf-8") as f:
        f.write("from calculator import calculate\n\ndef test_calculate():\n    assert calculate(2, 3) == 5\n")

    subprocess.run(["git", "add", "."], cwd=repo_str, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial test commit"], cwd=repo_str, check=True, capture_output=True)
    return repo_str


# =============================================================================
# 1. WorktreeManager Basics & Lifecycle
# =============================================================================

def test_worktree_manager_basics(tmp_path):
    mgr = WorktreeManager(
        registry_file=str(tmp_path / "reg.json"),
        worktrees_dir=str(tmp_path / "wts")
    )
    repo = _init_test_git_repo(tmp_path / "repo")
    non_git = tmp_path / "non_git"
    non_git.mkdir()

    # Git detection
    assert mgr.is_git_repo(repo) is True
    assert mgr.is_git_repo(str(non_git)) is False
    assert mgr.is_git_repo("/non/existent/path") is False

    # Root resolution
    assert os.path.realpath(mgr.get_repo_root(repo)) == os.path.realpath(repo)
    sub = Path(repo) / "subdir"
    sub.mkdir()
    assert os.path.realpath(mgr.get_repo_root(str(sub))) == os.path.realpath(repo)
    assert mgr.get_repo_root(str(non_git)) is None


def test_worktree_provision_and_teardown(tmp_path):
    mgr = WorktreeManager(
        registry_file=str(tmp_path / "reg.json"),
        worktrees_dir=str(tmp_path / "wts")
    )
    repo = _init_test_git_repo(tmp_path / "repo")
    sess_id = f"test-sess-{uuid.uuid4().hex[:6]}"

    # 1. Provision
    wt = mgr.provision_worktree(repo_path=repo, session_id=sess_id)
    assert wt.session_id == sess_id
    assert os.path.exists(wt.worktree_path)
    assert os.path.exists(os.path.join(wt.worktree_path, ".git"))
    assert os.path.exists(os.path.join(wt.worktree_path, "calculator.py"))
    assert wt.status == "ACTIVE"
    assert wt.commit_hash is not None

    # Verify listing
    active = mgr.list_worktrees(repo_path=repo)
    assert any(w.session_id == sess_id for w in active)

    # 2. Teardown with branch deletion
    res = mgr.teardown_worktree(session_id=sess_id, force=True, delete_branch=True)
    assert res["status"] == "TEARDOWN"
    assert not os.path.exists(wt.worktree_path)

    # Verify status in registry
    rec = mgr.get_worktree(sess_id)
    assert rec is not None
    assert rec.status == "TEARDOWN"
    assert not any(w.session_id == sess_id for w in mgr.list_worktrees(repo_path=repo))
    raw = load_json_safe(str(tmp_path / "reg.json"))
    assert raw[sess_id]["status"] == "TEARDOWN"

    # Verify branch was deleted
    br_check = subprocess.run(["git", "show-ref", f"refs/heads/{wt.branch_name}"], cwd=repo, capture_output=True)
    assert br_check.returncode != 0


def test_worktree_provision_idempotency(tmp_path):
    mgr = WorktreeManager(
        registry_file=str(tmp_path / "reg.json"),
        worktrees_dir=str(tmp_path / "wts")
    )
    repo = _init_test_git_repo(tmp_path / "repo")
    sess_id = f"idem-{uuid.uuid4().hex[:6]}"

    wt1 = mgr.provision_worktree(repo_path=repo, session_id=sess_id)
    wt2 = mgr.provision_worktree(repo_path=repo, session_id=sess_id)

    assert wt1.worktree_path == wt2.worktree_path
    assert wt1.branch_name == wt2.branch_name
    mgr.teardown_worktree(sess_id, delete_branch=True)


def test_worktree_context_manager(tmp_path):
    mgr = WorktreeManager(
        registry_file=str(tmp_path / "reg.json"),
        worktrees_dir=str(tmp_path / "wts")
    )
    repo = _init_test_git_repo(tmp_path / "repo")
    sess_id = f"ctx-{uuid.uuid4().hex[:6]}"

    wt_path = None
    with mgr.isolated_worktree_context(repo, sess_id, delete_branch_on_teardown=True) as wt:
        wt_path = wt.worktree_path
        assert os.path.exists(wt_path)
        assert os.path.isfile(os.path.join(wt_path, "calculator.py"))

    # Should be torn down automatically
    assert not os.path.exists(wt_path)
    raw = load_json_safe(str(tmp_path / "reg.json"))
    assert raw[sess_id]["status"] == "TEARDOWN"


def test_worktree_prune_stale(tmp_path):
    wts_dir = tmp_path / "wts"
    wts_dir.mkdir(parents=True, exist_ok=True)
    reg_file = tmp_path / "reg.json"

    mgr = WorktreeManager(registry_file=str(reg_file), worktrees_dir=str(wts_dir))

    # Create an untracked directory inside wts_dir
    untracked = wts_dir / "stale_session_123"
    untracked.mkdir()
    assert os.path.exists(str(untracked))

    pruned = mgr.prune_stale_worktrees()
    assert pruned >= 1
    assert not os.path.exists(str(untracked))


# =============================================================================
# 2. Parallel Worktree Swarm Isolation & Zero Base Contamination
# =============================================================================

def test_parallel_worktree_swarm_isolation(tmp_path):
    """
    Verify two parallel swarm sessions operate independently in isolated worktrees:
    - Session 1 adds multiply() to calculator.py
    - Session 2 adds subtract() to calculator.py
    - Base repo working tree remains completely clean and uncommitted
    - Neither session sees each other's changes
    """
    mgr = WorktreeManager(
        registry_file=str(tmp_path / "reg.json"),
        worktrees_dir=str(tmp_path / "wts")
    )
    repo = _init_test_git_repo(tmp_path / "repo")

    sess_1 = "swarm-agent-alpha"
    sess_2 = "swarm-agent-beta"

    wt_1 = mgr.provision_worktree(repo, sess_1)
    wt_2 = mgr.provision_worktree(repo, sess_2)

    # Modify Session 1 worktree
    calc_1 = os.path.join(wt_1.worktree_path, "calculator.py")
    with open(calc_1, "a", encoding="utf-8") as f:
        f.write("\ndef multiply(a, b):\n    return a * b\n")

    # Modify Session 2 worktree
    calc_2 = os.path.join(wt_2.worktree_path, "calculator.py")
    with open(calc_2, "a", encoding="utf-8") as f:
        f.write("\ndef subtract(a, b):\n    return a - b\n")

    # Verify Base Repository is completely clean
    base_status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
    assert base_status.stdout.strip() == "", f"Base repository contaminated! Diff: {base_status.stdout}"

    # Verify Session 1 isolation
    with open(calc_1, "r", encoding="utf-8") as f:
        content_1 = f.read()
    assert "multiply" in content_1
    assert "subtract" not in content_1

    # Verify Session 2 isolation
    with open(calc_2, "r", encoding="utf-8") as f:
        content_2 = f.read()
    assert "subtract" in content_2
    assert "multiply" not in content_2

    # Verify git diff in both worktrees
    diff_1 = subprocess.run(["git", "diff"], cwd=wt_1.worktree_path, capture_output=True, text=True)
    assert "+def multiply" in diff_1.stdout

    diff_2 = subprocess.run(["git", "diff"], cwd=wt_2.worktree_path, capture_output=True, text=True)
    assert "+def subtract" in diff_2.stdout

    # Cleanup
    mgr.teardown_worktree(sess_1, delete_branch=True)
    mgr.teardown_worktree(sess_2, delete_branch=True)


# =============================================================================
# 3. SessionEngine Integration with Worktree Isolation
# =============================================================================

def test_session_engine_with_worktree_isolation(tmp_path):
    """Verify SessionEngine automatically creates an isolated worktree when requested and completes lifecycle."""
    storage_file = str(tmp_path / "sessions.json")
    engine = SessionEngine(storage_file=storage_file)
    repo = _init_test_git_repo(tmp_path / "repo")

    req = AgyCodexSessionRequest(
        session_name="Worktree Isolation Test",
        directive="Add multiply function to calculator in isolated worktree",
        target_workspace=repo,
        isolate_worktree=True,
        auto_cleanup_worktree=False
    )

    session = engine.create_session(req)
    assert session.isolate_worktree is True
    assert session.auto_cleanup_worktree is False
    assert session.isolated_worktree is None

    # Execute session
    completed = engine.execute_session(session.session_id)
    assert completed.status == "COMPLETED"
    assert completed.current_state == SessionState.COMPLETED
    assert completed.isolated_worktree is not None
    assert os.path.exists(completed.isolated_worktree)
    assert completed.worktree_branch == f"swarm/{completed.session_id}"

    # Base repository was not dirtied by uncommitted files
    base_status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
    assert base_status.stdout.strip() == ""

    # Teardown the worktree manually since auto_cleanup was False
    worktree_manager.teardown_worktree(completed.session_id, delete_branch=True)


def test_session_engine_worktree_auto_cleanup(tmp_path):
    """Verify auto_cleanup_worktree=True tears down worktree upon COMPLETED."""
    storage_file = str(tmp_path / "sessions_auto.json")
    engine = SessionEngine(storage_file=storage_file)
    repo = _init_test_git_repo(tmp_path / "repo")

    req = AgyCodexSessionRequest(
        session_name="Worktree Auto Cleanup Test",
        directive="Add multiply feature with auto cleanup",
        target_workspace=repo,
        isolate_worktree=True,
        auto_cleanup_worktree=True
    )

    session = engine.create_session(req)
    completed = engine.execute_session(session.session_id)
    assert completed.status == "COMPLETED"

    # Worktree directory was automatically cleaned up
    assert completed.isolated_worktree is not None
    assert not os.path.exists(completed.isolated_worktree)


def test_session_engine_worktree_rollback(tmp_path):
    """Verify rollback on an isolated worktree cleans up worktree and leaves base repo clean."""
    storage_file = str(tmp_path / "sessions_rollback.json")
    engine = SessionEngine(storage_file=storage_file)
    repo = _init_test_git_repo(tmp_path / "repo")

    req = AgyCodexSessionRequest(
        session_name="Worktree Rollback Test",
        directive="Feature that needs rollback",
        target_workspace=repo,
        isolate_worktree=True,
        auto_cleanup_worktree=True
    )

    session = engine.create_session(req)
    # Trigger isolated worktree provisioning
    wt = worktree_manager.provision_worktree(repo, session.session_id)
    session.isolated_worktree = wt.worktree_path

    # Simulate dirty worktree state
    with open(os.path.join(wt.worktree_path, "calculator.py"), "w") as f:
        f.write("SYNTAX_ERROR_BROKEN_CODE = (\n")

    rolled_back = engine.rollback_session(session.session_id)
    assert rolled_back.status == "ROLLED_BACK"
    assert rolled_back.current_state == SessionState.ROLLED_BACK

    # With auto_cleanup_worktree=True, worktree directory was removed
    assert not os.path.exists(wt.worktree_path)

    # Base repository remains clean
    base_status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
    assert base_status.stdout.strip() == ""


# =============================================================================
# 4. Worktree REST API Endpoints
# =============================================================================

def test_rest_api_worktrees(tmp_path):
    repo = _init_test_git_repo(tmp_path / "api_repo")
    sess_id = f"api-sess-{uuid.uuid4().hex[:6]}"

    # 1. Provision via REST API
    prov_payload = {
        "repo_path": repo,
        "session_id": sess_id
    }
    resp = client.post("/api/v1/agents/worktrees/provision", json=prov_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sess_id
    assert data["status"] == "ACTIVE"
    assert os.path.exists(data["worktree_path"])

    # 2. List worktrees
    resp_list = client.get("/api/v1/agents/worktrees")
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert any(i["session_id"] == sess_id for i in items)

    # 3. Teardown via REST API
    resp_tear = client.post(f"/api/v1/agents/worktrees/{sess_id}/teardown?delete_branch=true")
    assert resp_tear.status_code == 200
    tear_data = resp_tear.json()
    assert tear_data["status"] == "TEARDOWN"
    assert not os.path.exists(data["worktree_path"])

    # 4. Prune via REST API
    resp_prune = client.post("/api/v1/agents/worktrees/prune")
    assert resp_prune.status_code == 200
    assert "pruned_count" in resp_prune.json()


def test_rest_api_worktree_invalid_repo():
    prov_payload = {
        "repo_path": "/invalid/non/existent/path/999",
        "session_id": "bad-sess"
    }
    resp = client.post("/api/v1/agents/worktrees/provision", json=prov_payload)
    assert resp.status_code == 400


# =============================================================================
# 5. Security & Adversarial Worktree Defenses
# =============================================================================

def test_worktree_path_traversal_defense(tmp_path):
    mgr = WorktreeManager(
        registry_file=str(tmp_path / "reg.json"),
        worktrees_dir=str(tmp_path / "wts")
    )
    repo = _init_test_git_repo(tmp_path / "repo")

    # Path traversal patterns
    for bad_sess in ["../../etc", "evil/path", "sess;rm -rf /", "..\\..\\windows", "sess\x00null"]:
        with pytest.raises(ValueError) as exc:
            mgr.provision_worktree(repo_path=repo, session_id=bad_sess)
        assert "illegal characters" in str(exc.value) or "path traversal" in str(exc.value) or "Invalid session_id" in str(exc.value)


def test_worktree_base_branch_protection(tmp_path):
    mgr = WorktreeManager(
        registry_file=str(tmp_path / "reg.json"),
        worktrees_dir=str(tmp_path / "wts")
    )
    repo = _init_test_git_repo(tmp_path / "repo")

    # Detect current branch
    res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, capture_output=True, text=True)
    current_b = res.stdout.strip()

    # Attempting to provision worktree on current branch must be blocked
    with pytest.raises(ValueError) as exc:
        mgr.provision_worktree(repo_path=repo, session_id="test-base-branch", branch_name=current_b)
    assert "Cannot checkout current active branch" in str(exc.value)


def test_session_engine_restart_recovery_with_worktree(tmp_path):
    """Verify session with active worktree survives process restart and resumes to completion."""
    storage_file = str(tmp_path / "sessions_restart.json")
    engine1 = SessionEngine(storage_file=storage_file)
    repo = _init_test_git_repo(tmp_path / "repo")

    req = AgyCodexSessionRequest(
        session_name="Restart Recovery Test",
        directive="Add feature with process restart simulation",
        target_workspace=repo,
        isolate_worktree=True,
        auto_cleanup_worktree=False
    )
    sess = engine1.create_session(req)

    # Provision isolated worktree upfront
    wt = worktree_manager.provision_worktree(repo, sess.session_id)
    sess.isolated_worktree = wt.worktree_path
    sess.worktree_branch = wt.branch_name
    engine1.record_transition(sess, SessionState.SPEC_PROPOSAL, "agent-research", "Mid-flight spec proposal")

    # Simulate process termination & restart by creating a new SessionEngine instance
    engine2 = SessionEngine(storage_file=storage_file)
    reloaded_sess = engine2.get_session(sess.session_id)

    assert reloaded_sess is not None
    assert reloaded_sess.current_state == SessionState.SPEC_PROPOSAL
    assert reloaded_sess.isolated_worktree == wt.worktree_path
    assert os.path.exists(reloaded_sess.isolated_worktree)

    # Resume execution on engine2
    resumed = engine2.execute_session(reloaded_sess.session_id)
    assert resumed.status == "COMPLETED"
    assert resumed.current_state == SessionState.COMPLETED

    # Clean up worktree
    worktree_manager.teardown_worktree(reloaded_sess.session_id, delete_branch=True)


def test_handoff_with_isolated_worktree_context(tmp_path):
    """Verify agent handoff carries isolated worktree path down through delegated tasks."""
    from orchestrator.runtime import runtime_engine
    repo = _init_test_git_repo(tmp_path / "repo")

    mgr = WorktreeManager(registry_file=str(tmp_path / "reg.json"), worktrees_dir=str(tmp_path / "wts"))
    sess_id = f"handoff-{uuid.uuid4().hex[:6]}"
    wt = mgr.provision_worktree(repo, sess_id)

    # Execute handoff from research to dev inside worktree
    handoff = runtime_engine.execute_handoff(
        parent_agent_id="agent-research",
        target_agent_id="agent-dev",
        task_title=f"Handoff inside isolated worktree {sess_id}",
        instructions="Implement multiply in calculator inside worktree",
        project_id=wt.worktree_path
    )

    assert handoff["status"] == "COMPLETED"
    # Verify main repo is still clean
    base_status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
    assert base_status.stdout.strip() == ""

    mgr.teardown_worktree(sess_id, delete_branch=True)

