# 🌐 NEXUS Control API Specification (v1)

FastAPI OpenAPI 3.1 documentation is available at `http://localhost:8000/docs`.

### Core Versioned Endpoints (/api/v1/...)
- `GET /api/v1/overview`: System status, telemetry summary, active agent counts, pending approvals.
- `GET /api/v1/projects`: Registered project inventory with health scores and environment status.
- `POST /api/v1/projects/{id}/audit`: Trigger project audit suite.
- `POST /api/v1/projects/{id}/test`: Run project unit and integration test suite.
- `POST /api/v1/projects/{id}/security`: Run project security and secret scan.
- `POST /api/v1/projects/{id}/deploy`: Request production deployment (intercepted by Approval Gate).
- `GET /api/v1/agents`: List 13 specialized agent manifests and telemetry.
- `POST /api/v1/agents/{id}/dispatch`: Dispatch task to specific agent.
- `GET /api/v1/approvals`: List all approval requests and their status.
- `POST /api/v1/approvals/{id}/decide`: Approve or reject a pending gate.
- `GET /api/v1/policy`: List loaded central policy rules.
- `POST /api/v1/policy/evaluate`: Evaluate risk tier for arbitrary command or target.
- `GET /api/v1/audit`: Query append-only audit trail with secret redaction.
- `GET /api/v1/secrets`: List safe metadata of configured secrets.
- `GET /api/v1/cost/status`: Real-time spend, budget ceiling, and free tier status.
- `GET /api/v1/automations/jobs`: Scheduled operational routines and schedules.
- `POST /api/v1/automations/run/{id}`: Manually trigger an automation job.
- `GET /api/v1/automations/brief`: Morning Engineering Brief in Markdown.
- `GET /api/v1/metrics`: Observability request counters, error rates, and latencies.
- `GET /api/v1/traces`: Distributed trace buffer with correlation and trace IDs.
- `GET /api/v1/integrations/isolated-projects`: Absolute isolation boundary declarations.
- `GET /api/v1/integrations/termux`: Mobile Android node heartbeat and status.
- `POST /api/v1/eco/execute`: Natural language prompt router.
- `WS  /ws`: Real-time 1 Hz telemetry streaming socket.
