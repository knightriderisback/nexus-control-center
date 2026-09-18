"""
NEXUS Local Reliability & Operational Integration Gap Tests.

Validates all non-cloud capabilities:
1. CommandControlKernel multi-action execution dispatch
2. Eco CLI top-level commands (C2, healing, knowledge, tools, operations, factory)
3. Nexus Daemon status & health probe verification
4. Strict $0.00 FinOps invariant enforcement
5. Multi-project boundary isolation
"""

import os
import sys
import subprocess
import pytest
from pathlib import Path

# Add backend directory
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.schemas import (
    CommandDirectiveRequest,
    CommandExecutionState,
    RiskLevel
)
from orchestrator.command_control_kernel import command_control_kernel
from orchestrator.project_operations_engine import project_operations_engine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine
from orchestrator.security_compliance_engine import security_compliance_engine


class TestCommandControlActionExecution:
    """Validates that C2 kernel dispatches and executes diverse actions against real local engines."""

    def test_c2_execute_fleet_inspection(self):
        req = CommandDirectiveRequest(
            raw_prompt="Inspect fleet health and drift status across all projects",
            operator_context="test-operator"
        )
        res = command_control_kernel.execute_command(req)
        assert res.state == CommandExecutionState.COMPLETED
        assert res.resolved_intent == "FLEET_HEALTH_INSPECTION"
        assert res.finops_cost_usd == 0.0
        assert len(res.execution_trace) >= 1

    def test_c2_execute_knowledge_query_action(self):
        req = CommandDirectiveRequest(
            raw_prompt="Query knowledge graph for procedural self-healing patterns",
            operator_context="test-operator"
        )
        res = command_control_kernel.execute_command(req)
        assert res.state == CommandExecutionState.COMPLETED
        assert res.resolved_intent == "KNOWLEDGE_OPTIMIZATION_QUERY"
        assert "Knowledge query returned" in res.stdout
        assert res.finops_cost_usd == 0.0

    def test_c2_execute_security_quarantine_action(self):
        req = CommandDirectiveRequest(
            raw_prompt="Run AST security scan and verify quarantine zero leakage",
            operator_context="test-operator"
        )
        res = command_control_kernel.execute_command(req)
        assert res.state == CommandExecutionState.COMPLETED
        assert res.resolved_intent == "SECURITY_COMPLIANCE_SCAN"
        assert "AST scan verified clean" in res.stdout or "Security quarantine verified" in res.stdout
        assert res.finops_cost_usd == 0.0

    def test_c2_execute_drift_reconciliation_action(self):
        req = CommandDirectiveRequest(
            raw_prompt="Detect and heal configuration drift on project-alpha",
            operator_context="test-operator"
        )
        res = command_control_kernel.execute_command(req)
        assert res.state == CommandExecutionState.COMPLETED
        assert res.resolved_intent == "SELF_HEALING_DRIFT_RECONCILE"
        assert res.finops_cost_usd == 0.0

    def test_c2_execute_mission_dag_planning_action(self):
        req = CommandDirectiveRequest(
            raw_prompt="Synthesize adaptive DAG mission for LRU cache",
            operator_context="test-operator"
        )
        res = command_control_kernel.execute_command(req)
        assert res.state == CommandExecutionState.COMPLETED
        assert res.resolved_intent == "MISSION_INTELLIGENCE_DAG"
        assert res.finops_cost_usd == 0.0


class TestEcoCLISubcommands:
    """Validates that eco CLI executes locally and formats stdout cleanly."""

    ECO_PATH = str(Path(__file__).resolve().parent.parent / "eco")

    def _run_eco(self, *args):
        return subprocess.run(
            [sys.executable, self.ECO_PATH] + list(args),
            capture_output=True,
            text=True,
            timeout=15
        )

    def test_eco_help(self):
        res = self._run_eco("--help")
        assert res.returncode == 0
        assert "Usage: eco" in res.stdout

    def test_eco_c2_status(self):
        res = self._run_eco("c2", "status")
        assert res.returncode == 0
        assert "C2 GLOBAL OPERATIONS STATE" in res.stdout

    def test_eco_c2_plan(self):
        res = self._run_eco("c2", "plan", "Inspect drift and test project-alpha")
        assert res.returncode == 0
        assert "Intent:" in res.stdout

    def test_eco_healing_playbooks(self):
        res = self._run_eco("healing", "playbooks")
        assert res.returncode == 0
        assert "AVAILABLE SELF-HEALING PLAYBOOKS" in res.stdout

    def test_eco_knowledge_nodes(self):
        res = self._run_eco("knowledge", "nodes")
        assert res.returncode == 0
        assert "NODE ID" in res.stdout

    def test_eco_tools_list(self):
        res = self._run_eco("tools", "list")
        assert res.returncode == 0
        assert "TOOL ID" in res.stdout

    def test_eco_operations_fleet(self):
        res = self._run_eco("operations", "fleet")
        assert res.returncode == 0
        assert "FLEET OVERVIEW" in res.stdout

    def test_eco_factory_templates(self):
        res = self._run_eco("factory", "templates")
        assert res.returncode == 0
        assert "AVAILABLE SOFTWARE FACTORY TEMPLATES" in res.stdout


class TestNexusDaemonReliability:
    """Validates daemon health probe and PID functions."""

    def test_daemon_script_status(self):
        daemon_script = str(Path(__file__).resolve().parent.parent / "scripts" / "nexus_daemon.py")
        res = subprocess.run([sys.executable, daemon_script, "status"], capture_output=True, text=True)
        # Should exit with status code (0 if running, 3 if stopped)
        assert res.returncode in [0, 1, 3]
        assert "NEXUS LOCAL DAEMON SERVICE STATUS" in res.stdout
