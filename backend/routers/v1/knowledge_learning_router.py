"""
NEXUS Phase 19: Autonomous Knowledge, Learning & Optimization REST API Router.
Mounted under /api/v1/knowledge, /api/v1/learning, and /api/v1/optimization.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body

from models.schemas import (
    KnowledgeNode,
    KnowledgeGraphEdge,
    LearningInsight,
    OptimizationRecommendation,
    ContextOptimizationRequest,
    ContextOptimizationResponse,
    DAGOptimizationPlan,
    ToolPerformanceMetric,
    KnowledgeTelemetry,
    KnowledgeTier,
    InsightCategory,
    InsightConfidence,
)
from orchestrator.knowledge_learning_engine import knowledge_learning_engine

# Routers
knowledge_router = APIRouter(prefix="/knowledge", tags=["Knowledge & Memory Engine"])
learning_router = APIRouter(prefix="/learning", tags=["Continuous Learning & Insights"])
optimization_router = APIRouter(prefix="/optimization", tags=["Strategy & Execution Optimization"])


# =========================================================================
# 1. KNOWLEDGE GRAPH & REST API ENDPOINTS (SECTION 21)
# =========================================================================

@knowledge_router.get("", response_model=List[KnowledgeNode])
def list_knowledge_root(
    tier: Optional[str] = Query(None, description="Filter by KnowledgeTier (EPISODIC, SEMANTIC, PROCEDURAL, META)"),
    category: Optional[str] = Query(None, description="Filter by InsightCategory")
):
    """GET /api/v1/knowledge: Lists knowledge nodes in the multi-tier store."""
    return knowledge_learning_engine.list_nodes(tier=tier, category=category)


@knowledge_router.get("/health")
def get_knowledge_health():
    """GET /api/v1/knowledge/health: Returns knowledge system health and FinOps invariant."""
    telemetry = knowledge_learning_engine.get_telemetry()
    return {
        "status": "ONLINE",
        "subsystem": "knowledge-learning-optimization",
        "total_nodes": telemetry.total_nodes,
        "health_score": telemetry.knowledge_health_score,
        "finops_zero_cost": telemetry.finops_zero_cost_verified,
        "timestamp": telemetry.last_learning_sweep_at
    }


@knowledge_router.get("/metrics", response_model=KnowledgeTelemetry)
@knowledge_router.get("/telemetry", response_model=KnowledgeTelemetry)
def get_knowledge_metrics():
    """GET /api/v1/knowledge/metrics & /telemetry: Returns detailed telemetry."""
    return knowledge_learning_engine.get_telemetry()


@knowledge_router.get("/patterns", response_model=List[LearningInsight])
def list_knowledge_patterns(category: Optional[str] = Query(None)):
    """GET /api/v1/knowledge/patterns: Returns learned patterns and insights."""
    return knowledge_learning_engine.list_insights(category=category)


@knowledge_router.get("/recommendations", response_model=List[OptimizationRecommendation])
def list_knowledge_recommendations(status: Optional[str] = Query(None)):
    """GET /api/v1/knowledge/recommendations: Returns optimization recommendations."""
    return knowledge_learning_engine.list_optimizations(status=status)


@knowledge_router.get("/provenance/{item_id}")
def get_knowledge_provenance(item_id: str):
    """GET /api/v1/knowledge/provenance/{id}: Returns audit trail and provenance chain."""
    try:
        return knowledge_learning_engine.get_provenance(item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@knowledge_router.post("/search", response_model=List[KnowledgeNode])
def post_search_knowledge(
    query: Optional[str] = Body(None, embed=True),
    q: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50)
):
    """POST /api/v1/knowledge/search: Hybrid search via BM25 and semantic tag matching."""
    search_q = query or q or ""
    tier_enum = KnowledgeTier(tier) if tier in [t.value for t in KnowledgeTier] else None
    cat_enum = InsightCategory(category) if category in [c.value for c in InsightCategory] else None
    return knowledge_learning_engine.query_knowledge(
        query=search_q,
        tier=tier_enum,
        category=cat_enum,
        limit=limit
    )


@knowledge_router.get("/search", response_model=List[KnowledgeNode])
def get_search_knowledge(
    q: str = Query(..., description="Hybrid search query terms"),
    tier: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50)
):
    """GET /api/v1/knowledge/search: Query string search."""
    tier_enum = KnowledgeTier(tier) if tier in [t.value for t in KnowledgeTier] else None
    cat_enum = InsightCategory(category) if category in [c.value for c in InsightCategory] else None
    return knowledge_learning_engine.query_knowledge(
        query=q,
        tier=tier_enum,
        category=cat_enum,
        limit=limit
    )


@knowledge_router.post("/revalidate")
def post_revalidate_knowledge(operator: str = Query("cyber-operator")):
    """POST /api/v1/knowledge/revalidate: Revalidates knowledge decay factors and fresh state."""
    return knowledge_learning_engine.revalidate_knowledge(operator=operator)


@knowledge_router.get("/nodes", response_model=List[KnowledgeNode])
def list_knowledge_nodes(
    tier: Optional[str] = Query(None, description="Filter by KnowledgeTier (EPISODIC, SEMANTIC, PROCEDURAL, META)"),
    category: Optional[str] = Query(None, description="Filter by InsightCategory")
):
    return knowledge_learning_engine.list_nodes(tier=tier, category=category)


@knowledge_router.get("/nodes/{node_id}", response_model=KnowledgeNode)
def get_knowledge_node_by_nodes_path(node_id: str):
    node = knowledge_learning_engine.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Knowledge node '{node_id}' not found.")
    return node


@knowledge_router.get("/{node_id}", response_model=KnowledgeNode)
def get_knowledge_node_by_root_path(node_id: str):
    """GET /api/v1/knowledge/{id}: Returns specific knowledge node."""
    node = knowledge_learning_engine.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Knowledge node '{node_id}' not found.")
    return node


@knowledge_router.post("/nodes", response_model=KnowledgeNode)
def create_knowledge_node(
    tier: KnowledgeTier = Body(...),
    category: InsightCategory = Body(...),
    title: str = Body(...),
    content: str = Body(...),
    tags: Optional[List[str]] = Body(None),
    confidence: InsightConfidence = Body(InsightConfidence.HIGH),
    metadata: Optional[Dict[str, Any]] = Body(None)
):
    return knowledge_learning_engine.add_knowledge_node(
        tier=tier,
        category=category,
        title=title,
        content=content,
        tags=tags,
        confidence=confidence,
        metadata=metadata
    )


@knowledge_router.post("/{node_id}/archive", response_model=KnowledgeNode)
def archive_knowledge_node(node_id: str, operator: str = Query("operator")):
    """POST /api/v1/knowledge/{id}/archive: Archives a knowledge node."""
    try:
        return knowledge_learning_engine.archive_node(node_id=node_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@knowledge_router.post("/{node_id}/retire", response_model=KnowledgeNode)
def retire_knowledge_node(node_id: str, operator: str = Query("operator")):
    """POST /api/v1/knowledge/{id}/retire: Retires a knowledge node."""
    try:
        return knowledge_learning_engine.retire_node(node_id=node_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@knowledge_router.get("/edges", response_model=List[KnowledgeGraphEdge])
def list_knowledge_edges():
    return knowledge_learning_engine.list_edges()


@knowledge_router.post("/edges", response_model=KnowledgeGraphEdge)
def link_knowledge_nodes(
    source_id: str = Body(..., embed=True),
    target_id: str = Body(..., embed=True),
    relation_type: str = Body(..., embed=True),
    weight: float = Body(1.0, embed=True)
):
    try:
        return knowledge_learning_engine.link_knowledge_nodes(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@knowledge_router.post("/optimize-context", response_model=ContextOptimizationResponse)
def optimize_agent_context(request: ContextOptimizationRequest):
    return knowledge_learning_engine.optimize_agent_context(request)


# =========================================================================
# 2. CONTINUOUS LEARNING & INSIGHTS ENDPOINTS
# =========================================================================

@learning_router.get("/insights", response_model=List[LearningInsight])
def list_learning_insights(category: Optional[str] = Query(None)):
    return knowledge_learning_engine.list_insights(category=category)


@learning_router.post("/insights", response_model=LearningInsight)
def record_learning_insight(
    title: str = Body(...),
    category: InsightCategory = Body(...),
    pattern: str = Body(...),
    rationale: str = Body(...),
    recommended_action: str = Body(...),
    supporting_evidence: Optional[List[str]] = Body(None),
    confidence: InsightConfidence = Body(InsightConfidence.HIGH),
    impacted_subsystems: Optional[List[str]] = Body(None)
):
    return knowledge_learning_engine.record_learning_insight(
        title=title,
        category=category,
        pattern=pattern,
        rationale=rationale,
        recommended_action=recommended_action,
        supporting_evidence=supporting_evidence,
        confidence=confidence,
        impacted_subsystems=impacted_subsystems
    )


@learning_router.post("/sweep", response_model=List[LearningInsight])
def trigger_learning_sweep():
    """Triggers autonomous knowledge extraction across missions, incidents, deployments, and security."""
    return knowledge_learning_engine.extract_insights_from_subsystems()


# =========================================================================
# 3. STRATEGY & EXECUTION OPTIMIZATION ENDPOINTS (SECTION 21)
# =========================================================================

@optimization_router.get("")
def get_optimization_status():
    """GET /api/v1/optimization: Returns optimization subsystem overview."""
    opts = knowledge_learning_engine.list_optimizations()
    return {
        "status": "ONLINE",
        "subsystem": "optimization-engine",
        "total_recommendations": len(opts),
        "proposed_count": sum(1 for o in opts if o.status == "PROPOSED"),
        "applied_count": sum(1 for o in opts if o.status == "APPLIED"),
        "rejected_count": sum(1 for o in opts if o.status == "REJECTED")
    }


@optimization_router.get("/recommendations", response_model=List[OptimizationRecommendation])
def list_optimization_recommendations(status: Optional[str] = Query(None)):
    """GET /api/v1/optimization/recommendations: Lists recommendations."""
    return knowledge_learning_engine.list_optimizations(status=status)


@optimization_router.post("/{recommendation_id}/accept", response_model=OptimizationRecommendation)
def accept_optimization_recommendation(
    recommendation_id: str,
    operator: str = Query("cyber-optimizer")
):
    """POST /api/v1/optimization/{id}/accept: Accepts recommendation."""
    try:
        return knowledge_learning_engine.accept_optimization(recommendation_id=recommendation_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@optimization_router.post("/{recommendation_id}/reject", response_model=OptimizationRecommendation)
def reject_optimization_recommendation(
    recommendation_id: str,
    operator: str = Query("cyber-optimizer"),
    reason: str = Body("Rejected by operator", embed=True)
):
    """POST /api/v1/optimization/{id}/reject: Rejects recommendation."""
    try:
        return knowledge_learning_engine.reject_optimization(recommendation_id=recommendation_id, operator=operator, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@optimization_router.post("/{recommendation_id}/govern")
def govern_optimization_recommendation(
    recommendation_id: str,
    operator: str = Query("cyber-optimizer")
):
    """POST /api/v1/optimization/{id}/govern: Creates governed mission proposal (Section 18)."""
    try:
        return knowledge_learning_engine.create_governed_mission_proposal(recommendation_id=recommendation_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@optimization_router.post("/recommendations/{recommendation_id}/apply", response_model=OptimizationRecommendation)
def apply_optimization_recommendation_legacy(
    recommendation_id: str,
    operator: str = Query("cyber-optimizer")
):
    try:
        return knowledge_learning_engine.apply_optimization(recommendation_id=recommendation_id, operator=operator)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@optimization_router.post("/recommendations/dag", response_model=DAGOptimizationPlan)
def optimize_mission_dag(
    mission_id: str = Body(..., embed=True),
    subtasks: List[Dict[str, Any]] = Body(..., embed=True)
):
    return knowledge_learning_engine.optimize_dag_schedule(mission_id=mission_id, subtasks=subtasks)


@optimization_router.post("/daemon/cycle")
def trigger_daemon_cycle():
    """POST /api/v1/optimization/daemon/cycle: Runs one operations daemon knowledge cycle."""
    return knowledge_learning_engine.run_daemon_cycle()


@optimization_router.get("/tools/performance", response_model=List[ToolPerformanceMetric])
def list_tool_performance_metrics():
    return knowledge_learning_engine.list_tool_metrics()
