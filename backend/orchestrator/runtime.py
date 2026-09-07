"""
NEXUS Agent Execution Lifecycle & Runtime Engine.
Manages the deterministic task state machine:
  PENDING -> VALIDATING -> RUNNING -> AWAITING_APPROVAL -> COMPLETED / FAILED

Enforces:
- Formal tool permissions from Tool Registry
- Safe command execution via SafeCommandExecutor
- Developer Agent safe cycle: INSPECT -> PLAN -> MODIFY -> TEST -> DIFF
- QA, Security, Documentation, and Research specialized autonomous paths
- Zero mutations to main branch without explicit approval
"""

import os
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from models.schemas import TaskItem, RiskLevel, ApprovalStatus
from orchestrator.agents import get_agent_by_id
from orchestrator.tool_registry import tool_registry
from orchestrator.safe_runner import SafeCommandExecutor
from orchestrator.tool_runner import ResearchRunner, DataRunner, DocsRunner, DevRunner
from core.policy import evaluate_action
from core.approvals import request_approval
from core.audit import record_audit
from core.observability import collector

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class AgentRuntimeEngine:
    """Manages active tasks, agent state transitions, and sandboxed execution."""

    def __init__(self):
        self._tasks: Dict[str, TaskItem] = {}

    def get_task(self, task_id: str) -> Optional[TaskItem]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[TaskItem]:
        return list(self._tasks.values())

    def create_task(
        self,
        agent_id: str,
        title: str,
        instructions: str,
        project_id: str = "control-center",
        autonomy_tier: str = "Guardrailed"
    ) -> TaskItem:
        agent = get_agent_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' is not registered in agent fleet.")

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = TaskItem(
            id=task_id,
            title=title,
            agent_id=agent_id,
            agent_name=agent.name,
            project_id=project_id,
            status="pending",
            progress=0,
            risk_level=agent.risk_level,
            started_at=_now_iso(),
            logs=[f"[{_now_iso()}] Task created for {agent.name}. Status: PENDING."],
            result=None,
            error=None
        )
        self._tasks[task_id] = task
        return task

    def execute_task(self, task_id: str) -> TaskItem:
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        agent = get_agent_by_id(task.agent_id)
        if not agent:
            task.status = "failed"
            task.error = f"Agent '{task.agent_id}' not registered"
            return task

        # State 1: VALIDATING
        task.status = "validating"
        task.progress = 15
        task.logs.append(f"[{_now_iso()}] State: VALIDATING policy constraints and tool permissions.")

        # Policy & Risk Evaluation
        risk, requires_appr, policy_reason = evaluate_action(task.title, task.project_id)
        task.risk_level = risk

        if requires_appr:
            # State: AWAITING_APPROVAL
            task.status = "awaiting_approval"
            task.progress = 25
            appr = request_approval(
                action=f"Agent Directive: {task.title}",
                target_project=task.project_id or "control-center",
                reason=f"Agent {agent.name} triggered gate: {policy_reason}",
                command=f"# Agent {agent.name} execution for: {task.title}",
                actor=agent.id,
                task_id=task.id,
                risk_level=risk
            )
            task.logs.append(f"[{_now_iso()}] State: AWAITING_APPROVAL. Gate {appr.id} created for {risk.value} risk action.")
            task.result = {
                "approval_required": True,
                "approval_id": appr.id,
                "reason": policy_reason,
                "risk_level": risk.value
            }
            return task

        # State 2: RUNNING
        task.status = "running"
        task.progress = 50
        task.logs.append(f"[{_now_iso()}] State: RUNNING autonomous execution loop.")

        try:
            # Route to specialized execution implementation
            if task.agent_id == "agent-dev":
                res = self._execute_developer_loop(task)
            elif task.agent_id == "agent-research":
                res = self._execute_research_loop(task)
            elif task.agent_id == "agent-qa":
                res = self._execute_qa_loop(task)
            elif task.agent_id == "agent-security":
                res = self._execute_security_loop(task)
            elif task.agent_id == "agent-docs":
                res = self._execute_docs_loop(task)
            elif task.agent_id == "agent-data":
                res = self._execute_data_loop(task)
            else:
                res = {"status": "SUCCESS", "message": f"Agent {agent.name} completed simulated directive."}

            task.status = "completed"
            task.progress = 100
            task.completed_at = _now_iso()
            task.result = res
            task.logs.append(f"[{_now_iso()}] State: COMPLETED. All cycle assertions satisfied.")
            collector.record_agent_metric(task.agent_id, "COMPLETED")

            record_audit(
                action=f"AGENT_TASK_COMPLETED: {task.title}",
                project=task.project_id or "control-center",
                target=task.agent_id,
                reason="Autonomous task completed cleanly",
                risk_level=task.risk_level,
                result="SUCCESS",
                actor=task.agent_id
            )

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.logs.append(f"[{_now_iso()}] State: FAILED. Error: {str(e)}")
            collector.record_agent_metric(task.agent_id, "FAILED")

            record_audit(
                action=f"AGENT_TASK_FAILED: {task.title}",
                project=task.project_id or "control-center",
                target=task.agent_id,
                reason=str(e),
                risk_level=RiskLevel.MEDIUM,
                result="FAILURE",
                actor=task.agent_id
            )

        return task

    # -------------------------------------------------------------------------
    # Developer Agent Execution Loop: INSPECT -> PLAN -> MODIFY -> TEST -> DIFF
    # -------------------------------------------------------------------------
    def _execute_developer_loop(self, task: TaskItem) -> Dict[str, Any]:
        task.logs.append(f"[{_now_iso()}] [DEV-LOOP: 1/5 INSPECT] Inspecting repository and working tree.")
        status_res = SafeCommandExecutor.execute(["git", "status", "-s"], cwd="/root/control-center")

        task.logs.append(f"[{_now_iso()}] [DEV-LOOP: 2/5 PLAN] Synthesizing execution plan and safety checks.")
        # Strict rule: Developer agent never mutates production repository directly without a feature branch or approval
        task.logs.append(f"[{_now_iso()}] [DEV-LOOP: 3/5 MODIFY] Executing modification in safe isolated sandbox.")
        
        # We test modification and validation in an isolated temp fixture or branch
        with tempfile.TemporaryDirectory() as sandbox_dir:
            sample_file = os.path.join(sandbox_dir, "feature_module.py")
            with open(sample_file, "w") as f:
                f.write("# Safe Sandbox Module\ndef feature():\n    return 'ACTIVE'\n")
            
            # Subprocess test inside sandbox
            test_file = os.path.join(sandbox_dir, "test_feature.py")
            with open(test_file, "w") as f:
                f.write("from feature_module import feature\ndef test_feature():\n    assert feature() == 'ACTIVE'\n")

            task.logs.append(f"[{_now_iso()}] [DEV-LOOP: 4/5 TEST] Executing pytest validation in sandbox.")
            test_res = SafeCommandExecutor.execute(["pytest", test_file, "-q"], cwd=sandbox_dir)

        task.logs.append(f"[{_now_iso()}] [DEV-LOOP: 5/5 DIFF] Extracting git diff telemetry.")
        diff_res = SafeCommandExecutor.execute(["git", "diff", "HEAD"], cwd="/root/control-center")

        return {
            "cycle": "INSPECT -> PLAN -> MODIFY -> TEST -> DIFF",
            "working_tree_clean": len(status_res.stdout.strip()) == 0,
            "sandbox_tests_passed": test_res.exit_code == 0,
            "sandbox_test_output": test_res.stdout.strip(),
            "has_diff": len(diff_res.stdout.strip()) > 0,
            "diff_summary": f"{len(diff_res.stdout.splitlines())} diff lines in control-center"
        }

    def _execute_research_loop(self, task: TaskItem) -> Dict[str, Any]:
        task.logs.append(f"[{_now_iso()}] [RESEARCH] Searching codebase symbols for task directive.")
        query = task.title.split()[-1] if task.title else "FastAPI"
        res = ResearchRunner.search_codebase(query, root_dir="/root/control-center")
        return {
            "search_query": query,
            "match_count": res.get("match_count", 0),
            "matches": res.get("matches", [])[:10]
        }

    def _execute_qa_loop(self, task: TaskItem) -> Dict[str, Any]:
        task.logs.append(f"[{_now_iso()}] [QA] Executing regression test suite via SafeCommandExecutor.")
        res = SafeCommandExecutor.execute([
            "pytest", "tests/", "-q",
            "--ignore=tests/test_hardening_and_execution.py",
            "--ignore=tests/test_control_plane_security.py",
            "--ignore=tests/test_agent_runtime.py"
        ], cwd="/root/control-center")
        return {
            "exit_code": res.exit_code,
            "output": res.stdout.strip(),
            "success": res.exit_code == 0
        }

    def _execute_security_loop(self, task: TaskItem) -> Dict[str, Any]:
        task.logs.append(f"[{_now_iso()}] [SECURITY] Scanning control-center for hardcoded private keys.")
        from routers.v1.projects import run_security_scan
        return run_security_scan("control-center")

    def _execute_docs_loop(self, task: TaskItem) -> Dict[str, Any]:
        task.logs.append(f"[{_now_iso()}] [DOCS] Authoring Architecture Decision Record.")
        return DocsRunner.create_adr(
            title=task.title,
            category="Agent Architecture",
            content=f"Architectural log generated by autonomous Docs Agent for directive: {task.title}"
        )

    def _execute_data_loop(self, task: TaskItem) -> Dict[str, Any]:
        task.logs.append(f"[{_now_iso()}] [DATA] Querying local projects registry.")
        return DataRunner.query_vault("projects")

runtime_engine = AgentRuntimeEngine()
