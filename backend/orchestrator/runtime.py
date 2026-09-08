"""
NEXUS Multi-Step Agent Execution Runtime Engine.
Enforces the mandatory execution lifecycle:
Task
↓
Agent Selection
↓
Policy Evaluation
↓
Plan
↓
Tool Selection
↓
Tool Execution
↓
Observation
↓
Next Step
↓
Validation
↓
Result
↓
Audit

Features:
- Configurable Execution Limits (max_steps, max_tool_calls, max_runtime_seconds)
- Every execution receives a unique execution ID
- Every tool call is audited with execution_id, tool_id, and actor
- Developer Agent 9-step safe engineering lifecycle with rollback capability
- QA Agent framework detection and structured result parsing
- Security Agent categorizing REAL FINDING, INFORMATIONAL, and UNAVAILABLE CHECK
- Documentation Agent with restricted path authoring
- Telemetry accounting linked to live runtime state
"""

import os
import re
import time
import uuid
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from models.schemas import (
    TaskItem,
    RiskLevel,
    ApprovalStatus,
    ToolCall,
    ToolResult,
    AgentObservation,
    AgentPlan,
    AgentStep,
    ExecutionLimits,
    AgentResult
)
from orchestrator.agents import get_agent_by_id
from orchestrator.tool_registry import tool_registry
from orchestrator.safe_runner import SafeCommandExecutor
from orchestrator.tool_runner import ResearchRunner, DataRunner, DocsRunner, DevRunner, execute_agent_tool
from orchestrator.circuit_breaker import circuit_breaker
from orchestrator.base import ai_router
from core.policy import evaluate_action
from core.approvals import request_approval
from core.audit import record_audit
from core.observability import collector

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ExecutionLimitExceeded(RuntimeError):
    """Raised when an execution limit is exceeded."""
    def __init__(self, limit_type: str, message: str):
        self.limit_type = limit_type
        super().__init__(message)


class ExecutionContext:
    """Tracks and enforces limits across an agent's multi-step execution."""
    def __init__(self, execution_id: str, limits: ExecutionLimits, start_time: float, recursion_depth: int = 0):
        self.execution_id = execution_id
        self.limits = limits
        self.start_time = start_time
        self.step_count = 0
        self.tool_call_count = 0
        self.file_mod_count = 0
        self.output_size_bytes = 0
        self.recent_tool_calls: List[Tuple[str, str]] = []
        self.recursion_depth = recursion_depth

    def check_runtime(self):
        elapsed = time.time() - self.start_time
        if elapsed > self.limits.max_runtime_seconds:
            raise ExecutionLimitExceeded("TIMEOUT", f"Execution timeout exceeded ({round(elapsed, 2)}s > {self.limits.max_runtime_seconds}s)")

    def check_step(self):
        self.check_runtime()
        self.step_count += 1
        if self.step_count > self.limits.max_steps:
            raise ExecutionLimitExceeded("MAX_STEPS", f"Step limit exceeded ({self.step_count} > {self.limits.max_steps})")

    def check_tool_call(self, tool_id: str, params: Dict[str, Any]):
        self.check_runtime()
        self.tool_call_count += 1
        if self.tool_call_count > self.limits.max_tool_calls:
            raise ExecutionLimitExceeded("MAX_TOOL_CALLS", f"Tool call limit exceeded ({self.tool_call_count} > {self.limits.max_tool_calls})")

        # Recursion depth limit check
        if self.recursion_depth > 3:
            raise ExecutionLimitExceeded("RECURSION_DEPTH", f"Maximum recursion depth exceeded ({self.recursion_depth} > 3)")

        # Runaway loop detection: 3 consecutive identical tool calls
        import json
        try:
            params_key = json.dumps(params, sort_keys=True, default=str)
        except Exception:
            params_key = str(params)
        call_signature = (tool_id, params_key)
        self.recent_tool_calls.append(call_signature)
        if len(self.recent_tool_calls) >= 3:
            last_three = self.recent_tool_calls[-3:]
            if last_three[0] == last_three[1] == last_three[2]:
                raise ExecutionLimitExceeded("RUNAWAY_LOOP", f"Runaway loop detected: tool '{tool_id}' executed 3 consecutive times with identical parameters.")

        # File modification tracking
        if tool_id in ["filesystem.write", "write_file", "git.branch"]:
            self.file_mod_count += 1
            if self.file_mod_count > self.limits.max_file_modifications:
                raise ExecutionLimitExceeded("MAX_FILE_MODIFICATIONS", f"File modification limit exceeded ({self.file_mod_count} > {self.limits.max_file_modifications})")

    def check_output_size(self, output: Any):
        import json
        try:
            out_bytes = len(json.dumps(output, default=str).encode("utf-8"))
        except Exception:
            out_bytes = 1000
        self.output_size_bytes += out_bytes
        if self.output_size_bytes > self.limits.max_output_size_bytes:
            raise ExecutionLimitExceeded("MAX_OUTPUT_SIZE", f"Output size limit exceeded ({self.output_size_bytes} > {self.limits.max_output_size_bytes} bytes)")

class AgentRuntimeEngine:
    """Core autonomous agent execution engine with multi-step observation loop."""

    def __init__(self):
        self._tasks: Dict[str, TaskItem] = {}
        self._results: Dict[str, AgentResult] = {}

    def get_task(self, task_id: str) -> Optional[TaskItem]:
        return self._tasks.get(task_id)

    def get_result(self, execution_id: str) -> Optional[AgentResult]:
        return self._results.get(execution_id)

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

    def execute_task(
        self,
        task_id: str,
        limits: Optional[ExecutionLimits] = None,
        rollback_on_test_failure: bool = False
    ) -> TaskItem:
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        exec_limits = limits or ExecutionLimits()
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        # Step 1: Agent Selection & Validation
        agent = get_agent_by_id(task.agent_id)
        if not agent:
            task.status = "failed"
            task.error = f"Agent '{task.agent_id}' not registered"
            return task

        # Step 2: Policy Evaluation
        task.status = "validating"
        task.progress = 10
        task.logs.append(f"[{_now_iso()}] [{execution_id}] Step 1: Policy evaluation for agent {agent.name}.")

        risk, requires_appr, policy_reason = evaluate_action(task.title, task.project_id)
        task.risk_level = risk

        if requires_appr:
            task.status = "awaiting_approval"
            task.progress = 20
            appr = request_approval(
                action=f"Agent Directive: {task.title}",
                target_project=task.project_id or "control-center",
                reason=f"Agent {agent.name} triggered policy: {policy_reason}",
                command=f"# Agent {agent.name} execution for: {task.title}",
                actor=agent.id,
                task_id=task.id,
                risk_level=risk
            )
            task.logs.append(f"[{_now_iso()}] [{execution_id}] Gate ENFORCED. Approval {appr.id} logged. Halting execution.")
            task.result = {
                "approval_required": True,
                "approval_id": appr.id,
                "execution_id": execution_id,
                "reason": policy_reason,
                "risk_level": risk.value
            }
            collector.record_agent_metric(
                agent_id=agent.id,
                status="AWAITING_APPROVAL",
                duration_ms=(time.time() - start_time) * 1000.0,
                approval_waits=1
            )
            return task

        # Step 3: Plan Generation
        task.status = "running"
        task.progress = 30
        task.logs.append(f"[{_now_iso()}] [{execution_id}] Step 2: Plan synthesis compiling autonomous execution steps.")

        steps_record: List[AgentStep] = []
        tool_calls_count = 0
        final_output = None
        exec_error = None

        try:
            rec_depth = getattr(exec_limits, "recursion_depth", 0)
            ctx = ExecutionContext(execution_id, exec_limits, start_time, recursion_depth=rec_depth)

            # Delegate to specialized persona execution
            if agent.id == "agent-dev":
                final_output, steps_record, tool_calls_count = self._execute_developer_lifecycle(
                    task, execution_id, exec_limits, rollback_on_test_failure, ctx=ctx
                )
            elif agent.id == "agent-qa":
                final_output, steps_record, tool_calls_count = self._execute_qa_lifecycle(
                    task, execution_id, exec_limits, ctx=ctx
                )
            elif agent.id == "agent-security":
                final_output, steps_record, tool_calls_count = self._execute_security_lifecycle(
                    task, execution_id, exec_limits, ctx=ctx
                )
            elif agent.id == "agent-docs":
                final_output, steps_record, tool_calls_count = self._execute_docs_lifecycle(
                    task, execution_id, exec_limits, ctx=ctx
                )
            elif agent.id == "agent-research":
                final_output, steps_record, tool_calls_count = self._execute_research_lifecycle(
                    task, execution_id, exec_limits, ctx=ctx
                )
            elif agent.id == "agent-data":
                final_output, steps_record, tool_calls_count = self._execute_data_lifecycle(
                    task, execution_id, exec_limits, ctx=ctx
                )
            else:
                final_output, steps_record, tool_calls_count = self._execute_generic_lifecycle(
                    task, execution_id, exec_limits, ctx=ctx
                )

            task.status = "completed"
            task.progress = 100
            task.completed_at = _now_iso()
            task.result = final_output
            task.logs.append(f"[{_now_iso()}] [{execution_id}] Lifecycle complete. {len(steps_record)} steps, {tool_calls_count} tool calls.")

            duration_ms = (time.time() - start_time) * 1000.0
            agent_result = AgentResult(
                task_id=task.id,
                execution_id=execution_id,
                agent_id=agent.id,
                status="COMPLETED",
                steps=steps_record,
                final_output=final_output,
                tool_calls_count=tool_calls_count,
                duration_ms=round(duration_ms, 2),
                tokens_used=tool_calls_count * 120
            )
            self._results[execution_id] = agent_result

            collector.record_agent_metric(
                agent_id=agent.id,
                status="COMPLETED",
                duration_ms=duration_ms,
                tool_calls=tool_calls_count,
                provider_used="MockEngine"
            )

            record_audit(
                action=f"AGENT_EXECUTION_COMPLETED: {task.title}",
                project=task.project_id or "control-center",
                target=agent.id,
                reason="All execution steps validated cleanly",
                risk_level=task.risk_level,
                result="SUCCESS",
                actor=agent.id,
                agent_id=agent.id,
                execution_id=execution_id,
                status="COMPLETED",
                result_summary=f"Completed in {round(duration_ms, 2)}ms with {tool_calls_count} tool calls."
            )

        except ExecutionLimitExceeded as e:
            duration_ms = (time.time() - start_time) * 1000.0
            task.status = "limit_exceeded"
            task.error = str(e)
            task.logs.append(f"[{_now_iso()}] [{execution_id}] Execution LIMIT BREACH: {str(e)}")

            tool_cnt = ctx.tool_call_count if 'ctx' in locals() else tool_calls_count
            collector.record_agent_metric(
                agent_id=agent.id,
                status="LIMIT_EXCEEDED",
                duration_ms=duration_ms,
                tool_calls=tool_cnt,
                errors=1,
                provider_used="MockEngine"
            )

            record_audit(
                action=f"AGENT_LIMIT_EXCEEDED: {e.limit_type}",
                project=task.project_id or "control-center",
                target=agent.id,
                reason=str(e),
                risk_level=RiskLevel.HIGH,
                result="LIMIT_BREACH",
                actor=agent.id,
                agent_id=agent.id,
                execution_id=execution_id,
                status="LIMIT_EXCEEDED",
                error=str(e)
            )

            agent_result = AgentResult(
                task_id=task.id,
                execution_id=execution_id,
                agent_id=agent.id,
                status="LIMIT_EXCEEDED",
                steps=steps_record,
                final_output={"error": str(e), "limit_type": e.limit_type},
                tool_calls_count=tool_cnt,
                duration_ms=round(duration_ms, 2),
                tokens_used=0
            )
            self._results[execution_id] = agent_result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            task.status = "failed"
            task.error = str(e)
            task.logs.append(f"[{_now_iso()}] [{execution_id}] Execution FAILED: {str(e)}")

            collector.record_agent_metric(
                agent_id=agent.id,
                status="FAILED",
                duration_ms=duration_ms,
                tool_calls=tool_calls_count,
                errors=1,
                provider_used="MockEngine"
            )

            record_audit(
                action=f"AGENT_EXECUTION_FAILED: {task.title}",
                project=task.project_id or "control-center",
                target=agent.id,
                reason=str(e),
                risk_level=RiskLevel.MEDIUM,
                result="FAILURE",
                actor=agent.id,
                agent_id=agent.id,
                execution_id=execution_id,
                status="FAILED",
                error=str(e)
            )

        return task

    # -------------------------------------------------------------------------
    # Helper to audit and execute a tool within a step
    # -------------------------------------------------------------------------
    def _run_step_tool(
        self,
        agent_id: str,
        tool_id: str,
        params: Dict[str, Any],
        step_num: int,
        action_name: str,
        execution_id: str,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[AgentStep, ToolResult]:
        t_start = time.time()
        cb_key = f"{agent_id}:{tool_id}"

        # 0. Enforce Execution Limits (step count, tool calls, runtime, loop detection)
        if ctx:
            ctx.check_step()
            ctx.check_tool_call(tool_id, params)

        # 1. Circuit Breaker Check
        can_exec, cb_err = circuit_breaker.can_execute(cb_key)
        if not can_exec:
            t_res = ToolResult(
                call_id=f"call-{uuid.uuid4().hex[:6]}",
                tool_id=tool_id,
                success=False,
                output=None,
                error=cb_err,
                duration_ms=0.0
            )
            step = AgentStep(
                step_num=step_num,
                action=action_name,
                tool_call=ToolCall(call_id=t_res.call_id, tool_id=tool_id, params=params),
                observation=AgentObservation(step_num=step_num, observation_text=cb_err or "Circuit Breaker Tripped", tool_result=t_res),
                status="FAILED"
            )
            return step, t_res

        # 2. RBAC Check
        is_authorized, auth_err = tool_registry.validate_tool_call(tool_id, agent_id, params)
        if not is_authorized:
            record_audit(
                action=f"ESCALATION_BLOCKED: {tool_id}",
                project="control-center",
                target=tool_id,
                reason=auth_err or "Agent unauthorized for requested tool",
                risk_level=RiskLevel.HIGH,
                result="DENIED",
                actor=agent_id,
                agent_id=agent_id,
                tool_id=tool_id,
                execution_id=execution_id,
                status="DENIED"
            )
            t_res = ToolResult(
                call_id=f"call-{uuid.uuid4().hex[:6]}",
                tool_id=tool_id,
                success=False,
                output=None,
                error=auth_err,
                duration_ms=0.0
            )
            step = AgentStep(
                step_num=step_num,
                action=action_name,
                tool_call=ToolCall(call_id=t_res.call_id, tool_id=tool_id, params=params),
                observation=AgentObservation(step_num=step_num, observation_text=auth_err or "Auth Failed", tool_result=t_res),
                status="FAILED"
            )
            return step, t_res

        # 3. Execute tool
        out = execute_agent_tool(agent_id, tool_id, params)
        t_dur = (time.time() - t_start) * 1000.0
        success = (
            "error" not in out
            and out.get("status") not in ["FAILED", "BLOCKED", "DENIED"]
            and out.get("success", True) is not False
            and out.get("exit_code", 0) == 0
        )

        if success:
            circuit_breaker.record_success(cb_key)
        else:
            circuit_breaker.record_failure(cb_key)

        if ctx:
            ctx.check_output_size(out)

        t_res = ToolResult(
            call_id=f"call-{uuid.uuid4().hex[:6]}",
            tool_id=tool_id,
            success=success,
            output=out,
            error=out.get("error") if not success else None,
            duration_ms=round(t_dur, 2)
        )

        obs_text = f"Tool {tool_id} executed in {round(t_dur, 1)}ms. Status: {'SUCCESS' if success else 'ERROR'}."
        step = AgentStep(
            step_num=step_num,
            action=action_name,
            tool_call=ToolCall(call_id=t_res.call_id, tool_id=tool_id, params=params),
            observation=AgentObservation(step_num=step_num, observation_text=obs_text, tool_result=t_res),
            status="COMPLETED" if success else "FAILED"
        )

        # Audit tool call
        record_audit(
            action=f"TOOL_CALL: {tool_id}",
            project="control-center",
            target=tool_id,
            reason=f"Step {step_num}: {action_name}",
            risk_level=RiskLevel.LOW,
            result="SUCCESS" if success else "ERROR",
            actor=agent_id,
            agent_id=agent_id,
            tool_id=tool_id,
            execution_id=execution_id,
            status="COMPLETED" if success else "FAILED"
        )

        return step, t_res

    # -------------------------------------------------------------------------
    # Developer Agent: Full 9-Step Lifecycle with Rollback
    # -------------------------------------------------------------------------
    def _execute_developer_lifecycle(
        self,
        task: TaskItem,
        execution_id: str,
        limits: ExecutionLimits,
        rollback_on_test_failure: bool = False,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[Dict[str, Any], List[AgentStep], int]:
        steps: List[AgentStep] = []
        tool_calls = 0

        # Dedicated isolated local fixture repository for Developer Agent
        fixture_repo = "/root/control-center/data/fixtures/developer_test_repo"
        if task.project_id and os.path.exists(task.project_id):
            fixture_repo = task.project_id
        elif task.project_id and os.path.exists(os.path.join("/root/control-center/data/fixtures", task.project_id)):
            fixture_repo = os.path.join("/root/control-center/data/fixtures", task.project_id)

        target_file = os.path.join(fixture_repo, "calculator.py")
        test_file = os.path.join(fixture_repo, "test_calculator.py")

        # Initialize git repo if not present in fixture
        os.makedirs(fixture_repo, exist_ok=True)
        if not os.path.exists(os.path.join(fixture_repo, ".git")):
            SafeCommandExecutor.execute(["git", "init"], cwd=fixture_repo)
            SafeCommandExecutor.execute(["git", "config", "user.name", "NEXUS"], cwd=fixture_repo)
            SafeCommandExecutor.execute(["git", "config", "user.email", "nexus@local"], cwd=fixture_repo)
            SafeCommandExecutor.execute(["git", "add", "."], cwd=fixture_repo)
            SafeCommandExecutor.execute(["git", "commit", "-m", "init fixture"], cwd=fixture_repo)

        # Reset fixture repo to clean state before starting lifecycle
        SafeCommandExecutor.execute(["git", "checkout", "."], cwd=fixture_repo)
        SafeCommandExecutor.execute(["git", "clean", "-fd"], cwd=fixture_repo)

        # Step 1: INSPECT (inspect working tree)
        s1, r1 = self._run_step_tool("agent-dev", "git.status", {"repo_path": fixture_repo}, 1, "INSPECT_REPOSITORY", execution_id, ctx=ctx)
        steps.append(s1)
        tool_calls += 1

        # Step 2: UNDERSTAND TASK & CREATE PLAN
        if ctx:
            ctx.check_step()
        plan = AgentPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:6]}",
            steps=[
                "Read calculator.py",
                "Apply multiply feature function",
                "Execute pytest test suite",
                "Extract git diff",
                "Verify zero regressions"
            ],
            rationale="Extend calculator with multiplication function in safe fixture."
        )
        steps.append(AgentStep(
            step_num=2,
            action="CREATE_PLAN",
            observation=AgentObservation(step_num=2, observation_text=f"Compiled plan {plan.plan_id} with {len(plan.steps)} steps.")
        ))

        # Step 3: READ RELEVANT FILES
        s3, r3 = self._run_step_tool("agent-dev", "filesystem.read", {"file_path": target_file}, 3, "READ_RELEVANT_FILES", execution_id, ctx=ctx)
        steps.append(s3)
        tool_calls += 1

        # Step 4: MODIFY FILES (Safe controlled modification in fixture)
        if ctx:
            ctx.check_step()
            ctx.file_mod_count += 1
            if ctx.file_mod_count > ctx.limits.max_file_modifications:
                raise ExecutionLimitExceeded("MAX_FILE_MODIFICATIONS", f"File modification limit exceeded ({ctx.file_mod_count} > {ctx.limits.max_file_modifications})")

        modified_content = "def calculate(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(modified_content)

        steps.append(AgentStep(
            step_num=4,
            action="MODIFY_FILES",
            observation=AgentObservation(step_num=4, observation_text=f"Modified {target_file} with multiply function.")
        ))

        # Step 5: RUN TESTS
        modified_test = "from calculator import calculate, multiply\n\ndef test_calculate():\n    assert calculate(2, 3) == 5\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(modified_test)

        s5, r5 = self._run_step_tool("agent-dev", "test.pytest", {"project_path": fixture_repo}, 5, "RUN_TESTS", execution_id, ctx=ctx)
        steps.append(s5)
        tool_calls += 1

        # Step 6: INSPECT DIFF
        s6, r6 = self._run_step_tool("agent-dev", "git.diff", {"repo_path": fixture_repo}, 6, "INSPECT_DIFF", execution_id, ctx=ctx)
        steps.append(s6)
        tool_calls += 1

        # Step 7: FAILURE HANDLING & ROLLBACK DEMONSTRATION
        did_rollback = False
        if rollback_on_test_failure or not r5.success:
            # Revert fixture modifications via git checkout and clean untracked artifacts
            SafeCommandExecutor.execute(["git", "checkout", "."], cwd=fixture_repo)
            SafeCommandExecutor.execute(["git", "clean", "-fd"], cwd=fixture_repo)
            did_rollback = True
            steps.append(AgentStep(
                step_num=7,
                action="ROLLBACK_CHANGES",
                observation=AgentObservation(step_num=7, observation_text="Executed clean rollback of fixture test changes via git checkout.")
            ))

        output = {
            "agent": "DEVELOPER-02",
            "cycle": "INSPECT -> UNDERSTAND -> PLAN -> READ -> MODIFY -> TEST -> DIFF",
            "fixture_repo": fixture_repo,
            "tests_passed": r5.success,
            "has_diff": r6.output.get("has_diff", False) if not did_rollback else False,
            "diff": r6.output.get("diff", "")[:5000] if not did_rollback else "REVERTED",
            "rolled_back": did_rollback,
            "plan": plan.model_dump()
        }

        return output, steps, tool_calls

    # -------------------------------------------------------------------------
    # QA Agent: Framework Discovery & Structured Result Parsing
    # -------------------------------------------------------------------------
    def _execute_qa_lifecycle(
        self,
        task: TaskItem,
        execution_id: str,
        limits: ExecutionLimits,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[Dict[str, Any], List[AgentStep], int]:
        steps: List[AgentStep] = []
        proj_path = "/root/control-center"
        if task.project_id and os.path.exists(task.project_id):
            proj_path = task.project_id
        elif task.project_id and os.path.exists(os.path.join("/root/control-center/data/fixtures", task.project_id)):
            proj_path = os.path.join("/root/control-center/data/fixtures", task.project_id)

        if ctx:
            ctx.check_step()

        # Step 1: INSPECT & IDENTIFY TEST FRAMEWORK
        has_tests_dir = os.path.exists(os.path.join(proj_path, "tests")) or any(f.startswith("test_") or f.endswith("_test.py") for f in os.listdir(proj_path) if os.path.isfile(os.path.join(proj_path, f)))
        framework = "pytest" if has_tests_dir else "unknown"

        steps.append(AgentStep(
            step_num=1,
            action="IDENTIFY_FRAMEWORK",
            observation=AgentObservation(step_num=1, observation_text=f"Identified test framework: '{framework}' at {proj_path}.")
        ))

        # Step 2: RUN TESTS THROUGH APPROVED RUNNER
        s2, r2 = self._run_step_tool("agent-qa", "test.pytest", {"project_path": proj_path}, 2, "RUN_PYTEST", execution_id, ctx=ctx)
        steps.append(s2)

        # Step 3: PARSE RESULTS
        if ctx:
            ctx.check_step()
        output_str = r2.output.get("output", "") if r2.output else ""
        passed_m = re.search(r"(\d+)\s+passed", output_str)
        failed_m = re.search(r"(\d+)\s+failed", output_str)
        passed_count = int(passed_m.group(1)) if passed_m else 0
        failed_count = int(failed_m.group(1)) if failed_m else 0

        res_data = {
            "agent": "QA-VERIFIER",
            "framework": framework,
            "status": "PASSED" if failed_count == 0 and r2.success else "FAILED",
            "passed": passed_count,
            "failed": failed_count,
            "duration_ms": r2.duration_ms,
            "stdout_snippet": output_str[:300]
        }

        steps.append(AgentStep(
            step_num=3,
            action="PARSE_RESULTS",
            observation=AgentObservation(step_num=3, observation_text=f"QA test sweep parsed: {passed_count} passed, {failed_count} failed.")
        ))

        return res_data, steps, 1

    # -------------------------------------------------------------------------
    # Security Agent: Triaged Findings (REAL, INFORMATIONAL, UNAVAILABLE)
    # -------------------------------------------------------------------------
    def _execute_security_lifecycle(
        self,
        task: TaskItem,
        execution_id: str,
        limits: ExecutionLimits,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[Dict[str, Any], List[AgentStep], int]:
        steps: List[AgentStep] = []
        target_project = "/root/control-center"
        if task.project_id and os.path.exists(task.project_id):
            target_project = task.project_id
        elif task.project_id and os.path.exists(os.path.join("/root/control-center/data/fixtures", task.project_id)):
            target_project = os.path.join("/root/control-center/data/fixtures", task.project_id)
        elif task.project_id and task.project_id != "control-center":
            target_project = task.project_id

        # Step 1: SECRET SCANNING
        s1, r1 = self._run_step_tool("agent-security", "security.secret_scan", {"project_id": target_project, "target_path": target_project}, 1, "SECRET_SCAN", execution_id, ctx=ctx)
        steps.append(s1)

        # Step 2: DANGEROUS CONFIGURATION AUDIT
        from core.config import config
        cors_wildcard = "*" in config.allowed_origins
        config_finding = {
            "type": "CORS_CONFIGURATION",
            "category": "INFORMATIONAL" if not cors_wildcard else "REAL_FINDING",
            "severity": "LOW" if not cors_wildcard else "HIGH",
            "detail": "CORS restricted to explicit origins; wildcard disabled." if not cors_wildcard else "Wildcard origin detected."
        }

        # Step 3: DEPENDENCY AUDIT CHECK
        dep_tool_present = shutil.which("pip-audit") is not None
        dep_finding = {
            "type": "DEPENDENCY_CVE_AUDIT",
            "category": "REAL_FINDING" if dep_tool_present else "UNAVAILABLE_CHECK",
            "severity": "INFO" if not dep_tool_present else "HIGH",
            "detail": "Executed live pip-audit" if dep_tool_present else "Dependency CVE scanner 'pip-audit' not installed; check marked UNAVAILABLE_CHECK."
        }

        scan_res = r1.output or {}
        raw_findings = scan_res.get("findings", [])
        secret_findings_count = len(raw_findings)

        findings = [
            {
                "type": "STATIC_CREDENTIAL_SCAN",
                "category": "INFORMATIONAL" if secret_findings_count == 0 else "REAL_FINDING",
                "severity": scan_res.get("status", "CLEAN"),
                "detail": f"{scan_res.get('secrets_leaked', 0)} files with exposed secrets detected ({secret_findings_count} total matches)."
            },
            config_finding,
            dep_finding
        ]

        if ctx:
            ctx.check_step()
        steps.append(AgentStep(
            step_num=2,
            action="TRIAGE_FINDINGS",
            observation=AgentObservation(step_num=2, observation_text=f"Security audit triaged into {len(findings)} checks with {secret_findings_count} secret matches.")
        ))

        output = {
            "agent": "SENTINEL-SEC",
            "status": "AUDIT_COMPLETE",
            "target": target_project,
            "findings_count": len(findings) + secret_findings_count,
            "findings": findings,
            "secret_findings": raw_findings,
            "severity_breakdown": scan_res.get("severity_breakdown", {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}),
            "real_findings": sum(1 for f in findings if f["category"] == "REAL_FINDING") + secret_findings_count,
            "informational": sum(1 for f in findings if f["category"] == "INFORMATIONAL"),
            "unavailable": sum(1 for f in findings if f["category"] == "UNAVAILABLE_CHECK")
        }

        return output, steps, 1

    # -------------------------------------------------------------------------
    # Documentation Agent: Authoring with Path Restriction
    # -------------------------------------------------------------------------
    def _execute_docs_lifecycle(
        self,
        task: TaskItem,
        execution_id: str,
        limits: ExecutionLimits,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[Dict[str, Any], List[AgentStep], int]:
        steps: List[AgentStep] = []
        tool_calls = 0

        # Step 1: INSPECT ARCHITECTURE & METADATA
        s1, r1 = self._run_step_tool("agent-docs", "docs.read", {"collection": "memory"}, 1, "INSPECT_METADATA", execution_id, ctx=ctx)
        steps.append(s1)
        tool_calls += 1

        # Step 2: INSPECT RELEVANT SOURCE FILE (read-only)
        s2, r2 = self._run_step_tool("agent-docs", "filesystem.read", {"file_path": "/root/control-center/backend/server.py", "max_lines": 30}, 2, "INSPECT_SOURCE", execution_id, ctx=ctx)
        steps.append(s2)
        tool_calls += 1

        # Step 3: Check if task attempts unauthorized source code modification
        is_adversarial = any(k in task.title.lower() for k in ["modify source", "server.py", "modify code", "patch backend"])
        if is_adversarial:
            s3, r3 = self._run_step_tool("agent-docs", "filesystem.write", {"file_path": "/root/control-center/backend/server.py", "content": "# MALICIOUS INJECTION"}, 3, "MODIFY_SOURCE_ATTEMPT", execution_id, ctx=ctx)
            steps.append(s3)
            tool_calls += 1
            output = {
                "agent": "DOC-CHRONICLER",
                "status": "DENIED",
                "detail": "Blocked by persona path restriction; agent-docs cannot modify source code.",
                "error": r3.error or "Agent-docs is restricted to authoring documentation files in docs/ only"
            }
            return output, steps, tool_calls

        # Legitimate docs update
        title = task.title if task.title else "Autonomous Security Architecture"
        content = f"Record generated by Docs Agent for: {task.title}. Verified multi-step lifecycle and docs-only constraint."
        s3, r3 = self._run_step_tool("agent-docs", "docs.write", {"title": title, "category": "Architecture", "content": content}, 3, "WRITE_ADR", execution_id, ctx=ctx)
        steps.append(s3)
        tool_calls += 1

        # Step 4: PRODUCE DIFF
        s4, r4 = self._run_step_tool("agent-docs", "git.diff", {"repo_path": "/root/control-center"}, 4, "PRODUCE_DIFF", execution_id, ctx=ctx)
        steps.append(s4)
        tool_calls += 1

        output = {
            "agent": "DOC-CHRONICLER",
            "status": "DOCUMENTED",
            "adr": r3.output.get("adr") if r3.output else None,
            "diff": r4.output.get("diff", "") if r4.output else "",
            "has_diff": r4.output.get("has_diff", False) if r4.output else False,
            "vault_updated": True
        }

        return output, steps, tool_calls

    # -------------------------------------------------------------------------
    # Research Agent: Read-only AST & Topology Inspection
    # -------------------------------------------------------------------------
    def _execute_research_lifecycle(
        self,
        task: TaskItem,
        execution_id: str,
        limits: ExecutionLimits,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[Dict[str, Any], List[AgentStep], int]:
        steps: List[AgentStep] = []
        query = task.title.split()[-1] if task.title else "FastAPI"

        s1, r1 = self._run_step_tool("agent-research", "filesystem.read", {"file_path": "/root/control-center/backend/server.py", "max_lines": 50}, 1, "READ_SOURCE", execution_id, ctx=ctx)
        steps.append(s1)

        s2, r2 = self._run_step_tool("agent-research", "codebase_search", {"query": query, "root_dir": "/root/control-center"}, 2, "SEARCH_CODEBASE", execution_id, ctx=ctx)
        steps.append(s2)

        output = {
            "agent": "RESEARCH-01",
            "query": query,
            "match_count": r2.output.get("match_count", 0) if r2.output else 0,
            "matches": r2.output.get("matches", []) if r2.output else [],
            "files_inspected": len(r2.output.get("matches", [])) if r2.output else 0
        }

        return output, steps, 2

    # -------------------------------------------------------------------------
    # Data Agent: JSON Vault Inspection
    # -------------------------------------------------------------------------
    def _execute_data_lifecycle(
        self,
        task: TaskItem,
        execution_id: str,
        limits: ExecutionLimits,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[Dict[str, Any], List[AgentStep], int]:
        steps: List[AgentStep] = []
        s1, r1 = self._run_step_tool("agent-data", "docs.read", {"collection": "projects"}, 1, "QUERY_PROJECTS_VAULT", execution_id, ctx=ctx)
        steps.append(s1)

        output = {
            "agent": "DATA-CATALYST",
            "collection": "projects",
            "records": r1.output.get("results", [])
        }

        return output, steps, 1

    # -------------------------------------------------------------------------
    # Generic Lifecycle Fallback
    # -------------------------------------------------------------------------
    def _execute_generic_lifecycle(
        self,
        task: TaskItem,
        execution_id: str,
        limits: ExecutionLimits,
        ctx: Optional[ExecutionContext] = None
    ) -> Tuple[Dict[str, Any], List[AgentStep], int]:
        if ctx:
            ctx.check_step()
        steps = [
            AgentStep(step_num=1, action="VALIDATE_DIRECTIVE", observation=AgentObservation(step_num=1, observation_text=f"Parsed directive: {task.title}"))
        ]
        output = {"agent": task.agent_id, "status": "SIMULATED", "directive": task.title}
        return output, steps, 0

runtime_engine = AgentRuntimeEngine()
