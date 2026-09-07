"""
NEXUS Phase 5: Agent Isolation Hardening Test Suite.
Verifies filesystem jailing per agent persona, RBAC boundary enforcement,
environment variable scrubbing, and process session isolation.
"""

import os
import pytest
from orchestrator.tool_registry import tool_registry
from orchestrator.tool_runner import execute_agent_tool, is_safe_path
from orchestrator.safe_runner import sanitize_environment, SafeCommandExecutor

# =============================================================================
# 1. Agent Filesystem Jailing & Scope Boundaries
# =============================================================================

def test_developer_agent_forbidden_from_overwriting_core_control_plane():
    # Attempt to write to backend/core/auth.py as agent-dev
    params = {
        "file_path": "/root/control-center/backend/core/auth.py",
        "content": "# malicious overwrite"
    }
    # RBAC check: tool is in profile, but tool_runner jailing catches it
    out = execute_agent_tool("agent-dev", "filesystem.write", params)
    assert out.get("status") == "BLOCKED"
    assert "forbidden from directly modifying core control plane files" in out.get("error", "")

def test_developer_agent_permitted_in_fixture_workspace():
    test_target = "/root/control-center/data/fixtures/developer_test_repo/isolation_probe.txt"
    try:
        params = {
            "file_path": test_target,
            "content": "safe dev test modification"
        }
        out = execute_agent_tool("agent-dev", "filesystem.write", params)
        assert out.get("status") == "WRITTEN"
        assert os.path.exists(test_target)
    finally:
        if os.path.exists(test_target):
            os.remove(test_target)

def test_docs_agent_restricted_to_docs_and_markdown():
    # Attempt to write python file in backend as agent-docs
    params = {
        "file_path": "/root/control-center/backend/malicious.py",
        "content": "print('exploit')"
    }
    out = execute_agent_tool("agent-docs", "filesystem.write", params)
    assert out.get("status") == "BLOCKED"
    assert "restricted to authoring documentation files in docs/ only" in out.get("error", "")

def test_docs_agent_permitted_in_docs_directory():
    test_target = "/root/control-center/docs/isolation_test.md"
    try:
        params = {
            "file_path": test_target,
            "content": "# Isolation Test Record"
        }
        out = execute_agent_tool("agent-docs", "filesystem.write", params)
        assert out.get("status") == "WRITTEN"
        assert os.path.exists(test_target)
    finally:
        if os.path.exists(test_target):
            os.remove(test_target)

def test_research_agent_strictly_read_only_by_rbac():
    # Attempt to call filesystem.write as agent-research
    is_auth, err = tool_registry.validate_tool_call("filesystem.write", "agent-research", {"file_path": "/tmp/test"})
    assert is_auth is False
    assert "not authorized to use tool 'filesystem.write'" in err

    # Attempt to call shell.safe as agent-research
    is_auth_shell, err_shell = tool_registry.validate_tool_call("shell.safe", "agent-research", {"cmd_args": ["ls"]})
    assert is_auth_shell is False
    assert "not authorized to use tool 'shell.safe'" in err_shell

def test_security_agent_cannot_write_by_rbac():
    is_auth, err = tool_registry.validate_tool_call("filesystem.write", "agent-security", {"file_path": "/tmp/test"})
    assert is_auth is False
    assert "not authorized to use tool 'filesystem.write'" in err

def test_qa_agent_cannot_write_by_rbac():
    is_auth, err = tool_registry.validate_tool_call("filesystem.write", "agent-qa", {"file_path": "/tmp/test"})
    assert is_auth is False
    assert "not authorized to use tool 'filesystem.write'" in err

# =============================================================================
# 2. Environment Variable Scrubbing & Inheritance Defense
# =============================================================================

def test_environment_sanitizer_strips_dangerous_variables():
    # Attempt to inject dangerous vars via env_override
    override = {
        "LD_PRELOAD": "/tmp/evil.so",
        "LD_LIBRARY_PATH": "/tmp/evil_libs",
        "BASH_ENV": "/tmp/evil_rc",
        "IFS": ":",
        "GCP_SERVICE_KEY": "secret_key_value",
        "OPENAI_API_KEY": "sk-12345",
        "SAFE_CUSTOM_VAR": "clean_value"
    }
    clean = sanitize_environment(override)
    assert "LD_PRELOAD" not in clean
    assert "LD_LIBRARY_PATH" not in clean
    assert "BASH_ENV" not in clean
    assert "IFS" not in clean
    assert "GCP_SERVICE_KEY" not in clean
    assert "OPENAI_API_KEY" not in clean
    assert clean.get("SAFE_CUSTOM_VAR") == "clean_value"

def test_subprocess_does_not_inherit_host_secrets():
    # Set a test secret in current process os.environ
    os.environ["SECRET_OPERATOR_PASSWORD"] = "adversarial_secret_1234"
    try:
        # Run python subprocess printing the environment variable without semicolon
        py_cmd = "print(__import__('os').environ.get('SECRET_OPERATOR_PASSWORD', 'SCRUBBED'))"
        res = SafeCommandExecutor.execute(["python3", "-c", py_cmd])
        assert res.exit_code == 0
        assert res.stdout.strip() == "SCRUBBED"
    finally:
        os.environ.pop("SECRET_OPERATOR_PASSWORD", None)

# =============================================================================
# 3. Process Session & Group Isolation
# =============================================================================

def test_subprocess_runs_in_isolated_process_group():
    # Check that child process group ID differs from parent PID
    py_cmd = "print(__import__('os').getpgrp() != __import__('os').getppid())"
    res = SafeCommandExecutor.execute(["python3", "-c", py_cmd])
    assert res.exit_code == 0
    assert "True" in res.stdout

# =============================================================================
# 4. Workspace Filesystem Boundary Isolation (fixture-workspace vs fixture-outside)
# =============================================================================

def test_filesystem_isolation_fixture_boundaries():
    ws = "/root/control-center/data/fixtures/fixture-workspace"
    outside = "/root/control-center/data/fixtures/fixture-outside"

    # 1. Allowed file within workspace must be readable
    r_ok = execute_agent_tool("agent-research", "filesystem.read", {"file_path": "allowed.txt", "workspace_root": ws})
    assert "ALLOWED_CONTENT_WORKSPACE" in r_ok.get("content", "")

    # 2. Nested allowed file within workspace must be readable
    r_nested = execute_agent_tool("agent-research", "filesystem.read", {"file_path": "sub/nested.txt", "workspace_root": ws})
    assert "NESTED_CONTENT_WORKSPACE" in r_nested.get("content", "")

    # 3. Relative path traversal escaping workspace must be blocked
    r_rel = execute_agent_tool("agent-research", "filesystem.read", {"file_path": "../fixture-outside/forbidden.txt", "workspace_root": ws})
    assert "outside workspace" in r_rel.get("error", "")

    # 4. Absolute path pointing to outside directory must be blocked
    r_abs = execute_agent_tool("agent-research", "filesystem.read", {"file_path": os.path.join(outside, "forbidden.txt"), "workspace_root": ws})
    assert "outside workspace" in r_abs.get("error", "")

def test_filesystem_isolation_symlink_escape_blocked():
    ws = "/root/control-center/data/fixtures/fixture-workspace"
    # Symlink points outside to ../fixture-outside/forbidden.txt
    symlink_target = os.path.join(ws, "symlink_outside")
    r_sym = execute_agent_tool("agent-research", "filesystem.read", {"file_path": symlink_target, "workspace_root": ws})
    assert "outside workspace" in r_sym.get("error", "")

def test_filesystem_isolation_directory_listing_and_writing_denied():
    ws = "/root/control-center/data/fixtures/fixture-workspace"

    # Directory listing within workspace succeeds
    l_ok = execute_agent_tool("agent-research", "filesystem.list", {"dir_path": "sub", "workspace_root": ws})
    assert "entries" in l_ok and "nested.txt" in l_ok["entries"]

    # Directory listing outside workspace fails
    l_denied = execute_agent_tool("agent-research", "filesystem.list", {"dir_path": "../fixture-outside", "workspace_root": ws})
    assert "outside workspace" in l_denied.get("error", "")

    # Write outside workspace fails
    w_denied = execute_agent_tool("agent-dev", "filesystem.write", {"file_path": "../fixture-outside/breach.txt", "content": "breach", "workspace_root": ws})
    assert w_denied.get("status") == "FAILED"
    assert "outside workspace" in w_denied.get("error", "")

# =============================================================================
# 5. Developer Agent Empirical Lifecycle & Rollback on Dedicated Fixture
# =============================================================================

def test_developer_agent_full_lifecycle_on_fixture_repository():
    from orchestrator.runtime import AgentRuntimeEngine
    engine = AgentRuntimeEngine()
    fixture_dir = "/root/control-center/data/fixtures/fixture-calculator"

    task = engine.create_task(
        "agent-dev",
        "Fix calculator implementation",
        "Resolve arithmetic flaw in fixture repository",
        project_id=fixture_dir
    )
    result = engine.execute_task(task.id, rollback_on_test_failure=False)
    assert result.status == "completed"
    assert result.result["tests_passed"] is True
    assert result.result["has_diff"] is True
    assert "diff" in result.result

def test_developer_agent_rollback_on_test_failure():
    from orchestrator.runtime import AgentRuntimeEngine
    import subprocess
    engine = AgentRuntimeEngine()
    fixture_dir = "/root/control-center/data/fixtures/fixture-calculator"

    task = engine.create_task(
        "agent-dev",
        "Test regression rollback execution",
        "Enforce clean git rollback on simulated failure",
        project_id=fixture_dir
    )
    result = engine.execute_task(task.id, rollback_on_test_failure=True)
    assert result.status == "completed"
    assert result.result["rolled_back"] is True

    # Confirm fixture repository working tree is completely clean
    st = subprocess.run(["git", "status", "--porcelain"], cwd=fixture_dir, capture_output=True, text=True)
    assert st.stdout.strip() == ""

# =============================================================================
# 6. QA Agent Reality Verification on Passing & Failing Suites
# =============================================================================

def test_qa_agent_executes_passing_fixture_suite():
    from orchestrator.runtime import AgentRuntimeEngine
    engine = AgentRuntimeEngine()
    pass_fixture = "/root/control-center/data/fixtures/fixture-qa-passing"

    task = engine.create_task("agent-qa", "Verify passing test suite", "Execute tests", project_id=pass_fixture)
    result = engine.execute_task(task.id)
    assert result.status == "completed"
    assert result.result["framework"] == "pytest"
    assert result.result["status"] == "PASSED"
    assert result.result["passed"] == 2
    assert result.result["failed"] == 0

def test_qa_agent_executes_failing_fixture_suite():
    from orchestrator.runtime import AgentRuntimeEngine
    engine = AgentRuntimeEngine()
    fail_fixture = "/root/control-center/data/fixtures/fixture-qa-failing"

    task = engine.create_task("agent-qa", "Verify failing test suite", "Execute tests", project_id=fail_fixture)
    result = engine.execute_task(task.id)
    assert result.status == "completed"
    assert result.result["framework"] == "pytest"
    assert result.result["status"] == "FAILED"
    assert result.result["failed"] == 1

# =============================================================================
# 7. Security Agent Secret Discovery & Finding Triaging
# =============================================================================

def test_security_agent_detects_deliberately_placed_safe_test_key():
    from orchestrator.runtime import AgentRuntimeEngine
    engine = AgentRuntimeEngine()
    sec_fixture = "/root/control-center/data/fixtures/fixture-security"

    task = engine.create_task("agent-security", "Audit repository credentials", "Detect secret leaks", project_id=sec_fixture)
    result = engine.execute_task(task.id)
    assert result.status == "completed"
    assert result.result["status"] == "AUDIT_COMPLETE"
    assert result.result["real_findings"] >= 1
    # Check that static credential scan captured the test key
    cred_finding = next(f for f in result.result["findings"] if f["type"] == "STATIC_CREDENTIAL_SCAN")
    assert cred_finding["category"] == "REAL_FINDING"

def test_security_agent_triages_findings_into_three_tiers():
    from orchestrator.runtime import AgentRuntimeEngine
    engine = AgentRuntimeEngine()
    clean_fixture = "/root/control-center/data/fixtures/fixture-workspace"

    task = engine.create_task("agent-security", "Audit clean workspace", "Triage findings", project_id=clean_fixture)
    result = engine.execute_task(task.id)
    assert result.status == "completed"
    # Ensure findings are partitioned into REAL_FINDING, INFORMATIONAL, and UNAVAILABLE_CHECK
    categories = {f["category"] for f in result.result["findings"]}
    assert "INFORMATIONAL" in categories
    assert "UNAVAILABLE_CHECK" in categories

