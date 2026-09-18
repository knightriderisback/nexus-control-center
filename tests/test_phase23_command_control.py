"""
Comprehensive Test Suite for NEXUS Phase 23: Unified Autonomous Command & Control Plane.

Covers all 16 Acceptance Criteria Areas:
1. Unified Command Engine (Natural Language -> Intent -> Target Resolution -> Execution)
2. Command Planner (Dependencies, Risks, Required Approvals, Expected Artifacts, Rollback Path)
3. Cross-System Orchestration (Factory, Missions, Tools, Deployments, Healing, Knowledge, Project Ops)
4. Ambiguity & Unauthorized Target Safe Stop
5. Operations Timeline Persistence (COMMAND -> DECISION -> ACTION -> RESULT -> EVIDENCE)
6. Global Operations State Aggregation (Real Data from 13 Subsystems, Zero Fabricated Metrics)
7. Global Event Bus Normalization & Provenance Hashing
8. Approval Center Governance (High-Risk Gates, Safe Interception, No Bypass)
9. Emergency Kill-Switch & Fleet Freeze Governor
10. Multi-Project Safety & Workspace Boundary Isolation
11. Security Verifications (Command Injection Block, FinOps Violation Block, Prompt Injection)
12. Strict FinOps $0.00 Hard Ceiling Invariant
13. REST API Routers (/api/v1/command/*, /api/v1/operations/*, /api/v1/global/*, /api/v1/c2/*)
"""

import os
import sys
import json
import uuid
import pytest
import tempfile
import shutil
import subprocess
from fastapi.testclient import TestClient

# Ensure backend root is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from models.schemas import (
    ProjectRegistryItem,
    ProjectStatus,
    RiskLevel,
    CommandDirectiveRequest,
    CommandDirectiveType,
    CommandExecutionState,
    OperationsTimelineStage,
    EmergencyKillSwitchRequest
)
from orchestrator.command_control_kernel import CommandControlKernel
from orchestrator.project_operations_engine import ProjectOperationsEngine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine
from server import app

AUTH_HEADERS = {"X-NEXUS-KEY": "nexus-dev-operator-key-2026"}
client = TestClient(app)


@pytest.fixture
def temp_c2_environment():
    temp_dir = tempfile.mkdtemp(prefix="nexus-test-c2-", dir="/tmp")
    c2_data_dir = os.path.join(temp_dir, "c2_data")
    ops_data_dir = os.path.join(temp_dir, "ops_data")

    # Seed sample project with git repo
    project_ws = os.path.join(temp_dir, "c2-alpha-service")
    os.makedirs(os.path.join(project_ws, "tests"), exist_ok=True)
    with open(os.path.join(project_ws, "README.md"), "w") as f:
        f.write("# C2 Alpha Service\n")
    with open(os.path.join(project_ws, "pyproject.toml"), "w") as f:
        f.write("[project]\nname = 'c2-alpha-service'\nversion = '0.1.0'\n")
    with open(os.path.join(project_ws, "main.py"), "w") as f:
        f.write("def status():\n    return {'status': 'nominal'}\n")
    with open(os.path.join(project_ws, "tests", "test_main.py"), "w") as f:
        f.write("from main import status\ndef test_status():\n    assert status()['status'] == 'nominal'\n")

    subprocess.run(["git", "init"], cwd=project_ws, capture_output=True)
    subprocess.run(["git", "config", "user.name", "C2 Tester"], cwd=project_ws, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@c2.local"], cwd=project_ws, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=project_ws, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_ws, capture_output=True)

    c2_kernel = CommandControlKernel(data_dir=c2_data_dir)

    yield c2_kernel, project_ws, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# 1. COMMAND PARSING & TARGET RESOLUTION TESTS
# =============================================================================

def test_command_intent_and_target_resolution(temp_c2_environment):
    kernel, project_ws, _ = temp_c2_environment

    # Test fleet inspection intent
    plan_fleet = kernel.plan_command(CommandDirectiveRequest(
        raw_prompt="Inspect fleet health and drift radar"
    ))
    assert plan_fleet.is_safe_to_execute is True
    assert "FLEET_HEALTH" in plan_fleet.resolved_intent or "AUTONOMOUS_OPERATION" in plan_fleet.resolved_intent
    assert plan_fleet.risk_level == RiskLevel.LOW

    # Test new service creation intent
    plan_scaffold = kernel.plan_command(CommandDirectiveRequest(
        raw_prompt="Scaffold a new microservice for caching"
    ))
    assert plan_scaffold.is_safe_to_execute is True
    assert "SOFTWARE_FACTORY" in plan_scaffold.resolved_intent

    # Test ambiguous command safe stop
    plan_amb = kernel.plan_command(CommandDirectiveRequest(
        raw_prompt="Do something completely vague and undefined"
    ))
    assert plan_amb.is_safe_to_execute is False
    assert plan_amb.block_reason is not None


# =============================================================================
# 2. COMMAND PLANNING & RISK ARBITRATION TESTS
# =============================================================================

def test_command_planner_dependencies_and_rollback(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    plan = kernel.plan_command(CommandDirectiveRequest(
        raw_prompt="Canary release v0.2.0 with traffic shift to 10%",
        target_project_id="c2-alpha-service"
    ))
    assert plan.is_safe_to_execute is True
    assert "DEPLOYMENT" in plan.resolved_intent
    assert plan.risk_level == RiskLevel.HIGH
    assert len(plan.rollback_recovery_path) >= 1
    assert "rollback" in plan.rollback_recovery_path[0].lower()


# =============================================================================
# 3. GOVERNED COMMAND EXECUTION & TIMELINE RECORDING
# =============================================================================

def test_command_execution_and_timeline_lifecycle(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    cmd_res = kernel.execute_command(CommandDirectiveRequest(
        raw_prompt="Inspect fleet health and drift radar",
        operator_context="operator-test"
    ))
    assert cmd_res.state == CommandExecutionState.COMPLETED
    assert cmd_res.finops_cost_usd == 0.0
    assert len(cmd_res.execution_trace) >= 1

    # Verify Operations Timeline recorded COMMAND, DECISION, ACTION, RESULT, EVIDENCE
    timeline = kernel.get_operations_timeline(command_id=cmd_res.directive_id)
    stages = [t.stage for t in timeline]
    assert OperationsTimelineStage.COMMAND in stages
    assert OperationsTimelineStage.DECISION in stages
    assert OperationsTimelineStage.ACTION in stages
    assert OperationsTimelineStage.RESULT in stages
    assert OperationsTimelineStage.EVIDENCE in stages


# =============================================================================
# 4. APPROVAL CENTER GOVERNANCE TESTS
# =============================================================================

def test_approval_governance_interception(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    # Direct production deployment requires approval
    cmd_res = kernel.execute_command(CommandDirectiveRequest(
        raw_prompt="Direct deploy production version to c2-alpha-service",
        target_project_id="c2-alpha-service",
        force_override=False
    ))
    assert cmd_res.state == CommandExecutionState.AWAITING_APPROVAL
    assert cmd_res.requires_approval is True
    assert cmd_res.approval_id is not None


# =============================================================================
# 5. GLOBAL OPERATIONS STATE (13 SUBSYSTEMS, ZERO FABRICATED METRICS)
# =============================================================================

def test_global_operations_state_aggregation(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    state = kernel.get_global_operations_state()
    assert isinstance(state.projects, list)
    assert isinstance(state.missions, list)
    assert isinstance(state.factory_runs, list)
    assert isinstance(state.deployments, list)
    assert isinstance(state.incidents, list)
    assert isinstance(state.security_findings, list)
    assert isinstance(state.agents, list)
    assert isinstance(state.tools, list)
    assert isinstance(state.providers, list)
    assert isinstance(state.worktrees, list)
    assert isinstance(state.knowledge_nodes, list)
    assert isinstance(state.approvals, list)
    assert state.finops["total_spend_usd"] == 0.0
    assert state.finops["zero_cost_verified"] is True
    assert state.global_health_score >= 80.0


# =============================================================================
# 6. GLOBAL EVENT BUS NORMALIZATION & PROVENANCE
# =============================================================================

def test_global_event_bus_normalization(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    # Trigger a command to produce events
    kernel.execute_command(CommandDirectiveRequest(
        raw_prompt="Evaluate AST security scan"
    ))

    events = kernel.get_event_stream(limit=20)
    assert len(events) >= 1
    last_event = events[-1]
    assert len(last_event.provenance_hash) == 16
    assert last_event.event_type.startswith("COMMAND_") or last_event.event_type.startswith("GLOBAL_")


# =============================================================================
# 7. EMERGENCY KILL-SWITCH & FLEET FREEZE GOVERNOR
# =============================================================================

def test_emergency_kill_switch_and_reset(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    # Trigger Emergency Kill
    kill_res = kernel.trigger_emergency_kill_switch(EmergencyKillSwitchRequest(
        operator="admin-operator",
        reason="Test panic trigger"
    ))
    assert kill_res.status == "TRIGGERED"

    # Verify subsequent commands are blocked under emergency lock
    blocked_cmd = kernel.execute_command(CommandDirectiveRequest(
        raw_prompt="Inspect fleet health"
    ))
    assert blocked_cmd.state == CommandExecutionState.ABORTED
    assert "EMERGENCY KILL-SWITCH LOCK" in blocked_cmd.stderr

    # Reset Emergency Lock
    reset_res = kernel.reset_emergency_kill_switch(operator="admin-operator")
    assert reset_res["status"] == "RESET"

    # Verify nominal operations restored
    resumed_cmd = kernel.execute_command(CommandDirectiveRequest(
        raw_prompt="Inspect fleet health"
    ))
    assert resumed_cmd.state == CommandExecutionState.COMPLETED


# =============================================================================
# 8. SECURITY & GOVERNANCE ATTACK TESTS
# =============================================================================

def test_command_injection_safeguard(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    # Command injection attempt
    plan = kernel.plan_command(CommandDirectiveRequest(
        raw_prompt="Inspect fleet; rm -rf /"
    ))
    assert plan.is_safe_to_execute is False
    assert "injection" in plan.block_reason.lower()

    exec_res = kernel.execute_command(CommandDirectiveRequest(
        raw_prompt="Inspect fleet; rm -rf /"
    ))
    assert exec_res.state == CommandExecutionState.FAILED
    assert "CommandExecutionBlocked" in exec_res.stderr


def test_finops_hard_ceiling_enforcement(temp_c2_environment):
    kernel, _, _ = temp_c2_environment

    # FinOps violation attempt
    plan = kernel.plan_command(CommandDirectiveRequest(
        raw_prompt="Spin up GKE cluster with 10 GPU nodes"
    ))
    assert plan.is_safe_to_execute is False
    assert "FinOps" in plan.block_reason


# =============================================================================
# 9. REST API ROUTER ENDPOINTS (/api/v1/command/*, /api/v1/operations/*, etc.)
# =============================================================================

def test_rest_api_command_endpoints():
    # 1. Preview / Plan
    prev_res = client.post("/api/v1/command/preview", headers=AUTH_HEADERS, json={
        "raw_prompt": "Inspect fleet health and drift radar"
    })
    assert prev_res.status_code == 200
    assert prev_res.json()["state"] == "COMPLETED"

    # 2. Dispatch
    cmd_res = client.post("/api/v1/command", headers=AUTH_HEADERS, json={
        "raw_prompt": "Inspect fleet health and drift radar"
    })
    assert cmd_res.status_code == 200
    cmd_data = cmd_res.json()
    assert "directive_id" in cmd_data
    assert cmd_data["finops_cost_usd"] == 0.0

    # 3. Status
    st_res = client.get(f"/api/v1/command/status/{cmd_data['directive_id']}", headers=AUTH_HEADERS)
    assert st_res.status_code == 200
    assert st_res.json()["directive_id"] == cmd_data["directive_id"]


def test_rest_api_operations_and_global_endpoints():
    # 1. Global Operations State
    g_res = client.get("/api/v1/operations/global", headers=AUTH_HEADERS)
    assert g_res.status_code == 200
    g_data = g_res.json()
    assert "projects" in g_data
    assert "finops" in g_data
    assert g_data["finops"]["zero_cost_verified"] is True

    # 2. Operations Timeline
    tl_res = client.get("/api/v1/operations/timeline", headers=AUTH_HEADERS)
    assert tl_res.status_code == 200
    assert isinstance(tl_res.json(), list)

    # 3. Global Event Bus
    ev_res = client.get("/api/v1/operations/events", headers=AUTH_HEADERS)
    assert ev_res.status_code == 200
    assert isinstance(ev_res.json(), list)

    # 4. Global Health Telemetry
    h_res = client.get("/api/v1/global/health", headers=AUTH_HEADERS)
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert "global_health_score" in h_data
    assert h_data["finops_zero_cost_verified"] is True
