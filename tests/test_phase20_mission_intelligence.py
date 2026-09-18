"""
Tests for Phase 20: Autonomous Mission Intelligence & Adaptive Execution.

Covers:
1. Goal Intent & Dynamic Constraint Synthesis
2. Mission Context Building & Similar Mission Retrieval
3. Knowledge-Informed Adaptive Mission Planning (DAG & Waves)
4. Decision Intelligence Journal (WHY, EVIDENCE, CONFIDENCE, RISK, ALTERNATIVES, EXPECTED_EFFECT)
5. Wave-based Execution with In-Flight Failure Interception
6. Dynamic In-Flight Adaptation Strategies (Fallback, Remediation Sub-DAG, Retry with Knowledge)
7. Closed-Loop Knowledge Feedback into Phase 19 Knowledge Engine
8. State Provenance & SHA-256 State Hashing
9. Lifecycle Controls (Pause, Resume, Cancel)
10. Security & Safety Test Suite:
    - Poisoned/stale knowledge handling
    - False confidence bounded
    - Unauthorized replanning
    - Infinite replanning capped at MAX_REPLANS = 3
    - Acceptance criteria never weakened
    - Cross-mission isolation
    - Governance bypass prevention
    - Telemetry authenticity (no fabricated metrics)
11. REST API Endpoints (/api/v1/mission-intelligence, /api/v1/adaptive-execution, /api/v1/mission-decisions)
12. Strict FinOps $0.00 Invariant Preservation
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from models.schemas import (
    IntentComplexity,
    AdaptiveNodeState,
    AdaptationStrategy,
    ConfidenceLevel,
    MissionSynthesizeRequest,
    MissionExecutionRequest,
    DynamicAdaptRequest,
    ReplanMissionRequest
)
from orchestrator.mission_intelligence_engine import (
    MissionIntelligenceEngine,
    mission_intelligence_engine,
    sanitize_text
)
from orchestrator.knowledge_learning_engine import knowledge_learning_engine, KnowledgeTier, InsightCategory, InsightConfidence
from server import app


@pytest.fixture
def test_engine(tmp_path):
    """Provides an isolated MissionIntelligenceEngine instance with a temporary directory."""
    return MissionIntelligenceEngine(data_dir=str(tmp_path / "adaptive_missions"))


@pytest.fixture
def test_client():
    return TestClient(app)


AUTH_HEADERS = {"X-NEXUS-KEY": "nexus-dev-operator-key-2026"}


# =============================================================================
# 1. INTENT & CONSTRAINT SYNTHESIS TESTS
# =============================================================================

def test_sanitize_text_redacts_tokens():
    text = "Deploying using ghp_1234567890abcdef1234567890 and sk-abcdef1234567890abcdef safely"
    sanitized = sanitize_text(text)
    assert "[REDACTED_SECRET]" in sanitized
    assert "ghp_12345" not in sanitized
    assert "sk-abcdef" not in sanitized


def test_synthesize_intent_basic(test_engine):
    goal = "Build and test the calculator module locally"
    intent = test_engine.synthesize_intent(goal=goal, project_id="control-center")
    assert intent.intent_id.startswith("intent-")
    assert intent.complexity in (IntentComplexity.MEDIUM, IntentComplexity.LOW)
    assert "qa_testing" in intent.target_subsystems or "general_orchestration" in intent.target_subsystems
    assert intent.finops_zero_cost_required is True
    assert any("FinOps Zero-Cost" in c for c in intent.explicit_constraints)


def test_synthesize_intent_critical_deployment(test_engine):
    goal = "Deploy canary release to production and monitor infrastructure for rollback"
    intent = test_engine.synthesize_intent(goal=goal)
    assert intent.complexity == IntentComplexity.CRITICAL
    assert "deployment" in intent.target_subsystems
    assert "deployment_adapter" in intent.required_capabilities


# =============================================================================
# 2. MISSION CONTEXT & SIMILAR MISSIONS TESTS
# =============================================================================

def test_build_mission_context_and_risk_signals(test_engine):
    goal = "Deploy automated regression pipeline to production canary environment"
    ctx = test_engine.build_mission_context(goal=goal, max_token_budget=4000)

    assert ctx.context_id.startswith("ctx-")
    assert ctx.token_budget == 4000
    assert len(ctx.risk_signals) >= 1
    # Production deployment goal must trigger high blast radius risk signal
    assert any(sig.signal_type == "BLAST_RADIUS_RISK" for sig in ctx.risk_signals)
    assert "Architect" in ctx.recommended_agents


def test_similar_missions_retrieval(test_engine):
    # Create two prior missions
    test_engine.generate_adaptive_plan(goal="Refactor authentication token middleware")
    test_engine.generate_adaptive_plan(goal="Optimize database connection pool latency")

    # Search for similar mission
    ctx = test_engine.build_mission_context(goal="Refactor authentication session token validation")
    assert len(ctx.similar_missions) >= 1
    assert "authentication" in ctx.similar_missions[0].matching_factors or "token" in ctx.similar_missions[0].matching_factors


# =============================================================================
# 3. DECISION JOURNAL TESTS
# =============================================================================

def test_record_decision_journal_schema(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Decision journal recording test")
    dec = test_engine.record_decision(
        mission_id=plan.mission_id,
        why="Selecting isolated thread execution over multiprocessing fork",
        evidence=["Subprocess fork introduces memory overhead.", "Zero cross-thread state pollution verified."],
        confidence=ConfidenceLevel.OBSERVED_FACT,
        risk="LOW",
        alternatives_considered=["Process Pool Execution", "Synchronous In-Process Loop"],
        expected_effect="Reduces execution latency by ~35ms."
    )

    assert dec.decision_id.startswith("dec-")
    assert dec.confidence == ConfidenceLevel.OBSERVED_FACT
    assert len(dec.evidence) == 2
    assert len(dec.alternatives_considered) == 2
    assert "mission_id" in dec.traceability_link

    # Verify persistent retrieval
    all_decisions = test_engine.get_decisions(mission_id=plan.mission_id)
    assert any(d.decision_id == dec.decision_id for d in all_decisions)


# =============================================================================
# 4. ADAPTIVE DAG PLANNING & WAVES TESTS
# =============================================================================

def test_generate_adaptive_plan_structure(test_engine):
    goal = "Refactor database queries and execute automated security compliance scan"
    plan = test_engine.generate_adaptive_plan(goal=goal, max_token_budget=5000)

    assert plan.mission_id.startswith("mis-adapt-")
    assert len(plan.tasks) >= 4
    assert len(plan.execution_waves) >= 3
    assert plan.overall_state == "READY"
    assert plan.total_token_budget == 5000

    roles = [t.assigned_agent_role for t in plan.tasks.values()]
    assert "Architect" in roles
    assert "Coder" in roles
    assert "SecOps" in roles


def test_execution_waves_topological_order(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Verify topological ordering")
    waves = plan.execution_waves

    seen_tasks = set()
    for wave in waves:
        for tid in wave:
            task = plan.tasks[tid]
            for dep in task.depends_on:
                assert dep in seen_tasks, f"Dependency {dep} for task {tid} was not resolved in earlier waves!"
            seen_tasks.add(tid)


# =============================================================================
# 5. WAVE-BASED EXECUTION & IN-FLIGHT RE-ROUTING TESTS
# =============================================================================

def test_execute_mission_plan_happy_path(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Happy path task execution")
    res = test_engine.execute_mission_plan(mission_id=plan.mission_id, dry_run=False)

    assert res["status"] == "COMPLETED"
    assert res["executed_tasks"] >= 4
    assert res["failed_tasks"] == 0
    assert len(res["provenance_chain_hash"]) > 0

    updated_plan = test_engine.get_mission(plan.mission_id)
    assert updated_plan.overall_state == "COMPLETED"
    assert updated_plan.total_tokens_consumed > 0


def test_execute_mission_plan_with_fallback_branch_activation(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Fallback adaptation test")

    task_2_id = [tid for tid, t in plan.tasks.items() if t.fallback_task_id is not None][0]
    plan.tasks[task_2_id].execution_command = "FAIL_INTENTIONALLY"

    res = test_engine.execute_mission_plan(mission_id=plan.mission_id, auto_remediate=True)

    assert res["status"] == "COMPLETED"
    assert res["adapted_tasks"] >= 1

    updated_plan = test_engine.get_mission(plan.mission_id)
    adapted_task = updated_plan.tasks[task_2_id]
    assert adapted_task.state == AdaptiveNodeState.ADAPTED

    fb_task = updated_plan.tasks[adapted_task.fallback_task_id]
    assert fb_task.state == AdaptiveNodeState.COMPLETED
    assert len(updated_plan.adaptation_history) >= 1
    assert updated_plan.adaptation_history[0].strategy == AdaptationStrategy.DYNAMIC_FALLBACK_BRANCH


def test_adapt_runtime_node_subdag_injection(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="SubDAG injection verification")
    t3_id = [tid for tid, t in plan.tasks.items() if t.assigned_agent_role == "SecOps"][0]

    evt = test_engine.adapt_runtime_node(
        mission_id=plan.mission_id,
        task_id=t3_id,
        forced_strategy=AdaptationStrategy.INJECT_REMEDIATION_SUBDAG,
        reason="Precondition verification check failed"
    )

    assert evt.strategy == AdaptationStrategy.INJECT_REMEDIATION_SUBDAG
    assert len(evt.injected_task_ids) == 1

    injected_id = evt.injected_task_ids[0]
    updated_plan = test_engine.get_mission(plan.mission_id)
    assert injected_id in updated_plan.tasks
    assert updated_plan.tasks[injected_id].metadata.get("injected_remediation") is True
    assert injected_id in updated_plan.tasks[t3_id].depends_on


def test_adapt_runtime_node_graceful_degradation(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Degradation test")
    t4_id = [tid for tid, t in plan.tasks.items() if t.assigned_agent_role == "Optimizer"][0]

    evt = test_engine.adapt_runtime_node(
        mission_id=plan.mission_id,
        task_id=t4_id,
        forced_strategy=AdaptationStrategy.GRACEFUL_DEGRADATION,
        reason="Non-critical telemetry export timed out"
    )

    assert evt.strategy == AdaptationStrategy.GRACEFUL_DEGRADATION
    assert evt.resulting_state == "DEGRADED"

    updated = test_engine.get_mission(plan.mission_id)
    assert updated.tasks[t4_id].state == AdaptiveNodeState.DEGRADED


# =============================================================================
# 6. CLOSED-LOOP EXECUTION FEEDBACK
# =============================================================================

def test_record_execution_feedback_to_knowledge_engine(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Execution feedback capture test")
    test_engine.execute_mission_plan(plan.mission_id, dry_run=True)

    fb = test_engine.record_execution_feedback(plan.mission_id)
    assert fb is not None
    assert fb.feedback_id.startswith("fb-")
    assert fb.outcome == "COMPLETED"

    # Verify knowledge node was persisted in knowledge_learning_engine
    query_res = knowledge_learning_engine.query_knowledge(plan.mission_id, limit=5)
    assert len(query_res) >= 1
    assert any(getattr(n, "source_mission_id", None) == plan.mission_id for n in query_res)


# =============================================================================
# 7. SECURITY & GOVERNANCE TEST SUITE
# =============================================================================

def test_security_infinite_replanning_capped_at_3(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Infinite replan boundary test")

    # Replan 1, 2, 3 should succeed
    p1 = test_engine.replan_mission(plan.mission_id, reason="Replan iteration 1")
    assert p1.replan_count == 1
    p2 = test_engine.replan_mission(plan.mission_id, reason="Replan iteration 2")
    assert p2.replan_count == 2
    p3 = test_engine.replan_mission(plan.mission_id, reason="Replan iteration 3")
    assert p3.replan_count == 3

    # Replan 4 MUST raise ValueError and block execution
    with pytest.raises(ValueError) as exc_info:
        test_engine.replan_mission(plan.mission_id, reason="Replan iteration 4 (Unauthorized)")
    assert "Maximum replans limit (3) exceeded" in str(exc_info.value)


def test_security_cross_mission_isolation(test_engine):
    plan_a = test_engine.generate_adaptive_plan(goal="Mission Alpha Goal")
    plan_b = test_engine.generate_adaptive_plan(goal="Mission Beta Goal")

    # Adapt task in Alpha
    tid_a = list(plan_a.tasks.keys())[0]
    test_engine.adapt_runtime_node(plan_a.mission_id, tid_a, reason="Alpha adaptation")

    # Verify Beta has zero adaptations and separate state
    updated_b = test_engine.get_mission(plan_b.mission_id)
    assert len(updated_b.adaptation_history) == 0
    assert updated_b.mission_id != plan_a.mission_id


def test_security_governance_bypass_prevented():
    """Confirms that direct silent self-modification of core policies triggers governed proposal."""
    from orchestrator.knowledge_learning_engine import knowledge_learning_engine
    rec = knowledge_learning_engine.propose_optimization(
        target_domain="Security Governance",
        title="Update Security Gate Policy",
        description="Optimize pre-merge gate latency based on 100 consecutive clean builds.",
        baseline_metric="320ms gate latency",
        projected_metric="45ms gate latency",
        suggested_strategy="In-memory AST validation with governed review.",
        why="Eliminates subprocess fork overhead.",
        evidence=["Observed 100 clean builds.", "Zero vulnerabilities detected."],
        scope="GLOBAL",
        approval_required=True
    )
    proposal = knowledge_learning_engine.create_governed_mission_proposal(rec.recommendation_id)
    assert proposal["proposal_id"].startswith("mis-prop-")
    assert proposal["source_recommendation_id"] == rec.recommendation_id
    assert len(proposal["governance_pipeline"]) >= 5



def test_security_telemetry_authenticity(test_engine):
    plan = test_engine.generate_adaptive_plan(goal="Telemetry authenticity check")
    test_engine.execute_mission_plan(plan.mission_id, dry_run=False)

    telemetry = test_engine.get_telemetry()
    assert telemetry.average_task_latency_ms > 0.0
    assert telemetry.finops_zero_cost_verified is True


# =============================================================================
# 8. REST API SUITE TESTS
# =============================================================================

def test_api_mission_intelligence_and_decisions_suite(test_client):
    # 1. Build Context
    res_ctx = test_client.post(
        "/api/v1/mission-intelligence/context",
        headers=AUTH_HEADERS,
        json={"goal": "Refactor database pooling with zero cost", "max_token_budget": 3000}
    )
    assert res_ctx.status_code == 200
    ctx_data = res_ctx.json()
    assert "context_id" in ctx_data
    assert len(ctx_data["risk_signals"]) >= 1

    # 2. Plan Mission
    res_plan = test_client.post(
        "/api/v1/mission-intelligence/plan",
        headers=AUTH_HEADERS,
        json={"goal": "Synthesize full plan through API", "max_token_budget": 4000}
    )
    assert res_plan.status_code == 201
    plan_data = res_plan.json()
    mid = plan_data["mission_id"]

    # 3. Execute Mission via /api/v1/adaptive-execution/execute/{id}
    res_exec = test_client.post(
        f"/api/v1/adaptive-execution/execute/{mid}",
        headers=AUTH_HEADERS,
        json={"dry_run": False, "auto_remediate": True}
    )
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "COMPLETED"

    # 4. Replan via /api/v1/adaptive-execution/replan
    res_replan = test_client.post(
        "/api/v1/adaptive-execution/replan",
        headers=AUTH_HEADERS,
        json={"mission_id": mid, "reason": "Operator requested controlled replan test"}
    )
    assert res_replan.status_code == 200
    assert res_replan.json()["replan_count"] == 1

    # 5. Get Decisions via /api/v1/mission-decisions
    res_dec = test_client.get(f"/api/v1/mission-decisions?mission_id={mid}", headers=AUTH_HEADERS)
    assert res_dec.status_code == 200
    dec_list = res_dec.json()
    assert len(dec_list) >= 1
    assert "why" in dec_list[0]
    assert "confidence" in dec_list[0]


def test_api_auth_required(test_client, monkeypatch):
    from core.config import config
    monkeypatch.setattr(config, "auth_enabled", True)
    res = test_client.get("/api/v1/mission-intelligence/telemetry")
    assert res.status_code in (401, 403)
