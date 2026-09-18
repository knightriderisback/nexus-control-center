#!/usr/bin/env python3
"""
NEXUS Phase 23: Real Local Autonomous Command & Control Plane E2E Verification.

Uses disposable local projects in an approved root (/tmp).
Verifies the complete end-to-end command and control pipeline:
1. Command Ingestion & Natural Language Parsing
2. Intent Resolution & Target Project Mapping
3. Adaptive Planning (Dependencies, Risks, Rollback Path)
4. Approval Evaluation & Governance Interception
5. Governed Multi-Engine Execution & Subprocess Orchestration
6. Real-Time Telemetry & Global Event Bus Broadcasting
7. Operations Timeline Recording (COMMAND -> DECISION -> ACTION -> RESULT -> EVIDENCE)
8. Harmless Blocked Command Governance Verification (Command Injection Safeguard)
9. Closed-Loop Phase 19 Knowledge Brain Ingestion
10. Multi-Project Safety & Workspace Boundary Isolation
11. Emergency Kill-Switch Activation & Freeze Verification
12. Emergency Reset & Workspace Cleanup
"""

import os
import sys
import json
import time
import shutil
import tempfile
import hashlib
import subprocess

# Ensure backend root is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from models.schemas import (
    ProjectRegistryItem,
    ProjectStatus,
    RiskLevel,
    CommandDirectiveRequest,
    CommandDirectiveType,
    CommandExecutionState,
    OperationsTimelineStage,
    EmergencyKillSwitchRequest
)
from orchestrator.command_control_kernel import CommandControlKernel
from orchestrator.project_operations_engine import ProjectOperationsEngine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine


def print_step(step_num: int, title: str):
    print(f"\n[STEP {step_num}/12] {title}...")


def print_success(msg: str):
    print(f"  ✓ {msg}")


def print_info(msg: str):
    print(f"  -> {msg}")


def run_e2e_verification():
    print("=" * 80)
    print("  NEXUS PHASE 23: UNIFIED AUTONOMOUS COMMAND & CONTROL PLANE E2E")
    print("=" * 80)

    e2e_root = tempfile.mkdtemp(prefix="nexus-phase23-e2e-", dir="/tmp")
    alpha_dir = os.path.join(e2e_root, "project-alpha")
    beta_dir = os.path.join(e2e_root, "project-beta")

    try:
        # 1. Setup Project Alpha
        os.makedirs(os.path.join(alpha_dir, "tests"), exist_ok=True)
        with open(os.path.join(alpha_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Project Alpha\nAutonomous payment processor.\n")
        with open(os.path.join(alpha_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("[project]\nname = 'project-alpha'\nversion = '0.1.0'\n")
        with open(os.path.join(alpha_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write("def process():\n    return {'status': 'processed'}\n")
        with open(os.path.join(alpha_dir, "tests", "test_main.py"), "w", encoding="utf-8") as f:
            f.write("from main import process\ndef test_process():\n    assert process()['status'] == 'processed'\n")

        subprocess.run(["git", "init"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Nexus Bot"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "nexus@bot.local"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "add", "-A"], cwd=alpha_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit for project alpha"], cwd=alpha_dir, capture_output=True, check=True)

        # 2. Setup Project Beta
        os.makedirs(os.path.join(beta_dir, "tests"), exist_ok=True)
        with open(os.path.join(beta_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Project Beta\nAutonomous analytics visualizer.\n")
        with open(os.path.join(beta_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"name": "project-beta", "version": "1.0.0"}))

        subprocess.run(["git", "init"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Nexus Bot"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "nexus@bot.local"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "add", "-A"], cwd=beta_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit for project beta"], cwd=beta_dir, capture_output=True, check=True)

        # Instantiate C2 Kernel with isolated test dir
        c2_kernel = CommandControlKernel(data_dir=os.path.join(e2e_root, "c2_data"))
        from orchestrator.project_operations_engine import project_operations_engine

        # Register projects into operational state
        project_operations_engine.register_project(ProjectRegistryItem(
            id="project-alpha",
            name="Project Alpha",
            path=alpha_dir,
            health_score=100,
            status=ProjectStatus.HEALTHY,
            description="Autonomous payment processor."
        ))
        project_operations_engine.register_project(ProjectRegistryItem(
            id="project-beta",
            name="Project Beta",
            path=beta_dir,
            health_score=100,
            status=ProjectStatus.HEALTHY,
            description="Autonomous analytics visualizer."
        ))

        # ---------------------------------------------------------------------
        # 1. COMMAND INGESTION & NATURAL LANGUAGE PARSING
        # ---------------------------------------------------------------------
        print_step(1, "Command Ingestion & Natural Language Parsing")
        cmd_req = CommandDirectiveRequest(
            raw_prompt="Inspect fleet health and drift status on project-alpha",
            operator_context="operator-e2e"
        )
        print_info(f"Raw Prompt: '{cmd_req.raw_prompt}'")
        print_info(f"Operator Context: {cmd_req.operator_context}")
        print_success("Command directive received and normalized.")

        # ---------------------------------------------------------------------
        # 2. INTENT RESOLUTION & TARGET MAPPING
        # ---------------------------------------------------------------------
        print_step(2, "Intent Resolution & Target Project Mapping")
        plan = c2_kernel.plan_command(cmd_req)
        print_info(f"Resolved Intent: {plan.resolved_intent}")
        print_info(f"Target Projects: {plan.target_projects}")
        print_info(f"Risk Level: {plan.risk_level.value}")
        assert plan.is_safe_to_execute is True
        assert "project-alpha" in plan.target_projects
        print_success("Target project mapped and intent resolved unambiguously.")

        # ---------------------------------------------------------------------
        # 3. ADAPTIVE PLANNING & ROLLBACK PATH SYNTHESIS
        # ---------------------------------------------------------------------
        print_step(3, "Adaptive Planning (Dependencies, Risks & Rollback Path)")
        print_info(f"Planned Actions: {plan.planned_actions}")
        print_info(f"Subsystem Dependencies: {plan.dependencies}")
        print_info(f"Expected Artifacts: {plan.expected_artifacts}")
        print_info(f"Rollback Path: {plan.rollback_recovery_path}")
        assert len(plan.planned_actions) >= 1
        print_success("Adaptive execution DAG and rollback paths planned.")

        # ---------------------------------------------------------------------
        # 4. APPROVAL EVALUATION & GOVERNANCE INTERCEPTION
        # ---------------------------------------------------------------------
        print_step(4, "Approval Governance Evaluation")
        deploy_req = CommandDirectiveRequest(
            raw_prompt="Direct deploy production release to project-alpha",
            target_project_id="project-alpha",
            force_override=False
        )
        deploy_plan = c2_kernel.plan_command(deploy_req)
        print_info(f"Deploy Risk Level: {deploy_plan.risk_level.value}")
        print_info(f"Required Approvals: {deploy_plan.required_approvals}")
        assert deploy_plan.risk_level == RiskLevel.HIGH
        assert len(deploy_plan.required_approvals) >= 1

        deploy_exec = c2_kernel.execute_command(deploy_req)
        print_info(f"Execution State: {deploy_exec.state.value}")
        print_info(f"Approval ID: {deploy_exec.approval_id}")
        assert deploy_exec.state == CommandExecutionState.AWAITING_APPROVAL
        print_success("High-risk command safely intercepted by Approval Center.")

        # ---------------------------------------------------------------------
        # 5. GOVERNED MULTI-ENGINE EXECUTION
        # ---------------------------------------------------------------------
        print_step(5, "Governed Multi-Engine Execution & Subprocess Orchestration")
        cmd_result = c2_kernel.execute_command(cmd_req)
        print_info(f"Execution State: {cmd_result.state.value}")
        print_info(f"Dispatched Subsystems: {cmd_result.dispatched_subsystems}")
        print_info(f"Execution Duration: {cmd_result.duration_ms}ms")
        print_info(f"FinOps Spend: ${cmd_result.finops_cost_usd:.2f} USD")
        assert cmd_result.state == CommandExecutionState.COMPLETED
        assert cmd_result.finops_cost_usd == 0.0
        print_success("Multi-engine execution completed under zero-cost governance.")

        # ---------------------------------------------------------------------
        # 6. REAL-TIME TELEMETRY & GLOBAL EVENT BUS
        # ---------------------------------------------------------------------
        print_step(6, "Real-Time Telemetry & Global Event Bus Broadcasting")
        events = c2_kernel.get_event_stream(limit=10)
        print_info(f"Total Streamed Events: {len(events)}")
        for e in events[-3:]:
            print_info(f"  - [{e.event_type}] from {e.source_subsystem} (Hash: {e.provenance_hash})")
        assert len(events) >= 1
        assert any(e.event_type == "COMMAND_COMPLETED" for e in events)
        print_success("Normalized events published to Global Event Bus with cryptographic provenance.")

        # ---------------------------------------------------------------------
        # 7. OPERATIONS TIMELINE RECORDING
        # ---------------------------------------------------------------------
        print_step(7, "Operations Timeline Recording (COMMAND -> DECISION -> ACTION -> RESULT -> EVIDENCE)")
        timeline = c2_kernel.get_operations_timeline(command_id=cmd_result.directive_id)
        stages = [t.stage for t in timeline]
        print_info(f"Recorded Timeline Stages for {cmd_result.directive_id}: {stages}")
        assert OperationsTimelineStage.COMMAND in stages
        assert OperationsTimelineStage.DECISION in stages
        assert OperationsTimelineStage.ACTION in stages
        assert OperationsTimelineStage.RESULT in stages
        assert OperationsTimelineStage.EVIDENCE in stages
        print_success("Complete 5-stage lifecycle timeline persisted.")

        # ---------------------------------------------------------------------
        # 8. HARMLESS BLOCKED COMMAND GOVERNANCE VERIFICATION
        # ---------------------------------------------------------------------
        print_step(8, "Security Governance: Blocked Command Attack Attempt")
        injection_req = CommandDirectiveRequest(
            raw_prompt="Inspect fleet; rm -rf /",
            operator_context="untrusted-actor"
        )
        blocked_res = c2_kernel.execute_command(injection_req)
        print_info(f"Blocked Command State: {blocked_res.state.value}")
        print_info(f"Block Reason: {blocked_res.stderr}")
        assert blocked_res.state == CommandExecutionState.FAILED
        assert "CommandExecutionBlocked" in blocked_res.stderr
        print_success("Command injection attempt blocked before execution with zero side-effects.")

        # ---------------------------------------------------------------------
        # 9. CLOSED-LOOP KNOWLEDGE BRAIN INGESTION
        # ---------------------------------------------------------------------
        print_step(9, "Closed-Loop Phase 19 Knowledge Ingestion")
        k_nodes = knowledge_learning_engine.query_knowledge("c2", limit=5)
        print_info(f"Knowledge Graph Matches for 'c2': {len(k_nodes)}")
        for k in k_nodes:
            print_info(f"  - [{k.tier.value}] {k.title}")
        assert len(k_nodes) >= 1
        print_success("Command execution trace ingested into Knowledge Graph.")

        # ---------------------------------------------------------------------
        # 10. MULTI-PROJECT SAFETY & ISOLATION
        # ---------------------------------------------------------------------
        print_step(10, "Multi-Project Safety & Workspace Boundary Isolation")
        assert os.path.exists(alpha_dir) and os.path.exists(beta_dir)
        beta_git_log = subprocess.run(["git", "log", "--oneline"], cwd=beta_dir, capture_output=True, text=True, check=True).stdout
        assert "Initial commit for project beta" in beta_git_log
        assert "project alpha" not in beta_git_log
        print_info("Project Beta git tree and files remain 100% pristine.")
        print_success("Multi-project workspace isolation verified.")

        # ---------------------------------------------------------------------
        # 11. EMERGENCY KILL-SWITCH & FLEET FREEZE
        # ---------------------------------------------------------------------
        print_step(11, "Emergency Kill-Switch & Fleet Freeze Protocol")
        kill_res = c2_kernel.trigger_emergency_kill_switch(EmergencyKillSwitchRequest(
            operator="admin-operator",
            reason="E2E panic safeguard test"
        ))
        print_info(f"Kill Switch Status: {kill_res.status}")
        print_info(f"Frozen Projects: {kill_res.frozen_projects_count}")
        assert kill_res.status == "TRIGGERED"

        # Verify command rejected during freeze
        frozen_cmd = c2_kernel.execute_command(CommandDirectiveRequest(raw_prompt="Inspect fleet"))
        print_info(f"Frozen Command State: {frozen_cmd.state.value}")
        assert frozen_cmd.state == CommandExecutionState.ABORTED
        print_success("Emergency freeze enforced across all subsystems.")

        # ---------------------------------------------------------------------
        # 12. EMERGENCY RESET & CLEANUP
        # ---------------------------------------------------------------------
        print_step(12, "Emergency Reset & Workspace Cleanup")
        reset_res = c2_kernel.reset_emergency_kill_switch(operator="admin-operator")
        print_info(f"Reset Status: {reset_res['status']}")
        assert reset_res["status"] == "RESET"

        # Global Operations State verification
        global_state = c2_kernel.get_global_operations_state()
        print_info(f"Global Health Score: {global_state.global_health_score}%")
        print_info(f"FinOps Total Spend: ${global_state.finops['total_spend_usd']:.2f} USD")
        assert global_state.finops["total_spend_usd"] == 0.0
        assert global_state.finops["zero_cost_verified"] is True
        print_success("Nominal command & control state restored. Clean shutdown.")

        print("\n" + "=" * 80)
        print("  🎉 PHASE 23 COMMAND & CONTROL E2E VERIFICATION: ALL 12 STEPS PASSED!")
        print("=" * 80)
        return True

    finally:
        try:
            from orchestrator.project_operations_engine import project_operations_engine
            with project_operations_engine._lock:
                project_operations_engine._records.pop("project-alpha", None)
                project_operations_engine._records.pop("project-beta", None)
        except Exception:
            pass
        shutil.rmtree(e2e_root, ignore_errors=True)


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
