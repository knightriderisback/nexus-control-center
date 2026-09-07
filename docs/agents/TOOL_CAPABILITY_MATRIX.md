# NEXUS Agent Tool Capability Matrix

This document provides the canonical capability, risk, and boundary matrix for all tools available to autonomous agents within the Personal Engineering OS control plane.

## Tool Definitions & Boundary Constraints

| Tool ID | Display Name | Risk Level | Execution Mode | Write Capability | Workspace Restriction | Requires Approval | Timeout | Permitted Agents |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `filesystem.read` | Filesystem Safe Reader | `LOW` | `read_only` | `False` | `workspace_boundary` | `False` | 10s | Research, Dev, Docs, QA |
| `filesystem.list` | Filesystem Safe Lister | `LOW` | `read_only` | `False` | `workspace_boundary` | `False` | 10s | Research, Dev, Data |
| `filesystem.write` | Sandboxed File Writer | `MEDIUM` | `sandboxed` | `True` | `project_workspace` | `True` | 15s | Dev, Docs (restricted to docs/) |
| `git.status` | Git Status Inspector | `LOW` | `read_only` | `False` | `repo_root` | `False` | 10s | Dev, Research, Recovery |
| `git.diff` | Git Diff Extractor | `LOW` | `read_only` | `False` | `repo_root` | `False` | 15s | Dev, QA |
| `git.branch` | Feature Branch Creator | `MEDIUM` | `sandboxed` | `True` | `repo_root` | `False` | 10s | Dev |
| `git.log` | Git Log Inspector | `LOW` | `read_only` | `False` | `repo_root` | `False` | 10s | Dev, Research, Recovery |
| `test.pytest` | Pytest Runner | `LOW` | `safe_subprocess` | `False` | `project_root` | `False` | 60s | QA, Dev |
| `security.secret_scan` | Secret Leak Scanner | `LOW` | `safe_subprocess` | `False` | `target_boundary` | `False` | 30s | Security |
| `docs.read` | Memory Vault Reader | `LOW` | `read_only` | `False` | `memory_vault` | `False` | 10s | Docs, Research |
| `docs.write` | ADR Chronicler | `LOW` | `sandboxed` | `True` | `docs_vault` | `False` | 15s | Docs |
| `shell.safe` | Controlled Safe Shell | `HIGH` | `safe_subprocess` | `True` | `approved_cwd` | `True` | 30s | DevOps, Dev |
| `codebase_search` | AST / Grep Searcher | `LOW` | `read_only` | `False` | `workspace_boundary` | `False` | 15s | Research, Dev |

---

## Agent Role Permission Profiles

| Agent Identifier | Permitted Tools | Write Capable | High-Risk Tools | Enforcement Boundary |
| :--- | :--- | :--- | :--- | :--- |
| `agent-research` | `filesystem.read`, `filesystem.list`, `git.log`, `docs.read`, `codebase_search` | **NO** | None | Read-only across allowed workspaces |
| `agent-dev` | `filesystem.read`, `filesystem.list`, `filesystem.write`, `git.status`, `git.diff`, `git.branch`, `git.log`, `test.pytest`, `shell.safe` | **YES** | `shell.safe` | Blocked from `backend/core/`; jailable to fixture |
| `agent-qa` | `filesystem.read`, `filesystem.list`, `git.diff`, `test.pytest` | **NO** | None | Read-only inspection + safe subprocess test run |
| `agent-security` | `filesystem.read`, `filesystem.list`, `security.secret_scan` | **NO** | None | Read-only regex audit + key discovery |
| `agent-docs` | `filesystem.read`, `filesystem.list`, `docs.read`, `docs.write` | **YES** (Docs only) | None | Jailed to `docs/` and `.md` files; blocked from code |
| `agent-devops` | `filesystem.read`, `filesystem.list`, `git.status`, `git.log`, `shell.safe` | **YES** | `shell.safe` | Gated by human approval engine |
| `agent-data` | `filesystem.read`, `filesystem.list`, `docs.read` | **NO** | None | Read-only vault query |
| `agent-infra` | `filesystem.read`, `git.status` | **NO** | None | Read-only configuration review |
| `agent-recovery` | `filesystem.read`, `git.status`, `git.log` | **NO** | None | Read-only git inspection |
| `agent-ux` | `filesystem.read`, `filesystem.list` | **NO** | None | Read-only frontend inspection |
| `agent-seo` | `filesystem.read`, `filesystem.list` | **NO** | None | Read-only metadata inspection |
| `agent-cost` | `filesystem.read` | **NO** | None | Read-only billing/cost file inspect |
| `agent-mon` | `filesystem.read` | **NO** | None | Read-only log inspection |

---

## Machine-Readable JSON Export

The full machine-readable capability matrix is exported and verified in:
[`data/tool_capability_matrix.json`](file:///root/control-center/data/tool_capability_matrix.json)
