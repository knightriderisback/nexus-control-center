import pytest
import os
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)
AUTH_HEADERS = {"X-NEXUS-KEY": "nexus-dev-operator-key-2026"}


def test_connector_status():
    """Verify local connector status endpoint returns valid host telemetry."""
    response = client.get("/api/v1/connector/status", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "os_environment" in data
    assert "is_termux" in data
    assert "connector_id" in data
    assert data["connected_projects_count"] >= 1


def test_connector_roots():
    """Verify allowed workspace scanner roots."""
    response = client.get("/api/v1/connector/roots", headers=AUTH_HEADERS)
    assert response.status_code == 200
    roots = response.json()
    assert isinstance(roots, list)
    assert len(roots) > 0


def test_connector_discover():
    """Verify recursive repository discovery finds current control-center."""
    response = client.get("/api/v1/connector/discover", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "discovered_projects" in data
    assert "scanned_roots" in data
    assert data["total_discovered"] >= 1
    
    # Check that control-center or a project was found
    found_paths = [p.get("path") or p.get("root_path") for p in data["discovered_projects"]]
    assert any(p and "/root/control-center" in p for p in found_paths)


def test_connector_onboard_and_dashboard():
    """Verify onboarding the control-center project and retrieving live dashboard."""
    # Onboard control-center
    onboard_payload = {
        "name": "NEXUS Control Center",
        "root_path": "/root/control-center",
        "git_branch": "main"
    }
    onboard_res = client.post("/api/v1/connector/onboard", json=onboard_payload, headers=AUTH_HEADERS)
    assert onboard_res.status_code in (200, 201)
    onboard_data = onboard_res.json()
    project_id = onboard_data.get("id") or onboard_data.get("project_id")
    assert project_id == "control-center"

    # Retrieve live project dashboard
    dash_res = client.get(f"/api/v1/connector/projects/{project_id}/dashboard", headers=AUTH_HEADERS)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["project"]["id"] == "control-center"
    assert "git" in dash_data
    assert dash_data["git"]["branch"] == "main"
    assert "available_actions" in dash_data
    assert "AUDIT" in dash_data["available_actions"]


def test_connector_project_actions():
    """Verify executing governed actions (AUDIT, TEST, SECURITY_SCAN) on project."""
    project_id = "control-center"
    
    for action in ["AUDIT", "SECURITY_SCAN", "RECONCILE_DRIFT"]:
        res = client.post(
            f"/api/v1/connector/projects/{project_id}/action",
            json={"action": action, "payload": {}},
            headers=AUTH_HEADERS
        )
        assert res.status_code == 200
        data = res.json()
        assert data["action"] == action
        assert data["status"] in ("COMPLETED", "SUCCESS")
        assert len(data["output"]) > 0


def test_connector_sync_all():
    """Verify bulk sync-all across all discovered workspaces."""
    response = client.post("/api/v1/connector/sync-all", json={}, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "synced_count" in data
    assert "synced_projects" in data
    assert data["synced_count"] >= 0
