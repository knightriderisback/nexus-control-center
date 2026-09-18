"""
NEXUS Phase 20: Mission Intelligence, Adaptive Execution, and Decisions REST Routers.

Exposes:
- /api/v1/mission-intelligence (Context, intent synthesis, similar missions, risk signals)
- /api/v1/adaptive-execution (Adaptive planning, wave execution, bounded replanning, lifecycle)
- /api/v1/mission-decisions (Persistent decision journal with 6-attribute rationale)
"""

from fastapi import APIRouter, HTTPException, status, Query, Body
from typing import Dict, Any, List, Optional

from models.schemas import (
    MissionIntentAnalysis,
    AdaptiveMissionPlan,
    MissionSynthesizeRequest,
    MissionExecutionRequest,
    DynamicAdaptRequest,
    ReplanMissionRequest,
    MissionAdaptationEvent,
    MissionDecision,
    MissionIntelligenceContext,
    AdaptiveExecutionTelemetry
)
from orchestrator.mission_intelligence_engine import mission_intelligence_engine

# -----------------------------------------------------------------------------
# 1. MISSION INTELLIGENCE ROUTER
# -----------------------------------------------------------------------------
mission_intelligence_router = APIRouter(prefix="/mission-intelligence", tags=["Mission Intelligence"])


@mission_intelligence_router.post("/context", response_model=MissionIntelligenceContext, status_code=status.HTTP_200_OK)
def build_mission_context(req: MissionSynthesizeRequest):
    """Synthesizes mission context, retrieves similar missions, and detects evidence-backed risk signals."""
    try:
        return mission_intelligence_engine.build_mission_context(
            goal=req.goal,
            project_id=req.project_id,
            context_hints=req.context_hints,
            max_token_budget=req.max_token_budget
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@mission_intelligence_router.post("/synthesize", response_model=MissionIntentAnalysis, status_code=status.HTTP_200_OK)
def synthesize_mission_intent(req: MissionSynthesizeRequest):
    """Parses a raw goal into a structured, constraint-aware mission intent."""
    try:
        return mission_intelligence_engine.synthesize_intent(
            goal=req.goal,
            project_id=req.project_id,
            context_hints=req.context_hints,
            max_token_budget=req.max_token_budget
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@mission_intelligence_router.post("/plan", response_model=AdaptiveMissionPlan, status_code=status.HTTP_201_CREATED)
def generate_adaptive_mission_plan(req: MissionSynthesizeRequest):
    """Synthesizes a complete adaptive mission plan with DAG, waves, agent assignments, and fallback routes."""
    try:
        return mission_intelligence_engine.generate_adaptive_plan(
            goal=req.goal,
            project_id=req.project_id,
            context_hints=req.context_hints,
            max_token_budget=req.max_token_budget
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@mission_intelligence_router.get("/missions", response_model=List[AdaptiveMissionPlan])
def list_adaptive_missions():
    """Lists all active and historical adaptive mission plans."""
    return mission_intelligence_engine.list_missions()


@mission_intelligence_router.get("/missions/{mission_id}", response_model=AdaptiveMissionPlan)
def get_adaptive_mission(mission_id: str):
    """Retrieves a specific adaptive mission by ID."""
    plan = mission_intelligence_engine.get_mission(mission_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission {mission_id} not found")
    return plan


@mission_intelligence_router.get("/telemetry", response_model=AdaptiveExecutionTelemetry)
def get_adaptive_telemetry():
    """Retrieves real-time adaptive execution telemetry and efficiency metrics."""
    return mission_intelligence_engine.get_telemetry()


@mission_intelligence_router.get("/health")
def get_health():
    """Returns the operational status and $0.00 zero-cost FinOps verification."""
    return mission_intelligence_engine.get_health()


# -----------------------------------------------------------------------------
# 2. ADAPTIVE EXECUTION ROUTER
# -----------------------------------------------------------------------------
adaptive_execution_router = APIRouter(prefix="/adaptive-execution", tags=["Adaptive Execution"])


@adaptive_execution_router.post("/execute/{mission_id}")
def execute_adaptive_mission(mission_id: str, req: Optional[MissionExecutionRequest] = None):
    """Executes the adaptive mission DAG wave by wave with real-time error interception."""
    try:
        dry_run = req.dry_run if req else False
        auto_remediate = req.auto_remediate if req else True
        concurrency_limit = req.concurrency_limit if req else 4
        return mission_intelligence_engine.execute_mission_plan(
            mission_id=mission_id,
            dry_run=dry_run,
            auto_remediate=auto_remediate,
            concurrency_limit=concurrency_limit
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@adaptive_execution_router.post("/adapt/{mission_id}", response_model=MissionAdaptationEvent)
def trigger_dynamic_adaptation(mission_id: str, req: DynamicAdaptRequest):
    """Forces or triggers dynamic in-flight re-routing / DAG mutation on a specific task node."""
    try:
        return mission_intelligence_engine.adapt_runtime_node(
            mission_id=mission_id,
            task_id=req.task_id,
            forced_strategy=req.forced_strategy,
            reason=req.reason
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@adaptive_execution_router.post("/replan", response_model=AdaptiveMissionPlan)
def replan_mission(req: ReplanMissionRequest):
    """Executes controlled runtime replanning with strict max 3 replans boundary."""
    try:
        return mission_intelligence_engine.replan_mission(
            mission_id=req.mission_id,
            reason=req.reason,
            failure_task_id=req.failure_task_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@adaptive_execution_router.post("/pause/{mission_id}")
def pause_mission(mission_id: str):
    """Pauses an actively executing adaptive mission."""
    ok = mission_intelligence_engine.pause_mission(mission_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission {mission_id} not found")
    return {"status": "PAUSED", "mission_id": mission_id}


@adaptive_execution_router.post("/resume/{mission_id}")
def resume_mission(mission_id: str):
    """Resumes a paused adaptive mission."""
    ok = mission_intelligence_engine.resume_mission(mission_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission {mission_id} not found")
    return {"status": "RUNNING", "mission_id": mission_id}


@adaptive_execution_router.post("/cancel/{mission_id}")
def cancel_mission(mission_id: str):
    """Cancels an adaptive mission."""
    ok = mission_intelligence_engine.cancel_mission(mission_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mission {mission_id} not found")
    return {"status": "CANCELLED", "mission_id": mission_id}


# -----------------------------------------------------------------------------
# 3. MISSION DECISIONS ROUTER
# -----------------------------------------------------------------------------
mission_decisions_router = APIRouter(prefix="/mission-decisions", tags=["Mission Decisions Journal"])


@mission_decisions_router.get("", response_model=List[MissionDecision])
def list_mission_decisions(mission_id: Optional[str] = Query(None, description="Optional mission ID filter")):
    """Retrieves all journaled mission decisions with full 6-attribute schema and traceability."""
    return mission_intelligence_engine.get_decisions(mission_id=mission_id)


# Backward compatibility alias for router import
router = mission_intelligence_router
