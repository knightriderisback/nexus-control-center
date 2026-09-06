"""
NEXUS Core Secret Manager Interface.
Provides secure, tiered secret resolution:
1. Process Environment Variables
2. GCP Secret Manager (When enabled & configured)
3. Safe Mock/Template fallback (Zero-cost & isolation safe)

Never logs, prints, or exposes raw secret values in exception messages or audit logs.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from core.config import config
from core.audit import record_audit
from models.schemas import RiskLevel

logger = logging.getLogger("nexus.secrets")

class SecretManager:
    """Least-privilege secret accessor with automated redaction."""

    def __init__(self):
        self.project_id = config.gcp_project_id
        self.template_path = os.path.join(config.base_dir, "data", "secrets", "secrets.template.json")
        self._template_cache = self._load_template()

    def _load_template(self) -> Dict[str, Any]:
        if os.path.exists(self.template_path):
            try:
                with open(self.template_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load secrets template: {e}")
        return {"secrets": {}}

    def mask_value(self, val: Optional[str]) -> str:
        """Returns safe masked representation of a secret string."""
        if not val:
            return "[UNSET]"
        if len(val) <= 6:
            return "******"
        return f"{val[:2]}****{val[-3:]}"

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieves a secret safely.
        Logs an audit trace of secret access without printing the value.
        """
        # 1. Environment Variable check
        env_val = os.getenv(name)
        if env_val:
            self._audit_access(name, source="ENVIRONMENT")
            return env_val

        # 2. GCP Secret Manager check (if not in mock mode and GCP project configured)
        if not os.getenv("USE_MOCK_SECRETS", "false").lower() in ("true", "1") and self.project_id:
            try:
                from google.cloud import secretmanager
                client = secretmanager.SecretManagerServiceClient()
                secret_id = name.lower().replace("_", "-")
                name_path = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
                response = client.access_secret_version(request={"name": name_path})
                val = response.payload.data.decode("UTF-8")
                self._audit_access(name, source="GCP_SECRET_MANAGER")
                return val
            except Exception:
                # Graceful fallback - do not crash if Secret Manager is not enabled or permission denied
                pass

        # 3. Default fallback
        if default is not None:
            return default

        return None

    def is_configured(self, name: str) -> bool:
        """Check if secret exists without retrieving payload."""
        if os.getenv(name):
            return True
        return False

    def list_secrets_metadata(self) -> List[Dict[str, Any]]:
        """List metadata for all known system secrets without leaking values."""
        results = []
        known_secrets = self._template_cache.get("secrets", {})

        for sec_name, meta in known_secrets.items():
            configured = self.is_configured(sec_name)
            results.append({
                "name": sec_name,
                "secret_id": meta.get("secret_id", sec_name.lower().replace("_", "-")),
                "description": meta.get("description", ""),
                "configured": configured,
                "status": "CONFIGURED" if configured else "PENDING_SETUP",
                "source": "ENVIRONMENT" if os.getenv(sec_name) else "UNRESOLVED",
                "preview": self.mask_value(os.getenv(sec_name)) if configured else "[UNSET]"
            })
        return results

    def _audit_access(self, secret_name: str, source: str):
        record_audit(
            action="SECRET_ACCESS",
            project=self.project_id,
            target=secret_name,
            reason=f"Resolved secret from {source}",
            risk_level=RiskLevel.LOW,
            result="AUTHORIZED"
        )

# Central Singleton
secret_manager = SecretManager()
