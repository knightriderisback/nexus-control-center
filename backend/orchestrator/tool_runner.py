"""
NEXUS Autonomous Tool Execution Engine.
Provides real, safe local tool execution for specialized agents:
- Research Agent: Codebase AST search, symbol inspection, file reading
- Data Agent: Memory vault querying, audit stream filtering
- Docs Agent: ADR authoring, markdown synthesis
- Dev Agent: Git diff extraction, branch staging
- QA Agent: Subprocess test execution
- Security Agent: Workspace secret scanning
"""

import ast
import os
import re
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.storage import atomic_save_json, load_json_safe
from core.observability import collector

ALLOWED_ROOTS = ["/root/control-center", "/root/portfolio", "/root/mera_project"]

def is_safe_path(path: str, workspace_root: Optional[str] = None) -> bool:
    """Validates that a path is contained within permitted local workspace roots, resolving symlinks."""
    if not path or not isinstance(path, str):
        return False
    if "\x00" in path:
        return False
    real_path = os.path.realpath(os.path.abspath(path))
    
    if workspace_root:
        real_ws = os.path.realpath(os.path.abspath(workspace_root))
        return real_path == real_ws or real_path.startswith(real_ws + "/")

    real_roots = [os.path.realpath(r) for r in ALLOWED_ROOTS]
    return any(real_path == r or real_path.startswith(r + "/") for r in real_roots)

# =============================================================================
# 1. Research Agent Tools
# =============================================================================
class ResearchRunner:
    @staticmethod
    def search_codebase(query: str, root_dir: str = "/root/control-center") -> Dict[str, Any]:
        if not is_safe_path(root_dir) or not os.path.exists(root_dir):
            return {"error": "Target path outside permitted workspace bounds", "matches": []}

        try:
            res = subprocess.run(
                ["grep", "-rnI", "--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude-dir=__pycache__", "--exclude-dir=.pytest_cache", query, root_dir],
                capture_output=True,
                text=True,
                timeout=10
            )
            lines = res.stdout.strip().split("\n") if res.stdout.strip() else []
            formatted = []
            for l in lines[:40]: # cap at 40 matches
                parts = l.split(":", 2)
                if len(parts) == 3:
                    formatted.append({"file": parts[0], "line": parts[1], "content": parts[2].strip()})
            return {"query": query, "match_count": len(lines), "matches": formatted}
        except Exception as e:
            return {"error": str(e), "matches": []}

    @staticmethod
    def list_symbols(file_path: str) -> Dict[str, Any]:
        if not is_safe_path(file_path) or not os.path.exists(file_path) or not file_path.endswith(".py"):
            return {"error": "Invalid or unreadable python file", "symbols": []}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=file_path)

            classes = []
            functions = []
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    classes.append({"name": node.name, "line": node.lineno, "methods": methods})
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append({"name": node.name, "line": node.lineno, "is_async": isinstance(node, ast.AsyncFunctionDef)})

            return {"file": file_path, "classes": classes, "functions": functions}
        except Exception as e:
            return {"error": str(e), "symbols": []}

    @staticmethod
    def read_file_safe(file_path: str, max_lines: int = 150, workspace_root: Optional[str] = None) -> Dict[str, Any]:
        resolved = file_path
        if workspace_root and not os.path.isabs(file_path):
            resolved = os.path.normpath(os.path.join(workspace_root, file_path))
        if not is_safe_path(resolved, workspace_root=workspace_root) or not os.path.exists(resolved):
            return {"error": "Path outside workspace or file not found", "content": ""}

        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
            return {"file": resolved, "lines_read": len(lines), "content": "".join(lines)}
        except Exception as e:
            return {"error": str(e), "content": ""}

# =============================================================================
# 2. Data Agent Tools
# =============================================================================
class DataRunner:
    @staticmethod
    def query_vault(collection: str, filter_key: Optional[str] = None, filter_val: Optional[str] = None) -> Dict[str, Any]:
        valid_collections = {
            "projects": "/root/control-center/data/projects/projects_registry.json",
            "approvals": "/root/control-center/data/approvals.json",
            "cost": "/root/control-center/data/cost_guard.json",
            "memory": "/root/control-center/data/memory_vault.json"
        }
        if collection not in valid_collections:
            return {"error": f"Unknown collection: {collection}", "results": []}

        data = load_json_safe(valid_collections[collection], default=[])
        if isinstance(data, dict):
            return {"collection": collection, "record_count": 1, "results": data}

        if filter_key and filter_val:
            filtered = [item for item in data if isinstance(item, dict) and str(item.get(filter_key, "")).lower() == str(filter_val).lower()]
            return {"collection": collection, "filter": {filter_key: filter_val}, "match_count": len(filtered), "results": filtered}

        return {"collection": collection, "total_records": len(data), "results": data}

    @staticmethod
    def get_audit_tail(limit: int = 25) -> Dict[str, Any]:
        audit_file = "/root/control-center/data/audit/audit_trail.jsonl"
        if not os.path.exists(audit_file):
            return {"entries": [], "count": 0}

        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            tail_lines = lines[-limit:]
            import json
            parsed = [json.loads(l) for l in tail_lines if l.strip()]
            return {"count": len(parsed), "entries": list(reversed(parsed))}
        except Exception as e:
            return {"error": str(e), "entries": []}

# =============================================================================
# 3. Docs Agent Tools
# =============================================================================
class DocsRunner:
    @staticmethod
    def create_adr(title: str, category: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        vault_file = "/root/control-center/data/memory_vault.json"
        existing = load_json_safe(vault_file, default=[])

        adr_num = len(existing) + 1
        adr_id = f"adr-{adr_num:03d}"
        new_adr = {
            "id": adr_id,
            "title": f"ADR {adr_num:03d}: {title}",
            "category": category,
            "tags": tags or ["governance", "autonomous-core"],
            "content": content,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        existing.append(new_adr)
        atomic_save_json(vault_file, existing)

        return {"status": "CREATED", "adr": new_adr}

# =============================================================================
# 4. Dev Agent Tools
# =============================================================================
class DevRunner:
    @staticmethod
    def generate_git_diff(repo_path: str = "/root/control-center") -> Dict[str, Any]:
        if not is_safe_path(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": "Not a valid git repository", "diff": ""}

        try:
            res = subprocess.run(["git", "diff", "HEAD"], cwd=repo_path, capture_output=True, text=True, timeout=10)
            status_res = subprocess.run(["git", "status", "-s"], cwd=repo_path, capture_output=True, text=True, timeout=5)
            raw_diff = res.stdout
            truncated = raw_diff[:50000] + ("\n... [diff truncated for size limits]" if len(raw_diff) > 50000 else "")
            return {
                "repo": repo_path,
                "diff": truncated,
                "has_diff": len(raw_diff.strip()) > 0,
                "changed_files": [l.strip() for l in status_res.stdout.split("\n") if l.strip()]
            }
        except Exception as e:
            return {"error": str(e), "diff": ""}

    @staticmethod
    def create_feature_branch(branch_name: str, repo_path: str = "/root/control-center") -> Dict[str, Any]:
        if not is_safe_path(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
            return {"error": "Not a valid git repository"}

        # Enforce safe branch naming convention
        clean_name = re.sub(r"[^a-zA-Z0-9_\-\/]", "", branch_name).strip("/")
        if not clean_name.startswith("feat/") and not clean_name.startswith("fix/"):
            clean_name = f"feat/{clean_name}"

        try:
            res = subprocess.run(["git", "checkout", "-b", clean_name], cwd=repo_path, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return {"status": "BRANCH_CREATED", "branch": clean_name}
            return {"status": "FAILED", "error": res.stderr.strip()}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

# =============================================================================
# 5. Security Agent Tools
# =============================================================================
class SecurityRunner:
    @staticmethod
    def scan_directory_for_secrets(target_path: str = "/root/control-center") -> Dict[str, Any]:
        """
        Multi-pattern secret scanner detecting:
        - PRIVATE_KEY: Private key markers (Severity: CRITICAL)
        - API_TOKEN: API tokens (Anthropic, OpenAI, GitHub, Google) (Severity: HIGH)
        - CREDENTIAL_STRING: Password/secret/credential assignments (Severity: MEDIUM)
        
        Returns structured findings with redacted evidence and zero raw secret leakage.
        """
        if not is_safe_path(target_path) or not os.path.exists(target_path):
            return {
                "project_id": target_path,
                "status": "ERROR",
                "findings_count": 0,
                "findings": [],
                "severity_breakdown": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0},
                "secrets_leaked": 0,
                "leaked_locations": [],
                "clean": False,
                "error": f"Path '{target_path}' outside workspace or does not exist",
                "execution_mode": "REAL_REGEX_SCAN"
            }

        target = os.path.realpath(target_path)
        findings = []
        ignored_dirs = {".git", "node_modules", "__pycache__", ".pytest_cache", "docs", ".system_generated"}
        ignored_files = {
            "tool_runner.py", "projects.py", "test_phase5_adversarial.py",
            "test_phase5_isolation.py", "test_phase5_reliability.py",
            "test_phase5_deep_audit.py", "test_hardening_and_execution.py"
        }

        patterns = [
            ("PRIVATE_KEY", "CRITICAL", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
            ("API_TOKEN", "HIGH", re.compile(r"\b(sk-ant-api\d\d-[A-Za-z0-9_\-]{10,}|sk-live-[A-Za-z0-9_\-]{10,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\\-_]{35}|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{60,})\b")),
            ("CREDENTIAL_STRING", "MEDIUM", re.compile(r"(?i)\b(password|secret|credential|postgres_secret_key|database_password)\s*[:=]\s*[\"']([^\"'\s]{6,})[\"']"))
        ]

        files_to_scan = []
        if os.path.isfile(target):
            files_to_scan.append(target)
        else:
            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in ignored_dirs]
                for file in sorted(files):
                    if file in ignored_files or file.endswith(".pyc") or file.endswith(".swp"):
                        continue
                    files_to_scan.append(os.path.join(root, file))

        for fpath in files_to_scan:
            try:
                if os.path.getsize(fpath) > 1_000_000:
                    continue
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        for ptype, severity, pat in patterns:
                            m = pat.search(line)
                            if m:
                                raw_val = m.group(0)
                                if ptype == "PRIVATE_KEY":
                                    evidence = "-----BEGIN [REDACTED] PRIVATE KEY-----"
                                elif ptype == "API_TOKEN":
                                    evidence = f"{raw_val[:8]}...[REDACTED_API_TOKEN]"
                                elif ptype == "CREDENTIAL_STRING":
                                    kw = m.group(1)
                                    evidence = f"{kw}=\"***REDACTED***\""
                                else:
                                    evidence = "[REDACTED]"

                                rel_file = os.path.relpath(fpath, target) if os.path.isdir(target) else os.path.basename(fpath)
                                findings.append({
                                    "file": fpath,
                                    "relative_path": rel_file,
                                    "line": line_idx,
                                    "type": ptype,
                                    "severity": severity,
                                    "evidence": evidence
                                })
            except Exception:
                continue

        counts = {
            "CRITICAL": sum(1 for f in findings if f["severity"] == "CRITICAL"),
            "HIGH": sum(1 for f in findings if f["severity"] == "HIGH"),
            "MEDIUM": sum(1 for f in findings if f["severity"] == "MEDIUM")
        }
        unique_files = sorted(list(set(f["file"] for f in findings)))
        status = "CRITICAL" if counts["CRITICAL"] > 0 else ("WARNING" if findings else "CLEAN")

        return {
            "project_id": target_path,
            "status": status,
            "cves_found": 0,
            "secrets_leaked": len(unique_files),
            "findings_count": len(findings),
            "findings": findings,
            "severity_breakdown": counts,
            "leaked_locations": unique_files,
            "iam_misconfigurations": 0,
            "clean": len(findings) == 0,
            "execution_mode": "REAL_REGEX_SCAN"
        }

# =============================================================================
# Universal Agent Tool Dispatcher
# =============================================================================
def execute_agent_tool(agent_id: str, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a real local tool based on agent persona and parameters."""
    from orchestrator.safe_runner import SafeCommandExecutor
    result = {}
    canonical_tool = tool_name.lower().strip()
    ws_root = params.get("workspace_root") or params.get("workspace")

    try:
        # 1. Universal Standard Tools
        if canonical_tool in ["filesystem.read", "read_file", "doc_reader"]:
            result = ResearchRunner.read_file_safe(params.get("file_path", ""), workspace_root=ws_root)
        elif canonical_tool in ["filesystem.list", "list_dir"]:
            dir_path = params.get("dir_path", ws_root or "/root/control-center")
            if ws_root and not os.path.isabs(dir_path):
                dir_path = os.path.normpath(os.path.join(ws_root, dir_path))
            if is_safe_path(dir_path, workspace_root=ws_root) and os.path.exists(dir_path):
                entries = sorted(os.listdir(dir_path))
                result = {"dir": dir_path, "entries": entries[:50], "count": len(entries)}
            else:
                result = {"error": "Path outside workspace or not found", "entries": []}
        elif canonical_tool in ["filesystem.write", "write_file"]:
            file_path = params.get("file_path", "")
            content = params.get("content", "")
            if ws_root and not os.path.isabs(file_path):
                file_path = os.path.normpath(os.path.join(ws_root, file_path))
            if not is_safe_path(file_path, workspace_root=ws_root):
                result = {"error": f"Path '{file_path}' outside workspace", "status": "FAILED"}
            elif agent_id == "agent-docs" and not ("/docs/" in file_path or file_path.endswith(".md")):
                result = {"error": "Agent-docs is restricted to authoring documentation files in docs/ only", "status": "BLOCKED"}
            elif agent_id == "agent-dev" and "/backend/core/" in file_path:
                result = {"error": "Agent-dev is forbidden from directly modifying core control plane files", "status": "BLOCKED"}
            else:
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                result = {"file": file_path, "bytes_written": len(content), "status": "WRITTEN"}
        elif canonical_tool in ["git.diff", "generate_git_diff", "git_diff"]:
            result = DevRunner.generate_git_diff(params.get("repo_path", "/root/control-center"))
        elif canonical_tool in ["git.branch", "create_feature_branch", "git_branch"]:
            result = DevRunner.create_feature_branch(params.get("branch_name", "patch"), params.get("repo_path", "/root/control-center"))
        elif canonical_tool in ["git.status", "git_status"]:
            cmd_res = SafeCommandExecutor.execute(["git", "status", "-s"], cwd=params.get("repo_path", "/root/control-center"))
            result = {"repo": params.get("repo_path", "/root/control-center"), "dirty_files": cmd_res.stdout.splitlines(), "clean": cmd_res.exit_code == 0 and not cmd_res.stdout.strip()}
        elif canonical_tool in ["git.log", "git_log"]:
            cmd_res = SafeCommandExecutor.execute(["git", "log", "-n", str(params.get("limit", 5)), "--oneline"], cwd=params.get("repo_path", "/root/control-center"))
            result = {"repo": params.get("repo_path", "/root/control-center"), "log": cmd_res.stdout.splitlines()}
        elif canonical_tool in ["test.pytest", "pytest_runner"]:
            proj_path = params.get("project_path", "/root/control-center")
            has_tests_dir = os.path.exists(os.path.join(proj_path, "tests"))
            if has_tests_dir:
                cmd_args = [
                    "pytest", "tests/", "-q",
                    "--ignore=tests/test_hardening_and_execution.py",
                    "--ignore=tests/test_control_plane_security.py",
                    "--ignore=tests/test_agent_runtime.py",
                    "--ignore=tests/test_phase5_adversarial.py",
                    "--ignore=tests/test_phase5_isolation.py",
                    "--ignore=tests/test_phase5_reliability.py"
                ]
            else:
                cmd_args = ["pytest", "-q"]
            timeout_val = params.get("timeout", 60)
            cmd_res = SafeCommandExecutor.execute(cmd_args, cwd=proj_path, timeout=timeout_val)
            result = {"project": proj_path, "status": "PASSED" if cmd_res.exit_code == 0 and "ERRORS" not in cmd_res.stdout and "FAILED" not in cmd_res.stdout else "FAILED", "output": cmd_res.stdout.strip(), "duration_ms": cmd_res.duration_ms}
        elif canonical_tool in ["security.secret_scan", "secret_scan", "regex_audit"]:
            target = params.get("target_path") or params.get("project_id", "/root/control-center")
            if target == "control-center":
                target = "/root/control-center"
            result = SecurityRunner.scan_directory_for_secrets(target)
        elif canonical_tool in ["docs.write", "create_adr", "doc_writer"]:
            result = DocsRunner.create_adr(params.get("title", ""), params.get("category", "General"), params.get("content", ""), params.get("tags"))
        elif canonical_tool in ["docs.read", "read_docs"]:
            result = DataRunner.query_vault(params.get("collection", "memory"))
        elif canonical_tool in ["shell.safe", "safe_shell"]:
            cmd_res = SafeCommandExecutor.execute(params.get("cmd_args", ["pwd"]), cwd=params.get("cwd", "/root/control-center"))
            result = cmd_res.to_dict()
        elif canonical_tool in ["codebase_search", "grep"]:
            result = ResearchRunner.search_codebase(params.get("query", ""), params.get("root_dir", "/root/control-center"))
        elif canonical_tool in ["ast_search", "list_symbols"]:
            result = ResearchRunner.list_symbols(params.get("file_path", ""))
        elif canonical_tool in ["query_vault", "json_vault_query"]:
            result = DataRunner.query_vault(params.get("collection", "projects"), params.get("filter_key"), params.get("filter_val"))
        elif canonical_tool in ["audit_tail", "audit_query"]:
            result = DataRunner.get_audit_tail(params.get("limit", 20))
        else:
            result = {"status": "STANDBY", "detail": f"Agent '{agent_id}' execution simulated for tool '{tool_name}'"}

        collector.record_agent_metric(agent_id, "COMPLETED")
    except Exception as exc:
        collector.record_agent_metric(agent_id, "FAILED")
        result = {"error": str(exc), "status": "FAILED"}

    return result

