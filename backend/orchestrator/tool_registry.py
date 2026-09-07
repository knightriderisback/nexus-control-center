"""
NEXUS Formal Tool Registry.
Enforces strict capability scoping, input/output schemas, approval constraints,
and risk tiers across all autonomous agents.
"""

from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from models.schemas import RiskLevel

class ToolDefinition(BaseModel):
    tool_id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: RiskLevel
    allowed_agents: List[str]
    requires_approval: bool
    execution_mode: str # read_only, sandboxed, safe_subprocess, approval_gated
    timeout: int = 30
    write_capability: bool = False
    workspace_restriction: Optional[str] = "read_only"

STANDARD_TOOLS: List[ToolDefinition] = [
    ToolDefinition(
        tool_id="filesystem.read",
        name="Filesystem Safe Reader",
        description="Reads file contents within permitted workspace boundaries with size capping.",
        input_schema={"file_path": "str", "max_lines": "Optional[int]"},
        output_schema={"file": "str", "lines_read": "int", "content": "str"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-research", "agent-dev", "agent-docs", "agent-qa"],
        requires_approval=False,
        execution_mode="read_only",
        timeout=10,
        write_capability=False,
        workspace_restriction="workspace_boundary"
    ),
    ToolDefinition(
        tool_id="filesystem.list",
        name="Filesystem Safe Directory Lister",
        description="Lists directory entries within permitted workspace paths.",
        input_schema={"dir_path": "str", "max_depth": "Optional[int]"},
        output_schema={"dir": "str", "entries": "List[str]", "count": "int"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-research", "agent-dev", "agent-data"],
        requires_approval=False,
        execution_mode="read_only",
        timeout=10,
        write_capability=False,
        workspace_restriction="workspace_boundary"
    ),
    ToolDefinition(
        tool_id="filesystem.write",
        name="Filesystem Sandboxed Writer",
        description="Writes or patches files in designated project workspaces with change tracking.",
        input_schema={"file_path": "str", "content": "str", "overwrite": "Optional[bool]"},
        output_schema={"file": "str", "bytes_written": "int", "status": "str"},
        risk_level=RiskLevel.MEDIUM,
        allowed_agents=["agent-dev", "agent-docs"],
        requires_approval=True,
        execution_mode="sandboxed",
        timeout=15,
        write_capability=True,
        workspace_restriction="project_workspace"
    ),
    ToolDefinition(
        tool_id="git.status",
        name="Git Status Inspector",
        description="Inspects git working tree state and uncommitted changes.",
        input_schema={"repo_path": "str"},
        output_schema={"repo": "str", "dirty_files": "List[str]", "clean": "bool"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-dev", "agent-research", "agent-recovery"],
        requires_approval=False,
        execution_mode="read_only",
        timeout=10,
        write_capability=False,
        workspace_restriction="repo_root"
    ),
    ToolDefinition(
        tool_id="git.diff",
        name="Git Diff Extractor",
        description="Computes unstaged or staged diff against git HEAD.",
        input_schema={"repo_path": "str", "staged": "Optional[bool]"},
        output_schema={"repo": "str", "diff": "str", "has_diff": "bool"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-dev", "agent-qa"],
        requires_approval=False,
        execution_mode="read_only",
        timeout=15,
        write_capability=False,
        workspace_restriction="repo_root"
    ),
    ToolDefinition(
        tool_id="git.branch",
        name="Git Safe Feature Branch Creator",
        description="Creates isolated feature or bugfix branches following strict naming rules.",
        input_schema={"branch_name": "str", "repo_path": "Optional[str]"},
        output_schema={"branch": "str", "status": "str"},
        risk_level=RiskLevel.MEDIUM,
        allowed_agents=["agent-dev"],
        requires_approval=False,
        execution_mode="sandboxed",
        timeout=10,
        write_capability=True,
        workspace_restriction="repo_root"
    ),
    ToolDefinition(
        tool_id="git.log",
        name="Git Log Inspector",
        description="Retrieves recent commit metadata and hashes.",
        input_schema={"repo_path": "str", "limit": "Optional[int]"},
        output_schema={"repo": "str", "commits": "List[Dict[str, str]]"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-dev", "agent-research", "agent-recovery"],
        requires_approval=False,
        execution_mode="read_only",
        timeout=10,
        write_capability=False,
        workspace_restriction="repo_root"
    ),
    ToolDefinition(
        tool_id="test.pytest",
        name="Pytest Test Runner",
        description="Executes project test suites in safe subprocess isolation.",
        input_schema={"project_path": "str", "test_file": "Optional[str]"},
        output_schema={"status": "str", "passed": "int", "failed": "int", "duration": "str"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-qa", "agent-dev"],
        requires_approval=False,
        execution_mode="safe_subprocess",
        timeout=60,
        write_capability=False,
        workspace_restriction="project_root"
    ),
    ToolDefinition(
        tool_id="security.secret_scan",
        name="Secret Leak Scanner",
        description="Executes regex scanner across workspace for exposed PEM keys and credentials.",
        input_schema={"target_path": "str"},
        output_schema={"status": "str", "secrets_leaked": "int", "leaked_locations": "List[str]"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-security"],
        requires_approval=False,
        execution_mode="safe_subprocess",
        timeout=30,
        write_capability=False,
        workspace_restriction="target_boundary"
    ),
    ToolDefinition(
        tool_id="docs.read",
        name="Documentation & Memory Vault Reader",
        description="Reads architectural documentation and memory vault records.",
        input_schema={"collection": "Optional[str]"},
        output_schema={"records": "List[Dict[str, Any]]", "count": "int"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-docs", "agent-research"],
        requires_approval=False,
        execution_mode="read_only",
        timeout=10,
        write_capability=False,
        workspace_restriction="memory_vault"
    ),
    ToolDefinition(
        tool_id="docs.write",
        name="ADR & Documentation Chronicler",
        description="Persists Architecture Decision Records and Markdown documentation.",
        input_schema={"title": "str", "category": "str", "content": "str", "tags": "Optional[List[str]]"},
        output_schema={"status": "str", "adr": "Dict[str, Any]"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-docs"],
        requires_approval=False,
        execution_mode="sandboxed",
        timeout=15,
        write_capability=True,
        workspace_restriction="docs_vault"
    ),
    ToolDefinition(
        tool_id="shell.safe",
        name="Controlled Allowlisted Shell Runner",
        description="Executes strictly allowlisted commands in controlled working directories. Unrestricted shell is forbidden.",
        input_schema={"cmd_args": "List[str]", "cwd": "str"},
        output_schema={"stdout": "str", "stderr": "str", "exit_code": "int"},
        risk_level=RiskLevel.HIGH,
        allowed_agents=["agent-devops", "agent-dev"],
        requires_approval=True,
        execution_mode="safe_subprocess",
        timeout=30,
        write_capability=True,
        workspace_restriction="approved_cwd"
    ),
    ToolDefinition(
        tool_id="codebase_search",
        name="Codebase AST & Content Searcher",
        description="Searches codebases for pattern matches and definitions.",
        input_schema={"query": "str", "root_dir": "Optional[str]"},
        output_schema={"query": "str", "match_count": "int", "matches": "List[Dict[str, Any]]"},
        risk_level=RiskLevel.LOW,
        allowed_agents=["agent-research", "agent-dev"],
        requires_approval=False,
        execution_mode="read_only",
        timeout=15,
        write_capability=False,
        workspace_restriction="workspace_boundary"
    )
]

AGENT_PERMISSION_PROFILES: Dict[str, List[str]] = {
    # Research: read-only
    "agent-research": ["filesystem.read", "filesystem.list", "git.log", "docs.read", "codebase_search"],
    # Developer: read + controlled write + tests + git diff
    "agent-dev": ["filesystem.read", "filesystem.list", "filesystem.write", "git.status", "git.diff", "git.branch", "git.log", "test.pytest", "shell.safe"],
    # QA: read + test execution
    "agent-qa": ["filesystem.read", "filesystem.list", "git.diff", "test.pytest"],
    # Security: read + security tools
    "agent-security": ["filesystem.read", "filesystem.list", "security.secret_scan"],
    # Documentation: read + docs-only write
    "agent-docs": ["filesystem.read", "filesystem.list", "docs.read", "docs.write"],
    # DevOps: read-only initially (+ shell.safe requiring approval)
    "agent-devops": ["filesystem.read", "filesystem.list", "git.status", "git.log", "shell.safe"],
    # Infrastructure: read-only initially
    "agent-infra": ["filesystem.read", "git.status"],
    # Data: read-only initially
    "agent-data": ["filesystem.read", "filesystem.list", "docs.read"],
    # UX: read-only initially
    "agent-ux": ["filesystem.read", "filesystem.list"],
    # SEO: read-only initially
    "agent-seo": ["filesystem.read", "filesystem.list"],
    # Cost: read-only
    "agent-cost": ["filesystem.read"],
    # Monitoring: read-only
    "agent-mon": ["filesystem.read"],
    # Recovery: read-only + approved recovery actions
    "agent-recovery": ["filesystem.read", "git.status", "git.log"]
}

class ToolRegistry:
    """Central repository and policy enforcement point for agent tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {t.tool_id: t for t in STANDARD_TOOLS}
        self.profiles = AGENT_PERMISSION_PROFILES

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    def list_tools(self, agent_id: Optional[str] = None) -> List[ToolDefinition]:
        if not agent_id:
            return list(self._tools.values())
        allowed_tool_ids = self.profiles.get(agent_id, [])
        return [t for t in self._tools.values() if t.tool_id in allowed_tool_ids or agent_id in t.allowed_agents]

    def register_tool(self, tool: ToolDefinition):
        self._tools[tool.tool_id] = tool

    def validate_tool_call(self, tool_id: str, agent_id: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verifies if agent has permission to execute the specified tool."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False, f"Unknown tool: '{tool_id}'"

        allowed_ids = self.profiles.get(agent_id, tool.allowed_agents)
        if tool_id not in allowed_ids and agent_id not in tool.allowed_agents:
            return False, f"Agent '{agent_id}' is not authorized to use tool '{tool_id}'. Permitted tools: {allowed_ids}"

        return True, None

    def export_matrix_dict(self) -> Dict[str, Any]:
        """Generates machine-readable tool capability and permission matrix."""
        tools_data = []
        for t in self._tools.values():
            tools_data.append({
                "tool_id": t.tool_id,
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level.value,
                "execution_mode": t.execution_mode,
                "write_capability": t.write_capability,
                "workspace_restriction": t.workspace_restriction,
                "requires_approval": t.requires_approval,
                "timeout_seconds": t.timeout,
                "allowed_agents": t.allowed_agents,
                "input_schema": t.input_schema,
                "output_schema": t.output_schema
            })

        agent_permissions = {}
        for agent_id, allowed_tool_ids in self.profiles.items():
            agent_permissions[agent_id] = {
                "permitted_tool_ids": allowed_tool_ids,
                "has_write_permission": any(self._tools[tid].write_capability for tid in allowed_tool_ids if tid in self._tools),
                "high_risk_tools": [tid for tid in allowed_tool_ids if tid in self._tools and self._tools[tid].risk_level == RiskLevel.HIGH]
            }

        return {
            "version": "1.0.0",
            "total_tools": len(tools_data),
            "tools": tools_data,
            "agent_permissions": agent_permissions
        }

tool_registry = ToolRegistry()

