"""
Automated Test Suite for customer-billing-engine
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

# Insert parent path for module discovery
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.main import app, _DATA_STORE

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    _DATA_STORE.clear()
    yield
    _DATA_STORE.clear()


def test_health_check_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["zero_cost_verified"] is True


def test_create_and_get_item_lifecycle():
    # 1. Create item
    payload = {"title": "Automated Unit Test Item", "status": "PENDING"}
    res = client.post("/api/v1/items", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert "id" in created
    assert created["title"] == "Automated Unit Test Item"

    item_id = created["id"]

    # 2. Get item
    get_res = client.get(f"/api/v1/items/{item_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == item_id

    # 3. List items
    list_res = client.get("/api/v1/items")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 4. Delete item
    del_res = client.delete(f"/api/v1/items/{item_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 5. Verify deleted 404
    missing_res = client.get(f"/api/v1/items/{item_id}")
    assert missing_res.status_code == 404


def test_create_item_validation_failure():
    res = client.post("/api/v1/items", json={"title": "   "})
    assert res.status_code == 400
