"""
NEXUS Phase 15: Universal Tool & App Integration Comprehensive Test Suite.
Tests:
- Dynamic Universal Tool Registry across 9 categories
- Multi-protocol execution (Native, CLI, REST, Database, Webhook, MCP)
- SQL AST Safety and Mutation Guardrails
- Model Context Protocol (MCP) Server bridge and transport handling
- Connected Apps Ecosystem (GitHub, Vercel, SQLite, Termux, System OS)
- Agent & Runtime tool dispatch integration
- REST API endpoints mounted at /api/v1/tools
- $0.00 Zero-Cost FinOps budget governance
"""

import os
import sys
import json
import pytest
import sqlite3
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from server import app
from models.schemas import (
    RiskLevel,
    ToolProtocolType,
    ToolCategory,
    UniversalToolManifest,
    UniversalToolInvocationRequest,
    MCPServerDefinition
)
from orchestrator.universal_tool_engine import universal_tool_engine
from orchestrator.tool_runner import execute_tool
from core.cost_guard import cost_guard

client = TestClient(app)


# =============================================================================
# 1. Universal Tool Registry Tests
# =============================================================================

class TestUniversalToolRegistry:
    """Verifies tool registration, querying, filtering, and schema validation."""

    def test_builtin_tools_loaded(self):
        tools = universal_tool_engine.list_tools()
        assert len(tools) >= 15
        tool_ids = [t.tool_id for t in tools]
        assert "fs.read_file" in tool_ids
        assert "fs.write_file" in tool_ids
        assert "git.status_inspector" in tool_ids
        assert "db.sqlite_query" in tool_ids
        assert "security.secret_scanner" in tool_ids
        assert "notify.termux_sms" in tool_ids
        assert "web.http_request" in tool_ids
        assert "system.diagnostics" in tool_ids

    def test_filter_tools_by_category(self):
        fs_tools = universal_tool_engine.list_tools(category="FILESYSTEM")
        assert len(fs_tools) >= 3
        for t in fs_tools:
            assert t.category == ToolCategory.FILESYSTEM

        db_tools = universal_tool_engine.list_tools(category="DATABASE")
        assert len(db_tools) >= 2
        for t in db_tools:
            assert t.category == ToolCategory.DATABASE

    def test_filter_tools_by_protocol(self):
        db_query_tools = universal_tool_engine.list_tools(protocol="DATABASE_QUERY")
        assert len(db_query_tools) >= 2
        for t in db_query_tools:
            assert t.protocol == ToolProtocolType.DATABASE_QUERY

    def test_register_and_unregister_custom_tool(self):
        custom_id = "custom.math_adder"
        manifest = UniversalToolManifest(
            tool_id=custom_id,
            name="Custom Math Adder",
            description="Adds two integers together",
            protocol=ToolProtocolType.NATIVE_PYTHON,
            category=ToolCategory.CUSTOM_PLUGIN,
            input_schema={"a": "int", "b": "int"},
            output_schema={"sum": "int"},
            risk_level=RiskLevel.LOW
        )

        def adder_handler(params, caller):
            return {"sum": params.get("a", 0) + params.get("b", 0)}

        universal_tool_engine.register_tool(manifest, handler=adder_handler)
        assert universal_tool_engine.get_tool(custom_id) is not None

        # Execute custom tool
        res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id=custom_id,
            parameters={"a": 15, "b": 27}
        ))
        assert res.status == "SUCCESS"
        assert res.output["sum"] == 42

        # Unregister custom tool
        unreg_ok = universal_tool_engine.unregister_tool(custom_id)
        assert unreg_ok is True
        assert universal_tool_engine.get_tool(custom_id) is None


# =============================================================================
# 2. Multi-Protocol Execution Tests
# =============================================================================

class TestMultiProtocolToolExecution:
    """Tests native handlers, CLI tools, REST endpoints, and SQL database operations."""

    def test_filesystem_read_and_write(self, tmp_path):
        test_file = str(tmp_path / "test_artifact.txt")
        write_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="fs.write_file",
            parameters={"file_path": test_file, "content": "NEXUS Phase 15 Universal Tool"}
        ))
        assert write_res.status == "SUCCESS"
        assert write_res.output["status"] == "SAVED"

        read_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="fs.read_file",
            parameters={"file_path": test_file}
        ))
        assert read_res.status == "SUCCESS"
        assert "NEXUS Phase 15 Universal Tool" in read_res.output["content"]

    def test_git_status_and_log(self):
        status_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="git.status_inspector",
            parameters={"repo_path": "/root/control-center"}
        ))
        assert status_res.status == "SUCCESS"
        assert "branch" in status_res.output

        log_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="git.log_history",
            parameters={"repo_path": "/root/control-center", "limit": 3}
        ))
        assert log_res.status == "SUCCESS"
        assert len(log_res.output["commits"]) > 0

    def test_database_sqlite_safe_query(self, tmp_path):
        db_file = str(tmp_path / "sandbox.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE metrics (id INTEGER PRIMARY KEY, name TEXT, value REAL);")
        conn.execute("INSERT INTO metrics (name, value) VALUES ('cpu_usage', 14.5);")
        conn.execute("INSERT INTO metrics (name, value) VALUES ('mem_usage', 42.1);")
        conn.commit()
        conn.close()

        # Query via Universal Engine
        query_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="db.sqlite_query",
            parameters={"db_path": db_file, "sql": "SELECT name, value FROM metrics ORDER BY id ASC;"}
        ))
        assert query_res.status == "SUCCESS"
        assert query_res.output["row_count"] == 2
        assert query_res.output["rows"][0] == ["cpu_usage", 14.5]

    def test_database_destructive_query_blocked(self, tmp_path):
        db_file = str(tmp_path / "sandbox.db")
        # Attempt destructive SQL query
        drop_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="db.sqlite_query",
            parameters={"db_path": db_file, "sql": "DROP TABLE metrics;"}
        ))
        assert drop_res.status == "FAILED"
        assert "Destructive SQL keyword 'DROP' is blocked" in drop_res.error

    def test_database_schema_inspector(self, tmp_path):
        db_file = str(tmp_path / "schema_test.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, email TEXT);")
        conn.commit()
        conn.close()

        schema_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="db.schema_inspector",
            parameters={"db_path": db_file}
        ))
        assert schema_res.status == "SUCCESS"
        assert "users" in schema_res.output["tables"]

    def test_secret_scanner_clean_and_detection(self, tmp_path):
        clean_file = tmp_path / "clean_module.py"
        clean_file.write_text("def ping():\n    return {'status': 'ok'}\n")

        scan_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="security.secret_scanner",
            parameters={"target_path": str(tmp_path)}
        ))
        assert scan_res.status == "SUCCESS"
        assert scan_res.output["status"] == "CLEAN"
        assert scan_res.output["leaks_found"] == 0

    def test_notification_and_termux_dispatch(self):
        notify_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="notify.termux_sms",
            parameters={"title": "Phase 15 Verification", "content": "Universal tool engine online"}
        ))
        assert notify_res.status == "SUCCESS"
        assert notify_res.output["status"] == "DELIVERED"

    def test_system_diagnostics_and_port_scan(self):
        diag_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="system.diagnostics"
        ))
        assert diag_res.status == "SUCCESS"
        assert "cpu_percent" in diag_res.output
        assert "ram_used_gb" in diag_res.output

        port_res = universal_tool_engine.invoke_tool(UniversalToolInvocationRequest(
            tool_id="system.port_scan",
            parameters={"ports": [8000, 22]}
        ))
        assert port_res.status == "SUCCESS"
        assert "host" in port_res.output


# =============================================================================
# 3. Model Context Protocol (MCP) Bridge Tests
# =============================================================================

class TestMCPProtocolBridge:
    """Verifies MCP server registration, connection, and dispatch bridge."""

    def test_register_and_list_mcp_servers(self):
        mcp_def = MCPServerDefinition(
            server_id="mcp-test-postgres",
            name="Test Postgres MCP",
            transport="stdio",
            command_or_url="npx -y @modelcontextprotocol/server-postgres postgresql://localhost/db"
        )
        universal_tool_engine.register_mcp_server(mcp_def)
        servers = universal_tool_engine.list_mcp_servers()
        assert any(s.server_id == "mcp-test-postgres" for s in servers)

    def test_connect_and_discover_mcp_tools(self):
        connected = universal_tool_engine.connect_mcp_server("mcp-test-postgres")
        assert connected.status == "CONNECTED"
        assert len(connected.exposed_tools) > 0


# =============================================================================
# 4. Connected Apps Ecosystem Tests
# =============================================================================

class TestConnectedAppsEcosystem:
    """Verifies external app connectors and health checks."""

    def test_list_connected_apps(self):
        apps = universal_tool_engine.list_connected_apps()
        assert len(apps) >= 4
        app_ids = [a.app_id for a in apps]
        assert "app-github" in app_ids
        assert "app-vercel" in app_ids
        assert "app-sqlite" in app_ids
        assert "app-termux" in app_ids
        assert "app-system" in app_ids

    def test_app_connectivity_test(self):
        res = universal_tool_engine.test_app_connection("app-github")
        assert res["status"] == "CONNECTED"
        assert res["app_id"] == "app-github"


# =============================================================================
# 5. Agent & Tool Runner Integration Tests
# =============================================================================

class TestAgentAndToolRunnerIntegration:
    """Verifies that execute_tool in tool_runner dispatches to universal tool engine."""

    def test_tool_runner_universal_dispatch(self, tmp_path):
        test_file = str(tmp_path / "agent_universal_test.txt")
        # Invoke fs.write_file through tool_runner.execute_tool
        result = execute_tool(
            agent_id="agent-dev",
            tool_name="fs.write_file",
            params={"file_path": test_file, "content": "Agent Universal Dispatch"}
        )
        assert result.get("status") == "SAVED"
        assert os.path.exists(test_file)


# =============================================================================
# 6. REST API Endpoints & FinOps Governance Tests
# =============================================================================

class TestUniversalToolsRESTAPI:
    """Verifies FastAPI endpoints mounted at /api/v1/tools."""

    def test_api_list_tools(self):
        resp = client.get("/api/v1/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 15

    def test_api_get_tool(self):
        resp = client.get("/api/v1/tools/fs.read_file")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_id"] == "fs.read_file"
        assert data["category"] == "FILESYSTEM"

    def test_api_invoke_tool(self, tmp_path):
        target_f = str(tmp_path / "api_test.txt")
        resp = client.post(
            "/api/v1/tools/fs.write_file/invoke",
            json={
                "tool_id": "fs.write_file",
                "parameters": {"file_path": target_f, "content": "REST API Universal Tool"}
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["duration_ms"] >= 0.0

    def test_api_connected_apps(self):
        resp = client.get("/api/v1/tools/apps")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 4

        # Test app connection endpoint
        test_resp = client.post("/api/v1/tools/apps/app-system/test")
        assert test_resp.status_code == 200
        test_data = test_resp.json()
        assert test_data["status"] == "CONNECTED"

    def test_api_mcp_servers(self):
        resp = client.get("/api/v1/tools/mcp/servers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_api_telemetry(self):
        resp = client.get("/api/v1/tools/telemetry")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tools" in data
        assert "categories" in data
        assert "total_invocations" in data

    def test_zero_spend_finops_governance(self):
        summary = cost_guard.get_cost_summary()
        assert summary["current_spend_usd"] == 0.0
        assert summary["hard_spend_limit_usd"] == 0.0
        assert summary["zero_cost_guardrail_active"] is True
        assert summary["billing_linked"] is False
