# Agent Reality & Implementation Matrix

## 1. Fleet Inventory Status (13 Agents)

Every agent manifest has been audited against real local execution capability.

| Agent ID | Persona Name | Declared Risk | Autonomous Lifecycle | Actual Execution Mode | Implementation Truth |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `agent-research` | RESEARCH-01 | LOW | INSPECT -> SEARCH | REAL | Real AST & filesystem search on host |
| `agent-dev` | DEVELOPER-02 | MEDIUM | 9-Step Full Cycle + Rollback | REAL | Real fixture git branch, edit, test & diff |
| `agent-qa` | QA-VERIFIER | LOW | INSPECT -> PYTEST -> PARSE | REAL | Real pytest runner & structured parsing |
| `agent-security` | SENTINEL-SEC | HIGH | REGEX -> CORS -> DEP | REAL | Real multi-pattern secret scanner |
| `agent-docs` | DOC-CHRONICLER | LOW | INSPECT -> WRITE -> DIFF | REAL | Real ADR creation & docs jailing |
| `agent-devops` | DEVOPS-RUNNER | HIGH | Task Dispatch | PARTIAL | Safe shell command runner; Cloud Run NOT deployed |
| `agent-infra` | INFRA-ENGINEER | CRITICAL | Step-by-Step | SIMULATED | GCP billing unlinked ($0.00 spend guardrail) |
| `agent-data` | DATA-CATALYST | HIGH | Query Vault | REAL | Local JSON memory vault query |
| `agent-ux` | UX-TACTICIAN | LOW | UI Audit | PARTIAL | Local React frontend verified via Vite |
| `agent-seo` | SEO-AMPLIFIER | LOW | Meta Audit | PARTIAL | Local HTML parser |
| `agent-cost` | COST-OPTIMIZER | LOW | Billing Guard | REAL | Local zero-cost guardrail & plan evaluation |
| `agent-mon` | METRICS-PROBER | LOW | Host Telemetry | REAL | Real `/proc` CPU, RAM, & disk telemetry |
| `agent-recovery` | RECOVERY-GUARDIAN | HIGH | State Recovery | PARTIAL | Git rollback logic verified in fixture |

---

## 2. Summary Counts
- **REAL**: 8 agents
- **PARTIAL**: 4 agents
- **SIMULATED**: 1 agent (`agent-infra`)
- **NOT_IMPLEMENTED**: 0 agents (all manifests exist and have defined lifecycles or handlers)
