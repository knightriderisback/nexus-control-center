from fastapi import APIRouter
from typing import List, Dict, Any
import json
import os
from core.config import config
from models.schemas import RiskLevel
from core.audit import record_audit

router = APIRouter(prefix="/docs", tags=["Documentation & Knowledge Matrix"])

DEFAULT_DOCS = [
    {
        "id": "adr-001",
        "title": "ADR 001: Centralized Personal Engineering OS Architecture",
        "category": "Architecture",
        "tags": ["control-plane", "nexus", "eco", "cloud-run"],
        "content": "Establishes NEXUS Control Center + eco CLI connected to a unified FastAPI Control API. Enforces zero-trust keyless security and least-privilege service accounts on personal-engineering-os-2026."
    },
    {
        "id": "adr-002",
        "title": "ADR 002: Keyless Workload Identity Federation with GitHub Actions",
        "category": "Security",
        "tags": ["iam", "workload-identity", "github-actions", "oidc"],
        "content": "All CI/CD deployments must authenticate using Google Cloud Workload Identity Federation (github-pool / github-provider) with an assertion.repository_owner condition. Generation of static service account JSON keys is strictly prohibited."
    },
    {
        "id": "adr-003",
        "title": "ADR 003: Policy Engine and Human-in-the-Loop Approval Gates",
        "category": "Governance",
        "tags": ["policy-engine", "approvals", "safety", "risk-tiers"],
        "content": "Actions classified as HIGH or CRITICAL risk (production deployments, IAM changes, billing changes, destructive drops) require explicit human approval via the HUD or eco CLI before execution."
    }
]

def load_docs() -> List[Dict[str, Any]]:
    if not os.path.exists(config.memory_file):
        with open(config.memory_file, "w") as f:
            json.dump(DEFAULT_DOCS, f, indent=2)
        return DEFAULT_DOCS
    try:
        with open(config.memory_file, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_DOCS

@router.get("")
def list_documentation() -> List[Dict[str, Any]]:
    return load_docs()
