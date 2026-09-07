# NEXUS Agent Isolation & Execution Boundaries

## Overview
This architectural document details the multi-layered isolation model governing autonomous agent executions within the Personal Engineering OS.

> [!NOTE]
> Isolation is enforced at the **application layer** using Role-Based Access Control (RBAC), filesystem realpath verification, persona path restrictions, and process group containment. It does not replace containerized or virtualized sandbox environments for untrusted multi-tenant workloads.

---

## 1. Filesystem Boundary Isolation

### 1.1 Canonical Root Verification (`is_safe_path`)
All filesystem interactions (reading, listing, writing) resolve target paths through `os.path.realpath(os.path.abspath(path))`. This guarantees that:
- Directory traversal sequences (`../../`) cannot escape the allowed perimeter.
- Workspace-internal symlinks pointing to sensitive host locations (`/etc`, `/root`, `/var`) are caught and blocked upon canonical target evaluation.
- Null-byte injections (`\x00`) are blocked before filesystem system calls.

### 1.2 Dedicated Workspace Scoping (`workspace_root`)
When a task is assigned to a specific workspace or fixture:
- All relative paths are evaluated relative to `workspace_root`.
- Absolute paths must reside inside the canonical `workspace_root` tree.
- Empirical testing on `data/fixtures/fixture-workspace` proves that:
  - Reading `allowed.txt` and `sub/nested.txt` succeeds.
  - Attempting to read `../fixture-outside/forbidden.txt` via relative path fails.
  - Attempting to access `/root/control-center/data/fixtures/fixture-outside/` via absolute path fails.
  - Attempting to access outside files via symlink `symlink_outside` fails.
  - Listing or writing outside `workspace_root` fails.

---

## 2. Agent Persona Scoping & RBAC Rules

| Agent Persona | Role | Read Scope | Write Scope | Prohibited Actions |
| :--- | :--- | :--- | :--- | :--- |
| `agent-research` | Codebase & AST Researcher | Permitted workspaces | None | All file writes and shell execution |
| `agent-dev` | Autonomous Developer | Permitted workspaces & fixtures | Design-approved project workspaces | Direct modification of `backend/core/*` |
| `agent-qa` | Automated QA Verifier | Permitted workspaces | None | File modifications, shell execution |
| `agent-security`| Vulnerability Sentinel | Permitted workspaces | None | File modifications, command execution |
| `agent-docs` | Documentation Chronicler| Permitted workspaces | `docs/` and `*.md` files only | Modification of application code or configs |

### Persona Jailing Details
- **Developer Agent Jailing**: Any attempt by `agent-dev` to write directly to `backend/core/` is blocked at the runner level with:
  `Agent-dev is forbidden from directly modifying core control plane files`
- **Documentation Agent Jailing**: Any attempt by `agent-docs` to modify non-markdown or non-docs files is blocked with:
  `Agent-docs is restricted to authoring documentation files in docs/ only`
- **Read-Only Personas**: `agent-research`, `agent-qa`, `agent-security`, `agent-data`, `agent-infra`, `agent-recovery`, `agent-ux`, `agent-seo`, `agent-cost`, `agent-mon` have zero write capabilities in their permission profiles. Calls to `filesystem.write` fail authorization before execution.

---

## 3. Subprocess & Environment Isolation

### 3.1 Process Group Management
Every subprocess spawned by `SafeCommandExecutor` runs with:
- `start_new_session=True`: Spawns the child in an independent process group.
- `close_fds=True`: Prevents leaking host file descriptors.
- Group termination: In case of timeout or cancellation, `os.killpg(os.getpgid(proc.pid), signal.SIGKILL)` terminates the entire process tree, leaving zero orphaned processes.

### 3.2 Environment Variable Scrubbing
Processes do not inherit raw environment variables. `sanitize_environment()` performs two tiers of scrubbing:
1. **Deny-listed Injection Variables**: Strips `LD_PRELOAD`, `LD_LIBRARY_PATH`, `BASH_ENV`, `IFS`, `SHELLOPTS`, `PS4`.
2. **Credential Scrubbing**: Strips any environment key matching `KEY`, `SECRET`, `TOKEN`, `PASS`, or `CRED`.
