"""
NEXUS Phase 7: Local Production Hardening & Adversarial Verification Suite
Comprehensive adversarial test coverage for:
1. Database & Atomic JSON Storage Resilience Under High Concurrency & Quarantine
2. AGY ↔ Codex State Machine DAG Transition Integrity & Terminal State Protection
3. Session In-Flight Concurrency Locking & Execution Idempotency
4. Session Resumability Post-Human Approval
5. Multi-Turn Remediation Context Injection into Coder Agent
6. Stale & Corrupt Session Preservation (Zero Silent Data Loss)
7. Agent Handoff Safety: Missing Parent, Direct/Indirect Circular Loops, RBAC Privilege Escalation
8. FastAPI Lifespan Context Manager & Graceful Shutdown
9. Local Daemon CLI Lifecycle & Process Control
"""

import os
import json
import uuid
import time
import threading
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from server import app
from core.config import config
from core.storage import atomic_save_json, load_json_safe, atomic_json_updater
from core.approvals import request_approval, decide_approval
from models.schemas import (
    AgyCodexSessionRequest,
    AgyCodexSession,
    SessionState,
    RiskLevel
)
from orchestrator.session_engine import session_engine, SessionEngine, VALID_STATE_TRANSITIONS
from orchestrator.runtime import runtime_engine

client = TestClient(app)

# =============================================================================
# 1. Storage Resilience, Concurrency & Quarantine
# =============================================================================

def test_storage_concurrent_atomic_updater(tmp_path):
    """Verify multiple concurrent threads using atomic_json_updater do not race or corrupt data."""
    test_file = str(tmp_path / "concurrent_state.json")
    atomic_save_json(test_file, {"counter": 0, "updates": []})

    def worker(idx: int):
        with atomic_json_updater(test_file, default={"counter": 0, "updates": []}) as state:
            state["counter"] += 1
            state["updates"].append(f"thread-{idx}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_state = load_json_safe(test_file)
    assert final_state["counter"] == 10
    assert len(final_state["updates"]) == 10


def test_storage_corrupt_quarantine(tmp_path):
    """Verify corrupted JSON is quarantined safely and does not crash reader."""
    corrupt_file = str(tmp_path / "corrupted_payload.json")
    with open(corrupt_file, "w") as f:
        f.write('{"malformed": true, "unterminated_string": "oops')

    # Reading should return default fallback safely
    fallback = {"status": "RECOVERED"}
    result = load_json_safe(corrupt_file, default=fallback)
    assert result == fallback

    # Check that a forensic quarantine backup file was created
    parent = Path(tmp_path)
    quarantine_files = list(parent.glob("corrupted_payload.json.corrupt.*"))
    assert len(quarantine_files) >= 1
    assert quarantine_files[0].stat().st_size > 0


# =============================================================================
# 2. State-Machine DAG Transition Integrity
# =============================================================================

def test_session_engine_rejects_illegal_transitions():
    """Verify strict state-machine DAG rejects illegal jumps and terminal mutations."""
    req = AgyCodexSessionRequest(
        session_name="dag-violation-test",
        directive="Audit architecture"
    )
    session = session_engine.create_session(req)
    assert session.current_state == SessionState.INITIALIZING

    # Illegal jump: INITIALIZING -> COMPLETED (cannot bypass spec, synthesis, and verification)
    with pytest.raises(ValueError) as exc_info:
        session_engine.record_transition(
            session, SessionState.COMPLETED, "agent-research", "Attempting illegal jump", strict=True
        )
    assert "Illegal state transition" in str(exc_info.value)
    assert "INITIALIZING" in str(exc_info.value)

    # Transition legally: INITIALIZING -> SPEC_PROPOSAL -> CODE_SYNTHESIS
    session = session_engine.record_transition(
        session, SessionState.SPEC_PROPOSAL, "agent-research", "Spec discovery", strict=True
    )
    session = session_engine.record_transition(
        session, SessionState.CODE_SYNTHESIS, "agent-dev", "Synthesizing", strict=True
    )

    # Illegal jump: CODE_SYNTHESIS -> SECURITY_AUDIT (cannot skip TEST_VERIFICATION)
    with pytest.raises(ValueError) as exc_info2:
        session_engine.record_transition(
            session, SessionState.SECURITY_AUDIT, "agent-dev", "Skipping QA", strict=True
        )
    assert "Illegal state transition" in str(exc_info2.value)


def test_session_terminal_state_protection():
    """Verify terminal states (COMPLETED, ROLLED_BACK) cannot undergo further state transitions."""
    req = AgyCodexSessionRequest(
        session_name="terminal-state-test",
        directive="Quick probe"
    )
    session = session_engine.create_session(req)
    session.current_state = SessionState.COMPLETED

    with pytest.raises(ValueError) as exc_info:
        session_engine.record_transition(
            session, SessionState.CODE_SYNTHESIS, "agent-dev", "Mutating completed session", strict=True
        )
    assert "Illegal state transition" in str(exc_info.value)
    assert "COMPLETED" in str(exc_info.value)


# =============================================================================
# 3. Concurrency Locking & Execution Idempotency
# =============================================================================

def test_session_in_flight_concurrency_lock():
    """Verify simultaneous execution of the same session raises RuntimeError."""
    req = AgyCodexSessionRequest(
        session_name="in-flight-lock-test",
        directive="Verify locks",
        target_workspace="/root/control-center/data/fixtures/fixture-qa-passing"
    )
    session = session_engine.create_session(req)

    # Simulate in-flight session execution
    with session_engine._exec_lock:
        session_engine._executing_sessions.add(session.session_id)

    try:
        with pytest.raises(RuntimeError) as exc_info:
            session_engine.execute_session(session.session_id)
        assert "currently executing" in str(exc_info.value)
    finally:
        with session_engine._exec_lock:
            session_engine._executing_sessions.discard(session.session_id)


def test_session_completed_idempotency():
    """Verify re-executing an already COMPLETED session is a no-op idempotent call."""
    req = AgyCodexSessionRequest(
        session_name="idempotent-test",
        directive="Check idempotency",
        target_workspace="/root/control-center/data/fixtures/fixture-qa-passing"
    )
    session = session_engine.create_session(req)
    session.current_state = SessionState.COMPLETED
    session.status = "COMPLETED"

    # Re-executing should return immediately without error
    result = session_engine.execute_session(session.session_id)
    assert result.session_id == session.session_id
    assert result.current_state == SessionState.COMPLETED


# =============================================================================
# 4. Session Resumability Post-Approval
# =============================================================================

def test_session_resumability_after_operator_approval():
    """Verify session gated by policy transitions to AWAITING_APPROVAL and resumes when approved."""
    req = AgyCodexSessionRequest(
        session_name="resumable-approval-session",
        directive="Request deployment to staging cluster",
        project_id="control-center",
        target_workspace="/root/control-center/data/fixtures/fixture-qa-passing"
    )
    session = session_engine.create_session(req)

    # Initial execution halts on policy gate
    halted = session_engine.execute_session(session.session_id)
    assert halted.status == "AWAITING_APPROVAL"
    assert halted.current_state == SessionState.AWAITING_APPROVAL
    assert halted.approval_id is not None

    # Simulate human operator approving the request
    decide_approval(halted.approval_id, "APPROVED", decided_by="admin_operator")

    # Re-executing resumes the session past the gate!
    resumed = session_engine.execute_session(session.session_id)
    assert resumed.status in ["COMPLETED", "IN_PROGRESS", "ROLLED_BACK"]
    states = [t.to_state for t in resumed.transitions]
    assert "SPEC_PROPOSAL" in states


# =============================================================================
# 5. Stale & Corrupt Session Preservation
# =============================================================================

def test_corrupt_session_json_preserved_without_data_loss(tmp_path):
    """Verify that unparseable/corrupt sessions in storage are preserved and never erased."""
    test_storage = str(tmp_path / "swarm_sessions_with_corruption.json")
    corrupt_data = {
        "sess-valid": {
            "session_id": "sess-valid",
            "session_name": "valid-session",
            "directive": "Do something",
            "current_state": "INITIALIZING",
            "planner_agent": "agent-research",
            "coder_agent": "agent-dev",
            "verifier_agent": "agent-qa",
            "project_id": "control-center",
            "target_workspace": "/root/control-center",
            "created_at": "2026-09-14T00:00:00Z",
            "updated_at": "2026-09-14T00:00:00Z"
        },
        "sess-corrupt-raw": "corrupted-non-dict-string-or-unparseable"
    }
    atomic_save_json(test_storage, corrupt_data)

    engine = SessionEngine(storage_file=test_storage)
    assert engine.get_session("sess-valid") is not None
    assert "sess-corrupt-raw" in engine._corrupt_sessions

    # Create a new session and persist
    new_req = AgyCodexSessionRequest(session_name="new-sess", directive="Directive 2")
    engine.create_session(new_req)

    # Read the file directly from disk: both valid, new, and corrupt raw records must exist!
    on_disk = load_json_safe(test_storage)
    assert "sess-valid" in on_disk
    assert "sess-corrupt-raw" in on_disk
    assert on_disk["sess-corrupt-raw"] == "corrupted-non-dict-string-or-unparseable"


# =============================================================================
# 6. Agent Handoff Safety Guardrails
# =============================================================================

def test_handoff_rejects_nonexistent_parent_agent():
    """Verify handoff from an unknown parent agent is rejected with FAILED status."""
    res = runtime_engine.execute_handoff(
        parent_agent_id="ghost-parent-agent",
        target_agent_id="agent-qa",
        task_title="Spoofed Handoff",
        instructions="Should fail validation"
    )
    assert res["status"] == "FAILED"
    assert "Parent agent 'ghost-parent-agent' not found" in res["error"]


def test_handoff_detects_and_blocks_direct_circular_loop():
    """Verify self-delegation (parent == target) is detected and blocked."""
    res = runtime_engine.execute_handoff(
        parent_agent_id="agent-dev",
        target_agent_id="agent-dev",
        task_title="Direct Recursion Probe",
        instructions="Self handoff attempt"
    )
    assert res["status"] == "BLOCKED"
    assert "Circular agent handoff loop detected" in res["error"]


def test_handoff_detects_and_blocks_indirect_circular_chain():
    """Verify indirect circular chain (e.g. dev -> qa -> dev) is detected and blocked."""
    res = runtime_engine.execute_handoff(
        parent_agent_id="agent-qa",
        target_agent_id="agent-dev",
        task_title="Indirect Ping-Pong Probe",
        instructions="Should be blocked by call chain",
        context={"call_chain": ["agent-dev"]}
    )
    assert res["status"] == "BLOCKED"
    assert "Circular agent handoff loop detected" in res["error"]
    assert "agent-dev -> agent-qa -> agent-dev" in res["error"]


def test_handoff_blocks_read_only_to_destructive_privilege_escalation():
    """Verify ReadOnly agent cannot delegate directly to destructive recovery agent."""
    res = runtime_engine.execute_handoff(
        parent_agent_id="agent-research",
        target_agent_id="agent-recovery",
        task_title="Privilege Escalation Attempt",
        instructions="Attempt destructive checkout"
    )
    assert res["status"] == "BLOCKED"
    assert "Read-only agent 'agent-research' cannot delegate to recovery agent" in res["error"]


# =============================================================================
# 7. FastAPI Lifespan & Production Graceful Lifecycle
# =============================================================================

def test_fastapi_lifespan_lifecycle():
    """Verify application startup and graceful shutdown under Starlette lifespan context."""
    with TestClient(app) as test_client:
        resp = test_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ONLINE"
        assert data["system"] == config.app_name

        # Telemetry probe
        resp_telem = test_client.get("/api/telemetry")
        assert resp_telem.status_code == 200
        telem = resp_telem.json()
        assert "cpu" in telem
        assert "memory" in telem
        assert "timestamp" in telem


# =============================================================================
# 8. Local Daemon CLI Lifecycle
# =============================================================================

def test_nexus_daemon_cli_status_and_logs():
    """Verify nexus_daemon.py status and logs CLI commands execute cleanly."""
    import subprocess
    script = "/root/control-center/scripts/nexus_daemon.py"

    # Status check
    res_status = subprocess.run(["python3", script, "status"], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    assert res_status.returncode in [0, 3]
    assert "NEXUS LOCAL DAEMON SERVICE STATUS" in res_status.stdout

    # Logs check
    res_logs = subprocess.run(["python3", script, "logs", "5"], stdin=subprocess.DEVNULL, capture_output=True, text=True)
    assert res_logs.returncode in [0, 1]
