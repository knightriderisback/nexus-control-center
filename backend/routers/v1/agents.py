from fastapi import APIRouter, HTTPException
from typing import List
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
    agent = get_agent_by_id(dispatch.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    risk, req_approval, policy_reason = evaluate_action(dispatch.title, dispatch.project_id or "")

    task_id = f"task-{uuid.uuid4().hex[:6]}"
    
    if req_approval:
        appr = request_approval(
            action=dispatch.title,
            target_project=dispatch.project_id or "general",
            reason=f"Mission objective: {dispatch.instructions}",
            actor=agent.name,
            task_id=task_id
        )
        task = TaskItem(
            id=task_id,
            title=dispatch.title,
            agent_id=agent.id,
            agent_name=agent.name,
            project_id=dispatch.project_id,
            status="awaiting_approval",
            progress=0,
            tokens_spent=150,
            risk_level=risk,
            started_at=datetime.utcnow().isoformat() + "Z",
            logs=[
                f"[{datetime.utcnow().strftime('%H:%M:%S')}] Mission objective evaluated: {dispatch.title}",
                f"[{datetime.utcnow().strftime('%H:%M:%S')}] POLICY GATE TRIGGERED: {risk.value} risk action.",
                f"[{datetime.utcnow().strftime('%H:%M:%S')}] Approval request {appr.id} logged. Awaiting operator clearance."
            ]
        )
        ACTIVE_TASKS.insert(0, task)
        return {"status": "AWAITING_APPROVAL", "task": task, "approval_id": appr.id}

    task = TaskItem(
        id=task_id,
        title=dispatch.title,
        agent_id=agent.id,
        agent_name=agent.name,
        project_id=dispatch.project_id,
        status="running",
        progress=25,
        tokens_spent=350,
        risk_level=risk,
        started_at=datetime.utcnow().isoformat() + "Z",
        logs=[
            f"[{datetime.utcnow().strftime('%H:%M:%S')}] Task dispatched to {agent.name}",
            f"[{datetime.utcnow().strftime('%H:%M:%S')}] Autonomy Tier: {dispatch.autonomy_tier}",
            f"[{datetime.utcnow().strftime('%H:%M:%S')}] Execution policy: {agent.execution_policy}",
            f"[{datetime.utcnow().strftime('%H:%M:%S')}] Processing directive: {dispatch.instructions[:100]}"
        ]
    )
    ACTIVE_TASKS.insert(0, task)

    record_audit(
        action=f"AGENT_DISPATCH: {dispatch.title}",
        project=dispatch.project_id or "general",
        target=agent.name,
        reason=dispatch.instructions,
        risk_level=risk,
        actor=agent.name,
        agent=agent.name
    )

    return {"status": "DISPATCHED", "task": task}
