"""
GCP Absolute Isolation Adapter.
Strictly monitors existing projects (protyourfolio, whatsapp-autopost-by-termux, gen-lang-client-0352285705)
WITHOUT ever modifying, configuring, deploying to, or migrating them.
"""

from typing import Dict, Any, List
from models.schemas import RiskLevel
from core.audit import record_audit

PROTECTED_LEGACY_PROJECTS = [
    "protyourfolio",
    "whatsapp-autopost-by-termux",
    "gen-lang-client-0352285705"
]

class GCPIsolationAdapter:
    def __init__(self):
        self.protected_projects = PROTECTED_LEGACY_PROJECTS

    def get_isolation_manifest(self) -> List[Dict[str, Any]]:
        """Returns read-only isolation boundaries for protected projects."""
        return [
            {
                "project_id": pid,
                "isolation_status": "PROTECTED_READ_ONLY",
                "policy_enforcement": "STRICT_ISOLATION",
                "write_permitted": False,
                "deploy_permitted": False,
                "notes": "Untouched legacy project. Absolute project isolation guaranteed."
            }
            for pid in self.protected_projects
        ]

    def assert_write_safe(self, target_project_id: str):
        """Raises exception if an action attempts to target a protected legacy project."""
        if target_project_id in self.protected_projects:
            record_audit(
                action="BLOCKED_LEGACY_MUTATION_ATTEMPT",
                project=target_project_id,
                target="Project Isolation Barrier",
                reason="Attempted operation targeted protected legacy GCP project",
                risk_level=RiskLevel.CRITICAL,
                result="DENIED"
            )
            raise PermissionError(
                f"Absolute Isolation Violation: Project '{target_project_id}' is strictly protected and cannot be modified."
            )

gcp_isolation_adapter = GCPIsolationAdapter()
