# 🛰️ NEXUS // System Architecture & Topology

## Executive Overview
The **Personal Engineering Operating System (NEXUS)** is a centralized, autonomous cloud-native control plane running on Google Cloud Platform project `personal-engineering-os-2026` (Project Number: `582208055065`). It connects mobile interfaces (Android Termux), workstation environments (Ubuntu Dev Box), and Google Cloud into a unified engineering cockpit with strict least privilege and zero-cost guardrails.

## Topology Diagram
```
Phone / Android Node (Termux)
         │  (mTLS / Heartbeat / eco mobile)
         ▼
Ubuntu Local Machine (Workstation / Brain)
         │  (eco CLI / FastAPI Control Engine / Port 8000)
         ▼
Google Cloud Platform (personal-engineering-os-2026)
  ├─ Workload Identity Federation (github-pool / github-provider)
  ├─ Dedicated Service Identities (0 Static Keys)
  ├─ Central Cloud Logging & Audit Engine
  └─ Cloud Run Serverless Container (Free-Tier Boundary: min_instances=0)
```

## System Components
1. **Frontend HUD**: Cyberpunk terminal aesthetic built on React 19, TypeScript, Tailwind CSS, and WebSockets.
2. **Control API**: High-performance FastAPI server providing versioned `/api/v1/...` REST and streaming endpoints.
3. **eco CLI**: Native executable (`/usr/local/bin/eco`) providing operator control, natural language directive routing, and approval resolution.
4. **Policy Engine**: Risk classifier enforcing 4 distinct risk tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
5. **Human Approval Gate**: State-machine intercepting destructive actions, deployments, and IAM alterations before execution.
6. **AI Agent Fleet**: 13 specialized neural workers covering dev, secops, infra, qa, ux, and recovery.
7. **Observability Engine**: OpenTelemetry-compatible tracing with `X-Correlation-ID`, request tracking, and latency metrics.
8. **Project Registry**: Single source of truth for repository telemetry, environments, and health scores.
