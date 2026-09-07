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
    """Validates that working directory is within allowed workspace boundaries."""
    abs_path = os.path.abspath(cwd)
    return any(abs_path == r or abs_path.startswith(r + "/") for r in ALLOWED_ROOTS)

def sanitize_environment() -> Dict[str, str]:
    """Creates a clean environment dict scrubbing secrets and credentials."""
    safe_keys = {"PATH", "LANG", "LC_ALL", "HOME", "USER", "TERM", "PYTHONPATH"}
    clean_env = {}
    for k, v in os.environ.items():
        if k in safe_keys:
            clean_env[k] = v
        # Ensure no token or secret keys are passed to subprocess
        elif not any(secret_term in k.upper() for secret_term in ["KEY", "SECRET", "TOKEN", "PASS", "CRED"]):
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

        for dangerous in DANGEROUS_ARG_CHARS:
            if dangerous in arg:
                return False, f"Dangerous shell character '{dangerous}' detected in argument: {arg}"

        # Path traversal checks
        if ".." in arg and ("../" in arg or "/.." in arg or arg == ".."):
            return False, f"Path traversal attempt '..' detected in argument: {arg}"

        # Check absolute path argument does not escape allowed roots
        if arg.startswith("/") and not arg.startswith("--") and not any(arg == r or arg.startswith(r + "/") for r in ALLOWED_ROOTS):
            return False, f"Path '{arg}' escapes permitted workspace boundaries: {ALLOWED_ROOTS}"

    return True, None

class SafeCommandExecutor:
    """Safely executes allowlisted commands with timeout and directory checks."""

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

        env = sanitize_environment()
        if env_override:
            env.update(env_override)

        import time
        start_time = time.time()
        try:
            # Strictly shell=False to prevent shell injection
            res = subprocess.run(
                cmd_args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                env=env
            )
            duration = (time.time() - start_time) * 1000.0

            record_audit(
                action=f"SAFE_EXEC: {cmd_args[0]}",
                project="control-center",
                target=cwd,
                reason="Subprocess executed via SafeCommandExecutor",
                risk_level=RiskLevel.LOW,
                result="SUCCESS" if res.returncode == 0 else "ERROR",
                actor=actor,
                execution_id=exec_id
            )

            return CommandExecutionResult(
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.returncode,
                duration_ms=round(duration, 2),
                execution_id=exec_id
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000.0
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
