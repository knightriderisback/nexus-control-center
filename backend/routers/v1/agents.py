from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime
from models.schemas import AgentManifest, TaskDispatchRequest, TaskItem, RiskLevel
from orchestrator.agents import get_agent_list, get_agent_by_id
from core.audit import record_audit
from core.policy import evaluate_action
from core.approvals import request_approval

router = APIRouter(prefix="/agents", tags=["AI Agent Swarm"])

ACTIVE_TASKS: List[TaskItem] = []

@router.get("", response_model=List[AgentManifest])
def list_agents():
    return get_agent_list()

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

