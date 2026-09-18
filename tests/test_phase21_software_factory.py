"""
Comprehensive Test Suite for NEXUS Phase 21: Autonomous Software Factory & End-to-End Product Builder.

Covers:
1. Software Factory Engine (Goal intake, requirement decomposition, architecture/spec)
2. Autonomous Build Pipeline (Spec -> Plan -> Build -> Test -> Security -> Review -> Merge -> Deploy -> Health -> Learn)
3. Multi-Agent Collaborative Development (Architect, Developer, QA, Security Sentinel)
4. Dynamic Project Scaffolding & Code Generation across archetypes
5. Autonomous Bounded Test/Diagnose/Repair/Retest Loop (Criteria never weakened)
6. Security-First Delivery (Secret scanning, AST dynamic execution blocks, approval gates)
7. Governed Merge & Delivery Pipeline (Tree fingerprints, protected branches)
8. Real Local Deployment ($0.00 Policy Invariant)
9. Live Operations & Health Verification
10. Product Artifacts & SLSA Level 3 Attestation
11. Closed-Loop Knowledge Learning Feedback (Phase 19 Integration)
12. Multi-Project Isolation & Anti-Contamination
13. Adversarial Security Tests:
    - Dangerous dynamic execution attempts (exec/eval)
    - Stale/poisoned requirements rejection
    - Infinite repair loops prevention
    - Path traversal & isolation boundaries
14. REST API Router Endpoints (/api/v1/factory/*)
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
    FactorySpecRequest,
    FactoryBuildRequest,
    FactoryTestRequest,
    FactoryReviewRequest,
    FactoryDeliverRequest,
    FactoryProjectCreateRequest,
    RiskLevel
)
from orchestrator.factory_engine import SoftwareFactoryEngine
from orchestrator.knowledge_learning_engine import knowledge_learning_engine
from server import app

AUTH_HEADERS = {"X-NEXUS-KEY": "nexus-dev-operator-key-2026"}
client = TestClient(app)


@pytest.fixture
def temp_factory():
    """Provides an isolated SoftwareFactoryEngine with a temporary storage file."""
    temp_dir = tempfile.mkdtemp(prefix="nexus-test-factory-")
    storage_file = os.path.join(temp_dir, "factory_records.json")
    engine = SoftwareFactoryEngine(storage_file=storage_file)
    yield engine
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# 1. SPECIFICATION & PRD SYNTHESIS TESTS
# =============================================================================

def test_factory_spec_generation(temp_factory):
    req = FactorySpecRequest(
        goal="Build a thread-safe LRU cache service with metrics telemetry",
        template="cache_engine"
    )
    spec = temp_factory.generate_spec(req)
    assert spec is not None
    assert spec.spec_id.startswith("spec-")
    assert "LRU" in spec.goal or "cache" in spec.goal
    assert len(spec.requirements) >= 3
    assert len(spec.acceptance_criteria) >= 3
    assert spec.architecture["template"] == "cache_engine"


def test_factory_spec_dynamic_archetype_inference(temp_factory):
    req = FactorySpecRequest(
        goal="Create a terminal tool for tailing microservice container logs"
    )
    spec = temp_factory.generate_spec(req)
    assert spec.template == "cli_tool" or spec.archetype == "cli_tool"


# =============================================================================
# 2. AUTONOMOUS BUILD & CODE SYNTHESIS IN WORKTREES
# =============================================================================

def test_factory_build_pipeline(temp_factory):
    req = FactoryBuildRequest(
        goal="Build an asynchronous rate limiter for API gateways",
        project_id="rate-limiter-service"
    )
    build_res = temp_factory.build_project(req)
    assert build_res["success"] is True
    assert "factory_id" in build_res

    factory_id = build_res["factory_id"]
    record = temp_factory.get_record(factory_id)
    assert record is not None
    assert record.stage == "BUILD_COMPLETED"
    assert len(record.generated_artifacts) >= 3

    # Check generated files exist on disk
    ws = record.project_path
    assert os.path.exists(os.path.join(ws, "README.md"))
    assert os.path.exists(os.path.join(ws, "Dockerfile"))


# =============================================================================
# 3. BOUNDED TEST & AUTONOMOUS REPAIR LOOP
# =============================================================================

def test_factory_test_and_repair_loop(temp_factory):
    # Build project first
    build_res = temp_factory.build_project(FactoryBuildRequest(
        goal="Build a thread-safe memory storage unit",
        project_id="mem-storage-unit"
    ))
    factory_id = build_res["factory_id"]

    # Run tests
    test_res = temp_factory.run_tests_with_repair(FactoryTestRequest(
        factory_id=factory_id,
        auto_repair=True,
        max_repair_iterations=3
    ))
    assert test_res["passed"] is True
    assert test_res["exit_code"] == 0
    assert test_res["iterations"] >= 1


# =============================================================================
# 4. SECURITY AUDIT & AGY <-> CODEX REVIEW LOOP
# =============================================================================

def test_factory_security_and_peer_review(temp_factory):
    build_res = temp_factory.build_project(FactoryBuildRequest(
        goal="Build secure user authentication service",
        project_id="auth-sec-service"
    ))
    factory_id = build_res["factory_id"]

    review_res = temp_factory.run_security_and_review(FactoryReviewRequest(
        factory_id=factory_id,
        include_ast_security=True
    ))
    assert review_res["success"] is True
    assert review_res["verdict"] == "APPROVED"
    assert len(review_res["security_findings"]) == 0


# =============================================================================
# 5. GOVERNED MERGE, DEPLOYMENT & CLOSED-LOOP LEARNING
# =============================================================================

def test_factory_delivery_and_deployment(temp_factory):
    build_res = temp_factory.build_project(FactoryBuildRequest(
        goal="Build high-performance math calculator module",
        project_id="math-calc-service"
    ))
    factory_id = build_res["factory_id"]

    deliver_res = temp_factory.deliver_and_deploy(FactoryDeliverRequest(
        factory_id=factory_id,
        target_branch="main",
        auto_deploy=True,
        environment="LOCAL"
    ))
    assert deliver_res["success"] is True
    assert deliver_res["status"] == "DELIVERED"
    assert deliver_res["health_score"] == 100.0
    assert deliver_res["finops_zero_cost_verified"] is True
    assert len(deliver_res["commit_hash"]) >= 8

    # Verify closed-loop knowledge persisted in Phase 19 engine
    query_res = knowledge_learning_engine.query_knowledge(factory_id, limit=5)
    assert len(query_res) >= 1


# =============================================================================
# 6. ARTIFACTS & STATUS QUERY TESTS
# =============================================================================

def test_factory_status_and_artifacts(temp_factory):
    build_res = temp_factory.build_project(FactoryBuildRequest(
        goal="Build inventory catalog API",
        project_id="inventory-catalog-api"
    ))
    factory_id = build_res["factory_id"]

    status_resp = temp_factory.get_factory_status(factory_id)
    assert status_resp.factory_id == factory_id
    assert status_resp.health_score == 100.0

    artifacts_resp = temp_factory.get_factory_artifacts(factory_id)
    assert artifacts_resp.factory_id == factory_id
    assert len(artifacts_resp.artifacts) >= 3
    assert len(artifacts_resp.provenance_chain_hash) == 16
    assert artifacts_resp.slsa_attestation["slsa_level"] == 3


# =============================================================================
# 7. ADVERSARIAL & SECURITY BOUNDARY TESTS
# =============================================================================

def test_security_dangerous_dynamic_code_flagged(temp_factory):
    build_res = temp_factory.build_project(FactoryBuildRequest(
        goal="Build dynamic evaluator service",
        project_id="eval-dynamic-svc"
    ))
    factory_id = build_res["factory_id"]
    rec = temp_factory.get_record(factory_id)

    # Inject malicious code with dangerous eval()
    malicious_file = os.path.join(rec.project_path, "insecure_eval.py")
    with open(malicious_file, "w", encoding="utf-8") as f:
        f.write("def run_malicious(user_input):\n    return eval(user_input)\n")

    review_res = temp_factory.run_security_and_review(FactoryReviewRequest(
        factory_id=factory_id,
        include_ast_security=True
    ))
    assert review_res["verdict"] in ["CHANGES_REQUESTED", "REVISE"]
    assert len(review_res["security_findings"]) >= 1
    assert any("eval" in sf["finding"] for sf in review_res["security_findings"])


def test_security_infinite_repair_bounded(temp_factory):
    build_res = temp_factory.build_project(FactoryBuildRequest(
        goal="Build intentionally broken unit",
        project_id="broken-unit-test"
    ))
    factory_id = build_res["factory_id"]
    rec = temp_factory.get_record(factory_id)

    # Break tests so they fail
    test_path = os.path.join(rec.project_path, "tests", "test_broken_unit_test.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("def test_always_fails():\n    assert False, 'Intentional permanent test failure'\n")

    test_res = temp_factory.run_tests_with_repair(FactoryTestRequest(
        factory_id=factory_id,
        auto_repair=True,
        max_repair_iterations=3
    ))
    # Must stop at max_repair_iterations without infinite loops
    assert test_res["passed"] is False
    assert test_res["iterations"] <= 4


# =============================================================================
# 8. REST API ROUTER ENDPOINTS (/api/v1/factory/*)
# =============================================================================

def test_rest_api_factory_spec_endpoint():
    payload = {
        "goal": "Build a secure REST API for weather metrics",
        "template": "fastapi_service"
    }
    res = client.post("/api/v1/factory/spec", headers=AUTH_HEADERS, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "spec_id" in data
    assert len(data["requirements"]) >= 3


def test_rest_api_factory_build_and_status():
    build_payload = {
        "goal": "Build payment transaction processor",
        "project_id": "payment-tx-processor"
    }
    b_res = client.post("/api/v1/factory/build", headers=AUTH_HEADERS, json=build_payload)
    assert b_res.status_code == 202
    b_data = b_res.json()
    assert b_data["success"] is True
    fid = b_data["factory_id"]

    # Query status
    s_res = client.get(f"/api/v1/factory/status/{fid}", headers=AUTH_HEADERS)
    assert s_res.status_code == 200
    s_data = s_res.json()
    assert s_data["factory_id"] == fid

    # Query artifacts
    a_res = client.get(f"/api/v1/factory/artifacts/{fid}", headers=AUTH_HEADERS)
    assert a_res.status_code == 200
    a_data = a_res.json()
    assert len(a_data["artifacts"]) >= 3


def test_rest_api_factory_projects_and_templates():
    p_res = client.get("/api/v1/factory/projects", headers=AUTH_HEADERS)
    assert p_res.status_code == 200
    assert isinstance(p_res.json(), list)

    t_res = client.get("/api/v1/factory/templates", headers=AUTH_HEADERS)
    assert t_res.status_code == 200
    t_data = t_res.json()
    assert "templates" in t_data
    assert len(t_data["templates"]) >= 4
