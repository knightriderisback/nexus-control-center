# 🛡️ Least Privilege IAM & Secret Security Architecture

## Core Principles
1. **Zero Static JSON Keys**: Under NO circumstances are service account keys generated, stored, or committed.
2. **Keyless GitHub Actions Authentication**: GitHub CI/CD uses Google Cloud Workload Identity Federation with strict repository owner validation:
   - Pool: `projects/582208055065/locations/global/workloadIdentityPools/github-pool`
   - Provider: `projects/582208055065/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
   - Condition: `assertion.repository_owner == 'knightriderisback'`
3. **Strict Separation of Service Identities**:
   - `nexus-control-sa`: Runtime identity (`logging.logWriter`, `monitoring.metricWriter`, `workloadIdentityUser`).
   - `nexus-deploy-sa`: CI/CD deployment identity bound to WIF.
   - `nexus-agent-sa`: Agent execution identity (`logging.logWriter`).
   - `nexus-monitor-sa`: Observability telemetry writer (`monitoring.metricWriter`).
4. **Absolute Project Isolation**:
   - Existing legacy projects (`protyourfolio`, `whatsapp-autopost-by-termux`, `gen-lang-client-0352285705`) are classified as `PROTECTED_READ_ONLY`. All write operations are strictly blocked by Policy Rule `pol-000`.
5. **Secret Resolution Hierarchy**:
   - Environment variables (`.env`) -> GCP Secret Manager -> Safe Template Mock.
   - Values are masked dynamically in logs and APIs.
