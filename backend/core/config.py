import os
from pydantic import BaseModel

class SystemConfig(BaseModel):
    app_name: str = "NEXUS // Personal Engineering OS"
    api_version: str = "v1"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", 8000))
    gcp_project_id: str = "personal-engineering-os-2026"
    gcp_project_number: str = "582208055065"
    gcp_region: str = "asia-south1"
    github_user: str = "knightriderisback"
    base_dir: str = "/root/control-center"
    data_dir: str = "/root/control-center/data"
    secrets_dir: str = "/root/control-center/data/secrets"
    audit_log_file: str = "/root/control-center/data/audit/audit_trail.jsonl"
    projects_file: str = "/root/control-center/data/projects/projects_registry.json"
    policies_file: str = "/root/control-center/data/policies/rules.json"
    approvals_file: str = "/root/control-center/data/approvals.json"
    memory_file: str = "/root/control-center/data/memory_vault.json"
    cost_guard_file: str = "/root/control-center/data/cost_guard.json"
    auth_enabled: bool = os.getenv("NEXUS_AUTH_ENABLED", "false").lower() in ("true", "1")
    api_key_header: str = "X-NEXUS-KEY"
    token_ttl_seconds: int = int(os.getenv("APPROVAL_TTL_SECONDS", "3600"))
    allowed_origins: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

config = SystemConfig()

