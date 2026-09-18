from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os
import uuid
from datetime import datetime
from orchestrator.worktree_manager import worktree_manager
from models.schemas import (
    AgentManifest,
    TaskDispatchRequest,
    TaskItem,
    RiskLevel,
    AgentHandoffRequest,
    AgentHandoffRecord,
    SwarmPipelineRequest,
    SwarmPipelineResult,
    AgyCodexSessionRequest,
    AgyCodexSession,
    WorktreeInfo,
    WorktreeProvisionRequest,
    MergeEvaluationRequest,
    MergeEvaluationResult,
    MergeExecutionRequest,
    MergeExecutionResult,
    MergeCandidateCreateRequest,
    MergeCandidate
)
from orchestrator.agents import get_agent_list, get_agent_by_id
from core.audit import record_audit
from core.policy import evaluate_action
from core.approvals import request_approval

router = APIRouter(prefix="/agents", tags=["AI Agent Swarm"])

ACTIVE_TASKS: List[TaskItem] = []

@router.get("", response_model=List[AgentManifest])
def list_agents():
    return get_agent_list()


@router.get("/worktrees", response_model=List[WorktreeInfo])
def list_worktrees(repo_path: Optional[str] = None):
    from orchestrator.worktree_manager import worktree_manager
    return worktree_manager.list_worktrees(repo_path)


@router.post("/worktrees/provision", response_model=WorktreeInfo)
def provision_worktree(req: WorktreeProvisionRequest):
    from orchestrator.worktree_manager import worktree_manager
    s_id = req.session_id or f"sess-{uuid.uuid4().hex[:8]}"
    try:
        wt = worktree_manager.provision_worktree(
            repo_path=req.repo_path,
            session_id=s_id,
            branch_name=req.branch_name
        )
        return wt
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/worktrees/{session_id}/teardown")
def teardown_worktree(session_id: str, force: bool = True, delete_branch: bool = False):
    from orchestrator.worktree_manager import worktree_manager
    return worktree_manager.teardown_worktree(session_id=session_id, force=force, delete_branch=delete_branch)


@router.post("/worktrees/prune")
def prune_worktrees():
    from orchestrator.worktree_manager import worktree_manager
    count = worktree_manager.prune_stale_worktrees()
    return {"pruned_count": count}


@router.post("/merge/evaluate", response_model=MergeEvaluationResult)
def evaluate_branch_merge(req: MergeEvaluationRequest):
    from orchestrator.merge_arbitrator import merge_arbitrator
    try:
        return merge_arbitrator.evaluate_merge(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge/execute", response_model=MergeExecutionResult)
def execute_branch_merge(req: MergeExecutionRequest):
    from orchestrator.merge_arbitrator import merge_arbitrator
    try:
        return merge_arbitrator.execute_merge(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/merge/history")
def list_merge_history(limit: int = 50):
    from orchestrator.merge_arbitrator import merge_arbitrator
    return merge_arbitrator.list_history(limit=limit)


@router.get("/merge/{merge_id}")
def get_merge_record(merge_id: str):
    from orchestrator.merge_arbitrator import merge_arbitrator
    rec = merge_arbitrator.get_merge_record(merge_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Merge record '{merge_id}' not found")
    return rec


@router.post("/merge/{merge_id}/review")
def review_merge_candidate(merge_id: str):
    from orchestrator.merge_arbitrator import merge_arbitrator
    rec = merge_arbitrator.get_merge_record(merge_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Merge record '{merge_id}' not found")
    staging_wt = os.path.join(worktree_manager.worktrees_dir, merge_id)
    if not os.path.exists(staging_wt):
        from orchestrator.safe_runner import SafeCommandExecutor
        branch_name = f"staging/{merge_id}"
        add_res = SafeCommandExecutor.execute(
            ["git", "worktree", "add", staging_wt, branch_name],
            cwd=rec["repo_path"]
        )
        if add_res.exit_code != 0:
            raise HTTPException(status_code=400, detail=f"Staging worktree for '{merge_id}' is not active: {add_res.stderr or add_res.stdout}")
    try:
        review = merge_arbitrator.review_merge_with_fleet(
            repo=rec["repo_path"],
            merge_id=merge_id,
            staging_wt_path=staging_wt,
            source_branch=rec["source_branch"],
            target_branch=rec["target_branch"],
            conflict_files=rec.get("conflict_files", [])
        )
        return {"status": "REVIEW_COMPLETED", "review": review}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge/{merge_id}/integrate", response_model=MergeExecutionResult)
def integrate_approved_merge(merge_id: str, approval_id: str):
    from orchestrator.merge_arbitrator import merge_arbitrator
    try:
        return merge_arbitrator.integrate_approved_candidate(merge_id=merge_id, approval_id=approval_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge/{merge_id}/reject")
def reject_merge_candidate(merge_id: str, reason: str = "Rejected by operator"):
    from orchestrator.merge_arbitrator import merge_arbitrator
    try:
        return merge_arbitrator.reject_candidate(merge_id=merge_id, reason=reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------------------------
# Merge Candidate Lifecycle State Machine Endpoints
# -----------------------------------------------------------------------------

@router.post("/merge/candidates", response_model=MergeCandidate)
def create_merge_candidate_endpoint(req: MergeCandidateCreateRequest):
    from orchestrator.merge_arbitrator import merge_arbitrator
    try:
        return merge_arbitrator.create_candidate(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/merge/candidates", response_model=List[MergeCandidate])
def list_merge_candidates_endpoint(limit: int = 50):
    from orchestrator.merge_arbitrator import merge_arbitrator
    return merge_arbitrator.list_candidates(limit=limit)


@router.get("/merge/candidates/{candidate_id}", response_model=MergeCandidate)
def get_merge_candidate_endpoint(candidate_id: str):
    from orchestrator.merge_arbitrator import merge_arbitrator
    cand = merge_arbitrator.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Merge candidate '{candidate_id}' not found")
    return cand


@router.post("/merge/candidates/{candidate_id}/analyze", response_model=MergeCandidate)
def analyze_merge_candidate_endpoint(candidate_id: str):
    from orchestrator.merge_arbitrator import merge_arbitrator
    cand = merge_arbitrator.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Merge candidate '{candidate_id}' not found")
    try:
        return merge_arbitrator.analyze_candidate(candidate_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge/candidates/{candidate_id}/verify", response_model=MergeCandidate)
def verify_merge_candidate_endpoint(candidate_id: str):
    from orchestrator.merge_arbitrator import merge_arbitrator
    cand = merge_arbitrator.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Merge candidate '{candidate_id}' not found")
    try:
        return merge_arbitrator.verify_candidate(candidate_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge/candidates/{candidate_id}/review")
def review_merge_candidate_endpoint(candidate_id: str):
    from orchestrator.merge_arbitrator import merge_arbitrator
    cand = merge_arbitrator.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Merge candidate '{candidate_id}' not found")
    try:
        review = merge_arbitrator.review_candidate(candidate_id)
        return {"status": "REVIEW_COMPLETED", "review": review}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge/candidates/{candidate_id}/integrate", response_model=MergeCandidate)
def integrate_merge_candidate_endpoint(candidate_id: str, approval_id: Optional[str] = None):
    from orchestrator.merge_arbitrator import merge_arbitrator
    cand = merge_arbitrator.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Merge candidate '{candidate_id}' not found")
    try:
        return merge_arbitrator.integrate_candidate(candidate_id, approval_id=approval_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge/candidates/{candidate_id}/rollback", response_model=MergeCandidate)
def rollback_merge_candidate_endpoint(candidate_id: str, reason: str = "Rollback requested"):
    from orchestrator.merge_arbitrator import merge_arbitrator
    cand = merge_arbitrator.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Merge candidate '{candidate_id}' not found")
    try:
        return merge_arbitrator.rollback_candidate(candidate_id, reason=reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merge/candidates/{candidate_id}/reject", response_model=MergeCandidate)
def reject_merge_candidate_lifecycle_endpoint(candidate_id: str, reason: str = "Rejected by operator"):
    from orchestrator.merge_arbitrator import merge_arbitrator
    cand = merge_arbitrator.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail=f"Merge candidate '{candidate_id}' not found")
    try:
        return merge_arbitrator.reject_candidate_by_id(candidate_id, reason=reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/{agent_id}", response_model=AgentManifest)
def get_agent(agent_id: str):
    agent = get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return agent

@router.post("/dispatch")
def dispatch_agent_task(dispatch: TaskDispatchRequest):
    from orchestrator.runtime import runtime_engine
    agent = get_agent_by_id(dispatch.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    task = runtime_engine.create_task(
        agent_id=dispatch.agent_id,
        title=dispatch.title,
        instructions=dispatch.instructions,
        project_id=dispatch.project_id or "control-center",
        autonomy_tier=dispatch.autonomy_tier or "Guardrailed"
    )

    executed_task = runtime_engine.execute_task(task.id)
    ACTIVE_TASKS.insert(0, executed_task)

    if executed_task.status == "awaiting_approval":
        appr_id = executed_task.result.get("approval_id") if executed_task.result else None
        return {"status": "AWAITING_APPROVAL", "task": executed_task, "approval_id": appr_id}

    return {"status": "DISPATCHED", "task": executed_task}


@router.get("/tools/registry")
def list_tool_registry():
    from orchestrator.tool_registry import tool_registry
    return [t.model_dump() for t in tool_registry.list_tools()]

@router.get("/{agent_id}/tools")
def list_agent_tools(agent_id: str):
    agent = get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    from orchestrator.tool_registry import tool_registry
    return [t.model_dump() for t in tool_registry.list_tools(agent_id)]

class ToolExecuteRequest(BaseModel):
    tool: str
    params: Optional[Dict[str, Any]] = None

@router.post("/{agent_id}/execute")
def execute_direct_tool(agent_id: str, req: ToolExecuteRequest):
    agent = get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    from orchestrator.tool_registry import tool_registry
    is_valid, err = tool_registry.validate_tool_call(req.tool, agent_id, req.params or {})
    if not is_valid:
        # Check alias if tool name is legacy
        pass

    from orchestrator.tool_runner import execute_agent_tool
    res = execute_agent_tool(agent_id, req.tool, req.params or {})
    return {"agent_id": agent_id, "tool": req.tool, "output": res}


@router.post("/handoff")
def trigger_agent_handoff(req: AgentHandoffRequest):
    from orchestrator.runtime import runtime_engine
    parent = get_agent_by_id(req.parent_agent_id)
    if not parent:
        raise HTTPException(status_code=404, detail=f"Parent agent '{req.parent_agent_id}' not found")
    target = get_agent_by_id(req.target_agent_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target agent '{req.target_agent_id}' not found")

    res = runtime_engine.execute_handoff(
        parent_agent_id=req.parent_agent_id,
        target_agent_id=req.target_agent_id,
        task_title=req.task_title,
        instructions=req.instructions,
        context=req.context or {},
        project_id=req.project_id or "control-center",
        parent_execution_id=req.parent_execution_id,
        recursion_depth=req.recursion_depth
    )
    return {"status": res.get("status", "COMPLETED"), "handoff": res}


@router.get("/handoffs/all")
def list_handoffs():
    from orchestrator.runtime import runtime_engine
    return [h.model_dump() for h in runtime_engine.list_handoffs()]


@router.get("/handoffs/{handoff_id}")
def get_handoff_by_id(handoff_id: str):
    from orchestrator.runtime import runtime_engine
    h = runtime_engine.get_handoff(handoff_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"Handoff '{handoff_id}' not found")
    return h.model_dump()


@router.post("/pipeline")
def trigger_swarm_pipeline(req: SwarmPipelineRequest):
    from orchestrator.runtime import runtime_engine
    res = runtime_engine.execute_swarm_pipeline(req)
    return {"status": res.status, "pipeline": res.model_dump()}


@router.get("/pipelines/all")
def list_swarm_pipelines():
    from orchestrator.runtime import runtime_engine
    return [p.model_dump() for p in runtime_engine.list_pipelines()]


@router.get("/pipelines/{pipeline_id}")
def get_swarm_pipeline_by_id(pipeline_id: str):
    from orchestrator.runtime import runtime_engine
    p = runtime_engine.get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")
    return p.model_dump()


# =============================================================================
# AGY ↔ Codex Autonomous Session Endpoints
# =============================================================================

@router.post("/sessions/create")
def create_swarm_session(req: AgyCodexSessionRequest, execute_now: bool = True):
    from orchestrator.session_engine import session_engine
    session = session_engine.create_session(req)
    if execute_now:
        session = session_engine.execute_session(session.session_id)
    return {"status": session.status, "session": session.model_dump()}


@router.get("/sessions/all")
def list_swarm_sessions():
    from orchestrator.session_engine import session_engine
    return [s.model_dump() for s in session_engine.list_sessions()]


@router.get("/sessions/{session_id}")
def get_swarm_session_by_id(session_id: str):
    from orchestrator.session_engine import session_engine
    s = session_engine.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return s.model_dump()


@router.post("/sessions/{session_id}/execute")
def execute_swarm_session_by_id(session_id: str):
    from orchestrator.session_engine import session_engine
    s = session_engine.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    res = session_engine.execute_session(session_id)
    return {"status": res.status, "session": res.model_dump()}


@router.post("/sessions/{session_id}/rollback")
def rollback_swarm_session_by_id(session_id: str):
    from orchestrator.session_engine import session_engine
    s = session_engine.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    res = session_engine.rollback_session(session_id)
    return {"status": res.status, "session": res.model_dump()}



