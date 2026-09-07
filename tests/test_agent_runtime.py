"""
Tests for Agent Runtime & Hardened Execution Core:
1. Tool Registry & RBAC Permissions
2. Safe Command Execution Layer & Sanitization
3. AI Router Abstraction & Fallback
4. Agent Runtime Engine State Machine
5. Developer Agent 5-Step Loop (INSPECT -> PLAN -> MODIFY -> TEST -> DIFF)
6. QA, Security, Docs, Data Specialized Autonomous Execution
"""

import os
import pytest
from orchestrator.tool_registry import tool_registry, ToolDefinition
from orchestrator.safe_runner import SafeCommandExecutor, validate_command, sanitize_environment
from orchestrator.base import ai_router, get_ai_adapter, MockProviderAdapter
from orchestrator.runtime import runtime_engine
from orchestrator.tool_runner import execute_agent_tool
from models.schemas import RiskLevel

# =============================================================================
# 1. Tool Registry & RBAC Tests
# =============================================================================

def test_tool_registry_initialization():
    tools = tool_registry.list_tools()
    assert len(tools) >= 12
    tool_ids = [t.tool_id for t in tools]
    assert "filesystem.read" in tool_ids
    assert "filesystem.write" in tool_ids
    assert "git.status" in tool_ids
    assert "git.diff" in tool_ids
    assert "git.branch" in tool_ids
    assert "test.pytest" in tool_ids
    assert "security.secret_scan" in tool_ids
    assert "docs.read" in tool_ids
    assert "docs.write" in tool_ids
    assert "shell.safe" in tool_ids

def test_tool_registry_rbac_validation():
    # Research Agent is authorized for filesystem.read
    valid, err = tool_registry.validate_tool_call("filesystem.read", "agent-research", {"file_path": "server.py"})
    assert valid is True
    assert err is None

    # Research Agent is NOT authorized for shell.safe (requires agent-devops / agent-dev)
    invalid, err = tool_registry.validate_tool_call("shell.safe", "agent-research", {"cmd_args": ["pwd"]})
    assert invalid is False
    assert "not authorized" in err

    # Unknown tool returns False
    unknown, err = tool_registry.validate_tool_call("unregistered_tool", "agent-dev", {})
    assert unknown is False
    assert "Unknown tool" in err

# =============================================================================
# 2. Safe Command Execution Tests
# =============================================================================

def test_safe_command_allowlisted_success():
    res = SafeCommandExecutor.execute(["echo", "SAFE_TEST"], cwd="/root/control-center")
    assert res.exit_code == 0
    assert "SAFE_TEST" in res.stdout

def test_safe_command_blocked_binary():
    res = SafeCommandExecutor.execute(["nc", "-l", "8080"], cwd="/root/control-center")
    assert res.exit_code == 126
    assert "not permitted by command allowlist" in res.stderr

def test_safe_command_directory_escape_blocked():
    res = SafeCommandExecutor.execute(["ls"], cwd="/etc")
    assert res.exit_code == 126
    assert "outside permitted workspace roots" in res.stderr

def test_safe_command_shell_injection_blocked():
    # Attempt command chaining via argument
    res = SafeCommandExecutor.execute(["echo", "hello; rm -rf /"], cwd="/root/control-center")
    assert res.exit_code == 126
    assert "Dangerous shell character" in res.stderr

    # Attempt subshell execution via argument
    res_subshell = SafeCommandExecutor.execute(["echo", "$(whoami)"], cwd="/root/control-center")
    assert res_subshell.exit_code == 126
    assert "Dangerous shell character" in res_subshell.stderr

def test_safe_command_env_sanitization(monkeypatch):
    monkeypatch.setenv("SECRET_API_TOKEN_XYZ", "super_secret_leak")
    monkeypatch.setenv("SAFE_VAR_PATH", "/usr/bin")
    clean_env = sanitize_environment()
    assert "SECRET_API_TOKEN_XYZ" not in clean_env
    assert "SAFE_VAR_PATH" not in clean_env or not any("TOKEN" in k for k in clean_env)

# =============================================================================
# 3. AI Router Abstraction Tests
# =============================================================================

@pytest.mark.anyio
async def test_ai_router_intent_classification():
    # Research intent
    res_research = await ai_router.route_directive("Search all FastAPI route definitions across backend")
    assert res_research["target_agent"] == "agent-research"
    assert res_research["suggested_tool"] == "codebase_search"
    assert res_research["provider"] in ["MockEngine", "Google Gemini"]

    # Developer intent
    res_dev = await ai_router.route_directive("Refactor and modify the authentication module")
    assert res_dev["target_agent"] == "agent-dev"
    assert res_dev["suggested_tool"] == "generate_git_diff"

    # QA intent
    res_qa = await ai_router.route_directive("Run pytest test suite for regression verification")
    assert res_qa["target_agent"] == "agent-qa"
    assert res_qa["suggested_tool"] == "test.pytest"

# =============================================================================
# 4. Agent Runtime Engine State Machine Tests
# =============================================================================

def test_runtime_engine_task_lifecycle_completed():
    # Low-risk task should transition: PENDING -> VALIDATING -> RUNNING -> COMPLETED
    task = runtime_engine.create_task(
        agent_id="agent-research",
        title="Inspect backend storage models",
        instructions="Search for atomic_save_json"
    )
    assert task.status == "pending"

    executed_task = runtime_engine.execute_task(task.id)
    assert executed_task.status == "completed"
    assert executed_task.progress == 100
    assert len(executed_task.logs) >= 3
    assert executed_task.result is not None

def test_runtime_engine_task_lifecycle_awaiting_approval():
    # High-risk / deployment task must transition: PENDING -> VALIDATING -> AWAITING_APPROVAL
    task = runtime_engine.create_task(
        agent_id="agent-devops",
        title="deploy production to cloud run",
        instructions="Trigger live container push"
    )
    assert task.status == "pending"

    executed_task = runtime_engine.execute_task(task.id)
    assert executed_task.status == "awaiting_approval"
    assert executed_task.result["approval_required"] is True
    assert executed_task.result["approval_id"].startswith("appr-")

# =============================================================================
# 5. Developer Agent 5-Step Loop Tests
# =============================================================================

def test_developer_agent_full_loop():
    task = runtime_engine.create_task(
        agent_id="agent-dev",
        title="Synthesize feature sandbox patch",
        instructions="Execute inspect, plan, modify, test, diff in safe isolated sandbox"
    )
    executed_task = runtime_engine.execute_task(task.id)
    assert executed_task.status == "completed"
    res = executed_task.result
    assert res["cycle"] == "INSPECT -> PLAN -> MODIFY -> TEST -> DIFF"
    assert res["sandbox_tests_passed"] is True
    assert "has_diff" in res

# =============================================================================
# 6. QA, Security, Docs & Data Agent Execution Tests
# =============================================================================

def test_qa_agent_execution():
    out = execute_agent_tool("agent-qa", "test.pytest", {"project_path": "/root/control-center"})
    assert "status" in out
    assert out["project"] == "/root/control-center"

def test_security_agent_execution():
    out = execute_agent_tool("agent-security", "security.secret_scan", {"project_id": "control-center"})
    assert "status" in out
    assert out["execution_mode"] == "REAL_REGEX_SCAN"
    assert out["cves_found"] == 0

def test_docs_agent_execution():
    out = execute_agent_tool(
        "agent-docs",
        "docs.write",
        {
            "title": "Control Plane Hardening Verification",
            "category": "Security",
            "content": "Verified formal tool registry, safe subprocess runner, and cryptographic approval tokens."
        }
    )
    assert out["status"] == "CREATED"
    assert "id" in out["adr"]

def test_data_agent_execution():
    out = execute_agent_tool("agent-data", "docs.read", {"collection": "projects"})
    assert out["collection"] == "projects"
    assert out["total_records"] >= 3
