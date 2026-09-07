"""
Tests for Control Plane Security:
1. API Authentication & Token Protection (/api/v1/* and /ws)
2. CORS Hardening & Origin Validation
3. Approval Security (Entropy, TTL, Replay Defense, Token Guessing, Concurrency)
"""

import time
import pytest
import concurrent.futures
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from server import app
from core.config import config
from core.auth import DEFAULT_DEV_TOKEN
from core.approvals import request_approval, decide_approval, load_approvals
from models.schemas import ApprovalStatus, RiskLevel

client = TestClient(app)

# =============================================================================
# 1. Control API Authentication Tests
# =============================================================================

def test_api_auth_enforcement(monkeypatch):
    # Temporarily enforce authentication
    monkeypatch.setattr(config, "auth_enabled", True)

    # 1. Unauthenticated request must receive 401
    resp_unauth = client.get("/api/v1/overview")
    assert resp_unauth.status_code == 401
    assert "credentials" in resp_unauth.json()["detail"].lower()

    # 2. Invalid token must receive 401
    resp_bad = client.get("/api/v1/overview", headers={"Authorization": "Bearer completely-wrong-token"})
    assert resp_bad.status_code == 401
    assert "invalid" in resp_bad.json()["detail"].lower()

    # 3. Valid operator Bearer token must succeed (200)
    resp_good = client.get("/api/v1/overview", headers={"Authorization": f"Bearer {DEFAULT_DEV_TOKEN}"})
    assert resp_good.status_code == 200
    assert resp_good.json()["fleet"]["total_agents"] == 13

    # 4. Valid X-NEXUS-KEY header must succeed (200)
    resp_key = client.get("/api/v1/overview", headers={"X-NEXUS-KEY": DEFAULT_DEV_TOKEN})
    assert resp_key.status_code == 200

def test_websocket_auth_enforcement(monkeypatch):
    monkeypatch.setattr(config, "auth_enabled", True)

    # 1. Unauthorized WebSocket connection is rejected before accept
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as ws:
            pass

    # 2. Invalid token WebSocket connection is rejected
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=invalid_token") as ws:
            pass

    # 3. Valid token WebSocket connection is accepted
    with client.websocket_connect(f"/ws?token={DEFAULT_DEV_TOKEN}") as ws:
        data = ws.receive_json()
        assert data["type"] == "telemetry_tick"
        assert "data" in data

# =============================================================================
# 2. CORS Hardening Tests
# =============================================================================

def test_cors_allowed_origin():
    # Allowed origin: http://localhost:5173
    resp = client.options(
        "/api/v1/overview",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"

def test_cors_unauthorized_origin_rejected():
    # Unauthorized origin: http://malicious-external-site.com
    resp = client.options(
        "/api/v1/overview",
        headers={
            "Origin": "http://malicious-external-site.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    # FastApi CORS middleware does not return Access-Control-Allow-Origin for forbidden origins
    assert resp.headers.get("access-control-allow-origin") != "http://malicious-external-site.com"
    assert resp.headers.get("access-control-allow-origin") != "*"

# =============================================================================
# 3. Approval Engine Security Tests
# =============================================================================

def test_approval_valid_lifecycle_with_token():
    appr = request_approval(
        action="TEST_TOKEN_FLOW",
        target_project="control-center",
        reason="Testing cryptographic token flow",
        actor="test_security_suite"
    )
    assert appr.id.startswith("appr-")
    assert appr.token is not None
    assert appr.token_hash is not None
    assert appr.created_at is not None
    assert appr.expires_at is not None

    # Decision with correct token
    decided = decide_approval(
        approval_id=appr.id,
        decision="APPROVED",
        decided_by="operator_test",
        token=appr.token
    )
    assert decided.status == ApprovalStatus.APPROVED
    assert decided.approved_by == "operator_test"
    assert decided.decided_at is not None

def test_approval_token_guessing_blocked():
    appr = request_approval(
        action="TEST_TOKEN_GUESS",
        target_project="control-center",
        reason="Testing token guessing prevention",
        actor="test_security_suite"
    )

    # Attempting to decide with an invalid / guessed token
    with pytest.raises(ValueError, match="Invalid approval token"):
        decide_approval(
            approval_id=appr.id,
            decision="APPROVED",
            decided_by="attacker",
            token="completely_guessed_fake_token_12345"
        )

    # Verify state remains PENDING
    stored = next(a for a in load_approvals() if a.id == appr.id)
    assert stored.status == ApprovalStatus.PENDING

def test_approval_ttl_expiry():
    # Create approval with 1 second TTL
    appr = request_approval(
        action="TEST_TTL_EXPIRY",
        target_project="control-center",
        reason="Testing expiry defense",
        actor="test_security_suite",
        ttl_seconds=1
    )

    # Sleep to force expiration
    time.sleep(1.2)

    with pytest.raises(ValueError, match="expired"):
        decide_approval(
            approval_id=appr.id,
            decision="APPROVED",
            decided_by="operator_test",
            token=appr.token
        )

    # Status must be updated to EXPIRED
    stored = next(a for a in load_approvals() if a.id == appr.id)
    assert stored.status == ApprovalStatus.EXPIRED

def test_approval_replay_prevention():
    appr = request_approval(
        action="TEST_REPLAY_DEFENSE",
        target_project="control-center",
        reason="Testing replay prevention",
        actor="test_security_suite"
    )

    # First decision succeeds
    decided = decide_approval(appr.id, "APPROVED", decided_by="admin", token=appr.token)
    assert decided.status == ApprovalStatus.APPROVED

    # Second decision (replay) must be rejected
    with pytest.raises(ValueError, match="already APPROVED. Replay blocked"):
        decide_approval(appr.id, "APPROVED", decided_by="admin", token=appr.token)

def test_approval_wrong_action_blocked():
    appr = request_approval(
        action="DEPLOY_PRODUCTION_V1",
        target_project="control-center",
        reason="Testing action mismatch defense",
        actor="test_security_suite"
    )

    with pytest.raises(ValueError, match="Action mismatch"):
        decide_approval(
            approval_id=appr.id,
            decision="APPROVED",
            token=appr.token,
            expected_action="DELETE_DATABASE"
        )

def test_approval_wrong_actor_blocked():
    appr = request_approval(
        action="TEST_ACTOR_BINDING",
        target_project="control-center",
        reason="Testing actor mismatch defense",
        actor="genuine_agent"
    )

    with pytest.raises(ValueError, match="Actor mismatch"):
        decide_approval(
            approval_id=appr.id,
            decision="APPROVED",
            token=appr.token,
            expected_actor="impersonator_agent"
        )

def test_approval_rejection_path():
    appr = request_approval(
        action="TEST_REJECTION",
        target_project="control-center",
        reason="Testing rejection lifecycle",
        actor="test_security_suite"
    )

    decided = decide_approval(appr.id, "REJECTED", decided_by="auditor", token=appr.token)
    assert decided.status == ApprovalStatus.REJECTED
    assert decided.approved_by == "auditor"

def test_approval_concurrency_safety():
    appr = request_approval(
        action="TEST_CONCURRENT_GATE",
        target_project="control-center",
        reason="Testing multi-threaded race conditions",
        actor="test_security_suite"
    )

    success_count = 0
    fail_count = 0

    def attempt_decision(worker_id: int):
        try:
            decide_approval(appr.id, "APPROVED", decided_by=f"worker_{worker_id}", token=appr.token)
            return True
        except ValueError:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_decision, i) for i in range(8)]
        results = [f.result() for f in futures]

    successes = sum(1 for r in results if r is True)
    fails = sum(1 for r in results if r is False)

    # Exactly one thread must succeed, all other 7 must fail
    assert successes == 1
    assert fails == 7
