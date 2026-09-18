"""
NEXUS Phase 19: Autonomous Knowledge, Learning & Optimization Test Suite.
Tests:
1. Multi-tier knowledge graph storage and fingerprint deduplication.
2. Local hybrid BM25 and semantic tag search.
3. Autonomous learning insight distillation and recurrence tracking.
4. Dynamic context and prompt optimization with token budget.
5. DAG schedule topology optimization and critical path compression.
6. Universal Tool performance latency & reliability profiling.
7. Optimization recommendation lifecycle (PROPOSED -> APPLIED).
8. Knowledge telemetry & health scoring.
9. FastAPI REST API endpoints (/api/v1/knowledge, /api/v1/learning, /api/v1/optimization).
10. Universal Tool Engine Phase 19 capabilities execution.
11. FinOps strict $0.00 zero-cost preservation invariant.
"""

import os
import json
import time
import pytest
from fastapi.testclient import TestClient

from models.schemas import (
    KnowledgeTier,
    InsightCategory,
    InsightConfidence,
    OptimizationStatus,
    ContextOptimizationRequest,
)
from orchestrator.knowledge_learning_engine import (
    KnowledgeLearningEngine,
    get_knowledge_learning_engine,
    _tokenize,
    _compute_bm25_score
)
from orchestrator.universal_tool_engine import universal_tool_engine
from core.cost_guard import cost_guard
from server import app


@pytest.fixture
def test_engine(tmp_path):
    """Creates an isolated KnowledgeLearningEngine for testing."""
    engine = KnowledgeLearningEngine()
    engine.data_dir = tmp_path
    return engine


@pytest.fixture
def client():
    return TestClient(app)


def test_tokenizer_and_bm25_scoring():
    text = "FastAPI asynchronous background tasks with zero-cost FinOps governance"
    tokens = _tokenize(text)
    assert "fastapi" in tokens
    assert "finops" in tokens
    assert "governance" in tokens

    q_tokens = _tokenize("fastapi finops")
    score = _compute_bm25_score(q_tokens, tokens)
    assert score > 0.0

    irrelevant_q = _tokenize("unrelated kubernetes cluster")
    irrelevant_score = _compute_bm25_score(irrelevant_q, tokens)
    assert irrelevant_score == 0.0


def test_knowledge_engine_initialization(test_engine):
    assert test_engine is not None
    telemetry = test_engine.get_telemetry()
    assert telemetry.total_nodes >= 5  # Bootstrap nodes present
    assert telemetry.knowledge_health_score == 100.0
    assert telemetry.finops_zero_cost_verified is True


def test_multi_tier_node_creation_and_fingerprinting(test_engine):
    # Create Episodic Node
    node1 = test_engine.add_knowledge_node(
        tier=KnowledgeTier.EPISODIC,
        category=InsightCategory.DEPLOYMENT,
        title="Local Serving Port Conflict in Mission 104",
        content="Detected port 8000 already occupied by zombie process. Remediated by reassigning port 8001.",
        tags=["deployment", "port_conflict", "mission_104"]
    )
    assert node1.node_id.startswith("kn-")
    assert node1.tier == KnowledgeTier.EPISODIC
    assert node1.fingerprint != ""

    # Duplicate addition should return existing node and increment access count
    node1_dup = test_engine.add_knowledge_node(
        tier=KnowledgeTier.EPISODIC,
        category=InsightCategory.DEPLOYMENT,
        title="Local Serving Port Conflict in Mission 104",
        content="Detected port 8000 already occupied by zombie process. Remediated by reassigning port 8001.",
        tags=["deployment", "port_conflict", "mission_104"]
    )
    assert node1_dup.node_id == node1.node_id
    assert node1_dup.access_count >= 2


def test_knowledge_graph_relational_edges(test_engine):
    n1 = test_engine.add_knowledge_node(
        tier=KnowledgeTier.SEMANTIC,
        category=InsightCategory.ARCHITECTURE,
        title="FastAPI Lifespan Background Automation Pattern",
        content="Use lifespan context manager for robust async background loops."
    )
    n2 = test_engine.add_knowledge_node(
        tier=KnowledgeTier.PROCEDURAL,
        category=InsightCategory.REMEDIATION,
        title="Background Worker Graceful Shutdown Recipe",
        content="Signal cancellation event and wait for pending tasks before unbinding ports."
    )

    edge = test_engine.link_knowledge_nodes(
        source_id=n1.node_id,
        target_id=n2.node_id,
        relation_type="OPTIMIZES",
        weight=0.9
    )
    assert edge.edge_id.startswith("edge-")
    assert edge.relation_type == "OPTIMIZES"
    assert len(test_engine.list_edges()) >= 1


def test_local_hybrid_search_bm25_and_tags(test_engine):
    test_engine.add_knowledge_node(
        tier=KnowledgeTier.SEMANTIC,
        category=InsightCategory.FINOPS,
        title="Zero-Cost Local First Execution Invariant",
        content="Enforce strict 0.00 USD spend ceiling by blocking cloud infrastructure.",
        tags=["finops", "zero_cost", "guardrail"]
    )

    # Search with exact and partial tokens
    matches = test_engine.query_knowledge("zero cost finops guardrail")
    assert len(matches) > 0
    assert any("Zero-Cost" in m.title for m in matches)

    # Search with tier filter
    filtered = test_engine.query_knowledge("zero cost", tier=KnowledgeTier.SEMANTIC)
    assert all(m.tier == KnowledgeTier.SEMANTIC for m in filtered)


def test_autonomous_learning_insight_recording(test_engine):
    insight = test_engine.record_learning_insight(
        title="Ephemeral Port Reallocation Heuristic",
        category=InsightCategory.REMEDIATION,
        pattern="Rapid local redeployments occasionally leave lingering sockets in TIME_WAIT.",
        rationale="Reallocating ephemeral ports bypasses OS TCP socket reuse wait intervals.",
        recommended_action="Attempt dynamic port fallback before killing host processes.",
        supporting_evidence=["Observed 4 socket collisions during rapid E2E runs."],
        confidence=InsightConfidence.HIGH,
        impacted_subsystems=["deployment", "self_healing"]
    )
    assert insight.insight_id.startswith("ins-")
    assert insight.recurrence_count == 1

    # Recording identical pattern should increment recurrence
    repeated = test_engine.record_learning_insight(
        title="Ephemeral Port Reallocation Heuristic",
        category=InsightCategory.REMEDIATION,
        pattern="Rapid local redeployments occasionally leave lingering sockets in TIME_WAIT.",
        rationale="Reallocating ephemeral ports bypasses OS TCP socket reuse wait intervals.",
        recommended_action="Attempt dynamic port fallback before killing host processes.",
    )
    assert repeated.insight_id == insight.insight_id
    assert repeated.recurrence_count >= 2


def test_subsystem_learning_sweep(test_engine):
    new_insights = test_engine.extract_insights_from_subsystems()
    assert isinstance(new_insights, list)
    # Insights should now be present in engine
    assert len(test_engine.list_insights()) >= len(new_insights)


def test_context_and_prompt_optimization(test_engine):
    req = ContextOptimizationRequest(
        query_context="How do I configure zero cost deployments with health checks?",
        target_agent_role="DeploymentSpecialist",
        max_token_budget=1000
    )
    res = test_engine.optimize_agent_context(req)
    assert "NEXUS AUTONOMOUS KNOWLEDGE" in res.optimized_context
    assert res.estimated_tokens_used > 0
    assert res.tokens_saved >= 0
    assert len(res.selected_patterns) > 0


def test_dag_schedule_optimizer_critical_path(test_engine):
    sample_subtasks = [
        {"subtask_id": "step-1-init", "dependencies": []},
        {"subtask_id": "step-2a-backend", "dependencies": ["step-1-init"]},
        {"subtask_id": "step-2b-frontend", "dependencies": ["step-1-init"]},
        {"subtask_id": "step-2c-docs", "dependencies": ["step-1-init"]},
        {"subtask_id": "step-3-deploy", "dependencies": ["step-2a-backend", "step-2b-frontend"]},
        {"subtask_id": "step-4-verify", "dependencies": ["step-3-deploy"]}
    ]

    plan = test_engine.optimize_dag_schedule(mission_id="test-mission-dag", subtasks=sample_subtasks)
    assert plan.original_step_count == 6
    assert plan.critical_path_length == 4  # [1], [2a, 2b, 2c], [3], [4]
    assert plan.estimated_speedup_percent > 0.0
    assert len(plan.parallelizable_groups) == 4
    # Wave 2 should contain 3 parallel steps
    assert len(plan.parallelizable_groups[1]) == 3


def test_tool_performance_and_reliability_profiling(test_engine):
    tool_id = "test.universal_tool"
    test_engine.record_tool_execution(tool_id=tool_id, duration_ms=45.0, success=True)
    test_engine.record_tool_execution(tool_id=tool_id, duration_ms=55.0, success=True)
    test_engine.record_tool_execution(tool_id=tool_id, duration_ms=120.0, success=False, error_msg="Timeout connecting")

    metrics = {m.tool_id: m for m in test_engine.list_tool_metrics()}
    assert tool_id in metrics
    tm = metrics[tool_id]
    assert tm.total_invocations == 3
    assert tm.success_rate_percent == 66.7
    assert tm.reliability_tier == "DEGRADED"
    assert "Timeout connecting" in tm.error_patterns[0]


def test_optimization_proposal_and_application(test_engine):
    rec = test_engine.propose_optimization(
        target_domain="DAG_SCHEDULING",
        title="Parallelize Static Asset Compilation",
        description="Run Vite frontend build concurrently with pytest backend tests.",
        baseline_metric="45s sequential",
        projected_metric="25s parallel (44% speedup)",
        suggested_strategy="Group tasks into wave [frontend, backend]"
    )
    assert rec.status == OptimizationStatus.PROPOSED

    applied = test_engine.apply_optimization(rec.recommendation_id, operator="test-operator")
    assert applied.status == OptimizationStatus.APPLIED
    assert applied.applied_at is not None


def test_knowledge_learning_rest_api(client):
    headers = {"Authorization": "Bearer nexus-dev-operator-key-2026"}

    # Health & Telemetry
    r = client.get("/api/v1/knowledge/health", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ONLINE"

    r = client.get("/api/v1/knowledge/telemetry", headers=headers)
    assert r.status_code == 200
    assert r.json()["knowledge_health_score"] >= 90.0

    # Nodes
    r = client.get("/api/v1/knowledge/nodes", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # Search
    r = client.get("/api/v1/knowledge/search?q=deployment", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # Learning Sweep
    r = client.post("/api/v1/learning/sweep", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # Optimization Recommendations
    r = client.get("/api/v1/optimization/recommendations", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_universal_tool_engine_phase19_tools():
    from models.schemas import UniversalToolInvocationRequest

    # 1. knowledge.search
    res = universal_tool_engine.invoke_tool(
        UniversalToolInvocationRequest(
            tool_id="knowledge.search",
            parameters={"query": "zero cost finops", "limit": 5}
        )
    )
    assert res.status == "SUCCESS"
    assert "matches" in res.output

    # 2. knowledge.record_insight
    res2 = universal_tool_engine.invoke_tool(
        UniversalToolInvocationRequest(
            tool_id="knowledge.record_insight",
            parameters={
                "title": "Universal Tool Search Speedup",
                "category": "PERFORMANCE",
                "pattern": "In-memory token index achieves sub-millisecond retrieval.",
                "rationale": "Avoids cold disk I/O during tight agent reasoning loops.",
                "recommended_action": "Maintain memory-mapped token cache."
            }
        )
    )
    assert res2.status == "SUCCESS"
    assert "insight_id" in res2.output

    # 3. learning.optimize_dag
    res3 = universal_tool_engine.invoke_tool(
        UniversalToolInvocationRequest(
            tool_id="learning.optimize_dag",
            parameters={
                "mission_id": "universal-tool-dag-test",
                "subtasks": [
                    {"subtask_id": "a", "dependencies": []},
                    {"subtask_id": "b", "dependencies": ["a"]},
                    {"subtask_id": "c", "dependencies": ["a"]}
                ]
            }
        )
    )
    assert res3.status == "SUCCESS"
    assert res3.output["critical_path_length"] == 2


def test_finops_zero_cost_preservation():
    summary = cost_guard.get_cost_summary()
    assert summary["current_spend_usd"] == 0.00
    assert summary["billing_linked"] is False
    assert summary["hard_spend_limit_usd"] == 0.00


def test_knowledge_archive_and_retire_lifecycle(test_engine):
    node = test_engine.add_knowledge_node(
        tier=KnowledgeTier.SEMANTIC,
        category=InsightCategory.ARCHITECTURE,
        title="Deprecated Port Allocation Strategy",
        content="Legacy static port binding for background microservices.",
        tags=["deprecated", "port_allocation"]
    )
    assert node.status == "ACTIVE"

    archived = test_engine.archive_node(node.node_id, operator="test_runner")
    assert archived.status == "ARCHIVED"

    retired = test_engine.retire_node(node.node_id, operator="test_runner")
    assert retired.status == "RETIRED"


def test_knowledge_revalidation_and_decay(test_engine):
    reval = test_engine.revalidate_knowledge(operator="test_daemon")
    assert reval["status"] == "SUCCESS"
    assert reval["revalidated_nodes_count"] >= 5
    assert "active_nodes_count" in reval


def test_knowledge_provenance_tracing(test_engine):
    node = test_engine.add_knowledge_node(
        tier=KnowledgeTier.PROCEDURAL,
        category=InsightCategory.SECURITY,
        title="Air-Gapped Local Secret Redaction",
        content="Pattern for masking high-entropy tokens before writing to audit log.",
        source_mission_id="mis-test-001",
        source_finding_id="sec-find-999"
    )
    prov = test_engine.get_provenance(node.node_id)
    assert prov["item_id"] == node.node_id
    assert prov["item_type"] == "KNOWLEDGE_NODE"
    assert prov["source_mission_id"] == "mis-test-001"
    assert prov["source_finding_id"] == "sec-find-999"
    assert prov["fingerprint"] != ""


def test_contradiction_handling_and_conditional_scoping(test_engine):
    # Base rule
    test_engine.add_knowledge_node(
        tier=KnowledgeTier.SEMANTIC,
        category=InsightCategory.PERFORMANCE,
        title="Local subprocess execution succeeds unconditionally",
        content="Direct python script execution completes within 100ms."
    )

    # Contradictory observation
    result = test_engine.handle_contradiction(
        pattern="Local subprocess execution succeeds unconditionally",
        condition_context="when memory ceiling is restricted below 64MB",
        evidence=["Exit code 137 OOMKilled in container cgroup limits"]
    )
    assert result["status"] == "CONTRADICTION_PRESERVED_AND_SCOPED"
    assert result["adjusted_nodes_count"] >= 1
    assert result["scoped_node_id"].startswith("kn-")


def test_self_modification_boundaries_and_governed_mission_proposal(test_engine):
    """
    Verifies Section 18:
    NEXUS does NOT silently self-modify security policies, core code, or gates.
    It generates a structured governed mission proposal instead.
    """
    rec = test_engine.propose_optimization(
        target_domain="FINOPS_ZERO_COST",
        title="Optimize AST Scanner Cache Retention",
        description="Retain parsed AST trees in LRU memory cache for 60 seconds.",
        baseline_metric="300ms AST parse latency",
        projected_metric="15ms cached parse latency",
        suggested_strategy="Inject LRU cache wrapper in SecOps AST parser.",
        why="Reduces repetitive disk reads during continuous security sweeps.",
        evidence=["Benchmark indicates 95% identical tree structures in warm runs."],
        risk="LOW",
        reversibility="HIGH",
        approval_required=True
    )
    assert rec.status == OptimizationStatus.PROPOSED
    assert rec.approval_required is True

    # Generate governed mission proposal (Pipeline: Mission -> Code -> Test -> SecOps -> Review -> Approval -> Delivery)
    proposal = test_engine.create_governed_mission_proposal(rec.recommendation_id, operator="test_operator")
    assert proposal["proposal_id"].startswith("mis-prop-")
    assert proposal["status"] == "PROPOSED_FOR_GOVERNANCE"
    assert len(proposal["governance_pipeline"]) == 6


def test_optimization_accept_and_reject_lifecycle(test_engine):
    rec1 = test_engine.propose_optimization(
        target_domain="TOOL_ROUTING",
        title="Tool Route Fast-Path",
        description="Route filesystem reads directly via local kernel syscalls.",
        baseline_metric="5ms",
        projected_metric="1ms",
        suggested_strategy="Direct syscall path"
    )
    accepted = test_engine.accept_optimization(rec1.recommendation_id, operator="operator")
    assert accepted.status == OptimizationStatus.APPLIED
    assert accepted.applied_at is not None

    rec2 = test_engine.propose_optimization(
        target_domain="PROMPT_CONTEXT",
        title="Aggressive Token Pruning",
        description="Truncate prompt system instructions by 80%.",
        baseline_metric="2000 tokens",
        projected_metric="400 tokens",
        suggested_strategy="Aggressive truncation"
    )
    rejected = test_engine.reject_optimization(rec2.recommendation_id, operator="operator", reason="Degrades reasoning fidelity")
    assert rejected.status == OptimizationStatus.REJECTED
    assert rejected.rejected_at is not None
    assert "reasoning fidelity" in rejected.rejection_reason


def test_operations_daemon_cycle(test_engine):
    """Verifies Section 23: Operations daemon bounded execution cycle."""
    res = test_engine.run_daemon_cycle()
    assert res["status"] == "COMPLETED"
    assert "insights_extracted_count" in res
    assert "cycle_duration_ms" in res
    assert res["cycle_duration_ms"] >= 0.0


def test_section21_rest_api_contract(client):
    """Verifies all Section 21 endpoints are live and respond with standard schemas."""
    headers = {"Authorization": "Bearer nexus-dev-operator-key-2026"}

    # 1. GET /api/v1/knowledge
    r = client.get("/api/v1/knowledge", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 2. GET /api/v1/knowledge/health
    r = client.get("/api/v1/knowledge/health", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ONLINE"

    # 3. GET /api/v1/knowledge/metrics
    r = client.get("/api/v1/knowledge/metrics", headers=headers)
    assert r.status_code == 200
    assert "total_nodes" in r.json()

    # 4. GET /api/v1/knowledge/patterns
    r = client.get("/api/v1/knowledge/patterns", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 5. GET /api/v1/knowledge/recommendations
    r = client.get("/api/v1/knowledge/recommendations", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 6. POST /api/v1/knowledge/search
    r = client.post("/api/v1/knowledge/search", json={"query": "zero cost finops"}, headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 7. POST /api/v1/knowledge/revalidate
    r = client.post("/api/v1/knowledge/revalidate", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "SUCCESS"

    # 8. GET /api/v1/optimization
    r = client.get("/api/v1/optimization", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ONLINE"

    # 9. GET /api/v1/optimization/recommendations
    r = client.get("/api/v1/optimization/recommendations", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    if len(r.json()) > 0:
        opt_id = r.json()[0]["recommendation_id"]
        # 10. GET /api/v1/knowledge/provenance/{id}
        r_prov = client.get(f"/api/v1/knowledge/provenance/{opt_id}", headers=headers)
        assert r_prov.status_code == 200
        assert r_prov.json()["item_id"] == opt_id

        # 11. POST /api/v1/optimization/{id}/govern
        r_gov = client.post(f"/api/v1/optimization/{opt_id}/govern", headers=headers)
        assert r_gov.status_code == 200
        assert "proposal_id" in r_gov.json()

