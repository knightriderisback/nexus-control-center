"""
NEXUS Phase 12-13: Autonomous Engineering Mission Control REST API Router.
Mounted at /api/v1/missions.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from models.schemas import (
    EngineeringMission,
    MissionPlanRequest,
    MissionRunRequest,
    MissionCheckpoint,
    MissionKnowledge,
    AgentCapability
)
from orchestrator.mission_engine import mission_engine
from orchestrator.capability_registry import capability_registry
from orchestrator.mission_memory import mission_memory
from orchestrator.traceability_engine import traceability_engine

router = APIRouter(prefix="/missions", tags=["Autonomous Missions"])


@router.post("", response_model=EngineeringMission)
@router.post("/plan", response_model=EngineeringMission)
def plan_or_create_mission(req: MissionPlanRequest):
    """
    Decomposes a natural-language goal into a structured engineering mission:
    normalized objective, requirements, acceptance criteria, capabilities,
    and a topological dependency DAG.
    """
    try:
        return mission_engine.plan_mission(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/run", response_model=EngineeringMission)
def run_mission(req: MissionRunRequest, background_tasks: BackgroundTasks):
    """
    Plans and executes an autonomous engineering mission end-to-end.
    If background=True, runs asynchronously and returns the planned mission state.
    """
    try:
        plan_req = MissionPlanRequest(
            goal=req.goal,
            repo_path=req.repo_path,
            target_branch=req.target_branch,
            context_files=req.context_files,
            constraints=req.constraints,
            max_parallel_tasks=req.max_parallel_tasks,
            max_remediation_rounds=req.max_remediation_rounds,
            auto_merge=req.auto_merge,
            auto_deliver_github=getattr(req, "auto_deliver_github", False),
            idempotency_key=getattr(req, "idempotency_key", None)
        )
        mission = mission_engine.plan_mission(plan_req)

        if req.background:
            background_tasks.add_task(mission_engine.execute_mission, mission.mission_id)
            return mission
        else:
            return mission_engine.execute_mission(mission.mission_id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[EngineeringMission])
def list_missions(limit: int = 50, state: Optional[str] = None):
    """Lists all engineering missions sorted by creation date."""
    return mission_engine.list_missions(limit=limit, state=state)


@router.get("/capabilities/list")
def list_capabilities() -> Dict[str, Any]:
    """Lists all registered agent capabilities."""
    all_caps = capability_registry.list_all_capabilities()
    return {
        "count": len(all_caps),
        "capabilities": {k: v.model_dump() if hasattr(v, "model_dump") else v.dict() for k, v in all_caps.items()}
    }


@router.get("/knowledge/list")
def list_knowledge(category: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Queries the structured mission knowledge layer."""
    entries = mission_memory.query_knowledge(category=category, limit=limit)
    return {
        "count": len(entries),
        "knowledge": [e.model_dump() if hasattr(e, "model_dump") else e.dict() for e in entries]
    }


@router.get("/{mission_id}", response_model=EngineeringMission)
def get_mission(mission_id: str):
    """Retrieves full details, subtasks, acceptance criteria, and telemetry for a mission."""
    mission = mission_engine.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    return mission


@router.post("/{mission_id}/start", response_model=EngineeringMission)
@router.post("/{mission_id}/execute", response_model=EngineeringMission)
def start_mission(mission_id: str, background: bool = False, background_tasks: BackgroundTasks = None):
    """Triggers execution of a planned or ready mission."""
    mission = mission_engine.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")

    try:
        if background and background_tasks:
            background_tasks.add_task(mission_engine.execute_mission, mission_id)
            return mission
        return mission_engine.execute_mission(mission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/pause", response_model=EngineeringMission)
def pause_mission(mission_id: str):
    """Pauses an executing mission and saves a recovery checkpoint."""
    try:
        return mission_engine.pause_mission(mission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/resume", response_model=EngineeringMission)
def resume_mission(mission_id: str):
    """Resumes a paused, failed, or awaiting-approval mission from its checkpoint."""
    try:
        return mission_engine.resume_mission(mission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/cancel", response_model=EngineeringMission)
def cancel_mission(mission_id: str):
    """Cancels an in-flight mission and safely tears down ephemeral worktrees."""
    try:
        return mission_engine.cancel_mission(mission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/retry", response_model=EngineeringMission)
def retry_mission(mission_id: str, subtask_id: Optional[str] = None):
    """Retries a failed mission or specific failed subtask."""
    try:
        return mission_engine.retry_mission(mission_id, subtask_id=subtask_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mission_id}/rollback", response_model=EngineeringMission)
def rollback_mission(mission_id: str):
    """Rolls back changes from an unmerged or failed mission."""
    try:
        return mission_engine.rollback_mission(mission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{mission_id}/graph")
def get_mission_graph(mission_id: str):
    """Retrieves the dependency DAG graph nodes and execution levels for visualization."""
    try:
        return mission_engine.get_mission_graph(mission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{mission_id}/traceability")
def get_mission_traceability(mission_id: str):
    """Retrieves the complete requirement-to-outcome traceability matrix."""
    try:
        return mission_engine.get_mission_traceability(mission_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{mission_id}/why-artifact")
def why_artifact(mission_id: str, path: str = Query(..., description="Path to artifact")):
    """Answers: 'Why is this code/artifact part of this mission?'"""
    mission = mission_engine.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    return traceability_engine.why_artifact(mission, path)


@router.get("/{mission_id}/tests-for-requirement")
def tests_for_requirement(mission_id: str, requirement_id: str = Query(..., description="Requirement ID")):
    """Answers: 'Which requirement does this test verify?'"""
    mission = mission_engine.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    return {
        "mission_id": mission_id,
        "requirement_id": requirement_id,
        "tests": traceability_engine.tests_for_requirement(mission, requirement_id)
    }


@router.get("/{mission_id}/checkpoints")
def get_mission_checkpoints(mission_id: str):
    """Retrieves all saved recovery checkpoints for a mission."""
    checkpoints = mission_memory.get_checkpoints(mission_id)
    return {
        "mission_id": mission_id,
        "count": len(checkpoints),
        "checkpoints": [cp.model_dump() if hasattr(cp, "model_dump") else cp.dict() for cp in checkpoints]
    }


@router.get("/{mission_id}/events")
def get_mission_events(mission_id: str):
    """Retrieves chronological lifecycle events and transitions for a mission."""
    mission = mission_engine.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    return {
        "mission_id": mission_id,
        "state": str(mission.state.value if hasattr(mission.state, "value") else mission.state),
        "events": getattr(mission, "events", []) or []
    }


@router.get("/{mission_id}/changelog")
def get_mission_changelog(mission_id: str):
    """Retrieves the synthesized release changelog for a completed mission."""
    mission = mission_engine.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    return {
        "mission_id": mission_id,
        "goal": mission.goal,
        "state": mission.state,
        "changelog": mission.release_changelog or "Changelog not yet generated."
    }
