"""
NEXUS Controlled Safe Subprocess Execution Engine.
Enforces strict binary allowlisting, argument sanitization, directory boundaries,
environment isolation, and audit emission for all agent subprocess executions.

Notice: This is a controlled execution layer and application sandbox,
not a full virtualization/kernel container sandbox.
"""

import os
import re
import uuid
import subprocess
from typing import List, Dict, Any, Optional
from core.audit import record_audit
from models.schemas import RiskLevel

ALLOWED_BINARIES = {
    "git",
    "pytest",
    "python3",
    "python",
    "grep",
    "ls",
    "cat",
    "echo",
    "find"
}

ALLOWED_ROOTS = [
    "/root/control-center",
    "/root/projects",
    "/root/portfolio",
    "/root/mera_project",
    "/tmp"
]

DANGEROUS_ARG_CHARS = [";", "&&", "||", "|", "`", "$(", "${", ">", "<", "\n", "\r"]
MAX_OUTPUT_SIZE = 500_000 # 500 KB limit to prevent memory exhaustion

class CommandExecutionResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int, duration_ms: float = 0.0, execution_id: Optional[str] = None):
        self.execution_id = execution_id or f"exec-{uuid.uuid4().hex[:8]}"
        self.stdout = stdout[:MAX_OUTPUT_SIZE]
        self.stderr = stderr[:MAX_OUTPUT_SIZE]
        self.exit_code = exit_code
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "success": self.exit_code == 0
        }

def is_safe_cwd(cwd: str) -> bool:
    """Validates that working directory is within allowed workspace boundaries, resolving symlinks."""
    if not cwd or not isinstance(cwd, str):
        return False
    real_cwd = os.path.realpath(os.path.abspath(cwd))
    real_roots = [os.path.realpath(r) for r in ALLOWED_ROOTS]
    return any(real_cwd == r or real_cwd.startswith(r + "/") for r in real_roots)

def sanitize_environment(env_override: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Creates a clean environment dict scrubbing secrets, credentials, and injection vectors."""
    safe_keys = {"PATH", "LANG", "LC_ALL", "HOME", "USER", "TERM", "TMPDIR", "PYTHONIOENCODING"}
    clean_env = {}
    for k, v in os.environ.items():
        if k in safe_keys:
            clean_env[k] = v

    raw_pythonpath = os.environ.get("PYTHONPATH", "")
    if raw_pythonpath:
        approved_parts = [
            p for p in raw_pythonpath.split(":")
            if any(os.path.realpath(p).startswith(os.path.realpath(r)) for r in ALLOWED_ROOTS)
        ]
        if approved_parts:
            clean_env["PYTHONPATH"] = ":".join(approved_parts)

    if env_override:
        dangerous_vars = {"LD_PRELOAD", "LD_LIBRARY_PATH", "BASH_ENV", "IFS", "SHELLOPTS", "PS4"}
        for k, v in env_override.items():
            if k.upper() in dangerous_vars:
                continue
            if any(secret_term in k.upper() for secret_term in ["KEY", "SECRET", "TOKEN", "PASS", "CRED"]):
                continue
            clean_env[k] = v

    return clean_env

Tuple_Validation = tuple[bool, Optional[str]]

def validate_command(cmd_args: List[str], cwd: str) -> Tuple_Validation:
    if not cmd_args or not isinstance(cmd_args, list):
        return False, "Command arguments must be a non-empty list of strings"

    binary = os.path.basename(cmd_args[0])
    if binary not in ALLOWED_BINARIES:
        return False, f"Binary '{binary}' is not permitted by command allowlist. Permitted: {sorted(list(ALLOWED_BINARIES))}"

    if not is_safe_cwd(cwd):
        return False, f"Working directory '{cwd}' is outside permitted workspace roots: {ALLOWED_ROOTS}"

    for arg in cmd_args:
        if not isinstance(arg, str):
            return False, f"Invalid argument type: {type(arg)}"

        if "\x00" in arg:
            return False, f"Null byte '\\x00' detected in argument: {arg}"

        for dangerous in DANGEROUS_ARG_CHARS:
            if dangerous in arg:
                return False, f"Dangerous shell character '{dangerous}' detected in argument: {arg}"

        # Path traversal checks
        if ".." in arg and ("../" in arg or "/.." in arg or arg == ".."):
            return False, f"Path traversal attempt '..' detected in argument: {arg}"

        # Check absolute path argument does not escape allowed roots (including via symlinks)
        if arg.startswith("/") and not arg.startswith("--"):
            real_arg = os.path.realpath(arg)
            real_roots = [os.path.realpath(r) for r in ALLOWED_ROOTS]
            if not any(real_arg == r or real_arg.startswith(r + "/") for r in real_roots):
                return False, f"Path '{arg}' escapes permitted workspace boundaries: {ALLOWED_ROOTS}"

    return True, None

class SafeCommandExecutor:
    """Safely executes allowlisted commands with timeout, process group isolation, and directory checks."""

    @staticmethod
    def execute(
        cmd_args: List[str],
        cwd: str = "/root/control-center",
        timeout: int = 30,
        env_override: Optional[Dict[str, str]] = None,
        actor: str = "safe_runner",
        execution_id: Optional[str] = None
    ) -> CommandExecutionResult:
        exec_id = execution_id or f"exec-{uuid.uuid4().hex[:8]}"

        is_valid, err_msg = validate_command(cmd_args, cwd)
        if not is_valid:
            record_audit(
                action=f"SAFE_EXEC_BLOCKED: {cmd_args[0] if cmd_args else 'unknown'}",
                project="control-center",
                target=cwd,
                reason=err_msg or "SecurityPolicyViolation",
                risk_level=RiskLevel.MEDIUM,
                result="BLOCKED",
                actor=actor,
                execution_id=exec_id
            )
            return CommandExecutionResult(
                stdout="",
                stderr=f"SecurityPolicyViolation: {err_msg}",
                exit_code=126,
                execution_id=exec_id
            )

        if not os.path.exists(cwd):
            return CommandExecutionResult(
                stdout="",
                stderr=f"DirectoryNotFound: Path '{cwd}' does not exist",
                exit_code=127,
                execution_id=exec_id
            )

        env = sanitize_environment(env_override)

        import time
        import signal
        start_time = time.time()
        proc = None
        try:
            # Strictly shell=False, start_new_session=True for process group isolation
            proc = subprocess.Popen(
                cmd_args,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                env=env,
                start_new_session=True,
                close_fds=True
            )
            stdout_str, stderr_str = proc.communicate(timeout=timeout)
            duration = (time.time() - start_time) * 1000.0

            record_audit(
                action=f"SAFE_EXEC: {cmd_args[0]}",
                project="control-center",
                target=cwd,
                reason="Subprocess executed via SafeCommandExecutor",
                risk_level=RiskLevel.LOW,
                result="SUCCESS" if proc.returncode == 0 else "ERROR",
                actor=actor,
                execution_id=exec_id
            )

            return CommandExecutionResult(
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=proc.returncode,
                duration_ms=round(duration, 2),
                execution_id=exec_id
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000.0
            if proc:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                try:
                    proc.communicate(timeout=2)
                except Exception:
                    pass

            record_audit(
                action=f"SAFE_EXEC_TIMEOUT: {cmd_args[0]}",
                project="control-center",
                target=cwd,
                reason=f"Exceeded deadline of {timeout}s",
                risk_level=RiskLevel.LOW,
                result="TIMEOUT",
                actor=actor,
                execution_id=exec_id
            )
            return CommandExecutionResult(
                stdout="",
                stderr=f"CommandTimeout: Subprocess exceeded {timeout}s deadline",
                exit_code=124,
                duration_ms=round(duration, 2),
                execution_id=exec_id
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000.0
            return CommandExecutionResult(
                stdout="",
                stderr=f"ExecutionException: {str(e)}",
                exit_code=1,
                duration_ms=round(duration, 2),
                execution_id=exec_id
            )
