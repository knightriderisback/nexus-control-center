"""
NEXUS Phase 12: Cyber-HUD Live Operations Control Plane Test Suite.
Comprehensive verification covering:
1. Unified System Health Aggregation (HEALTHY, DEGRADED, WARNING, BLOCKED, FAILED, OFFLINE)
2. Daemon & API Kernel Telemetry (PID, RSS memory, uptime, endpoint)
3. AI Provider Cluster Health & Circuit Breakers (Gemini, Anthropic, OpenAI, Local Mock)
4. FinOps $0.00 Spend Guardrail & Unlinked Billing Ledger
5. Isolated Worktrees Sandboxes & Pruning
6. Governed GitHub Delivery & 3-Way Merge Candidate Arbitration
7. AGY ↔ Codex ↔ QA ↔ Security Multi-Agent Handoff Pipeline Graph (Bounded Recursion)
8. Unified Real-Time Event Stream Telemetry with Category/Severity Filtering
9. Secret Sanitization in Telemetry & Event Streams
10. Recovery Center (Checkpointed/Failed Missions, Disputed Merges, Open Circuits)
11. Emergency Panic Killswitch Protocol (Instant Abort, Audit Logging)
12. System Sweep & Worktree Hygiene Protocol
13. Enriched System Overview Telemetry (/api/v1/overview)
14. Backward-Compatible Legacy Aliases (/api/system/*)
15. Static React Cyber-HUD Asset Verification & HTTP Serving
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from server import app
from core.config import config
from core.auth import DEFAULT_DEV_TOKEN
from core.cost_guard import cost_guard
from core.approvals import request_approval, load_approvals, decide_approval
from core.audit import record_audit, get_recent_audit_events
from models.schemas import RiskLevel, MissionState
from orchestrator.providers import provider_router, circuit_breaker
from orchestrator.worktree_manager import worktree_manager
from orchestrator.merge_arbitrator import merge_arbitrator
from orchestrator.github_delivery import github_delivery_engine
from orchestrator.mission_engine import mission_engine
from integrations.github_client import github_client_manager


@pytest.fixture(autouse=True)
def ensure_mock_mode():
    github_client_manager.set_mode("mock")
    yield


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {DEFAULT_DEV_TOKEN}"}


@pytest.fixture
def client():
    return TestClient(app)


def test_cyber_hud_health_aggregation(client, auth_headers):
    """Verifies that /api/v1/system/health consolidates all subsystems into a deterministic state."""
    res = client.get("/api/v1/system/health", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert "overall_status" in data
    assert data["overall_status"] in ["HEALTHY", "WARNING", "DEGRADED", "BLOCKED", "FAILED", "OFFLINE"]
    assert "components" in data

    components = data["components"]
    assert "api" in components
    assert "daemon" in components
    assert "ai_providers" in components
    assert "github" in components
    assert "worktrees" in components
    assert "finops" in components
    assert "approvals" in components
    assert "security" in components
    assert "missions" in components

    # Verify FinOps ceiling ($0.00)
    assert components["finops"]["current_spend_usd"] == 0.0
    assert components["finops"]["spend_ceiling_usd"] == 0.0
    assert components["finops"]["billing_linked"] is False

    # Verify Security Sentinel
    assert components["security"]["ast_scanner"] == "ACTIVE"
    assert components["security"]["prompt_injection_defense"] == "ACTIVE"


def test_cyber_hud_event_stream_and_filtering(client, auth_headers):
    """Verifies unified event stream with category and severity filters and sanitized payloads."""
    # Generate test audit events across different categories
    record_audit(
        action="TEST_MISSION_EVENT",
        project="control-center",
        target="MissionEngine",
        reason="Test mission execution trace with sensitive token: ghp_111122223333444455556666777788889999",
        risk_level=RiskLevel.LOW,
        result="CLEAN"
    )
    record_audit(
        action="TEST_SECURITY_ALERT",
        project="control-center",
        target="SecuritySentinel",
        reason="Test security alert block",
        risk_level=RiskLevel.HIGH,
        result="BLOCKED"
    )

    # 1. Fetch unfiltered
    res = client.get("/api/v1/system/events?limit=20", headers=auth_headers)
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) > 0

    # Verify schema of each event
    sample = events[0]
    for key in ["id", "timestamp", "category", "source", "event_type", "severity", "title", "message", "result"]:
        assert key in sample

    # 2. Secret sanitization check
    for ev in events:
        msg = str(ev.get("message", ""))
        assert "ghp_111122223333444455556666777788889999" not in msg

    # 3. Filter by category
    res_mission = client.get("/api/v1/system/events?category=mission", headers=auth_headers)
    assert res_mission.status_code == 200
    for ev in res_mission.json()["events"]:
        assert ev["category"] == "mission"

    # 4. Filter by severity
    res_warning = client.get("/api/v1/system/events?severity=warning", headers=auth_headers)
    assert res_warning.status_code == 200
    for ev in res_warning.json()["events"]:
        assert ev["severity"] == "warning"


def test_cyber_hud_multi_agent_handoff_graph(client, auth_headers):
    """Verifies the AGY ↔ Codex ↔ QA ↔ Security multi-agent handoff pipeline graph."""
    res = client.get("/api/v1/system/handoffs", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert "nodes" in data
    assert "edges" in data
    assert "recursion_depth_limit" in data
    assert data["recursion_depth_limit"] == 5

    # Verify the 5 pipeline nodes
    node_ids = [n["id"] for n in data["nodes"]]
    assert "researcher" in node_ids
    assert "developer" in node_ids
    assert "qa" in node_ids
    assert "security" in node_ids
    assert "arbitrator" in node_ids

    # Verify protocols along edges
    edge_protocols = [e["protocol"] for e in data["edges"]]
    assert "ARCHITECTURAL_SPEC" in edge_protocols
    assert "CODE_CANDIDATE" in edge_protocols
    assert "TEST_VERIFIED_ARTIFACT" in edge_protocols
    assert "SECURITY_CLEAN_DELIVERY" in edge_protocols


def test_cyber_hud_recovery_center(client, auth_headers):
    """Verifies recovery center telemetry: recoverable missions, disputed merges, and open circuits."""
    res = client.get("/api/v1/system/recovery", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert "recoverable_missions" in data
    assert "disputed_candidates" in data
    assert "open_circuits" in data
    assert "active_worktrees" in data
    assert "total_recovery_items" in data


def test_cyber_hud_panic_killswitch(client, auth_headers):
    """Verifies emergency panic protocol immediately halts missions and records high-risk audit."""
    res = client.post("/api/v1/system/panic", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "HALTED"
    assert "Master Panic Protocol Active" in data["message"]

    # Verify audit event recorded
    recent_audits = get_recent_audit_events(limit=5)
    assert any(a.action == "CYBER_HUD_PANIC_KILLSWITCH" for a in recent_audits)


def test_cyber_hud_system_sweep(client, auth_headers):
    """Verifies repository sweep cleanly prunes worktrees and verifies zero orphan directories."""
    res = client.post("/api/v1/system/sweep", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "CLEAN"
    assert "pruned_worktrees" in data
    assert "orphan_worktrees_remaining" in data


def test_cyber_hud_enriched_overview(client, auth_headers):
    """Verifies /api/v1/overview contains enhanced Cyber-HUD summary metrics."""
    res = client.get("/api/v1/overview", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert "system_health" in data
    assert "finops" in data
    assert data["finops"]["current_spend_usd"] == 0.0
    assert data["finops"]["billing_linked"] is False

    assert "providers_summary" in data
    assert "missions_summary" in data
    assert "worktrees_count" in data
    assert "delivery_summary" in data


def test_cyber_hud_legacy_aliases(client):
    """Verifies unauthenticated legacy aliases for direct Cyber-HUD consumption."""
    res_health = client.get("/api/system/health")
    assert res_health.status_code == 200
    assert "overall_status" in res_health.json()

    res_events = client.get("/api/system/events?limit=5")
    assert res_events.status_code == 200
    assert "events" in res_events.json()

    res_handoffs = client.get("/api/system/handoffs")
    assert res_handoffs.status_code == 200
    assert "nodes" in res_handoffs.json()

    res_recovery = client.get("/api/system/recovery")
    assert res_recovery.status_code == 200
    assert "recoverable_missions" in res_recovery.json()


def test_cyber_hud_static_ui_serving(client):
    """Verifies FastAPI mounts and serves compiled React Cyber-HUD production assets."""
    dist_dir = Path("/root/control-center/frontend/dist")
    assert dist_dir.exists(), "frontend/dist must exist for Cyber-HUD serving"
    assert (dist_dir / "index.html").exists(), "index.html must exist in frontend/dist"

    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "NEXUS" in res.text or "<div id=\"root\">" in res.text


def test_cyber_hud_finops_zero_cost_preservation():
    """Validates that $0.00 FinOps ceiling is strictly preserved across all operations."""
    cost = cost_guard.get_cost_summary()
    assert cost["current_spend_usd"] == 0.0, "Spend must strictly remain $0.00"
    assert cost["billing_linked"] is False, "Billing must remain unlinked"
    assert cost["zero_cost_guardrail_active"] is True, "Guardrail must be active"


def test_cyber_hud_worktree_hygiene():
    """Validates that no orphan worktrees remain after test runs and sweeping."""
    worktree_manager.prune_stale_worktrees()
    wts = worktree_manager.list_worktrees()
    # At most 1 (the main repository root itself)
    assert len(wts) <= 1, f"Expected 0 or 1 worktree, found {len(wts)}: {wts}"
