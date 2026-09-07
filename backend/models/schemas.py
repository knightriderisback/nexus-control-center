from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ProjectStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    ALERT = "ALERT"
    UNKNOWN = "UNKNOWN"

class ProjectRegistryItem(BaseModel):
    id: str
    name: str
    path: str
    github_repo: Optional[str] = None
    environment: str = "production"
    deployment_provider: str = "Cloud Run / Local"
    domain: Optional[str] = None
    status: ProjectStatus = ProjectStatus.HEALTHY
    health_score: int = 100
    last_audit: Optional[str] = None
    last_test: Optional[str] = None
    last_security_scan: Optional[str] = None
    documentation_url: Optional[str] = None
    owner: str = "knightriderisback"
    risk: RiskLevel = RiskLevel.LOW
    description: Optional[str] = ""

class AgentManifest(BaseModel):
    id: str
    name: str
    role: str
    category: str
    autonomy_tier: str = "Guardrailed" # Autonomous, Guardrailed, Step-by-Step
    allowed_tools: List[str]
    risk_level: RiskLevel = RiskLevel.MEDIUM
    project_scope: List[str] = ["*"]
    execution_policy: str
    model: str
    avatar: str
    color: str
    capabilities: List[str]
    status: str = "idle" # idle, active, monitoring, paused, halted
    current_task: Optional[str] = "Standby"
    task_count: int = 0
    token_velocity: int = 0
    total_tokens: int = 0

class TaskItem(BaseModel):
    id: str
    title: str
    agent_id: str
    agent_name: str
    project_id: Optional[str] = "general"
    status: str = "pending" # pending, running, awaiting_approval, completed, failed, aborted
    progress: int = 0
    tokens_spent: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    started_at: str
    completed_at: Optional[str] = None
    logs: List[str] = []
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class PolicyRule(BaseModel):
    id: str
    name: str
    action_pattern: str
    risk_level: RiskLevel
    requires_approval: bool
    description: str

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"

class ApprovalRequest(BaseModel):
    id: str
    task_id: Optional[str] = None
    action: str
    target_project: str
    risk_level: RiskLevel
    command: Optional[str] = None
    actor: str = "agent"
    reason: str
    timestamp: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    decided_at: Optional[str] = None
    token_hash: Optional[str] = None
    token: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    ttl_seconds: int = 3600
    executed_at: Optional[str] = None

class AuditEvent(BaseModel):
    id: str
    correlation_id: str
    timestamp: str
    actor: str
    agent: Optional[str] = None
    agent_id: Optional[str] = None
    execution_id: Optional[str] = None
    tool_id: Optional[str] = None
    user: str = "operator"
    action: str
    project: str
    target: str
    reason: str
    risk_level: RiskLevel
    approval_id: Optional[str] = None
    result: str # SUCCESS, FAILURE, REJECTED, PENDING_APPROVAL
    status: Optional[str] = None
    result_summary: Optional[str] = None
    error: Optional[str] = None

class ToolCall(BaseModel):
    call_id: str
    tool_id: str
    params: Dict[str, Any] = {}
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False

class ToolResult(BaseModel):
    call_id: str
    tool_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: float = 0.0

class AgentObservation(BaseModel):
    step_num: int
    observation_text: str
    tool_result: Optional[ToolResult] = None

class AgentPlan(BaseModel):
    plan_id: str
    steps: List[str]
    rationale: str

class AgentStep(BaseModel):
    step_num: int
    action: str
    tool_call: Optional[ToolCall] = None
    observation: Optional[AgentObservation] = None
    status: str = "COMPLETED"

class ExecutionLimits(BaseModel):
    max_steps: int = 10
    max_tool_calls: int = 20
    max_runtime_seconds: int = 120
    max_file_modifications: int = 10
    max_output_size_bytes: int = 500_000

class AgentResult(BaseModel):
    task_id: str
    execution_id: str
    agent_id: str
    status: str
    steps: List[AgentStep] = []
    final_output: Any = None
    tool_calls_count: int = 0
    duration_ms: float = 0.0
    tokens_used: int = 0


class MacroRunRequest(BaseModel):
    macro_id: str
    project_id: Optional[str] = "control-center"
    args: Optional[Dict[str, Any]] = {}

class EcoNLCommandRequest(BaseModel):
    prompt: str
    project_id: Optional[str] = None

class TaskDispatchRequest(BaseModel):
    title: str
    agent_id: str
    project_id: Optional[str] = "personal-engineering-os-2026"
    autonomy_tier: Optional[str] = "Guardrailed"
    instructions: str
