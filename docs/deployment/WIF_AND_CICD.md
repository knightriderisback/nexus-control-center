# 🚀 Production CI/CD & Workload Identity Federation

## Overview
The CI/CD pipeline runs on GitHub Actions using Google Cloud Workload Identity Federation (WIF). Zero static JSON credentials are used.

## 12-Stage Pipeline Workflow
1. **Code Linting**: Python (`flake8`) and Frontend ESLint.
2. **Type Checking**: TypeScript static type checks.
3. **Unit Tests**: Pytest testing core policy, approvals, secrets, and agents.
4. **Integration Tests**: FastAPI TestClient end-to-end API verification.
5. **Security Scan**: Regex and AST scan detecting unencrypted private keys.
6. **Policy Engine Validation**: Asserts 10 rules loaded and active.
7. **Approval Gate Verification**: Verifies human clearance for production changes.
8. **Container Build**: Multi-stage Docker build targeting Artifact Registry.
9. **Pre-deploy Health Check**: Validates GCP project isolation boundaries.
10. **Keyless Deployment**: Cloud Run deployment with min-instances=0 (Free Tier).
11. **Post-deploy Smoke Test**: Verifies endpoints via `scripts/verify_system.sh`.
12. **Automated Rollback**: Triggers `scripts/rollback.sh` on failure.
