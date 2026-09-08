# Sandbox Escape & Filesystem Boundary Audit

## 1. Boundary Architecture Truth
- **Level**: Application-level execution boundary.
- **Root Model**: The backend control plane runs as user `root` on Linux host.
- **Jailing Mechanism**: Canonical path resolution (`os.path.realpath`), symlink traversal detection, directory boundary checks, and strict parameter validation.
- **Reality Notice**: This is **NOT** a kernel seccomp, gVisor, or containerized cgroup sandbox. Any claim of a hardware or kernel hypervisor sandbox is FALSE.

---

## 2. Escape Vectors Tested

### 2.1 Directory Traversal Probes
- Traversal payloads (`../../../etc/passwd`, `/root/control-center/../../etc/shadow`) evaluated across `filesystem.read`, `filesystem.write`, and `SafeCommandExecutor`.
- Result: Canonical path resolution identifies escapes outside `ALLOWED_ROOTS` (`/root/control-center`, `/root/portfolio`, `/root/mera_project`).
- Outcome: **BLOCKED / REJECTED**.

### 2.2 Symlink Escape Attacks
- Created fixture symlink pointing from inside `data/fixtures/fixture-workspace` to outside target `/etc/shadow`.
- Result: `os.path.realpath` resolves symlink destination to host `/etc/shadow`, violating boundary check.
- Outcome: **BLOCKED**.

### 2.3 Null-Byte Injection
- Injected `\x00` characters into filesystem paths (`/root/control-center/..\x00/etc`).
- Result: Explicit null byte rejection prior to system calls.
- Outcome: **BLOCKED**.

### 2.4 Environment Variable Stripping
- Subprocesses executed via `SafeCommandExecutor` scrub dangerous variables (`LD_PRELOAD`, `LD_LIBRARY_PATH`, credential variables).
- Outcome: **VERIFIED**.

---

## 3. Capability Status

| Capability | Status | Notes |
| :--- | :--- | :--- |
| Path Canonicalization & Jailing | REAL | Application-level via `os.path.realpath` |
| Symlink Escape Resistance | REAL | Verified against `/etc` pointer |
| Null-Byte Sanitation | REAL | Checked before filesystem calls |
| Kernel Container / gVisor Isolation | NOT_IMPLEMENTED | Host process execution only |
