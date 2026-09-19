import os
import sys
import pytest
from fastapi.testclient import TestClient

from backend.server import app
from backend.orchestrator.local_connector import local_connector_engine
from backend.registry.projects import load_projects
from backend.models.schemas import AutoSyncConfig

client = TestClient(app)
AUTH_HEADERS = {"X-NEXUS-KEY": "nexus-dev-operator-key-2026"}



def test_universal_discovery_archetypes():
    """Verify universal discovery detects projects and extracts accurate archetypes."""
    res = client.get("/api/v1/connector/discover", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "scanned_roots" in data
    assert "discovered_projects" in data
    assert data["total_discovered"] >= 1

    # Find control-center itself
    cc = next((p for p in data["discovered_projects"] if "control-center" in p["path"] or p["project_id"] == "control-center"), None)
    assert cc is not None
    assert cc["detected_type"] == "fastapi"
    assert cc["has_git"] is True
    assert cc["has_tests"] is True
    assert cc["build_config"]["test_framework"] == "pytest"


def test_auto_sync_status_and_config():
    """Verify Auto-Sync status query and config update."""
    # 1. Query initial status
    res = client.get("/api/v1/connector/auto-sync/status", headers=AUTH_HEADERS)
    assert res.status_code == 200
    status_data = res.json()
    assert "enabled" in status_data
    assert "interval_seconds" in status_data
    assert "status" in status_data
    assert status_data["status"] in ("IDLE", "RUNNING", "DISABLED")
    assert "active_roots" in status_data

    # 2. Update config
    update_res = client.post(
        "/api/v1/connector/auto-sync/config",
        json={
            "enabled": True,
            "interval_seconds": 15,
            "auto_register_discovered": True,
            "reconcile_git_state": True,
            "custom_roots": ["/tmp"]
        },
        headers=AUTH_HEADERS
    )
    assert update_res.status_code == 200
    cfg_data = update_res.json()
    assert cfg_data["interval_seconds"] == 15
    assert cfg_data["auto_register_discovered"] is True
    assert "/tmp" in cfg_data["active_roots"]


def test_auto_sync_trigger_execution():
    """Verify manual trigger of Universal Auto-Sync cycle."""
    res = client.post("/api/v1/connector/auto-sync/trigger", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert "duration_seconds" in data
    assert data["total_discovered"] >= 1
    assert "reconciled_count" in data
    assert data["reconciled_count"] >= 1


def test_reconcile_fleet_drift():
    """Verify fleet reconciliation against filesystem and Git state."""
    res = client.post("/api/v1/connector/reconcile-all", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "reconciled_count" in data
    assert "drift_count" in data
    assert "synced_projects" in data
    assert data["reconciled_count"] >= 1


def test_connector_status_with_auto_sync():
    """Verify live status endpoint reflects full health and registered fleet."""
    res = client.get("/api/v1/connector/status", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert data["connected_projects_count"] >= 1
    assert len(data["allowed_roots"]) >= 1
