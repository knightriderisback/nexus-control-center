import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ONLINE"

def test_v1_overview():
    resp = client.get("/api/v1/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "fleet" in data
    assert data["fleet"]["total_agents"] == 13
    assert data["cloud_project"] == "personal-engineering-os-2026"

def test_v1_projects():
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 3
    ids = [p["id"] for p in projects]
    assert "personal-engineering-os-2026" in ids
    assert "control-center" in ids
    assert "portfolio" in ids

def test_v1_agents():
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 200
    assert len(resp.json()) == 13

def test_v1_approvals():
    resp = client.get("/api/v1/approvals")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_v1_policy():
    resp = client.get("/api/v1/policy")
    assert resp.status_code == 200
    assert len(resp.json()) >= 9

def test_v1_audit():
    resp = client.get("/api/v1/audit")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_v1_cost():
    resp = client.get("/api/v1/cost/status")
    assert resp.status_code == 200
    assert resp.json()["billing_account_linked"] is False

def test_v1_secrets():
    resp = client.get("/api/v1/secrets")
    assert resp.status_code == 200
    assert len(resp.json()) >= 4

def test_v1_metrics():
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert "total_requests" in resp.json()

def test_v1_traces():
    resp = client.get("/api/v1/traces")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_v1_automations():
    resp = client.get("/api/v1/automations/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 6

def test_v1_isolated_projects():
    resp = client.get("/api/v1/integrations/isolated-projects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    for p in data:
        assert p["write_permitted"] is False
        assert p["isolation_status"] == "PROTECTED_READ_ONLY"
