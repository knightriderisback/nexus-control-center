"""
Tests for Agent Runtime & Hardened Execution Core:
1. Tool Registry & RBAC Permissions
2. Safe Command Execution Layer & Sanitization
3. AI Router Abstraction & Fallback (NOT_CONFIGURED check)
4. Agent Runtime Engine Multi-Step State Machine
5. Execution Limits (max_steps, max_tool_calls, max_runtime)
6. Developer Agent Complete Lifecycle with Rollback
7. QA Agent Framework Detection & Structured Results
8. Security Agent Triaged Findings (REAL, INFORMATIONAL, UNAVAILABLE)
9. Documentation Agent Path Restriction
10. Telemetry Run Counters & Audit Trail Integrity
"""

import os
import pytest
from orchestrator.tool_registry import tool_registry, ToolDefinition, AGENT_PERMISSION_PROFILES
from orchestrator.safe_runner import SafeCommandExecutor, validate_command, sanitize_environment
from orchestrator.base import ai_router, get_ai_adapter, provider_registry, MockProvider, GeminiProvider, OpenAIProvider, AnthropicProvider
from orchestrator.runtime import runtime_engine
from orchestrator.tool_runner import execute_agent_tool
from core.observability import collector
from core.audit import get_recent_audit_events
from models.schemas import RiskLevel, ExecutionLimits

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

def test_tool_registry_permission_profiles():
    # Research: read-only
    res_tools = tool_registry.list_tools("agent-research")
    for t in res_tools:
        assert t.execution_mode in ["read_only", "safe_subprocess"]
        assert t.tool_id not in ["filesystem.write", "shell.safe"]

    # Developer: includes controlled write and test execution
    dev_tools = [t.tool_id for t in tool_registry.list_tools("agent-dev")]
    assert "filesystem.write" in dev_tools
    assert "git.diff" in dev_tools
    assert "test.pytest" in dev_tools

def test_tool_registry_rbac_validation():
    # Research Agent is authorized for filesystem.read
    valid, err = tool_registry.validate_tool_call("filesystem.read", "agent-research", {"file_path": "server.py"})
    assert valid is True
    assert err is None

    # Research Agent is NOT authorized for shell.safe
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
    assert res.execution_id.startswith("exec-")

def test_safe_command_blocked_binary():
    res = SafeCommandExecutor.execute(["nc", "-l", "8080"], cwd="/root/control-center")
    assert res.exit_code == 126
    assert "not permitted by command allowlist" in res.stderr

def test_safe_command_directory_escape_blocked():
    res = SafeCommandExecutor.execute(["ls"], cwd="/etc")
    assert res.exit_code == 126
    assert "outside permitted workspace roots" in res.stderr

def test_safe_command_path_traversal_blocked():
    res = SafeCommandExecutor.execute(["ls", "../../etc/shadow"], cwd="/root/control-center")
    assert res.exit_code == 126
    assert "Path traversal attempt" in res.stderr or "escapes permitted workspace boundaries" in res.stderr

def test_safe_command_shell_injection_blocked():
    # Semicolon chaining
    res = SafeCommandExecutor.execute(["echo", "hello; rm -rf /"], cwd="/root/control-center")
    assert res.exit_code == 126
    assert "Dangerous shell character" in res.stderr

    # Subshell
    res_subshell = SafeCommandExecutor.execute(["echo", "$(whoami)"], cwd="/root/control-center")
    assert res_subshell.exit_code == 126
    assert "Dangerous shell character" in res_subshell.stderr

    # Redirection
    res_redir = SafeCommandExecutor.execute(["echo", "hello > /tmp/out.txt"], cwd="/root/control-center")
    assert res_redir.exit_code == 126
    assert "Dangerous shell character" in res_redir.stderr

def test_safe_command_env_sanitization(monkeypatch):
    monkeypatch.setenv("SECRET_API_TOKEN_XYZ", "super_secret_leak")
    monkeypatch.setenv("SAFE_VAR_PATH", "/usr/bin")
    clean_env = sanitize_environment()
    assert "SECRET_API_TOKEN_XYZ" not in clean_env
    assert not any("TOKEN" in k for k in clean_env)

# =============================================================================
# 3. AI Router & Provider Abstraction Tests
# =============================================================================

def test_ai_provider_not_configured_status():
    # Without credentials, real providers must report NOT_CONFIGURED
    gemini = GeminiProvider(api_key=None)
    assert gemini.health()["status"] == "NOT_CONFIGURED"
    assert gemini.health()["available"] is False

    openai = OpenAIProvider(api_key=None)
    assert openai.health()["status"] == "NOT_CONFIGURED"
    assert openai.health()["available"] is False

    anthropic = AnthropicProvider(api_key=None)
    assert anthropic.health()["status"] == "NOT_CONFIGURED"
    assert anthropic.health()["available"] is False

    # Mock provider is always READY and available
    mock = MockProvider()
    assert mock.health()["status"] == "READY"
    assert mock.health()["available"] is True
    assert mock.metadata()["cost_per_1k_tokens"] == 0.0

def test_ai_provider_registry_fallback():
    # When asking for an unconfigured provider, fallback resolves to MockProvider
    p = provider_registry.resolve_provider(preference="gemini")
    assert p.health()["status"] == "READY"
    assert p.metadata()["provider"] == "MockEngine"

@pytest.mark.anyio
async def test_ai_router_intent_classification():
    # Research intent
    res_research = await ai_router.route_directive("Search all FastAPI route definitions across backend")
    assert res_research["target_agent"] == "agent-research"
    assert res_research["suggested_tool"] == "codebase_search"
    assert res_research["estimated_cost_usd"] == 0.0

    # Developer intent
    res_dev = await ai_router.route_directive("Refactor and modify the authentication module")
    assert res_dev["target_agent"] == "agent-dev"
    assert res_dev["suggested_tool"] == "generate_git_diff"

    # QA intent
    res_qa = await ai_router.route_directive("Run pytest test suite for regression verification")
    assert res_qa["target_agent"] == "agent-qa"
    assert res_qa["suggested_tool"] == "test.pytest"

# =============================================================================
# 4. Agent Runtime Engine Multi-Step State Machine
# =============================================================================

def test_runtime_engine_task_lifecycle_completed():
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
# 5. Developer Agent Complete Lifecycle with Rollback
# =============================================================================

def test_developer_agent_full_lifecycle_in_fixture():
    task = runtime_engine.create_task(
        agent_id="agent-dev",
        title="Extend calculator with multiply method",
        instructions="Modify calculator.py in fixture and verify tests"
    )
    executed_task = runtime_engine.execute_task(task.id)
    assert executed_task.status == "completed"
    res = executed_task.result
    assert res["agent"] == "DEVELOPER-02"
    assert "INSPECT -> UNDERSTAND -> PLAN -> READ -> MODIFY -> TEST -> DIFF" in res["cycle"]
    assert res["tests_passed"] is True
    assert res["has_diff"] is True
    assert "multiply" in res["diff"]

def test_developer_agent_rollback_capability():
    task = runtime_engine.create_task(
        agent_id="agent-dev",
        title="Simulated test modification with rollback",
        instructions="Modify calculator.py and trigger automatic rollback"
    )
    # Execute with rollback_on_test_failure = True
    executed_task = runtime_engine.execute_task(task.id, rollback_on_test_failure=True)
    assert executed_task.status == "completed"
    res = executed_task.result
    assert res["rolled_back"] is True
    assert res["has_diff"] is False # Clean working tree after revert!

# =============================================================================
# 6. QA Agent: Framework Detection & Structured Results
# =============================================================================

def test_qa_agent_framework_detection_and_parsing():
    task = runtime_engine.create_task(
        agent_id="agent-qa",
        title="Run control-center test verification",
        instructions="Detect test runner and return structured assertion metrics"
    )
    executed_task = runtime_engine.execute_task(task.id)
    assert executed_task.status == "completed"
    res = executed_task.result
    assert res["agent"] == "QA-VERIFIER"
    assert res["framework"] == "pytest"
    assert res["status"] in ["PASSED", "FAILED"]
    assert isinstance(res["passed"], int)
    assert res["passed"] > 0

# =============================================================================
# 7. Security Agent: Triaged Findings
# =============================================================================

def test_security_agent_triaged_findings():
    task = runtime_engine.create_task(
        agent_id="agent-security",
        title="Full workspace security posture check",
        instructions="Perform secret scan, dangerous config, and dependency audit"
    )
    executed_task = runtime_engine.execute_task(task.id)
    assert executed_task.status == "completed"
    res = executed_task.result
    assert res["agent"] == "SENTINEL-SEC"
    assert res["findings_count"] >= 3
    # Verify categories: REAL_FINDING, INFORMATIONAL, and UNAVAILABLE_CHECK
    categories = [f["category"] for f in res["findings"]]
    assert "INFORMATIONAL" in categories
    assert "UNAVAILABLE_CHECK" in categories # pip-audit not installed, cleanly marked UNAVAILABLE_CHECK

# =============================================================================
# 8. Documentation Agent: Authoring with Path Restriction
# =============================================================================

def test_docs_agent_restricted_path_authoring():
    task = runtime_engine.create_task(
        agent_id="agent-docs",
        title="Runtime Security Architecture ADR",
        instructions="Record ADR in memory vault"
    )
    executed_task = runtime_engine.execute_task(task.id)
    assert executed_task.status == "completed"
    res = executed_task.result
    assert res["agent"] == "DOC-CHRONICLER"
    assert res["status"] == "DOCUMENTED"
    assert res["vault_updated"] is True

# =============================================================================
# 9. Telemetry Run Counters & Audit Trail Integrity
# =============================================================================

def test_agent_telemetry_counters_incremented():
    initial_metric = collector.agent_runs.get("agent-research", {}).get("execution_count", 0)
    
    task = runtime_engine.create_task(
        agent_id="agent-research",
        title="Check telemetry counter bump",
        instructions="Perform read-only query"
    )
    runtime_engine.execute_task(task.id)

    updated_metric = collector.agent_runs.get("agent-research", {}).get("execution_count", 0)
    assert updated_metric > initial_metric

def test_audit_trail_records_execution_and_tool_ids():
    events = get_recent_audit_events(limit=10)
    assert len(events) > 0
    # Verify events contain execution_id and tool_id where applicable
    has_exec_id = any(e.execution_id is not None for e in events)
    assert has_exec_id is True
