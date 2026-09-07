import os
import pytest
from fastapi.testclient import TestClient
from server import app
from core.storage import atomic_save_json, load_json_safe

client = TestClient(app)

def test_research_agent_codebase_search_dispatch():
    payload = {
        "agent_id": "agent-research",
        "title": "Search FastAPI routes",
        "instructions": "FastAPI",
        "autonomy_tier": "Autonomous",
        "project_id": "control-center"
    }
    resp = client.post("/api/v1/agents/dispatch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DISPATCHED"
    task = data["task"]
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["result"]["match_count"] > 0
    assert len(task["result"]["matches"]) > 0

def test_research_agent_ast_symbol_tool():
    payload = {
        "tool": "ast_search",
        "params": {"file_path": "/root/control-center/backend/core/storage.py"}
    }
    resp = client.post("/api/v1/agents/agent-research/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool"] == "ast_search"
    funcs = [f["name"] for f in data["output"]["functions"]]
    assert "load_json_safe" in funcs
    assert "atomic_save_json" in funcs

def test_data_agent_vault_query():
    payload = {
        "tool": "query_vault",
        "params": {"collection": "projects"}
    }
    resp = client.post("/api/v1/agents/agent-data/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["output"]["collection"] == "projects"
    assert data["output"]["total_records"] >= 3

def test_docs_agent_create_adr():
    payload = {
        "tool": "create_adr",
        "params": {
            "title": "Autonomous Execution Engine Activation",
            "category": "Architecture",
            "content": "Establishes real AST search and storage tools for AI swarm."
        }
    }
    resp = client.post("/api/v1/agents/agent-docs/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["output"]["status"] == "CREATED"
    assert "id" in data["output"]["adr"]

def test_dev_agent_git_diff_tool():
    payload = {
        "tool": "generate_git_diff",
        "params": {"repo_path": "/root/control-center"}
    }
    resp = client.post("/api/v1/agents/agent-dev/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "has_diff" in data["output"]
    assert data["output"]["repo"] == "/root/control-center"

def test_atomic_storage_operations(tmp_path):
    test_file = str(tmp_path / "test_data.json")
    payload = {"test_key": "active_value", "number": 42}
    
    atomic_save_json(test_file, payload)
    loaded = load_json_safe(test_file)
    assert loaded == payload

    missing = load_json_safe(str(tmp_path / "nonexistent.json"), default={"fallback": True})
    assert missing == {"fallback": True}
