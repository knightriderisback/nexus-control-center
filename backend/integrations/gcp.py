import subprocess
from datetime import datetime
from typing import Dict, Any
from core.config import config

def get_gcp_system_status() -> Dict[str, Any]:
    return {
        "project_id": config.gcp_project_id,
        "project_number": config.gcp_project_number,
        "display_name": "Personal Engineering OS",
        "lifecycle_state": "ACTIVE",
        "region_primary": config.gcp_region,
        "billing": {
            "status": "UNLINKED",
            "guardrail": "Active ($0.00 / month hard zero-incurrence guarantee)",
            "cost_estimate": "$0.00"
        },
        "identity": {
            "service_account": f"nexus-control-sa@{config.gcp_project_id}.iam.gserviceaccount.com",
            "roles": [
                "roles/logging.logWriter",
                "roles/monitoring.metricWriter",
                "roles/iam.workloadIdentityUser"
            ],
            "keys_count": 0,
            "security_posture": "KEYLESS_ZERO_TRUST"
        },
        "workload_identity": {
            "pool": "github-pool",
            "provider": "github-provider",
            "issuer": "https://token.actions.githubusercontent.com",
            "condition": f"assertion.repository_owner == '{config.github_user}'",
            "status": "OPERATIONAL",
            "full_provider_uri": f"projects/{config.gcp_project_number}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
        },
        "enabled_apis": [
            {"name": "iam.googleapis.com", "title": "Identity & Access Management"},
            {"name": "iamcredentials.googleapis.com", "title": "IAM Service Account Credentials"},
            {"name": "cloudresourcemanager.googleapis.com", "title": "Cloud Resource Manager"},
            {"name": "logging.googleapis.com", "title": "Cloud Logging"},
            {"name": "monitoring.googleapis.com", "title": "Cloud Monitoring"},
            {"name": "serviceusage.googleapis.com", "title": "Service Usage"},
            {"name": "bigquery.googleapis.com", "title": "BigQuery"},
            {"name": "cloudtrace.googleapis.com", "title": "Cloud Trace"}
        ],
        "cloud_run_readiness": {
            "dockerfile": "READY (/root/control-center/Dockerfile)",
            "cicd_pipeline": "READY (.github/workflows/deploy-cloud-run.yml)",
            "cloudbuild": "READY (/root/control-center/cloudbuild.yaml)",
            "service_account": f"CONFIGURED (nexus-control-sa@{config.gcp_project_id}.iam.gserviceaccount.com)",
            "federation": "CONFIGURED (github-pool / github-provider)",
            "blockers": [
                "Google Cloud Billing Account must be linked to personal-engineering-os-2026 before run.googleapis.com can be activated"
            ]
        }
    }
