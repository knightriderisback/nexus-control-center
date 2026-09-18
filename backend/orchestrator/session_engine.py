"""
NEXUS AGY ↔ Codex Autonomous Orchestration Session Engine.
Provides stateful, persistent, auditable multi-agent collaborative workflows:
- State Machine with Controlled Transitions & DAG Integrity Verification
- Planner (AGY) ↔ Coder (Codex) ↔ Verifier (QA) ↔ Sentinel (Security)
- Multi-Turn Revision & Feedback Loops with Remediation Context
- Automated Checkpointing and Safe Rollback Recovery
- Persistent Session Storage via Atomic JSON with Corruption Quarantine
- Concurrency Locking & Idempotent Session Resumability
- Full Policy & Approval Governance Integration
"""

import os
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

from core.config import config
from core.storage import load_json_safe, atomic_save_json
from core.audit import record_audit
from core.policy import evaluate_action
from core.approvals import request_approval, load_approvals
from models.schemas import (
    AgyCodexSession,
    AgyCodexSessionRequest,
    SessionState,
    TransitionRecord,
    RiskLevel
)
from orchestrator.agents import get_agent_by_id
from orchestrator.safe_runner import SafeCommandExecutor
from orchestrator.worktree_manager import worktree_manager

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Strict state machine transition DAG
VALID_STATE_TRANSITIONS: Dict[str, Set[str]] = {
    SessionState.INITIALIZING.value: {
        SessionState.SPEC_PROPOSAL.value,
        SessionState.AWAITING_APPROVAL.value,
        SessionState.FAILED.value
    },
    SessionState.AWAITING_APPROVAL.value: {
        SessionState.SPEC_PROPOSAL.value,
        SessionState.FAILED.value,
        SessionState.ROLLED_BACK.value
    },
    SessionState.SPEC_PROPOSAL.value: {
        SessionState.CODE_SYNTHESIS.value,
        SessionState.FEEDBACK_REVISION.value,
        SessionState.AWAITING_APPROVAL.value,
        SessionState.FAILED.value
    },
    SessionState.CODE_SYNTHESIS.value: {
        SessionState.TEST_VERIFICATION.value,
        SessionState.FEEDBACK_REVISION.value,
        SessionState.ROLLED_BACK.value,
        SessionState.FAILED.value
    },
    SessionState.TEST_VERIFICATION.value: {
        SessionState.SECURITY_AUDIT.value,
        SessionState.FEEDBACK_REVISION.value,
        SessionState.ROLLED_BACK.value,
        SessionState.FAILED.value
    },
    SessionState.SECURITY_AUDIT.value: {
        SessionState.COMPLETED.value,
        SessionState.FEEDBACK_REVISION.value,
        SessionState.ROLLED_BACK.value,
        SessionState.FAILED.value
    },
    SessionState.FEEDBACK_REVISION.value: {
        SessionState.CODE_SYNTHESIS.value,
        SessionState.SPEC_PROPOSAL.value,
        SessionState.ROLLED_BACK.value,
        SessionState.FAILED.value
    },
    SessionState.COMPLETED.value: set(),  # Terminal state
    SessionState.FAILED.value: {SessionState.ROLLED_BACK.value},
    SessionState.ROLLED_BACK.value: set(),  # Terminal state
}

class SessionEngine:
    """Stateful orchestrator for persistent AGY ↔ Codex workflows with local production hardening."""

    def __init__(self, storage_file: Optional[str] = None):
        self.storage_file = storage_file or config.sessions_file
        self._sessions: Dict[str, AgyCodexSession] = {}
        self._corrupt_sessions: Dict[str, Any] = {}
        self._executing_sessions: Set[str] = set()
        self._exec_lock = threading.Lock()
        self._load_sessions()

    def _load_sessions(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.storage_file)), exist_ok=True)
        raw_data = load_json_safe(self.storage_file, default={})
        self._sessions.clear()
        self._corrupt_sessions.clear()
        if isinstance(raw_data, dict):
            for s_id, s_dict in raw_data.items():
                try:
                    if isinstance(s_dict, dict):
                        self._sessions[s_id] = AgyCodexSession(**s_dict)
                    else:
                        self._corrupt_sessions[s_id] = s_dict
                except Exception:
                    self._corrupt_sessions[s_id] = s_dict

    def _persist_sessions(self):
        # Merge active valid sessions with preserved corrupt records to avoid silent data loss
        data = {**self._corrupt_sessions, **{s_id: s.model_dump() for s_id, s in self._sessions.items()}}
        atomic_save_json(self.storage_file, data)

    def get_session(self, session_id: str) -> Optional[AgyCodexSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[AgyCodexSession]:
        return list(self._sessions.values())

    def create_session(self, req: AgyCodexSessionRequest) -> AgyCodexSession:
        session_id = f"sess-{uuid.uuid4().hex[:8]}"
        workspace = req.target_workspace or "/root/control-center/data/fixtures/developer_test_repo"
        if not os.path.exists(workspace):
            workspace = "/root/control-center"

        session = AgyCodexSession(
            session_id=session_id,
            session_name=req.session_name,
            directive=req.directive,
            current_state=SessionState.INITIALIZING,
            planner_agent=req.planner_agent or "agent-research",
            coder_agent=req.coder_agent or "agent-dev",
            verifier_agent=req.verifier_agent or "agent-qa",
            project_id=req.project_id or "control-center",
            target_workspace=workspace,
            revision_count=0,
            max_revisions=req.max_revisions,
            auto_rollback_on_failure=req.auto_rollback_on_failure,
            isolate_worktree=req.isolate_worktree,
            auto_cleanup_worktree=req.auto_cleanup_worktree,
            isolated_worktree=None,
            worktree_branch=None,
            auto_merge_on_completion=req.auto_merge_on_completion,
            merge_target_branch=req.merge_target_branch,
            merge_result=None,
            transitions=[],
            created_at=_now_iso(),
            updated_at=_now_iso(),
            status="INITIALIZED"
        )
        self._sessions[session_id] = session
        self._persist_sessions()

        record_audit(
            action=f"SWARM_SESSION_CREATED: {req.session_name}",
            project=session.project_id,
            target=session_id,
            reason=req.directive,
            risk_level=RiskLevel.LOW,
            result="INITIALIZED",
            actor="orchestrator",
            execution_id=session_id,
            status="INITIALIZED"
        )
        return session

    def record_transition(
        self,
        session: AgyCodexSession,
        to_state: SessionState,
        trigger_agent: str,
        reason: str,
        payload: Optional[Dict[str, Any]] = None,
        strict: bool = True
    ) -> AgyCodexSession:
        from_state = session.current_state.value
        target_state = to_state.value if isinstance(to_state, SessionState) else str(to_state)

        # Enforce DAG transition integrity
        if strict and from_state in VALID_STATE_TRANSITIONS:
            allowed = VALID_STATE_TRANSITIONS[from_state]
            if target_state not in allowed:
                raise ValueError(
                    f"Illegal state transition for session '{session.session_id}': "
                    f"cannot transition from '{from_state}' to '{target_state}'. "
                    f"Allowed transitions from '{from_state}': {sorted(list(allowed)) or 'None (Terminal State)'}"
                )

        trans_id = f"trans-{uuid.uuid4().hex[:8]}"
        trans = TransitionRecord(
            transition_id=trans_id,
            from_state=from_state,
            to_state=target_state,
            trigger_agent=trigger_agent,
            timestamp=_now_iso(),
            payload=payload or {},
            reason=reason
        )
        session.transitions.append(trans)
        session.current_state = to_state if isinstance(to_state, SessionState) else SessionState(target_state)
        session.updated_at = _now_iso()
        self._persist_sessions()

        record_audit(
            action=f"SWARM_SESSION_TRANSITION: {from_state} -> {target_state}",
            project=session.project_id,
            target=session.session_id,
            reason=reason,
            risk_level=RiskLevel.LOW,
            result=target_state,
            actor=trigger_agent,
            execution_id=session.session_id,
            status=target_state
        )
        return session

    def execute_session(self, session_id: str) -> AgyCodexSession:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        # Concurrency protection: prevent simultaneous duplicate execution
        with self._exec_lock:
            if session_id in self._executing_sessions:
                raise RuntimeError(f"Session '{session_id}' is currently executing in another thread or process.")
            # Idempotency check
            if session.current_state in [SessionState.COMPLETED, SessionState.ROLLED_BACK]:
                return session
            self._executing_sessions.add(session_id)

        try:
            return self._run_workflow(session)
        finally:
            with self._exec_lock:
                self._executing_sessions.discard(session_id)

    def _run_workflow(self, session: AgyCodexSession) -> AgyCodexSession:
        from orchestrator.runtime import runtime_engine

        # Resumability check: if currently awaiting approval, inspect approval status
        if session.current_state == SessionState.AWAITING_APPROVAL:
            if session.approval_id:
                all_apprs = load_approvals()
                appr = next((a for a in all_apprs if a.id == session.approval_id), None)
                if appr and appr.status == "REJECTED":
                    session.status = "REJECTED"
                    session.error = f"Session rejected by operator: {appr.decision_reason or 'Policy gate denied'}"
                    return self.record_transition(
                        session, SessionState.FAILED, "human_operator", session.error, strict=False
                    )
                elif not appr or appr.status == "PENDING":
                    return session
            # If approved, fall through to start execution!

        # Step 0: Policy evaluation if fresh
        if session.current_state == SessionState.INITIALIZING:
            risk, requires_appr, policy_reason = evaluate_action(session.directive, session.project_id)
            if requires_appr:
                appr = request_approval(
                    action=f"Session Directive: {session.directive}",
                    target_project=session.project_id,
                    reason=f"Session triggered policy: {policy_reason}",
                    command=f"# SWARM Session {session.session_id}: {session.directive}",
                    actor="orchestrator",
                    risk_level=risk
                )
                session.approval_id = appr.id
                session.status = "AWAITING_APPROVAL"
                self.record_transition(
                    session, SessionState.AWAITING_APPROVAL, "policy_engine",
                    f"Gated by policy: {policy_reason}", {"approval_id": appr.id}
                )
                return session

        # Worktree isolation initialization
        if session.isolate_worktree and worktree_manager.is_git_repo(session.target_workspace):
            if not session.isolated_worktree or not os.path.exists(session.isolated_worktree):
                wt = worktree_manager.provision_worktree(
                    repo_path=session.target_workspace,
                    session_id=session.session_id
                )
                session.isolated_worktree = wt.worktree_path
                session.worktree_branch = wt.branch_name
                self._persist_sessions()

        effective_workspace = session.isolated_worktree or session.target_workspace

        # Capture baseline checkpoint
        if not session.checkpoint_id:
            chk_res = SafeCommandExecutor.execute(["git", "rev-parse", "HEAD"], cwd=effective_workspace)
            session.checkpoint_id = chk_res.stdout.strip() if chk_res.exit_code == 0 else f"chk-{uuid.uuid4().hex[:6]}"

        # Phase 1: SPEC_PROPOSAL (AGY Planner)
        if session.current_state in [SessionState.INITIALIZING, SessionState.AWAITING_APPROVAL]:
            self.record_transition(
                session, SessionState.SPEC_PROPOSAL, session.planner_agent,
                f"Planner {session.planner_agent} initiating architecture & spec discovery"
            )
            plan_task = runtime_engine.create_task(
                agent_id=session.planner_agent,
                title=f"Spec Discovery: Swarm Session {session.session_id}",
                instructions=f"Analyze codebase and formulate implementation plan for: {session.directive} in {effective_workspace}",
                project_id=effective_workspace
            )
            executed_plan = runtime_engine.execute_task(plan_task.id)
            if executed_plan.status != "completed":
                session.status = "FAILED"
                session.error = f"Planner agent '{session.planner_agent}' failed: {executed_plan.error}"
                return self.record_transition(
                    session, SessionState.FAILED, session.planner_agent, session.error
                )
            session.spec_proposal = executed_plan.result or {"summary": session.directive}

        # Iterative Synthesis & Verification Loop
        while True:
            # Phase 2: CODE_SYNTHESIS (Codex Coder)
            self.record_transition(
                session, SessionState.CODE_SYNTHESIS, session.coder_agent,
                f"Coder {session.coder_agent} synthesizing implementation (iteration {session.revision_count + 1})",
                {"revision": session.revision_count, "remediation": session.last_feedback}
            )
            remed_prompt = f"\nREMEDIATION CONTEXT FROM PREVIOUS VERIFICATION: {session.last_feedback}" if session.last_feedback else ""
            code_task = runtime_engine.create_task(
                agent_id=session.coder_agent,
                title=f"Code Implementation: Swarm Session {session.session_id}",
                instructions=f"Synthesize code modifications for directive: {session.directive}. Plan: {session.spec_proposal}.{remed_prompt}",
                project_id=effective_workspace
            )
            executed_code = runtime_engine.execute_task(code_task.id)
            if executed_code.status != "completed":
                session.status = "FAILED"
                session.error = f"Coder agent '{session.coder_agent}' failed code synthesis: {executed_code.error}"
                if session.auto_rollback_on_failure:
                    return self.rollback_session(session.session_id)
                return self.record_transition(
                    session, SessionState.FAILED, session.coder_agent, session.error
                )

            session.code_artifacts = executed_code.result or {}

            # Phase 3: TEST_VERIFICATION (QA Verifier)
            self.record_transition(
                session, SessionState.TEST_VERIFICATION, session.verifier_agent,
                f"Verifier {session.verifier_agent} running automated test suite",
                {"workspace": effective_workspace}
            )
            qa_task = runtime_engine.create_task(
                agent_id=session.verifier_agent,
                title=f"Verification Suite: {session.directive}",
                instructions="Run automated assertions and report test delta",
                project_id=effective_workspace
            )
            executed_qa = runtime_engine.execute_task(qa_task.id)
            session.verification_results = executed_qa.result or {}

            tests_passed = (
                executed_qa.status == "completed"
                and session.verification_results.get("status") in ["PASSED", "VERIFIED"]
                and session.verification_results.get("failed", 0) == 0
            )

            if tests_passed:
                # Phase 4: SECURITY_AUDIT (Sentinel Security)
                self.record_transition(
                    session, SessionState.SECURITY_AUDIT, "agent-security",
                    "Security Sentinel scanning synthesized artifacts for secrets & boundary violations"
                )
                sec_task = runtime_engine.create_task(
                    agent_id="agent-security",
                    title=f"Security Scan: {session.directive}",
                    instructions="Audit codebase for secrets and policy violations",
                    project_id=effective_workspace
                )
                executed_sec = runtime_engine.execute_task(sec_task.id)
                session.security_results = executed_sec.result or {}

                sec_clean = (
                    executed_sec.status == "completed"
                    and session.security_results.get("clean", True) is not False
                    and session.security_results.get("status") not in ["CRITICAL", "FAILED"]
                )

                if sec_clean:
                    session.status = "COMPLETED"
                    self.record_transition(
                        session, SessionState.COMPLETED, "orchestrator",
                        "All synthesis, QA verification, and security audits verified cleanly."
                    )

                    # Ensure synthesized changes in worktree are committed before auto-merge or finalization
                    if session.isolated_worktree and session.worktree_branch:
                        status_chk = SafeCommandExecutor.execute(["git", "status", "--porcelain"], cwd=session.isolated_worktree)
                        if status_chk.exit_code == 0 and status_chk.stdout.strip():
                            SafeCommandExecutor.execute(["git", "add", "."], cwd=session.isolated_worktree)
                            SafeCommandExecutor.execute(
                                ["git", "commit", "-m", f"feat(swarm): {session.directive} [session {session.session_id}]"],
                                cwd=session.isolated_worktree
                            )

                    if session.auto_merge_on_completion and session.worktree_branch:
                        from orchestrator.merge_arbitrator import merge_arbitrator
                        from models.schemas import MergeExecutionRequest, MergeStrategy
                        target_b = session.merge_target_branch or "main"
                        merge_req = MergeExecutionRequest(
                            repo_path=session.target_workspace,
                            source_branch=session.worktree_branch,
                            target_branch=target_b,
                            session_id=session.session_id,
                            strategy=MergeStrategy.AUTO
                        )
                        merge_res = merge_arbitrator.execute_merge(merge_req)
                        session.merge_result = merge_res.model_dump()
                        self._persist_sessions()

                    if session.auto_cleanup_worktree and session.isolated_worktree:
                        worktree_manager.teardown_worktree(session.session_id, force=True, delete_branch=False)
                    break
                else:
                    feedback_detail = f"Security scan detected violations: {session.security_results.get('findings', [])}"
            else:
                qa_err = session.verification_results.get("error") or "Test assertions failed"
                feedback_detail = f"QA test verification failed: {qa_err}"

            # Set remediation feedback for next turn
            session.last_feedback = feedback_detail

            # Check if revision is permitted
            if session.revision_count < session.max_revisions:
                session.revision_count += 1
                self.record_transition(
                    session, SessionState.FEEDBACK_REVISION, "orchestrator",
                    f"Transitioning to remediation feedback loop: {feedback_detail}",
                    {"feedback": feedback_detail, "revision": session.revision_count}
                )
                continue
            else:
                # Exhausted revisions - trigger recovery
                if session.auto_rollback_on_failure:
                    return self.rollback_session(session.session_id)
                else:
                    session.status = "FAILED"
                    session.error = feedback_detail
                    self.record_transition(
                        session, SessionState.FAILED, "orchestrator",
                        f"Session failed after {session.max_revisions} revisions without recovery.",
                        {"error": feedback_detail}
                    )
                    if session.auto_cleanup_worktree and session.isolated_worktree:
                        worktree_manager.teardown_worktree(session.session_id, force=True, delete_branch=False)
                break

        return session

    def rollback_session(self, session_id: str) -> AgyCodexSession:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        # Execute safe recovery command on target workspace
        ws = session.isolated_worktree or session.target_workspace
        cmd_res = SafeCommandExecutor.execute(["git", "checkout", "."], cwd=ws)
        SafeCommandExecutor.execute(["git", "clean", "-fd"], cwd=ws)

        if session.auto_cleanup_worktree and session.isolated_worktree:
            worktree_manager.teardown_worktree(session.session_id, force=True, delete_branch=True)

        session.status = "ROLLED_BACK"
        session.error = "Rolled back to baseline state after verification failure."
        self.record_transition(
            session, SessionState.ROLLED_BACK, "agent-recovery",
            f"Automated recovery executed on {ws}. Workspace restored to clean baseline.",
            {"exit_code": cmd_res.exit_code, "checkpoint": session.checkpoint_id},
            strict=False
        )
        record_audit(
            action=f"SESSION_ROLLBACK_EXECUTED: {session.session_id}",
            project=session.project_id,
            target=ws,
            reason="Automated rollback triggered after verification failure",
            risk_level=RiskLevel.MEDIUM,
            result="ROLLED_BACK",
            actor="agent-recovery",
            execution_id=session.session_id,
            status="ROLLED_BACK"
        )
        return session

session_engine = SessionEngine()
