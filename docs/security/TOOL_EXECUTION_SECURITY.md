# Controlled Tool Execution & Sandboxing Security

## 1. Scope & Reality
This document defines the security architecture and isolation mechanisms enforced by the NEXUS `SafeCommandExecutor` and `ToolRegistry`.

- **Controlled Execution Layer**: REAL
- **Binary Allowlisting**: REAL
- **Path Traversal Defense**: REAL
- **Shell Injection Rejection**: REAL
- **Environment Scrubbing**: REAL
- **Kernel Container Sandbox**: NOT_IMPLEMENTED (Application-level sandbox only; full OS/cgroup isolation deferred to container phase)

## 2. Safe Subprocess Execution Engine (`SafeCommandExecutor`)

All shell commands and binary executions pass through `backend/orchestrator/safe_runner.py`.

### 2.1. Strict Binary Allowlisting
Only the following binaries are permitted for execution:
- `git`
- `pytest`
- `python3` / `python`
- `grep`
- `ls`
- `cat`
- `echo`
- `find`

Attempts to run unapproved binaries (e.g., `bash`, `sh`, `curl`, `wget`, `nc`, `rm`, `sudo`) are rejected with `PermissionError` and logged to the security audit trail.

### 2.2. Directory Boundary & Path Traversal Protection
Execution is strictly restricted to designated workspace roots:
- `/root/control-center`
- `/root/portfolio`
- `/root/mera_project`
- `/tmp`

The executor validates:
1. `cwd` is resolved via `os.path.realpath` and verified against allowed roots.
2. Arguments containing `..` or leading slashes are verified to ensure they do not traverse outside workspace boundaries.
3. Path traversal attempts immediately trigger a security fault and audit event.

### 2.3. Shell Injection Elimination
Commands are invoked using structured argument arrays (`List[str]`) directly with `shell=False`.
Furthermore, arguments are scanned for dangerous shell chaining and interpolation characters:
- `;`
- `&&`
- `||`
- `|`
- `` ` ``
- `$(`
- `${`
- `>`
- `<`
- `\n`, `\r`

If any argument contains these sequences, execution is rejected before spawning a process.

### 2.4. Environment Scrubbing
The execution environment is sanitized before passing to `subprocess.Popen`:
- Dangerous variables (`LD_PRELOAD`, `PYTHONPATH`, `IFS`, `BASH_ENV`) are stripped.
- Sensitive environment keys (`GCP_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are removed from agent child processes.

### 2.5. Memory Exhaustion Mitigation
Output capture from `stdout` and `stderr` is capped at 500 KB (`MAX_OUTPUT_SIZE`). Any excessive output is safely truncated to prevent buffer flooding.
