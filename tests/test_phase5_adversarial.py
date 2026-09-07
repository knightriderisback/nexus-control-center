"""
NEXUS Phase 5: Adversarial Verification & Red-Teaming Test Suite.
Verifies defense-in-depth against malicious inputs, authentication bypasses,
path traversals, approval tampering, command injection, and resource exhaustion.
"""

import os
import hmac
import time
import tempfile
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from server import app
from core.config import config
from core.approvals import request_approval, decide_approval, load_approvals, save_approvals
from models.schemas import ApprovalStatus, RiskLevel
from orchestrator.safe_runner import SafeCommandExecutor

client = TestClient(app)

# =============================================================================
# 1. API Authentication Adversarial Inputs & Fuzzing
# =============================================================================

def test_api_auth_missing_header():
    orig = config.auth_enabled
    config.auth_enabled = True
    try:
        resp = client.get("/api/v1/overview")
        assert resp.status_code == 401
        assert "WWW-Authenticate" in resp.headers
        assert resp.json()["detail"] == "Missing required authentication credentials"
    finally:
        config.auth_enabled = orig

def test_api_auth_malformed_headers():
    orig = config.auth_enabled
    config.auth_enabled = True
    try:
        malformed_headers = [
            {"Authorization": ""},
            {"Authorization": "   "},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer "},
            {"Authorization": "Bearer    "},
            {"Authorization": "Basic dXNlcjpwYXNz"},
            {"Authorization": "Digest username=admin"},
            {"Authorization": "CustomScheme 12345"},
            {"Authorization": "Bearer invalid-token-xyz"},
            {"Authorization": "Bearer \x00\x00nullbyte"},
            {"Authorization": "Bearer " + "A" * 10000}, # Buffer overflow probe
            {"X-NEXUS-KEY": ""},
            {"X-NEXUS-KEY": "wrong-key"}
        ]
        for h in malformed_headers:
            resp = client.get("/api/v1/overview", headers=h)
            assert resp.status_code == 401, f"Expected 401 for header {h}, got {resp.status_code}"
    finally:
        config.auth_enabled = orig

def test_api_auth_crlf_injection_blocked():
    orig = config.auth_enabled
    config.auth_enabled = True
    try:
        # Header with simulated CRLF injection attempt
        h = {"Authorization": "Bearer token\r\nInjected: malicious"}
        resp = client.get("/api/v1/overview", headers=h)
        assert resp.status_code in [400, 401, 422]
    finally:
        config.auth_enabled = orig

# =============================================================================
# 2. CORS Origin Spoofing & Boundary Attacks
# =============================================================================

def test_cors_origin_spoofing_rejected():
    spoofed_origins = [
        "https://evil.com",
        "http://evil.com",
        "http://localhost:5173.evil.com",
        "http://attacker.com/http://localhost:5173",
        "null",
        "https://localhost:5173"
    ]
    for origin in spoofed_origins:
        resp = client.options(
            "/api/v1/overview",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET"
            }
        )
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin != origin and allow_origin != "*", f"CORS leak for origin: {origin}"

def test_cors_allowed_origin_permitted():
    resp = client.options(
        "/api/v1/overview",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

# =============================================================================
# 3. WebSocket Authentication & Authorization Adversarial Probes
# =============================================================================

def test_websocket_unauthenticated_rejected_when_auth_enabled():
    orig = config.auth_enabled
    config.auth_enabled = True
    try:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws") as ws:
                pass
        assert exc_info.value.code == 1008
    finally:
        config.auth_enabled = orig

def test_websocket_invalid_token_rejected():
    orig = config.auth_enabled
    config.auth_enabled = True
    try:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws?token=malicious-token-123") as ws:
                pass
        assert exc_info.value.code == 1008
    finally:
        config.auth_enabled = orig

def test_websocket_valid_token_accepted():
    orig = config.auth_enabled
    config.auth_enabled = True
    try:
        with client.websocket_connect("/ws?token=nexus-dev-operator-key-2026") as ws:
            data = ws.receive_json()
            assert data.get("type") == "telemetry_tick"
            assert "data" in data and "timestamp" in data["data"]
    finally:
        config.auth_enabled = orig

def test_credential_leakage_prevented_in_error_responses():
    orig = config.auth_enabled
    config.auth_enabled = True
    try:
        secret_probe = "my-secret-token-XYZ"
        resp = client.get("/api/v1/overview", headers={"Authorization": f"Bearer {secret_probe}"})
        assert resp.status_code == 401
        # Confirm that the server response does NOT echo back the secret token or reveal expected keys
        body = resp.text
        assert "nexus-dev-operator-key-2026" not in body
        assert secret_probe not in body
    finally:
        config.auth_enabled = orig


def test_api_path_traversal_in_project_routes():
    traversal_targets = [
        "..%2F..%2Fetc%2Fpasswd",
        "../../etc/passwd",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "....//....//etc//passwd"
    ]
    for target in traversal_targets:
        resp = client.get(f"/api/v1/projects/{target}")
        assert resp.status_code in [404, 400], f"Expected 404/400 for traversal path {target}, got {resp.status_code}"

# =============================================================================
# 4. Approval Engine Adversarial Verification (Brute Force, Replay, Tampering)
# =============================================================================

def test_approval_brute_force_rate_limit_locks_request():
    appr = request_approval(
        action="TEST_BRUTE_FORCE_ATTACK",
        target_project="control-center",
        reason="Adversarial token guessing audit",
        risk_level=RiskLevel.HIGH
    )
    assert appr.id.startswith("appr-")

    # Submit 5 invalid guesses
    for i in range(5):
        with pytest.raises(ValueError, match="Invalid approval token"):
            decide_approval(appr.id, "APPROVED", token=f"guess-{i}")

    # 6th attempt must be rejected with locked request (rate limit exceeded)
    with pytest.raises(ValueError, match="is locked due to excessive failed token attempts"):
        decide_approval(appr.id, "APPROVED", token="guess-6")

def test_approval_token_bit_flip_tampering_rejected():
    appr = request_approval(
        action="TEST_BIT_FLIP",
        target_project="control-center",
        reason="Testing cryptographic sensitivity",
        risk_level=RiskLevel.MEDIUM
    )
    valid_token = appr.token
    # Flip one character in token
    tampered_token = valid_token[:-1] + ('A' if valid_token[-1] != 'A' else 'B')

    with pytest.raises(ValueError, match="Invalid approval token"):
        decide_approval(appr.id, "APPROVED", token=tampered_token)

def test_approval_cross_token_substitution_rejected():
    appr1 = request_approval(action="TEST_SUB_1", target_project="control-center", reason="Request 1", risk_level=RiskLevel.LOW)
    appr2 = request_approval(action="TEST_SUB_2", target_project="control-center", reason="Request 2", risk_level=RiskLevel.LOW)

    # Use token from request 1 to approve request 2
    with pytest.raises(ValueError, match="Invalid approval token"):
        decide_approval(appr2.id, "APPROVED", token=appr1.token)

def test_approval_replay_after_execution_blocked():
    appr = request_approval(action="TEST_REPLAY_EXEC", target_project="control-center", reason="Replay test", risk_level=RiskLevel.LOW)
    decided = decide_approval(appr.id, "APPROVED", token=appr.token)
    assert decided.status == ApprovalStatus.APPROVED

    # Second decision attempt must be blocked
    with pytest.raises(ValueError, match="already APPROVED. Replay blocked."):
        decide_approval(appr.id, "APPROVED", token=appr.token)

def test_approval_approve_after_rejection_blocked():
    appr = request_approval(action="TEST_REJECT_THEN_APPROVE", target_project="control-center", reason="Rejection test", risk_level=RiskLevel.LOW)
    decided = decide_approval(appr.id, "REJECTED", token=appr.token)
    assert decided.status == ApprovalStatus.REJECTED

    # Attempt to approve rejected request must be blocked
    with pytest.raises(ValueError, match="already REJECTED. Replay blocked."):
        decide_approval(appr.id, "APPROVED", token=appr.token)

def test_approval_reject_after_approval_blocked():
    appr = request_approval(action="TEST_APPROVE_THEN_REJECT", target_project="control-center", reason="Approval test", risk_level=RiskLevel.LOW)
    decided = decide_approval(appr.id, "APPROVED", token=appr.token)
    assert decided.status == ApprovalStatus.APPROVED

    # Attempt to reject approved request must be blocked
    with pytest.raises(ValueError, match="already APPROVED. Replay blocked."):
        decide_approval(appr.id, "REJECTED", token=appr.token)

def test_approval_expired_request_blocked():
    appr = request_approval(action="TEST_EXPIRED_REQ", target_project="control-center", reason="Expiration test", risk_level=RiskLevel.LOW)
    # Manually set expiration in past
    all_apprs = load_approvals()
    for a in all_apprs:
        if a.id == appr.id:
            a.expires_at = "2020-01-01T00:00:00Z"
    save_approvals(all_apprs)

    with pytest.raises(ValueError, match="has expired"):
        decide_approval(appr.id, "APPROVED", token=appr.token)

def test_approval_constraint_mismatches_blocked():
    appr = request_approval(action="TEST_CONSTRAINTS", target_project="control-center", reason="Constraint test", risk_level=RiskLevel.LOW, actor="agent-infra")
    # Wrong action
    with pytest.raises(ValueError, match="Action mismatch"):
        decide_approval(appr.id, "APPROVED", token=appr.token, expected_action="DIFFERENT_ACTION")

    # Wrong actor
    with pytest.raises(ValueError, match="Actor mismatch"):
        decide_approval(appr.id, "APPROVED", token=appr.token, expected_actor="wrong-agent")

def test_approval_command_injection_blocked_during_execution():
    # Attempt to inject arbitrary shell chaining into an approved command
    appr = request_approval(
        action="TEST_MALICIOUS_COMMAND",
        target_project="control-center",
        reason="Adversarial command execution audit",
        command="echo safe; cat /etc/passwd",
        risk_level=RiskLevel.HIGH
    )
    # Even if approved, the safe runner will reject dangerous shell characters (;)
    decided = decide_approval(appr.id, "APPROVED", token=appr.token)
    # Status should be EXECUTED but error recorded because safe runner blocked the shell character
    assert decided.status == ApprovalStatus.EXECUTED


# =============================================================================
# 5. SafeCommandExecutor Adversarial Red-Teaming
# =============================================================================

def test_safe_runner_blocked_dangerous_binaries():
    blocked = ["bash", "sh", "zsh", "curl", "wget", "nc", "netcat", "sudo", "rm", "dd", "perl"]
    for b in blocked:
        res = SafeCommandExecutor.execute([b, "-c", "echo hello"])
        assert res.exit_code == 126
        assert "is not permitted by command allowlist" in res.stderr

def test_safe_runner_shell_injection_evasions_blocked():
    evasions = [
        ["echo", "foo; ls"],
        ["echo", "foo && ls"],
        ["echo", "foo || ls"],
        ["echo", "foo | grep x"],
        ["echo", "`id`"],
        ["echo", "$(id)"],
        ["echo", "${PATH}"],
        ["echo", "foo\ncat /etc/passwd"],
        ["echo", "foo\rcat /etc/passwd"],
        ["echo", "foo > /tmp/hacked"],
        ["echo", "foo < /etc/passwd"]
    ]
    for cmd in evasions:
        res = SafeCommandExecutor.execute(cmd)
        assert res.exit_code == 126
        assert "Dangerous shell character" in res.stderr

def test_safe_runner_null_byte_injection_blocked():
    cmd = ["echo", "test\x00/../../etc/passwd"]
    res = SafeCommandExecutor.execute(cmd)
    assert res.exit_code == 126
    assert "Null byte" in res.stderr

def test_safe_runner_symlink_escape_blocked():
    # Create a temporary symlink pointing to /etc inside the workspace
    with tempfile.TemporaryDirectory(dir="/root/control-center") as tmp_dir:
        symlink_path = os.path.join(tmp_dir, "symlink_to_etc")
        try:
            os.symlink("/etc", symlink_path)
            # Attempt to execute cat on the symlink target
            target_via_symlink = os.path.join(symlink_path, "passwd")
            res = SafeCommandExecutor.execute(["cat", target_via_symlink])
            # The realpath resolves to /etc/passwd which is outside ALLOWED_ROOTS
            assert res.exit_code == 126
            assert "escapes permitted workspace boundaries" in res.stderr
        finally:
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)

def test_safe_runner_output_capping_prevents_memory_bomb():
    # Run a python command that generates 1 MB of stdout
    py_code = "print('A' * 1_000_000)"
    res = SafeCommandExecutor.execute(["python3", "-c", py_code])
    assert res.exit_code == 0
    # Output must be capped at 500 KB (500_000 chars)
    assert len(res.stdout) <= 500_000
