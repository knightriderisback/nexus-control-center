# Agent Tool Permissions & Role-Based Access Control (RBAC)

## 1. Overview
NEXUS defines a strict Capability Scoping matrix enforcing least-privilege access across all 13 agent personas. Agents are restricted to specific standard tools declared in `backend/orchestrator/tool_registry.py`.

- **RBAC Enforcement**: REAL
- **Tool Permission Validation**: REAL
- **Approval Constraints**: REAL

## 2. Standard Tool Catalog

| Tool ID | Name | Execution Mode | Risk Level | Requires Approval |
| :--- | :--- | :--- | :--- | :--- |
| `filesystem.read` | Filesystem Safe Reader | `read_only` | LOW | No |
| `filesystem.list` | Filesystem Safe Directory Lister | `read_only` | LOW | No |
| `filesystem.write` | Filesystem Sandboxed Writer | `sandboxed` | MEDIUM | Yes |
| `git.status` | Git Status Inspector | `read_only` | LOW | No |
| `git.diff` | Git Diff Extractor | `read_only` | LOW | No |
| `git.branch` | Git Safe Feature Branch Creator | `sandboxed` | MEDIUM | No |
| `git.log` | Git Log Inspector | `read_only` | LOW | No |
| `test.pytest` | Pytest Test Runner | `safe_subprocess` | LOW | No |
| `security.secret_scan` | Secret Leak Scanner | `safe_subprocess` | LOW | No |
| `docs.read` | Memory & Docs Reader | `read_only` | LOW | No |
| `docs.write` | ADR & Documentation Chronicler | `sandboxed` | LOW | No |
| `shell.safe` | Controlled Allowlisted Shell Runner | `safe_subprocess` | HIGH | Yes |
| `codebase_search` | Codebase AST & Content Searcher | `read_only` | LOW | No |

## 3. Agent Persona Permission Profiles

| Agent ID | Persona Name | Permitted Tools | Permitted Operations |
| :--- | :--- | :--- | :--- |
| `agent-research` | RESEARCH-01 | `filesystem.read`, `filesystem.list`, `git.log`, `docs.read`, `codebase_search` | Read-only inspection & code search |
| `agent-dev` | DEVELOPER-02 | `filesystem.read`, `filesystem.list`, `filesystem.write`, `git.status`, `git.diff`, `git.branch`, `git.log`, `test.pytest`, `shell.safe` | Code modification in fixtures, test execution, diffs |
| `agent-qa` | QA-VERIFIER | `filesystem.read`, `filesystem.list`, `git.diff`, `test.pytest` | Automated pytest runner, result parsing |
| `agent-security` | SENTINEL-SEC | `filesystem.read`, `filesystem.list`, `security.secret_scan` | Workspace secret audits & risk classification |
| `agent-docs` | DOC-CHRONICLER | `filesystem.read`, `filesystem.list`, `docs.read`, `docs.write` | Architecture Decision Record authoring |
| `agent-devops` | DEVOPS-RUNNER | `filesystem.read`, `filesystem.list`, `git.status`, `git.log`, `shell.safe` | CI/CD inspection; safe shell requires approval |
| `agent-infra` | INFRA-ENGINEER | `filesystem.read`, `git.status` | IaC configuration audit (read-only) |
| `agent-data` | DATA-CATALYST | `filesystem.read`, `filesystem.list`, `docs.read` | Data schema & vault queries |
| `agent-ux` | UX-TACTICIAN | `filesystem.read`, `filesystem.list` | UI component inspection |
| `agent-seo` | SEO-AMPLIFIER | `filesystem.read`, `filesystem.list` | Metadata inspection |
| `agent-cost` | COST-OPTIMIZER | `filesystem.read` | Resource plan inspection & $0.00 guardrails |
| `agent-mon` | METRICS-PROBER | `filesystem.read` | System metrics & socket inspection |
| `agent-recovery` | RECOVERY-GUARDIAN | `filesystem.read`, `git.status`, `git.log` | Repository health & rollback readiness |
