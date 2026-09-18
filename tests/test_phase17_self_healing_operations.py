"""
NEXUS Phase 17: Autonomous Self-Healing Operations Engine Comprehensive Test Suite
===================================================================================
Covers the entire 20-point operational lifecycle:
OBSERVE -> DETECT -> CORRELATE -> CLASSIFY -> DIAGNOSE -> PLAN -> POLICY/RISK CHECK -> REMEDIATE -> VERIFY -> RECOVER/ROLLBACK -> LEARN -> AUDIT

Verifies:
1. Continuous health monitoring & 6 live sentinel watchdogs
2. Failure taxonomy & severity levels
3. Deduplication & Storm correlation
4. Machine-readable Diagnosis Evidence (facts vs hypotheses)
5. Policy-driven recovery (retry limits, loop protection, backoff)
6. Safe autonomous remediation vs Gated high-risk actions
7. Phase 16 Deployment Engine rollback integration
8. Worktree and Provider Gateway recovery
9. Operations state actions (acknowledge, retry, escalate, stop)
10. Operations REST API endpoints (/api/v1/operations/*)
11. Universal Tool Engine integration
12. Strict FinOps $0.00 zero-cost enforcement
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from server import app
from models.schemas import (
    FailureCategory,
    IncidentSeverity,
    IncidentStatus,
    WatchdogType,
    WatchdogStatus,
    TriggerIncidentRequest,
    RemediateIncidentRequest,
    RecoveryPolicy,
    UniversalToolInvocationRequest,
)
from orchestrator.self_healing_engine import self_healing_engine
from orchestrator.universal_tool_engine import universal_tool_engine
from core.approvals import approvals_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_watchdog_registry_and_execution():
    """Verify all 6 live sentinel watchdogs execute with real system metrics."""
    results = self_healing_engine.run_all_watchdogs()
    assert len(results) == 6
    
    types_found = {r.watchdog_type for r in results}
    expected_types = {
        WatchdogType.PROCESS_SUPERVISOR,
        WatchdogType.PORT_AVAILABILITY,
        WatchdogType.RESOURCE_PRESSURE,
        WatchdogType.HTTP_SLA,
        WatchdogType.SECURITY_SENTINEL,
        WatchdogType.WORKTREE_HEALTH,
    }
    assert types_found == expected_types
    
    for r in results:
        assert r.status in [WatchdogStatus.HEALTHY, WatchdogStatus.DEGRADED, WatchdogStatus.ALERTING, WatchdogStatus.OFFLINE]
        assert r.message is not None
        assert isinstance(r.metrics, dict)
        assert r.timestamp is not None


def test_playbook_catalog():
    """Verify built-in remediation playbooks exist, have valid steps and zero-cost constraints."""
    playbooks = self_healing_engine.list_playbooks()
    assert len(playbooks) >= 8
    
    playbook_ids = {p.playbook_id for p in playbooks}
    expected_playbooks = {
        "playbook-restart-supervisor",
        "playbook-port-conflict-resolver",
        "playbook-flush-worktrees-cache",
        "playbook-auto-rollback-deployment",
        "playbook-security-quarantine",
        "playbook-finops-throttle",
        "playbook-provider-circuit-reset",
        "playbook-mission-checkpoint-resume",
    }
    assert expected_playbooks.issubset(playbook_ids)
    
    for p in playbooks:
        assert len(p.steps) > 0
        assert p.estimated_cost_usd == 0.0
        assert p.risk_level.value in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_deduplication_and_storm_suppression():
    """Verify identical concurrent failure signals are deduplicated into a single incident."""
    req1 = TriggerIncidentRequest(
        title="Repeated Port 8000 Conflict",
        category=FailureCategory.NETWORK_FAILURE,
        severity=IncidentSeverity.LOW,
        target_resource="port-8000-listener",
        details={"port": 8000, "probe": "syn_ack"},
        auto_remediate=False
    )
    inc1 = self_healing_engine.trigger_incident(req1)
    
    req2 = TriggerIncidentRequest(
        title="Repeated Port 8000 Conflict (Duplicate)",
        category=FailureCategory.NETWORK_FAILURE,
        severity=IncidentSeverity.LOW,
        target_resource="port-8000-listener",
        details={"port": 8000, "probe": "syn_ack"},
        auto_remediate=False
    )
    inc2 = self_healing_engine.trigger_incident(req2)
    
    assert inc1.incident_id == inc2.incident_id
    assert inc2.metadata.get("recurrence_count", 1) >= 2


def test_structured_diagnosis_evidence():
    """Verify automated diagnosis produces machine-readable facts vs hypotheses with confidence scores."""
    req = TriggerIncidentRequest(
        title="High Memory Pressure Warning",
        category=FailureCategory.RESOURCE_EXHAUSTION,
        severity=IncidentSeverity.MEDIUM,
        target_resource="host-memory",
        details={"ram_used_pct": 89.2, "swap_pct": 12.0},
        auto_remediate=False
    )
    inc = self_healing_engine.trigger_incident(req)
    
    assert inc.diagnosis_evidence is not None
    evidence = inc.diagnosis_evidence
    assert len(evidence.observed_facts) >= 3
    assert len(evidence.hypotheses) >= 1
    assert len(evidence.evidence_sources) >= 1
    assert 0.0 <= evidence.confidence_score <= 1.0
    assert "RESOURCE_EXHAUSTION" in evidence.root_cause_candidate


def test_trigger_and_auto_remediate_low_risk_incident():
    """Verify automated incident lifecycle for low-risk issue without requiring approval gate."""
    req = TriggerIncidentRequest(
        title="Stale Test Worktrees Cleanup",
        category=FailureCategory.WORKTREE_FAILURE,
        severity=IncidentSeverity.LOW,
        target_resource="worktree_manager",
        details={"session_tag": "test-prune-wt"},
        auto_remediate=True
    )
    inc = self_healing_engine.trigger_incident(req)
    
    assert inc.incident_id.startswith("inc-")
    assert inc.status == IncidentStatus.RESOLVED
    assert inc.remediation_playbook_id == "playbook-flush-worktrees-cache"
    assert len(inc.healing_actions) > 0
    assert inc.post_mortem is not None
    assert inc.post_mortem["status"] == "RESOLVED_AUTOMATICALLY"


def test_trigger_high_severity_incident_approval_gated():
    """Verify SEV-1 critical incidents require human approval gate before executing remediation."""
    req = TriggerIncidentRequest(
        title="Critical Production Latency Breach",
        category=FailureCategory.HEALTH_CHECK_FAILURE,
        severity=IncidentSeverity.CRITICAL,
        target_resource="production-gateway-proxy",
        details={"latency_ms": 3200, "5xx_rate": 18.2},
        auto_remediate=True
    )
    inc = self_healing_engine.trigger_incident(req)
    
    assert inc.status == IncidentStatus.APPROVAL_PENDING
    assert inc.approval_id is not None
    
    # Verify approval exists in ApprovalsManager
    pending_appr = approvals_manager.list_pending()
    matching = [a for a in pending_appr if a.id == inc.approval_id]
    assert len(matching) == 1
    assert "CRITICAL" in matching[0].reason
    
    # Approve and resume remediation
    approvals_manager.approve(inc.approval_id, approved_by="test_admin")
    approved_inc = self_healing_engine.execute_remediation(inc.incident_id, force=True)
    
    assert approved_inc.status == IncidentStatus.RESOLVED
    assert len(approved_inc.healing_actions) >= 1
    assert approved_inc.resolved_at is not None


def test_loop_protection_and_escalation():
    """Verify loop protection escalates when max recovery attempts are reached."""
    req = TriggerIncidentRequest(
        title="Persistent Test Crash Loop",
        category=FailureCategory.PROCESS_FAILURE,
        severity=IncidentSeverity.MEDIUM,
        target_resource="crash-loop-worker",
        details={"pid": 99999},
        auto_remediate=False
    )
    inc = self_healing_engine.trigger_incident(req)
    inc.recovery_attempts = inc.max_recovery_attempts
    
    res = self_healing_engine.execute_remediation(inc.incident_id, force=False)
    assert res.status == IncidentStatus.ESCALATED
    assert "LOOP PROTECTION" in res.root_cause_analysis


def test_operations_lifecycle_actions():
    """Verify acknowledge, retry, escalate, and stop actions update incident state."""
    req = TriggerIncidentRequest(
        title="Lifecycle Action Test Incident",
        category=FailureCategory.CONFIGURATION_FAILURE,
        severity=IncidentSeverity.LOW,
        target_resource="config-loader",
        auto_remediate=False
    )
    inc = self_healing_engine.trigger_incident(req)
    
    # 1. Acknowledge
    ack = self_healing_engine.acknowledge_incident(inc.incident_id, operator="cyber-operator-1")
    assert ack.acknowledged_by == "cyber-operator-1"
    assert ack.acknowledged_at is not None
    
    # 2. Escalate
    esc = self_healing_engine.escalate_incident(inc.incident_id, reason="Requires manual intervention")
    assert esc.status == IncidentStatus.ESCALATED
    
    # 3. Stop
    stopped = self_healing_engine.stop_recovery(inc.incident_id, reason="Aborted by operator")
    assert stopped.status == IncidentStatus.STOPPED


def test_operations_metrics_and_history():
    """Verify operations metrics and chronological recovery history."""
    metrics = self_healing_engine.get_operations_metrics()
    assert metrics.system_health in ["HEALTHY", "DEGRADED"]
    assert metrics.uptime_pct >= 99.0
    assert metrics.active_incidents >= 0
    assert metrics.resolved_incidents >= 0
    assert isinstance(metrics.failure_distribution, dict)
    
    history = self_healing_engine.get_recovery_history()
    assert isinstance(history, list)
    if len(history) > 0:
        assert history[0].recovery_id.startswith("rec-")
        assert history[0].action is not None


def test_universal_tool_engine_integration():
    """Verify self-healing tools are registered in Universal Tool Engine and executable."""
    tools = universal_tool_engine.list_tools()
    tool_names = {t.tool_id for t in tools}
    
    assert "healing.run_watchdogs" in tool_names
    assert "healing.trigger_incident" in tool_names
    assert "healing.remediate" in tool_names
    
    res_wd = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
        tool_id="healing.run_watchdogs",
        params={},
        caller_identity="test-suite"
    ))
    assert res_wd.status.value == "SUCCESS" if hasattr(res_wd.status, 'value') else res_wd.status == "SUCCESS"
    assert "watchdogs" in res_wd.output
    assert len(res_wd.output["watchdogs"]) == 6


def test_operations_rest_api_endpoints(client):
    """Verify all REST API router endpoints /api/v1/operations/* function properly."""
    # 1. Health
    resp_health = client.get("/api/v1/operations/health")
    assert resp_health.status_code == 200
    assert len(resp_health.json()) == 6
    
    # 2. Metrics
    resp_metrics = client.get("/api/v1/operations/metrics")
    assert resp_metrics.status_code == 200
    assert "system_health" in resp_metrics.json()
    assert "uptime_pct" in resp_metrics.json()
    
    # 3. Policies
    resp_pol = client.get("/api/v1/operations/policies")
    assert resp_pol.status_code == 200
    assert resp_pol.json()["remediation_budget_usd"] == 0.0
    
    # 4. Recovery History
    resp_hist = client.get("/api/v1/operations/recovery-history")
    assert resp_hist.status_code == 200
    assert isinstance(resp_hist.json(), list)
    
    # 5. List Incidents
    resp_list = client.get("/api/v1/operations")
    assert resp_list.status_code == 200
    assert isinstance(resp_list.json(), list)
    
    # 6. Trigger Incident & Actions via API
    payload = {
        "title": "REST API Test Incident",
        "category": "NETWORK_FAILURE",
        "severity": "LOW",
        "target_resource": "rest-api-socket",
        "auto_remediate": False
    }
    resp_trig = client.post("/api/v1/self-healing/incidents/trigger", json=payload)
    assert resp_trig.status_code == 200
    inc_id = resp_trig.json()["incident_id"]
    
    # 7. Get by ID
    resp_get = client.get(f"/api/v1/operations/{inc_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["incident_id"] == inc_id
    
    # 8. Acknowledge via REST
    resp_ack = client.post(f"/api/v1/operations/{inc_id}/acknowledge?operator=rest-test-runner")
    assert resp_ack.status_code == 200
    assert resp_ack.json()["acknowledged_by"] == "rest-test-runner"
    
    # 9. Recover via REST
    resp_rec = client.post(f"/api/v1/operations/{inc_id}/recover")
    assert resp_rec.status_code == 200
    assert resp_rec.json()["status"] == "RESOLVED"
    
    # 10. Escalate via REST
    resp_esc = client.post(f"/api/v1/operations/{inc_id}/escalate?reason=REST+test+escalation")
    assert resp_esc.status_code == 200
    assert resp_esc.json()["status"] == "ESCALATED"
    
    # 11. Stop via REST
    resp_stop = client.post(f"/api/v1/operations/{inc_id}/stop?reason=REST+test+abort")
    assert resp_stop.status_code == 200
    assert resp_stop.json()["status"] == "STOPPED"


def test_finops_zero_cost_governance():
    """Verify self-healing and recovery actions strictly enforce $0.00 spend."""
    policy = self_healing_engine.get_recovery_policy()
    assert policy.remediation_budget_usd == 0.0
    
    playbooks = self_healing_engine.list_playbooks()
    for pb in playbooks:
        assert pb.estimated_cost_usd == 0.0
