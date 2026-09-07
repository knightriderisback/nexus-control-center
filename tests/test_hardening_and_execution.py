import pytest
from fastapi.testclient import TestClient
from server import app
from core.approvals import request_approval, decide_approval, load_approvals
from models.schemas import ApprovalStatus

client = TestClient(app)

def test_approval_replay_blocked():
    req = request_approval(
        action="TEST_REPLAY_BLOCK",
        target_project="control-center",
        reason="Testing replay defense",
        actor="test_runner"
    )
    decided = decide_approval(req.id, "APPROVED", decided_by="admin")
    assert decided.status in (ApprovalStatus.APPROVED, ApprovalStatus.EXECUTED)
    
    # Attempt second decision on same approval - must raise ValueError
    with pytest.raises(ValueError, match="already"):
        decide_approval(req.id, "REJECTED", decided_by="attacker")

def test_comment_only_command_skips_shell():
    req = request_approval(
        action="TEST_COMMENT_SKIP",
        target_project="control-center",
        reason="Testing comment command skip",
        command="# echo This should not run as shell",
        actor="test_runner"
    )
    decided = decide_approval(req.id, "APPROVED", decided_by="admin")
    assert decided.status == ApprovalStatus.APPROVED

def test_real_pytest_runner_on_project():
    resp = client.post("/api/v1/projects/control-center/test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "control-center"
    assert data["status"] == "PASSED"
    assert data["tests_total"] >= 27
    assert data["execution_mode"] == "REAL_PYTEST"

def test_real_security_scan_on_project():
    resp = client.post("/api/v1/projects/control-center/security")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "control-center"
    assert data["execution_mode"] == "REAL_REGEX_SCAN"
    assert data["cves_found"] == 0

def test_cost_guard_evaluation_api():
    resp_paid = client.post("/api/v1/cost/evaluate", json={"service": "compute.googleapis.com", "action": "create_instance"})
    assert resp_paid.status_code == 200
    assert resp_paid.json()["allowed"] is False

    resp_free = client.post("/api/v1/cost/evaluate", json={"service": "run.googleapis.com", "action": "read_logs"})
    assert resp_free.status_code == 200
    assert resp_free.json()["allowed"] is True

def test_observability_metrics_endpoint():
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] > 0
    assert "status_codes" in data
