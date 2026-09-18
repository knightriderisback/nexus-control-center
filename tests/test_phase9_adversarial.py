"""
NEXUS Phase 9: Swarm Branch Merge Arbitration Adversarial & Resilience Suite.
Comprehensive verification covering:
1. Malicious branch name injection prevention
2. Path traversal attack prevention
3. Terminal lifecycle state mutation protection
4. Duplicate integration idempotency
5. Rollback safety and target ref restoration
6. Target branch staleness race aborts
7. Scoped approval anti-replay defense
8. Primary dirty working-tree zero pollution guarantee
9. Corrupted persistence file recovery
10. Concurrency locking & multi-threaded merge serialization
11. REST API security rejection and error handling
"""

import os
import shutil
import subprocess
import uuid
import threading
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from server import app
from core.storage import load_json_safe, atomic_save_json
from core.approvals import request_approval, decide_approval, load_approvals
from models.schemas import (
    MergeStrategy,
    MergeEvaluationRequest,
    MergeExecutionRequest,
    MergeCandidateCreateRequest,
    MergeLifecycleState,
    ApprovalStatus
)
from orchestrator.merge_arbitrator import MergeArbitrator, merge_arbitrator
from orchestrator.worktree_manager import worktree_manager

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
# 1. Malicious Branch Name & Path Traversal Injection Prevention
# =============================================================================

@pytest.mark.parametrize("malicious_branch", [
    "../../etc/passwd",
    "; rm -rf /",
    "--upload-pack=touch /tmp/evil",
    "-f",
    "/root/forbidden",
    "feature..branch",
    "feature/branch; echo pwned",
    "feat|evil",
    "feat$evil",
    "branch.lock",
    "trailing/slash/",
    ""
])
def test_malicious_branch_injection_rejected(tmp_path, malicious_branch):
    repo = _init_test_git_repo(tmp_path / "repo")

    # Direct candidate creation must raise ValueError
    with pytest.raises(ValueError) as exc:
        req = MergeCandidateCreateRequest(
            repo_path=repo,
            source_branch=malicious_branch,
            target_branch="main"
        )
        merge_arbitrator.create_candidate(req)
    assert "Malicious or invalid branch name" in str(exc.value) or "must be a non-empty string" in str(exc.value)

    # Evaluate merge must raise ValueError
    with pytest.raises(ValueError) as exc_eval:
        eval_req = MergeEvaluationRequest(
            repo_path=repo,
            source_branch=malicious_branch,
            target_branch="main"
        )
        merge_arbitrator.evaluate_merge(eval_req)
    assert "Malicious or invalid branch name" in str(exc_eval.value) or "must be a non-empty string" in str(exc_eval.value)

    # Execute merge must raise ValueError
    with pytest.raises(ValueError) as exc_exec:
        exec_req = MergeExecutionRequest(
            repo_path=repo,
            source_branch=malicious_branch,
            target_branch="main"
        )
        merge_arbitrator.execute_merge(exec_req)
    assert "Malicious or invalid branch name" in str(exc_exec.value) or "must be a non-empty string" in str(exc_exec.value)


def test_path_traversal_repo_path_rejected(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    invalid_path = str(tmp_path / "nonexistent" / "deep" / "repo")

    with pytest.raises(ValueError) as exc:
        req = MergeCandidateCreateRequest(
            repo_path=invalid_path,
            source_branch="swarm/test",
            target_branch="main"
        )
        merge_arbitrator.create_candidate(req)
    assert "does not exist or is invalid" in str(exc.value)


# =============================================================================
# 2. Terminal Lifecycle State Mutation Protection
# =============================================================================

def test_terminal_state_mutation_guards(tmp_path):
    """Ensure that once a candidate enters a terminal state, subsequent mutations are blocked."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "checkout", "-b", "swarm/terminal-test", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "feat.py"), "w") as f:
        f.write("X = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # 1. Test REJECTED candidate mutation guard
    cand_req = MergeCandidateCreateRequest(repo_path=repo, source_branch="swarm/terminal-test", target_branch="main")
    c_rej = merge_arbitrator.create_candidate(cand_req)
    c_rej = merge_arbitrator.reject_candidate_by_id(c_rej.candidate_id, reason="Rejected initially")

    assert c_rej.state == MergeLifecycleState.REJECTED
    with pytest.raises(ValueError) as exc:
        merge_arbitrator.analyze_candidate(c_rej.candidate_id)
    assert "is in terminal state 'REJECTED'" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        merge_arbitrator.verify_candidate(c_rej.candidate_id)
    assert "is in terminal state 'REJECTED'" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        merge_arbitrator.integrate_candidate(c_rej.candidate_id)
    assert "is in terminal state 'REJECTED'" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        merge_arbitrator.reject_candidate_by_id(c_rej.candidate_id)
    assert "Cannot reject candidate" in str(exc.value)

    # 2. Test ROLLED_BACK candidate mutation guard
    c_rb = merge_arbitrator.create_candidate(cand_req)
    c_rb = merge_arbitrator.analyze_candidate(c_rb.candidate_id)
    c_rb = merge_arbitrator.verify_candidate(c_rb.candidate_id)
    c_rb = merge_arbitrator.integrate_candidate(c_rb.candidate_id)
    assert c_rb.state == MergeLifecycleState.INTEGRATED

    # Roll back
    c_rb = merge_arbitrator.rollback_candidate(c_rb.candidate_id, reason="Safety rollback")
    assert c_rb.state == MergeLifecycleState.ROLLED_BACK

    with pytest.raises(ValueError) as exc:
        merge_arbitrator.integrate_candidate(c_rb.candidate_id)
    assert "is in terminal state 'ROLLED_BACK'" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        merge_arbitrator.rollback_candidate(c_rb.candidate_id)
    assert "Cannot rollback candidate" in str(exc.value)


# =============================================================================
# 3. Duplicate Integration Idempotency
# =============================================================================

def test_duplicate_integration_idempotency(tmp_path):
    """Calling integrate_candidate on an already INTEGRATED candidate must be a clean no-op."""
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-idem"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "swarm/idem", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "idem.py"), "w") as f:
        f.write("IDEM = True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "idem commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    cand_req = MergeCandidateCreateRequest(repo_path=repo, source_branch="swarm/idem", target_branch="target-idem")
    c = merge_arbitrator.create_candidate(cand_req)
    c = merge_arbitrator.analyze_candidate(c.candidate_id)
    c = merge_arbitrator.verify_candidate(c.candidate_id)
    c = merge_arbitrator.integrate_candidate(c.candidate_id)
    assert c.state == MergeLifecycleState.INTEGRATED
    target_commit_first = subprocess.run(["git", "rev-parse", "target-idem"], cwd=repo, capture_output=True, text=True).stdout.strip()

    # Call integrate again
    c_second = merge_arbitrator.integrate_candidate(c.candidate_id)
    assert c_second.state == MergeLifecycleState.INTEGRATED
    target_commit_second = subprocess.run(["git", "rev-parse", "target-idem"], cwd=repo, capture_output=True, text=True).stdout.strip()
    assert target_commit_first == target_commit_second


# =============================================================================
# 4. Rollback Restores Target Branch Ref
# =============================================================================

def test_rollback_restores_target_base_commit(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-rb"], cwd=repo, check=True, capture_output=True)
    initial_target_commit = subprocess.run(["git", "rev-parse", "target-rb"], cwd=repo, capture_output=True, text=True).stdout.strip()

    subprocess.run(["git", "checkout", "-b", "swarm/rb-feature", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "buggy.py"), "w") as f:
        f.write("CRITICAL_BUG = True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "buggy commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    cand_req = MergeCandidateCreateRequest(repo_path=repo, source_branch="swarm/rb-feature", target_branch="target-rb")
    c = merge_arbitrator.create_candidate(cand_req)
    c = merge_arbitrator.analyze_candidate(c.candidate_id)
    c = merge_arbitrator.verify_candidate(c.candidate_id)
    c = merge_arbitrator.integrate_candidate(c.candidate_id)
    assert c.state == MergeLifecycleState.INTEGRATED

    # Target branch now has the commit
    advanced_commit = subprocess.run(["git", "rev-parse", "target-rb"], cwd=repo, capture_output=True, text=True).stdout.strip()
    assert advanced_commit != initial_target_commit

    # Roll back
    c_rolled = merge_arbitrator.rollback_candidate(c.candidate_id, reason="Emergency rollback: regression detected")
    assert c_rolled.state == MergeLifecycleState.ROLLED_BACK

    # Check target-rb branch ref is restored to initial_target_commit
    restored_commit = subprocess.run(["git", "rev-parse", "target-rb"], cwd=repo, capture_output=True, text=True).stdout.strip()
    assert restored_commit == initial_target_commit

    # Verify backup branch was created
    backup_branch = f"backup/cand-{c.candidate_id}"
    chk_backup = subprocess.run(["git", "show-ref", f"refs/heads/{backup_branch}"], cwd=repo, capture_output=True)
    assert chk_backup.returncode == 0


# =============================================================================
# 5. Target Branch Staleness Race Detection
# =============================================================================

def test_target_branch_staleness_race_aborts(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-race"], cwd=repo, check=True, capture_output=True)

    subprocess.run(["git", "checkout", "-b", "swarm/race-feat", "main"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "feat_race.py"), "w") as f:
        f.write("RACE = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "race commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    cand_req = MergeCandidateCreateRequest(repo_path=repo, source_branch="swarm/race-feat", target_branch="target-race")
    c = merge_arbitrator.create_candidate(cand_req)
    c = merge_arbitrator.analyze_candidate(c.candidate_id)
    c = merge_arbitrator.verify_candidate(c.candidate_id)
    assert c.state == MergeLifecycleState.READY_TO_INTEGRATE

    # Simulate concurrent advance on target-race before integrate_candidate is called
    subprocess.run(["git", "checkout", "target-race"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "other.py"), "w") as f:
        f.write("OTHER = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "concurrent commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    # Candidate integration must detect target staleness and abort to REQUIRES_HUMAN
    c_int = merge_arbitrator.integrate_candidate(c.candidate_id)
    assert c_int.state == MergeLifecycleState.REQUIRES_HUMAN
    assert "advanced from" in (c_int.error or "")


# =============================================================================
# 6. Scoped Approval Anti-Replay Defense
# =============================================================================

def test_scoped_approval_anti_replay_adversarial(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    subprocess.run(["git", "branch", "target-appr"], cwd=repo, check=True, capture_output=True)

    # Branch with IaC file (high risk)
    subprocess.run(["git", "checkout", "-b", "swarm/iac-feat", "main"], cwd=repo, check=True, capture_output=True)
    os.makedirs(os.path.join(repo, "infra"), exist_ok=True)
    with open(os.path.join(repo, "infra", "prod.tf"), "w") as f:
        f.write("# prod infrastructure\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "iac prod"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    cand_req = MergeCandidateCreateRequest(repo_path=repo, source_branch="swarm/iac-feat", target_branch="target-appr")
    c1 = merge_arbitrator.create_candidate(cand_req)
    c1 = merge_arbitrator.analyze_candidate(c1.candidate_id)
    c1 = merge_arbitrator.verify_candidate(c1.candidate_id)
    assert c1.state == MergeLifecycleState.APPROVAL_PENDING
    assert c1.approval_id is not None
    appr_id = c1.approval_id

    # Operator approves
    decide_approval(approval_id=appr_id, decision="APPROVED", user="lead-devops")

    # Integrate candidate 1
    c1 = merge_arbitrator.integrate_candidate(c1.candidate_id, approval_id=appr_id)
    assert c1.state == MergeLifecycleState.INTEGRATED

    # Verify approval is now EXECUTED
    all_apprs = load_approvals()
    matched_appr = next((a for a in all_apprs if a.id == appr_id), None)
    assert matched_appr is not None
    assert matched_appr.status == ApprovalStatus.EXECUTED

    # Adversary creates a different branch and tries to reuse the consumed approval ID
    subprocess.run(["git", "checkout", "-b", "swarm/malicious-feat", "main"], cwd=repo, check=True, capture_output=True)
    os.makedirs(os.path.join(repo, "infra"), exist_ok=True)
    with open(os.path.join(repo, "infra", "backdoor.tf"), "w") as f:
        f.write("# unauthorized backdoor IaC\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "backdoor"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    cand_req2 = MergeCandidateCreateRequest(repo_path=repo, source_branch="swarm/malicious-feat", target_branch="target-appr")
    c2 = merge_arbitrator.create_candidate(cand_req2)
    c2 = merge_arbitrator.analyze_candidate(c2.candidate_id)
    c2 = merge_arbitrator.verify_candidate(c2.candidate_id)

    # Attempting to integrate with the replayed approval must raise ValueError
    with pytest.raises(ValueError) as exc:
        merge_arbitrator.integrate_candidate(c2.candidate_id, approval_id=appr_id)
    assert "is not in APPROVED state" in str(exc.value)


# =============================================================================
# 7. Primary Dirty Working-Tree Zero Pollution Guarantee
# =============================================================================

def test_dirty_primary_working_tree_untouched(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")

    # Checkout main and create dirty uncommitted edits
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    dirty_file = os.path.join(repo, "uncommitted_work.txt")
    with open(dirty_file, "w") as f:
        f.write("UNCOMMITTED_WIP = True\n")

    # Swarm branch targeting main
    subprocess.run(["git", "branch", "swarm/clean-worker"], cwd=repo, check=True, capture_output=True)
    # Commit to swarm/clean-worker without touching main working tree
    subprocess.run(["git", "checkout", "swarm/clean-worker"], cwd=repo, check=True, capture_output=True)
    with open(os.path.join(repo, "worker_output.py"), "w") as f:
        f.write("WORKER_READY = True\n")
    subprocess.run(["git", "add", "worker_output.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "worker commit"], cwd=repo, check=True, capture_output=True)

    # Return to main with dirty uncommitted file
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    assert os.path.exists(dirty_file)

    cand_req = MergeCandidateCreateRequest(repo_path=repo, source_branch="swarm/clean-worker", target_branch="main")
    c = merge_arbitrator.create_candidate(cand_req)
    c = merge_arbitrator.analyze_candidate(c.candidate_id)
    c = merge_arbitrator.verify_candidate(c.candidate_id)
    c = merge_arbitrator.integrate_candidate(c.candidate_id)

    # Primary working tree was dirty, so integration was deferred to STAGED_READY
    assert c.integration_state == "STAGED_READY"

    # CRITICAL: Verify uncommitted file is completely untouched
    assert os.path.exists(dirty_file)
    with open(dirty_file, "r") as f:
        assert f.read() == "UNCOMMITTED_WIP = True\n"


# =============================================================================
# 8. Corrupted Persistence File Resilience
# =============================================================================

def test_corrupted_persistence_resilience(tmp_path):
    test_hist_file = str(tmp_path / "corrupt_history.json")
    test_cand_file = str(tmp_path / "corrupt_candidates.json")

    # 1. Invalid syntax in candidates file
    with open(test_cand_file, "w") as f:
        f.write("{ INVALID JSON SYNTAX [,,,] }")

    arb = MergeArbitrator(history_file=test_hist_file, candidates_file=test_cand_file)
    # Must not raise an exception and return empty list
    candidates = arb.list_candidates()
    assert candidates == []
    assert arb.get_candidate("cand-none") is None

    # 2. Corrupted items (non-dict values and malformed fields)
    atomic_save_json(test_cand_file, {
        "valid": {"candidate_id": "cand-v1", "repo_path": "/r", "source_branch": "s", "target_branch": "t", "state": "CREATED", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", "correlation_id": "corr-1"},
        "broken_str": "THIS IS A STRING NOT A DICT",
        "broken_dict": {"missing_keys": True}
    })
    cands = arb.list_candidates()
    assert len(cands) == 1
    assert cands[0].candidate_id == "cand-v1"

    # 3. Corrupted history file
    with open(test_hist_file, "w") as f:
        f.write("NOT JSON")
    hist = arb.list_history()
    assert hist == []
    assert arb.get_merge_record("merge-none") is None


# =============================================================================
# 9. Concurrency & Repository Mutex Lock
# =============================================================================

def test_concurrent_evaluations_under_repo_lock(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")
    for i in range(3):
        b_name = f"swarm/concurrent-{i}"
        subprocess.run(["git", "checkout", "-b", b_name, "main"], cwd=repo, check=True, capture_output=True)
        with open(os.path.join(repo, f"file_{i}.py"), "w") as f:
            f.write(f"V = {i}\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"commit {i}"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)

    results = []
    errors = []

    def run_eval(idx):
        try:
            req = MergeEvaluationRequest(
                repo_path=repo,
                source_branch=f"swarm/concurrent-{idx}",
                target_branch="main",
                run_pre_merge_tests=False
            )
            res = merge_arbitrator.evaluate_merge(req)
            results.append(res)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=run_eval, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert len(errors) == 0
    assert len(results) == 3
    for r in results:
        assert r.mergeable is True


# =============================================================================
# 10. REST API Adversarial Rejection
# =============================================================================

def test_rest_api_adversarial_rejections(tmp_path):
    repo = _init_test_git_repo(tmp_path / "repo")

    # 1. Malicious branch name via /merge/evaluate
    eval_resp = client.post("/api/v1/agents/merge/evaluate", json={
        "repo_path": repo,
        "source_branch": "swarm/branch; echo hack",
        "target_branch": "main"
    })
    assert eval_resp.status_code == 400
    assert "Malicious or invalid branch name" in eval_resp.json().get("detail", "")

    # 2. Path traversal via /merge/candidates
    cand_resp = client.post("/api/v1/agents/merge/candidates", json={
        "repo_path": "/root/control-center/../../etc/shadow",
        "source_branch": "swarm/valid",
        "target_branch": "main"
    })
    assert cand_resp.status_code == 400

    # 3. Non-existent candidate operations
    int_resp = client.post("/api/v1/agents/merge/candidates/cand-ghost-404/integrate")
    assert int_resp.status_code == 404

    roll_resp = client.post("/api/v1/agents/merge/candidates/cand-ghost-404/rollback")
    assert roll_resp.status_code == 404

    rej_resp = client.post("/api/v1/agents/merge/candidates/cand-ghost-404/reject")
    assert rej_resp.status_code == 404
