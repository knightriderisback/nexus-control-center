"""
Unit and Integration Test Suite for NEXUS Phase 21: Autonomous Software Factory & Product Builder.

Covers:
- PRD & Blueprint Synthesis across Archetypes
- Multi-Tier Workspace Scaffolding
- Fullstack Code Generation (FastAPI, Docker, Specs)
- Dynamic Pytest Generation & Execution
- Autonomous Self-Correction & Repair Loop (Bounded Iterations)
- Security Sentinel & AST Code Audit
- SLSA Level 3 Cryptographic Provenance Attestation
- Closed-Loop Knowledge Learning Feedback (Phase 19 Integration)
- Product Catalog Registration & Query
- FinOps $0.00 Zero-Cost Governance Invariant
- REST API Router Endpoints
"""

import os
import sys
import json
import uuid
import pytest
import tempfile
import shutil
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from models.schemas import (
    ProductArchetype,
    ProductBuildStage,
    ProductBuildState,
    ProductSynthesizeRequest,
    ProductBuildRequest
)
from orchestrator.product_builder_engine import ProductBuilderEngine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine
from server import app

AUTH_HEADERS = {"X-NEXUS-KEY": "nexus-dev-operator-key-2026"}
client = TestClient(app)


@pytest.fixture
def temp_builder():
    """Isolated ProductBuilderEngine instance using a temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="nexus-test-builder-")
    engine = ProductBuilderEngine(data_dir=temp_dir)
    yield engine
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# 1. PRD & BLUEPRINT SYNTHESIS TESTS
# =============================================================================

def test_synthesize_fullstack_blueprint(temp_builder):
    req = ProductSynthesizeRequest(
        prompt="Build a real-time collaborative task board with automated sync",
        archetype=ProductArchetype.FULLSTACK_WEB,
        product_name="task-sync-board"
    )
    spec = temp_builder.synthesize_product_blueprint(req)
    assert spec is not None
    assert spec.spec_id.startswith("spec-")
    assert spec.product_name == "task-sync-board"
    assert spec.archetype == ProductArchetype.FULLSTACK_WEB
    assert len(spec.features) >= 3
    assert len(spec.api_endpoints) >= 3
    assert "FastAPI" in spec.target_stack.get("backend", "")


def test_synthesize_cli_archetype_detection(temp_builder):
    req = ProductSynthesizeRequest(
        prompt="Build a terminal tool for inspecting kubernetes pods and logs"
    )
    spec = temp_builder.synthesize_product_blueprint(req)
    assert spec.archetype == ProductArchetype.CLI_TOOL
    assert spec.product_name != ""


def test_synthesize_ai_agent_archetype(temp_builder):
    req = ProductSynthesizeRequest(
        prompt="Create an autonomous AI agent system for automated pull request code reviews"
    )
    spec = temp_builder.synthesize_product_blueprint(req)
    assert spec.archetype == ProductArchetype.AI_AGENT_SYSTEM


# =============================================================================
# 2. END-TO-END PRODUCT BUILD & SCAFFOLDING TESTS
# =============================================================================

def test_end_to_end_product_build(temp_builder):
    req = ProductBuildRequest(
        prompt="Build an enterprise telemetry metrics ingest API",
        archetype=ProductArchetype.MICROSERVICE_API,
        product_name="metrics-ingest-api",
        auto_repair=True
    )
    build = temp_builder.create_product_build(req)

    assert build is not None
    assert build.build_id.startswith("build-")
    assert build.state == ProductBuildState.COMPLETED
    assert build.current_stage == ProductBuildStage.DELIVERY_VERIFICATION
    assert len(build.components) >= 2

    # Verify workspace files exist
    ws = build.workspace_path
    assert os.path.exists(os.path.join(ws, "backend", "main.py"))
    assert os.path.exists(os.path.join(ws, "tests", "test_product_api.py"))
    assert os.path.exists(os.path.join(ws, "requirements.txt"))
    assert os.path.exists(os.path.join(ws, "Dockerfile"))
    assert os.path.exists(os.path.join(ws, "README.md"))
    assert os.path.exists(os.path.join(ws, "slsa_provenance.json"))

    # Verify test execution results
    assert build.test_results.get("status") == "PASSED"
    assert build.test_results.get("passed", 0) >= 3

    # Verify SLSA Provenance
    assert len(build.provenance_chain_hash) == 16
    assert len(build.slsa_provenance_hash) == 64


def test_dry_run_build_scaffolding_only(temp_builder):
    req = ProductBuildRequest(
        prompt="Fast prototype microservice",
        archetype=ProductArchetype.MICROSERVICE_API,
        dry_run=True
    )
    build = temp_builder.create_product_build(req)
    assert build.state == ProductBuildState.IN_PROGRESS
    assert build.current_stage == ProductBuildStage.SCAFFOLDING


# =============================================================================
# 3. AUTONOMOUS SELF-CORRECTION & REPAIR LOOP
# =============================================================================

def test_manual_repair_cycle(temp_builder):
    req = ProductBuildRequest(
        prompt="Build a resilient cache microservice",
        archetype=ProductArchetype.MICROSERVICE_API
    )
    build = temp_builder.create_product_build(req)
    initial_corrections = len(build.corrections_applied)

    repaired = temp_builder.repair_build(build.build_id, reason="Developer forced self-healing test")
    assert repaired.build_id == build.build_id
    assert len(repaired.corrections_applied) == initial_corrections + 1
    assert repaired.corrections_applied[-1]["reason"] == "Developer forced self-healing test"


# =============================================================================
# 4. SECURITY SENTINEL & AST CODE AUDIT
# =============================================================================

def test_security_sentinel_zero_vulnerabilities(temp_builder):
    req = ProductBuildRequest(
        prompt="Build secure authentication service",
        archetype=ProductArchetype.MICROSERVICE_API
    )
    build = temp_builder.create_product_build(req)
    assert len(build.security_findings) == 0


# =============================================================================
# 5. CLOSED-LOOP KNOWLEDGE LEARNING FEEDBACK (PHASE 19)
# =============================================================================

def test_closed_loop_knowledge_feedback(temp_builder):
    req = ProductBuildRequest(
        prompt="Build data transform engine",
        archetype=ProductArchetype.DATA_PIPELINE,
        product_name="data-transform-engine"
    )
    build = temp_builder.create_product_build(req)

    # Query Phase 19 Knowledge Engine
    results = knowledge_learning_engine.query_knowledge(build.build_id, limit=5)
    assert len(results) >= 1
    assert any("data-transform-engine" in r.title.lower() or build.build_id in r.tags for r in results)


# =============================================================================
# 6. PRODUCT CATALOG & DELIVERY REGISTRATION
# =============================================================================

def test_product_catalog_registration(temp_builder):
    req = ProductBuildRequest(
        prompt="Build catalog test app",
        archetype=ProductArchetype.FULLSTACK_WEB,
        product_name="catalog-test-app"
    )
    build = temp_builder.create_product_build(req)
    catalog = temp_builder.get_catalog()

    assert len(catalog) >= 1
    item = next((c for c in catalog if c["build_id"] == build.build_id), None)
    assert item is not None
    assert item["product_name"] == "catalog-test-app"
    assert item["status"] == "READY_FOR_DEPLOYMENT"
    assert item["slsa_provenance_hash"] == build.slsa_provenance_hash


# =============================================================================
# 7. FINOPS ZERO-COST TELEMETRY
# =============================================================================

def test_finops_zero_cost_invariant(temp_builder):
    telem = temp_builder.get_telemetry()
    assert telem.finops_zero_cost_verified is True


# =============================================================================
# 8. REST API ROUTER ENDPOINTS
# =============================================================================

def test_rest_api_synthesize_endpoint():
    payload = {
        "prompt": "Build a secure REST API for managing IoT device telemetry",
        "archetype": "MICROSERVICE_API",
        "product_name": "iot-telemetry-api"
    }
    res = client.post("/api/v1/product-builder/synthesize", headers=AUTH_HEADERS, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["product_name"] == "iot-telemetry-api"
    assert data["archetype"] == "MICROSERVICE_API"


def test_rest_api_build_endpoint():
    payload = {
        "prompt": "Build a REST customer billing engine",
        "archetype": "MICROSERVICE_API",
        "product_name": "customer-billing-engine"
    }
    res = client.post("/api/v1/product-builder/build", headers=AUTH_HEADERS, json=payload)
    assert res.status_code == 202
    data = res.json()
    assert data["product_name"] == "customer-billing-engine"
    assert data["state"] == "COMPLETED"

    build_id = data["build_id"]

    # Query single build
    get_res = client.get(f"/api/v1/product-builder/builds/{build_id}", headers=AUTH_HEADERS)
    assert get_res.status_code == 200
    assert get_res.json()["build_id"] == build_id

    # List builds
    list_res = client.get("/api/v1/product-builder/builds", headers=AUTH_HEADERS)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_rest_api_catalog_and_health():
    cat_res = client.get("/api/v1/product-builder/catalog", headers=AUTH_HEADERS)
    assert cat_res.status_code == 200
    assert isinstance(cat_res.json(), list)

    health_res = client.get("/api/v1/product-builder/health", headers=AUTH_HEADERS)
    assert health_res.status_code == 200
    h_data = health_res.json()
    assert h_data["status"] == "HEALTHY"
    assert h_data["finops_zero_cost_verified"] is True
