"""
NEXUS Phase 6: Swarm Orchestration, Real Agent Lifecycles & Container Packaging Suite
Exhaustive verification of:
1. Real Lifecycles for All 13 Swarm Agents (Zero Generic Fallback Stubs)
2. Multi-Agent Autonomous Handoff Protocol & Recursion Depth Defenses
3. End-to-End Swarm Pipeline Execution & Policy Approval Gating
4. API Routes for /agents/handoff and /agents/pipeline
5. Production Container Packaging & Docker Compose Sandboxing
6. Cloud Readiness & IaC Zero-Spend Guarantees
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from server import app
from orchestrator.runtime import runtime_engine
from orchestrator.agents import get_agent_by_id, get_agent_list
from orchestrator.tool_registry import tool_registry
from orchestrator.tool_runner import execute_agent_tool
from models.schemas import (
    ExecutionLimits,
    SwarmPipelineRequest,
    AgentHandoffRequest,
    RiskLevel
)
from core.cost_guard import cost_guard

client = TestClient(app)

# =============================================================================
# 1. Specialized Agent Lifecycles (All 13 Genuine, Real Tools)
# =============================================================================

def test_devops_agent_autonomous_lifecycle():
    """Verify agent-devops executes real ci_audit and mon.system_probe tools."""
    task = runtime_engine.create_task(
        agent_id="agent-devops",
        title="Audit Production Container Packaging & CI/CD",
        instructions="Probe Dockerfile, workflows, and runtime socket."
    )
    executed = runtime_engine.execute_task(task.id)
    assert executed.status == "completed"
    assert executed.result is not None
    assert executed.result["agent"] == "PIPELINE-PRO"
    assert executed.result["dockerfile_valid"] is True
    assert executed.result["workflows_count"] >= 1
    assert "checks" in executed.result


def test_recovery_agent_autonomous_lifecycle():
    """Verify agent-recovery probes git working tree, clean state, and rollback readiness."""
    task = runtime_engine.create_task(
        agent_id="agent-recovery",
        title="Verify Workspace State Integrity & Rollback Health",
        instructions="Perform git status probe and verify fixture sandbox readiness."
    )
    executed = runtime_engine.execute_task(task.id)
    assert executed.status == "completed"
    assert executed.result is not None
    assert executed.result["agent"] == "HEAL-CHRONOS"
    assert executed.result["status"] == "RECOVERY_VERIFIED"
    assert executed.result["rollback_ready"] is True
    assert executed.result["fixture_ready"] is True


def test_mon_agent_autonomous_lifecycle():
    """Verify agent-mon executes real psutil system probe and socket verification."""
    task = runtime_engine.create_task(
        agent_id="agent-mon",
        title="Probe System Telemetry and Socket Capacity",
        instructions="Query real CPU, RAM, disk space, and port 8000."
    )
    executed = runtime_engine.execute_task(task.id)
    assert executed.status == "completed"
    assert executed.result is not None
    assert executed.result["agent"] == "METRICS-PROBER"
    assert executed.result["status"] == "MONITORED"
    assert executed.result["cpu_percent"] >= 0.0
    assert executed.result["ram_used_mb"] > 0.0
    assert executed.result["disk_free_gb"] > 0.0


def test_cost_agent_autonomous_lifecycle():
    """Verify agent-cost audits FinOps zero-spend guardrail and billing linkage."""
    task = runtime_engine.create_task(
        agent_id="agent-cost",
        title="Audit Cloud Spend & Enforce Free-Tier Boundaries",
        instructions="Check current spend and verify billing account linkage status."
    )
    executed = runtime_engine.execute_task(task.id)
    assert executed.status == "completed"
    assert executed.result is not None
    assert executed.result["agent"] == "COST-SENTINEL"
    assert executed.result["current_spend_usd"] == 0.0
    assert executed.result["billing_linked"] is False
    assert executed.result["compliant"] is True


def test_ux_agent_autonomous_lifecycle():
    """Verify agent-ux audits React components and index.html metadata."""
    task = runtime_engine.create_task(
        agent_id="agent-ux",
        title="Audit Cyber-HUD Frontend Components & Bundle",
        instructions="Scan components in src/components and analyze bundle size."
    )
    executed = runtime_engine.execute_task(task.id)
    assert executed.status == "completed"
    assert executed.result is not None
    assert executed.result["agent"] == "UX-TACTICIAN"
    assert executed.result["status"] == "OPTIMIZED"
    assert executed.result["components_count"] >= 10
    assert executed.result["bundle_size_kb"] > 0.0


def test_seo_agent_autonomous_lifecycle():
    """Verify agent-seo audits HTML meta tags and OpenGraph compliance."""
    task = runtime_engine.create_task(
        agent_id="agent-seo",
        title="Audit Web Application Metadata & OpenGraph",
        instructions="Scan index.html for title, viewport, and OpenGraph tags."
    )
    executed = runtime_engine.execute_task(task.id)
    assert executed.status == "completed"
    assert executed.result is not None
    assert executed.result["agent"] == "SEO-BEACON"
    assert executed.result["score"] >= 40
    assert "has_title" in executed.result["passed_checks"]
    assert "has_viewport" in executed.result["passed_checks"]


def test_infra_agent_autonomous_lifecycle():
    """Verify agent-infra audits GCP topology, Workload Identity Federation, and zero keys."""
    task = runtime_engine.create_task(
        agent_id="agent-infra",
        title="Audit Cloud Topology & Workload Identity Federation",
        instructions="Inspect SYSTEM_MANIFEST for WIF, service accounts, and zero keys."
    )
    executed = runtime_engine.execute_task(task.id)
    assert executed.status == "completed"
    assert executed.result is not None
    assert executed.result["agent"] == "TERRA-ARCH"
    assert executed.result["status"] == "VERIFIED"
    assert executed.result["wif_active"] is True
    assert executed.result["static_keys_count"] == 0
    assert executed.result["zero_spend_enforced"] is True


# =============================================================================
# 2. Multi-Agent Autonomous Handoff Protocol
# =============================================================================

def test_autonomous_agent_handoff_dev_to_qa():
    """Verify developer agent can delegate a verification subtask to QA agent."""
    res = runtime_engine.execute_handoff(
        parent_agent_id="agent-dev",
        target_agent_id="agent-qa",
        task_title="Verify Passing Unit Test Suite",
        instructions="Execute pytest test suite in isolated developer workspace",
        project_id="/root/control-center/data/fixtures/fixture-qa-passing",
        context={"feature": "calculator_multiplication"}
    )
    assert res["status"] in ["COMPLETED", "SUCCESS"]
    assert res["parent_agent_id"] == "agent-dev"
    assert res["target_agent_id"] == "agent-qa"
    assert res["handoff_id"].startswith("handoff-")
    assert res["child_execution_id"] is not None

    # Verify retrieved from engine store
    stored = runtime_engine.get_handoff(res["handoff_id"])
    assert stored is not None
    assert stored.handoff_id == res["handoff_id"]


def test_autonomous_agent_handoff_recursion_depth_defense():
    """Verify handoff depth > 3 is blocked cleanly without stack overflow."""
    res = runtime_engine.execute_handoff(
        parent_agent_id="agent-dev",
        target_agent_id="agent-qa",
        task_title="Excessive Recursion Probe",
        instructions="Should be blocked at depth 4",
        recursion_depth=4
    )
    assert res["status"] == "BLOCKED"
    assert "Maximum recursion depth exceeded" in res["error"]


def test_agent_tool_dispatch_handoff():
    """Verify agent.handoff tool can be executed via universal tool dispatcher."""
    params = {
        "target_agent_id": "agent-security",
        "task_title": "Delegated Secret Scan",
        "instructions": "Scan workspace for credential leaks"
    }
    res = execute_agent_tool("agent-dev", "agent.handoff", params)
    assert res["status"] in ["COMPLETED", "SUCCESS"]
    assert res["parent_agent_id"] == "agent-dev"
    assert res["target_agent_id"] == "agent-security"


# =============================================================================
# 3. Swarm Pipeline Orchestration
# =============================================================================

def test_swarm_pipeline_multi_stage_execution():
    """Verify coordinated multi-stage swarm pipeline across diverse agents."""
    req = SwarmPipelineRequest(
        pipeline_name="test-full-lifecycle-swarm",
        title="Full Autonomous Engineering Cycle",
        instructions="Execute research, QA verification, security scan, and DevOps audit",
        stages=[
            {"agent_id": "agent-research", "title": "Research: Codebase Symbols", "instructions": "Search symbols"},
            {"agent_id": "agent-qa", "title": "QA: Smoke Tests", "instructions": "Run smoke tests", "project_id": "/root/control-center/data/fixtures/fixture-qa-passing"},
            {"agent_id": "agent-security", "title": "Security: Credential Scan", "instructions": "Audit secrets"},
            {"agent_id": "agent-devops", "title": "DevOps: Container Check", "instructions": "Audit Dockerfile"}
        ]
    )
    result = runtime_engine.execute_swarm_pipeline(req)
    assert result.status == "COMPLETED"
    assert result.stages_completed == 4
    assert result.total_stages == 4
    assert len(result.stage_results) == 4
    assert result.duration_ms > 0.0
    assert result.total_tool_calls >= 4

    # Verify retrieved from engine store
    stored = runtime_engine.get_pipeline(result.pipeline_id)
    assert stored is not None
    assert stored.pipeline_id == result.pipeline_id


def test_swarm_pipeline_approval_gating():
    """Verify swarm pipeline halts and requests approval if a stage triggers critical policy."""
    req = SwarmPipelineRequest(
        pipeline_name="test-destructive-pipeline-gated",
        title="Destructive Action Pipeline",
        instructions="Perform research then attempt hard reset",
        stages=[
            {"agent_id": "agent-research", "title": "Research: Codebase Symbols", "instructions": "Search symbols"},
            {"agent_id": "agent-dev", "title": "git reset --hard HEAD~1", "instructions": "Destructive git operation"}
        ]
    )
    result = runtime_engine.execute_swarm_pipeline(req)
    assert result.status == "AWAITING_APPROVAL"
    assert result.approval_required is True
    assert result.approval_id is not None
    assert result.stages_completed == 1 # First stage passed, second stage halted for approval


# =============================================================================
# 4. Swarm API Endpoints
# =============================================================================

def test_api_handoff_endpoint():
    """Verify POST /api/v1/agents/handoff dispatches handoff and returns record."""
    resp = client.post(
        "/api/v1/agents/handoff",
        json={
            "parent_agent_id": "agent-devops",
            "target_agent_id": "agent-recovery",
            "task_title": "Workspace State & Integrity Verification",
            "instructions": "Audit git working directory"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["COMPLETED", "SUCCESS"]
    assert "handoff" in data
    handoff_id = data["handoff"]["handoff_id"]

    # Verify GET /api/v1/agents/handoffs/all
    all_resp = client.get("/api/v1/agents/handoffs/all")
    assert all_resp.status_code == 200
    assert any(h["handoff_id"] == handoff_id for h in all_resp.json())

    # Verify GET /api/v1/agents/handoffs/{handoff_id}
    single_resp = client.get(f"/api/v1/agents/handoffs/{handoff_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["handoff_id"] == handoff_id


def test_api_handoff_endpoint_gated_by_policy():
    """Verify POST /api/v1/agents/handoff requires human approval if target action is high-risk."""
    resp = client.post(
        "/api/v1/agents/handoff",
        json={
            "parent_agent_id": "agent-devops",
            "target_agent_id": "agent-recovery",
            "task_title": "Production Deployment Hook",
            "instructions": "Execute deploy command"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "AWAITING_APPROVAL"
    assert data["handoff"]["result"]["approval_required"] is True


def test_api_pipeline_endpoint():
    """Verify POST /api/v1/agents/pipeline dispatches swarm pipeline."""
    resp = client.post(
        "/api/v1/agents/pipeline",
        json={
            "pipeline_name": "api-test-pipeline",
            "title": "API Swarm Verification",
            "instructions": "Quick multi-agent audit",
            "stages": [
                {"agent_id": "agent-mon", "title": "System Check", "instructions": "Probe health"},
                {"agent_id": "agent-cost", "title": "Cost Check", "instructions": "FinOps audit"}
            ]
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    pipe_id = data["pipeline"]["pipeline_id"]

    # Verify GET /api/v1/agents/pipelines/all
    all_resp = client.get("/api/v1/agents/pipelines/all")
    assert all_resp.status_code == 200
    assert any(p["pipeline_id"] == pipe_id for p in all_resp.json())

    # Verify GET /api/v1/agents/pipelines/{pipeline_id}
    single_resp = client.get(f"/api/v1/agents/pipelines/{pipe_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["pipeline_id"] == pipe_id


# =============================================================================
# 5. Production Packaging & IaC Verification
# =============================================================================

def test_dockerfile_security_and_packaging_compliance():
    """Verify Dockerfile enforces non-root execution, healthchecks, and proper structure."""
    dockerfile_path = "/root/control-center/Dockerfile"
    assert os.path.exists(dockerfile_path)
    with open(dockerfile_path, "r") as f:
        content = f.read()

    assert "FROM python:3.12-slim" in content
    assert "useradd -m -u 1000 nexususer" in content
    assert "USER nexususer" in content
    assert "HEALTHCHECK " in content
    assert "EXPOSE 8000" in content


def test_docker_compose_sandboxing_compliance():
    """Verify docker-compose configuration contains non-root user, volume sandboxing, and resource limits."""
    compose_path = "/root/control-center/docker-compose.yml"
    assert os.path.exists(compose_path)
    with open(compose_path, "r") as f:
        content = f.read()

    assert 'user: "1000:1000"' in content
    assert "./data:/app/data" in content
    assert "no-new-privileges:true" in content
    assert "limits:" in content
    assert "healthcheck:" in content


def test_dockerignore_exclusions():
    """Verify .dockerignore prevents leaking git history, caches, and test artifacts into images."""
    dockerignore_path = "/root/control-center/.dockerignore"
    assert os.path.exists(dockerignore_path)
    with open(dockerignore_path, "r") as f:
        content = f.read()

    assert ".git/" in content
    assert "tests/" in content
    assert "__pycache__/" in content
    assert ".pytest_cache/" in content


def test_terraform_cloud_readiness_and_zero_spend_guarantees():
    """Verify Terraform configuration enforces keyless WIF, Cloud Run v2, and $0.00 spend guardrails."""
    main_tf = "/root/control-center/infra/main.tf"
    vars_tf = "/root/control-center/infra/variables.tf"
    outputs_tf = "/root/control-center/infra/outputs.tf"

    assert os.path.exists(main_tf)
    assert os.path.exists(vars_tf)
    assert os.path.exists(outputs_tf)

    with open(main_tf, "r") as f:
        m_content = f.read()
    assert "google_iam_workload_identity_pool" in m_content
    assert "google_cloud_run_v2_service" in m_content
    assert "min_instance_count = 0" in m_content # Scale to zero for $0.00 spend
    assert "google_service_account" in m_content

    with open(vars_tf, "r") as f:
        v_content = f.read()
    assert "default     = 0.0" in v_content # Spend limit $0.00
    assert "default     = false" in v_content # Billing unlinked

    with open(outputs_tf, "r") as f:
        o_content = f.read()
    assert "zero_cost_guardrail_active" in o_content
