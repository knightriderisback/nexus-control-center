# ADR 001: Architecture of the Personal Engineering OS (NEXUS)

## Context
A centralized engineering control plane was needed to orchestrate multiple distributed environments: Android (Termux), local workstation (Ubuntu), and cloud (GCP).

## Decision
1. Dedicated GCP Project `personal-engineering-os-2026` serves as the immutable root for the Personal Engineering OS.
2. Complete isolation for existing projects (`protyourfolio`, `whatsapp-autopost-by-termux`, `gen-lang-client-0352285705`).
3. Keyless Workload Identity Federation for all cloud access.
4. FastAPI backend with OpenAPI documentation, distributed tracing, and audit logs.
5. Multi-agent swarm with provider-agnostic adapters and deterministic fallbacks.
6. Central policy engine with 4 risk tiers and mandatory human approval gates for HIGH/CRITICAL actions.
