"""
NEXUS Safe Subprocess Execution Engine.
Enforces strict binary allowlisting, argument sanitization, directory boundaries,
and environment isolation for all agent executions.
"""

import os
import re
import subprocess
from typing import List, Dict, Any, Optional

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

DANGEROUS_ARG_CHARS = [";", "&&", "||", "|", "`", "$(", "${", "\n", "\r"]

class CommandExecutionResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int, duration_ms: float = 0.0):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
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

    return True, None

Tuple_Validation = tuple[bool, Optional[str]]

class SafeCommandExecutor:
    """Safely executes allowlisted commands with timeout and directory checks."""

    @staticmethod
    def execute(
        cmd_args: List[str],
        cwd: str = "/root/control-center",
        timeout: int = 30,
        env_override: Optional[Dict[str, str]] = None
    ) -> CommandExecutionResult:
        is_valid, err_msg = validate_command(cmd_args, cwd)
        if not is_valid:
            return CommandExecutionResult(
                stdout="",
                stderr=f"SecurityPolicyViolation: {err_msg}",
                exit_code=126
            )

        if not os.path.exists(cwd):
            return CommandExecutionResult(
                stdout="",
                stderr=f"DirectoryNotFound: Path '{cwd}' does not exist",
                exit_code=127
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
            return CommandExecutionResult(
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.returncode,
                duration_ms=round(duration, 2)
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000.0
            return CommandExecutionResult(
                stdout="",
                stderr=f"CommandTimeout: Subprocess exceeded {timeout}s deadline",
                exit_code=124,
                duration_ms=round(duration, 2)
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000.0
            return CommandExecutionResult(
                stdout="",
                stderr=f"ExecutionException: {str(e)}",
                exit_code=1,
                duration_ms=round(duration, 2)
            )
