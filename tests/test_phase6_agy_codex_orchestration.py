"""
NEXUS Phase 6: AGY ↔ Codex Autonomous Orchestration & Recovery Suite
Exhaustive verification of:
1. Persistent Session Storage & Atomic State Updates
2. Controlled State Transitions & Auditability
3. AGY Planner ↔ Codex Coder ↔ QA Verifier ↔ Security Sentinel Workflows
4. Feedback Loops & Multi-Turn Remediation Attempts
5. Checkpoint Capture & Automated Recovery Rollback
6. Policy & Approval Gating on High-Risk Session Directives
7. API Endpoints (/agents/sessions/create, /all, /{id}, /rollback)
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from server import app
from orchestrator.session_engine import session_engine, SessionEngine
from models.schemas import (
    AgyCodexSessionRequest,
    AgyCodexSession,
    SessionState
)
from core.config import config

client = TestClient(app)

# =============================================================================
# 1. Session Creation, Storage & Persistence
# =============================================================================

def test_session_create_and_state_persistence(tmp_path):
    """Verify session is created in INITIALIZING state and atomically persisted to storage."""
    req = AgyCodexSessionRequest(
        session_name="test-storage-session",
        directive="Refactor calculator operations",
        project_id="control-center",
        target_workspace="/root/control-center/data/fixtures/developer_test_repo"
    )
    session = session_engine.create_session(req)
    assert session.session_id.startswith("sess-")
    assert session.current_state == SessionState.INITIALIZING
    assert session.directive == "Refactor calculator operations"

    # Verify session is retrievable via memory cache
    retrieved = session_engine.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.session_name == "test-storage-session"

    # Verify session is persisted on disk
    assert os.path.exists(session_engine.storage_file)
    with open(session_engine.storage_file, "r") as f:
        stored_dict = json.load(f)
    assert session.session_id in stored_dict
    assert stored_dict[session.session_id]["current_state"] == "INITIALIZING"


def test_session_controlled_state_transitions():
    """Verify state transitions enforce from_state, to_state, trigger_agent, and audit logging."""
    req = AgyCodexSessionRequest(
        session_name="test-transition-session",
        directive="Analyze system topology"
    )
    session = session_engine.create_session(req)
    assert session.current_state == SessionState.INITIALIZING

    # Transition to SPEC_PROPOSAL
    session = session_engine.record_transition(
        session, SessionState.SPEC_PROPOSAL, "agent-research",
        "Architecture discovery initiated", {"scope": "AST"}
    )
    assert session.current_state == SessionState.SPEC_PROPOSAL
    assert len(session.transitions) == 1
    assert session.transitions[0].from_state == "INITIALIZING"
    assert session.transitions[0].to_state == "SPEC_PROPOSAL"
    assert session.transitions[0].trigger_agent == "agent-research"

    # Transition to CODE_SYNTHESIS
    session = session_engine.record_transition(
        session, SessionState.CODE_SYNTHESIS, "agent-dev",
        "Codex synthesizer generating code", {"files": ["main.py"]}
    )
    assert session.current_state == SessionState.CODE_SYNTHESIS
    assert len(session.transitions) == 2
    assert session.transitions[1].from_state == "SPEC_PROPOSAL"
    assert session.transitions[1].to_state == "CODE_SYNTHESIS"


# =============================================================================
# 2. End-to-End Workflow: AGY ↔ Codex ↔ Verifier ↔ Security
# =============================================================================

def test_agy_codex_full_successful_lifecycle():
    """Verify complete cooperative workflow across Planner -> Coder -> Verifier -> Security -> COMPLETED."""
    req = AgyCodexSessionRequest(
        session_name="test-full-lifecycle-session",
        directive="Validate passing test fixture and audit secrets",
        project_id="control-center",
        target_workspace="/root/control-center/data/fixtures/fixture-qa-passing",
        auto_rollback_on_failure=True
    )
    session = session_engine.create_session(req)
    executed = session_engine.execute_session(session.session_id)

    assert executed.status == "COMPLETED"
    assert executed.current_state == SessionState.COMPLETED
    assert executed.spec_proposal is not None
    assert executed.code_artifacts is not None
    assert executed.verification_results is not None
    assert executed.security_results is not None

    # Verify transitions trajectory
    states = [t.to_state for t in executed.transitions]
    assert "SPEC_PROPOSAL" in states
    assert "CODE_SYNTHESIS" in states
    assert "TEST_VERIFICATION" in states
    assert "SECURITY_AUDIT" in states
    assert "COMPLETED" in states


def test_agy_codex_feedback_loop_and_remediation():
    """Verify failed verification triggers FEEDBACK_REVISION and loops back to Codex coder."""
    req = AgyCodexSessionRequest(
        session_name="test-feedback-loop-session",
        directive="Fix failing test suite with remediation",
        project_id="control-center",
        target_workspace="/root/control-center/data/fixtures/fixture-qa-failing",
        max_revisions=2,
        auto_rollback_on_failure=True
    )
    session = session_engine.create_session(req)
    executed = session_engine.execute_session(session.session_id)

    # Because fixture-qa-failing deliberately fails assertions:
    # It must have attempted revisions up to max_revisions and rolled back!
    assert executed.revision_count == 2
    states = [t.to_state for t in executed.transitions]
    assert "FEEDBACK_REVISION" in states
    assert executed.current_state == SessionState.ROLLED_BACK
    assert executed.status == "ROLLED_BACK"


def test_session_automated_recovery_rollback():
    """Verify rollback_session restores workspace cleanly and emits audit record."""
    req = AgyCodexSessionRequest(
        session_name="test-rollback-session",
        directive="Attempt unauthorized modification and rollback",
        project_id="control-center",
        target_workspace="/root/control-center/data/fixtures/developer_test_repo"
    )
    session = session_engine.create_session(req)
    rolled = session_engine.rollback_session(session.session_id)

    assert rolled.status == "ROLLED_BACK"
    assert rolled.current_state == SessionState.ROLLED_BACK
    assert "Rolled back to baseline state" in rolled.error

    last_trans = rolled.transitions[-1]
    assert last_trans.to_state == "ROLLED_BACK"
    assert last_trans.trigger_agent == "agent-recovery"


def test_session_policy_and_approval_gating():
    """Verify session halts in AWAITING_APPROVAL if directive triggers critical policy."""
    req = AgyCodexSessionRequest(
        session_name="test-gated-session",
        directive="Production Deployment Hook and Cloud Run deploy",
        project_id="control-center"
    )
    session = session_engine.create_session(req)
    executed = session_engine.execute_session(session.session_id)

    assert executed.status == "AWAITING_APPROVAL"
    assert executed.current_state == SessionState.AWAITING_APPROVAL
    assert executed.approval_id is not None
    assert executed.approval_id.startswith("appr-")


# =============================================================================
# 3. Session API Endpoints
# =============================================================================

def test_api_session_lifecycle_endpoints():
    """Verify POST /sessions/create, GET /sessions/all, GET /sessions/{id}, POST /sessions/{id}/rollback."""
    create_resp = client.post(
        "/api/v1/agents/sessions/create?execute_now=false",
        json={
            "session_name": "api-session-test",
            "directive": "Inspect AST tree for backend server",
            "project_id": "control-center",
            "target_workspace": "/root/control-center/data/fixtures/fixture-qa-passing"
        }
    )
    assert create_resp.status_code == 200
    s_data = create_resp.json()["session"]
    sess_id = s_data["session_id"]
    assert sess_id.startswith("sess-")
    assert s_data["current_state"] == "INITIALIZING"

    # Verify GET /sessions/all
    all_resp = client.get("/api/v1/agents/sessions/all")
    assert all_resp.status_code == 200
    assert any(s["session_id"] == sess_id for s in all_resp.json())

    # Verify GET /sessions/{session_id}
    single_resp = client.get(f"/api/v1/agents/sessions/{sess_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["session_id"] == sess_id

    # Verify POST /sessions/{session_id}/rollback
    rb_resp = client.post(f"/api/v1/agents/sessions/{sess_id}/rollback")
    assert rb_resp.status_code == 200
    assert rb_resp.json()["status"] == "ROLLED_BACK"
    assert rb_resp.json()["session"]["current_state"] == "ROLLED_BACK"
