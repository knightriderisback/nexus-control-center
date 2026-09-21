from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ProjectStatus(str, Enum):
    HEALTHY = "HEALTHY"
    ACTIVE = "ACTIVE"
    WARNING = "WARNING"
    ALERT = "ALERT"
    UNKNOWN = "UNKNOWN"

class ProjectRegistryItem(BaseModel):
    id: str
    name: str
    path: str
    github_repo: Optional[str] = None
    repository: Optional[str] = None
    branch: str = "main"
    type: Optional[str] = "generic_git"
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
    tags: List[str] = []
    sources: List[str] = []

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

    def __getitem__(self, item: str) -> Any:
        if item == "agent_id":
            return self.id
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if item == "agent_id":
            return self.id
        return getattr(self, item, default)

    def get(self, item: str, default: Any = None) -> Any:
        if item == "agent_id":
            return self.id
        return getattr(self, item, default)

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
    failed_attempts: int = 0

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
    max_output_size_bytes: int = 1_000_000
    recursion_depth: int = 0

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

class AgentHandoffRequest(BaseModel):
    parent_agent_id: str
    target_agent_id: str
    task_title: str
    instructions: str
    context: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = "control-center"
    parent_execution_id: Optional[str] = None
    recursion_depth: int = 0

class AgentHandoffRecord(BaseModel):
    handoff_id: str
    parent_agent_id: str
    target_agent_id: str
    parent_execution_id: Optional[str] = None
    child_execution_id: Optional[str] = None
    status: str
    task_title: str
    recursion_depth: int = 0
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SwarmPipelineRequest(BaseModel):
    pipeline_name: str
    title: str
    project_id: Optional[str] = "control-center"
    instructions: str
    stages: Optional[List[Dict[str, Any]]] = None
    autonomy_tier: Optional[str] = "Guardrailed"

class SwarmPipelineResult(BaseModel):
    pipeline_id: str
    pipeline_name: str
    status: str
    stages_completed: int
    total_stages: int
    stage_results: List[Dict[str, Any]] = []
    duration_ms: float = 0.0
    total_tool_calls: int = 0
    total_tokens_used: int = 0
    approval_required: bool = False
    approval_id: Optional[str] = None

class SessionState(str, Enum):
    INITIALIZING = "INITIALIZING"
    SPEC_PROPOSAL = "SPEC_PROPOSAL"
    CODE_SYNTHESIS = "CODE_SYNTHESIS"
    TEST_VERIFICATION = "TEST_VERIFICATION"
    SECURITY_AUDIT = "SECURITY_AUDIT"
    FEEDBACK_REVISION = "FEEDBACK_REVISION"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"

class TransitionRecord(BaseModel):
    transition_id: str
    from_state: str
    to_state: str
    trigger_agent: str
    timestamp: str
    payload: Dict[str, Any] = {}
    reason: str

class AgyCodexSessionRequest(BaseModel):
    session_name: str
    directive: str
    planner_agent: Optional[str] = "agent-research"
    coder_agent: Optional[str] = "agent-dev"
    verifier_agent: Optional[str] = "agent-qa"
    project_id: Optional[str] = "control-center"
    target_workspace: Optional[str] = None
    max_revisions: int = 2
    auto_rollback_on_failure: bool = True
    isolate_worktree: bool = False
    auto_cleanup_worktree: bool = False
    auto_merge_on_completion: bool = False
    merge_target_branch: Optional[str] = None

class AgyCodexSession(BaseModel):
    session_id: str
    session_name: str
    directive: str
    current_state: SessionState = SessionState.INITIALIZING
    planner_agent: str = "agent-research"
    coder_agent: str = "agent-dev"
    verifier_agent: str = "agent-qa"
    project_id: str = "control-center"
    target_workspace: str
    revision_count: int = 0
    max_revisions: int = 2
    auto_rollback_on_failure: bool = True
    isolate_worktree: bool = False
    auto_cleanup_worktree: bool = False
    isolated_worktree: Optional[str] = None
    worktree_branch: Optional[str] = None
    auto_merge_on_completion: bool = False
    merge_target_branch: Optional[str] = None
    merge_result: Optional[Dict[str, Any]] = None
    spec_proposal: Optional[Dict[str, Any]] = None
    code_artifacts: Optional[Dict[str, Any]] = None
    verification_results: Optional[Dict[str, Any]] = None
    security_results: Optional[Dict[str, Any]] = None
    transitions: List[TransitionRecord] = []
    created_at: str
    updated_at: str
    checkpoint_id: Optional[str] = None
    status: str = "IN_PROGRESS"
    approval_id: Optional[str] = None
    error: Optional[str] = None
    last_feedback: Optional[str] = None

class WorktreeInfo(BaseModel):
    session_id: str
    repo_path: str
    worktree_path: str
    branch_name: str
    created_at: str
    status: str = "ACTIVE"
    commit_hash: Optional[str] = None

class WorktreeProvisionRequest(BaseModel):
    repo_path: str
    session_id: Optional[str] = None
    branch_name: Optional[str] = None

class MergeStrategy(str, Enum):
    AUTO = "AUTO"
    FAST_FORWARD = "FAST_FORWARD"
    THREE_WAY = "THREE_WAY"
    OURS = "OURS"
    THEIRS = "THEIRS"
    AGENT_RESOLVE = "AGENT_RESOLVE"

class MergeEvaluationRequest(BaseModel):
    repo_path: str
    source_branch: str
    target_branch: str = "main"
    session_id: Optional[str] = None
    run_pre_merge_tests: bool = True

class MergeEvaluationResult(BaseModel):
    repo_path: str
    source_branch: str
    target_branch: str
    mergeable: bool
    is_fast_forward: bool = False
    has_conflicts: bool = False
    conflict_files: List[str] = []
    divergence: Dict[str, int] = {}
    diff_summary: Optional[str] = None
    semantic_test_passed: Optional[bool] = None
    evaluated_at: str
    three_way_analysis: Optional[Dict[str, Any]] = None
    conflict_type: Optional[str] = None
    mergeability: Optional[str] = None
    risk_classification: Optional[Dict[str, Any]] = None

class MergeExecutionRequest(BaseModel):
    repo_path: str
    source_branch: str
    target_branch: str = "main"
    strategy: MergeStrategy = MergeStrategy.AUTO
    session_id: Optional[str] = None
    commit_message: Optional[str] = None
    delete_source_branch_on_success: bool = False
    run_pre_merge_tests: bool = True
    auto_resolve_conflicts: bool = True
    approval_id: Optional[str] = None
    allow_ours_theirs: bool = False

class MergeClassification(str, Enum):
    CLEAN_MERGE = "CLEAN_MERGE"
    AUTO_MERGEABLE = "AUTO_MERGEABLE"
    CONFLICTED = "CONFLICTED"
    HIGH_RISK = "HIGH_RISK"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"
    REJECTED = "REJECTED"

class ConflictType(str, Enum):
    CLEAN_MERGE = "CLEAN_MERGE"
    TEXTUAL_CONFLICT = "TEXTUAL_CONFLICT"
    RENAME_DELETE_CONFLICT = "RENAME_DELETE_CONFLICT"
    BINARY_CONFLICT = "BINARY_CONFLICT"
    SEMANTIC_TEST_FAILURE = "SEMANTIC_TEST_FAILURE"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"

class MergeabilityClassification(str, Enum):
    FAST_FORWARD = "FAST_FORWARD"
    CLEAN_THREE_WAY = "CLEAN_THREE_WAY"
    RESOLVABLE_CONFLICT = "RESOLVABLE_CONFLICT"
    UNRESOLVABLE_CONFLICT = "UNRESOLVABLE_CONFLICT"
    DANGEROUS_PATH_VIOLATION = "DANGEROUS_PATH_VIOLATION"

class ThreeWayAnalysis(BaseModel):
    merge_base_commit: str
    source_commit: str
    target_commit: str
    is_fast_forward: bool
    source_changes: Dict[str, Any]
    target_changes: Dict[str, Any]
    overlapping_files: List[str] = []
    rename_delete_conflicts: List[str] = []
    binary_conflicts: List[str] = []
    dangerous_path_changes: List[str] = []
    divergence: Dict[str, int] = {}

class RiskClassification(BaseModel):
    risk_level: RiskLevel
    requires_approval: bool
    policy_reason: Optional[str] = None
    dangerous_paths: List[str] = []
    sensitive_categories: List[str] = []

class VerificationCandidate(BaseModel):
    ephemeral_worktree_path: Optional[str] = None
    candidate_commit: Optional[str] = None
    candidate_tree_sha: Optional[str] = None
    target_base_commit: Optional[str] = None
    tests_executed: bool = False
    tests_passed: Optional[bool] = None
    test_output: Optional[str] = None
    security_clean: Optional[bool] = None
    security_findings: List[str] = []
    verification_status: str

class MergeDecision(BaseModel):
    merge_id: str
    session_id: Optional[str] = None
    source_branch: str
    target_branch: str
    status: str
    classification: str
    mergeability: MergeabilityClassification
    strategy_used: str
    merge_commit: Optional[str] = None
    candidate_tree_sha: Optional[str] = None
    conflict_files: List[str] = []
    resolved_files: List[str] = []
    reason: str
    approval_id: Optional[str] = None
    executed_at: str
    three_way_analysis: Optional[ThreeWayAnalysis] = None
    verification_candidate: Optional[VerificationCandidate] = None
    multi_agent_review: Optional[Dict[str, Any]] = None

class MergeExecutionResult(BaseModel):
    merge_id: str
    status: str
    repo_path: str
    source_branch: str
    target_branch: str
    strategy_used: str
    merge_commit: Optional[str] = None
    candidate_tree_sha: Optional[str] = None
    conflict_files: List[str] = []
    resolved_files: List[str] = []
    test_results: Optional[Dict[str, Any]] = None
    security_results: Optional[Dict[str, Any]] = None
    approval_id: Optional[str] = None
    executed_at: str
    error: Optional[str] = None
    decision: Optional[MergeDecision] = None


# =============================================================================
# Merge Candidate Lifecycle State Machine Models
# =============================================================================

class MergeLifecycleState(str, Enum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    ARBITRATING = "ARBITRATING"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFYING = "VERIFYING"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    READY_TO_INTEGRATE = "READY_TO_INTEGRATE"
    INTEGRATING = "INTEGRATING"
    INTEGRATED = "INTEGRATED"
    # Terminal & failure states
    CONFLICTED = "CONFLICTED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class MergeTransitionRecord(BaseModel):
    from_state: str
    to_state: str
    actor: str
    timestamp: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MergeCandidateCreateRequest(BaseModel):
    repo_path: str
    source_branch: str
    target_branch: str = "main"
    session_id: Optional[str] = None
    auto_advance: bool = False
    strategy: MergeStrategy = MergeStrategy.AUTO
    allow_ours_theirs: bool = False


class MergeCandidate(BaseModel):
    candidate_id: str
    session_id: Optional[str] = None
    repo_path: str
    source_branch: str
    target_branch: str
    state: MergeLifecycleState = MergeLifecycleState.CREATED
    source_commit: Optional[str] = None
    target_commit: Optional[str] = None
    target_base_commit: Optional[str] = None
    merge_base_commit: Optional[str] = None
    candidate_commit: Optional[str] = None
    candidate_tree_sha: Optional[str] = None
    candidate_worktree: Optional[str] = None
    strategy: str = "AUTO"
    allow_ours_theirs: bool = False
    conflict_files: List[str] = []
    resolved_files: List[str] = []
    three_way_analysis: Optional[Dict[str, Any]] = None
    risk_classification: Optional[Dict[str, Any]] = None
    verification_results: Optional[Dict[str, Any]] = None
    security_results: Optional[Dict[str, Any]] = None
    approval_id: Optional[str] = None
    approval_state: Optional[str] = None
    integration_state: Optional[str] = None
    error: Optional[str] = None
    transitions: List[MergeTransitionRecord] = []
    created_at: str
    updated_at: str
    correlation_id: str


# =============================================================================
# Phase 10: Autonomous Engineering Intelligence & Control Plane Schemas
# =============================================================================

class ProviderType(str, Enum):
    MOCK = "mock"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL = "local"


class ProviderHealthStatus(str, Enum):
    READY = "READY"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    DEGRADED = "DEGRADED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    ERROR = "ERROR"


class ProviderErrorType(str, Enum):
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INVALID_REQUEST = "INVALID_REQUEST"
    CONTENT_POLICY_REJECTION = "CONTENT_POLICY_REJECTION"
    QUOTA_EXHAUSTION = "QUOTA_EXHAUSTION"
    COST_POLICY_REJECTION = "COST_POLICY_REJECTION"
    INTERNAL_PROVIDER_ERROR = "INTERNAL_PROVIDER_ERROR"


class ProviderMetadata(BaseModel):
    provider_name: str
    model_id: str
    context_window: int
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    cost_per_1k_tokens: float = 0.0
    provider: Optional[str] = None
    model: Optional[str] = None
    supports_streaming: bool = True
    supports_tools: bool = True
    is_local: bool = False

    def __init__(self, **data):
        if "provider" not in data and "provider_name" in data:
            data["provider"] = data["provider_name"]
        if "model" not in data and "model_id" in data:
            data["model"] = data["model_id"]
        if "cost_per_1k_tokens" not in data and "cost_per_1k_input_tokens" in data:
            data["cost_per_1k_tokens"] = data["cost_per_1k_input_tokens"]
        super().__init__(**data)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ProviderHealthResponse(BaseModel):
    provider: str
    status: ProviderHealthStatus
    available: bool
    configured: bool
    latency_ms: Optional[float] = None
    error_rate_pct: float = 0.0
    circuit_state: str = "CLOSED"
    reason: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class LLMGenerationRequest(BaseModel):
    prompt: str
    system_instruction: Optional[str] = None
    provider_preference: Optional[str] = None
    model_override: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 2048
    project_context: Optional[str] = None
    stream: bool = False


class LLMGenerationResponse(BaseModel):
    provider: str
    model: str
    content: str
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    finish_reason: str = "STOP"
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None


class EngineeringSpecRequest(BaseModel):
    directive: str
    target_project: Optional[str] = None
    context_files: List[str] = []
    constraints: List[str] = []


class ProposedModification(BaseModel):
    file_path: str
    action: str  # "MODIFY", "CREATE", "DELETE"
    rationale: str
    diff_snippet: Optional[str] = None


class EngineeringBlueprint(BaseModel):
    spec_id: str
    title: str
    directive: str
    target_project: str
    architecture_summary: str
    target_files: List[str] = []
    proposed_modifications: List[ProposedModification] = []
    test_strategy: str
    verification_assertions: List[str] = []
    risk_tier: str = "LOW"
    estimated_tokens: int = 0
    created_at: str


class TaskDAGNode(BaseModel):
    node_id: str
    agent_id: str
    title: str
    instructions: str
    dependencies: List[str] = []
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TaskDAGPlan(BaseModel):
    plan_id: str
    directive: str
    target_project: str
    nodes: Dict[str, TaskDAGNode]
    execution_order: List[List[str]]  # Topological levels for concurrent execution
    total_nodes: int
    status: str = "PENDING"  # PENDING, EXECUTING, COMPLETED, FAILED
    created_at: str
    completed_at: Optional[str] = None


class ControlPlaneTelemetryEvent(BaseModel):
    event_id: str
    timestamp: str
    event_type: str
    agent_id: Optional[str] = None
    action: str
    details: Dict[str, Any] = {}
    severity: str = "INFO"
    correlation_id: Optional[str] = None


class FleetAgentStatus(BaseModel):
    agent_id: str
    name: str
    role: str
    category: str
    status: str
    current_task: Optional[str] = None
    task_count: int = 0
    success_rate_pct: float = 100.0
    latency_p95_ms: float = 0.0
    token_velocity: int = 0
    total_tokens: int = 0
    circuit_state: str = "CLOSED"


class ControlPlaneStatus(BaseModel):
    status: str
    active_agents: int
    total_agents: int
    active_sessions: int
    active_worktrees: int
    open_circuits: int
    monthly_spend_usd: float
    zero_cost_enforced: bool
    telemetry_events_count: int
    uptime_seconds: float


class MissionState(str, Enum):
    DRAFT = "DRAFT"
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    PLANNED = "PLANNED"
    DECOMPOSED = "DECOMPOSED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    VERIFYING = "VERIFYING"
    ARBITRATING = "ARBITRATING"
    DELIVERY_PENDING = "DELIVERY_PENDING"
    DELIVERING = "DELIVERING"
    OBSERVING = "OBSERVING"
    RECOVERING = "RECOVERING"
    REMEDIATING = "REMEDIATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"


class FailureCategory(str, Enum):
    TRANSIENT = "TRANSIENT"
    DEPENDENCY = "DEPENDENCY"
    PROVIDER = "PROVIDER"
    CODE = "CODE"
    TEST = "TEST"
    SECURITY = "SECURITY"
    RESOURCE = "RESOURCE"
    STATE = "STATE"
    GIT = "GIT"
    DELIVERY = "DELIVERY"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    # Operational incident failure categories (Phase 17+)
    PROCESS_FAILURE = "PROCESS_FAILURE"
    HEALTH_CHECK_FAILURE = "HEALTH_CHECK_FAILURE"
    DEPLOYMENT_FAILURE = "DEPLOYMENT_FAILURE"
    BUILD_FAILURE = "BUILD_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    AUTH_FAILURE = "AUTH_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    WORKTREE_FAILURE = "WORKTREE_FAILURE"
    MERGE_FAILURE = "MERGE_FAILURE"
    DELIVERY_FAILURE = "DELIVERY_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"
    SECURITY_POLICY_FAILURE = "SECURITY_POLICY_FAILURE"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"
    # Backward compatible aliases
    PROCESS_CRASH = "PROCESS_FAILURE"
    PORT_CONFLICT = "NETWORK_FAILURE"
    HTTP_SLA_BREACH = "HEALTH_CHECK_FAILURE"
    SECURITY_ANOMALY = "SECURITY_POLICY_FAILURE"
    STATE_CORRUPTION = "CONFIGURATION_FAILURE"
    WORKTREE_DEADLOCK = "WORKTREE_FAILURE"
    FINOPS_SPIKE = "SECURITY_POLICY_FAILURE"


class MissionRequirement(BaseModel):
    requirement_id: str  # e.g. REQ-001
    category: str = "functional"  # functional, technical, quality, security, operational, delivery
    description: str
    acceptance_criteria: List[str] = []
    priority: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    status: str = "PENDING"  # PENDING, IN_PROGRESS, SATISFIED, BLOCKED, FAILED
    assigned_subtask_ids: List[str] = []


class AcceptanceCriterion(BaseModel):
    criterion_id: str  # e.g. AC-001
    requirement_id: Optional[str] = None
    description: str
    evaluator: str  # file_exists, test_passes, endpoint_responds, schema_valid, build_succeeds, security_scan_clean, secret_scan_clean, expected_api_contract, expected_artifact, expected_git_state, expected_deployment_health
    params: Dict[str, Any] = {}
    status: str = "PENDING"  # PENDING, PASSED, FAILED, SKIPPED
    evidence: Optional[str] = None
    timestamp: Optional[str] = None


class AgentCapability(BaseModel):
    model_config = {"extra": "allow"}
    name: str
    agent_id: Optional[str] = None
    version: str = "1.0.0"
    provider: str = "nexus"
    capabilities: List[str] = []
    supported_tasks: List[str] = []
    risk_level: RiskLevel = RiskLevel.LOW
    tools: List[str] = []
    execution_limits: Dict[str, Any] = {}
    availability: str = "AVAILABLE"  # AVAILABLE, BUSY, OFFLINE
    health: str = "HEALTHY"
    cost_policy: Dict[str, Any] = {"cost_per_token": 0.0, "max_tokens": 100000}

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if item == "agent_id":
            return getattr(self, "agent_id", None) or getattr(self, "id", default)
        return getattr(self, item, default)


class MissionCheckpoint(BaseModel):
    checkpoint_id: str
    mission_id: str
    timestamp: str
    state: str
    graph_state: Dict[str, Any] = {}
    node_states: Dict[str, Any] = {}
    artifacts: List[str] = []
    current_workspace: Optional[str] = None
    retry_counters: Dict[str, int] = {}
    acceptance_results: Dict[str, Any] = {}
    risk_state: Dict[str, Any] = {}


class TraceabilityLink(BaseModel):
    link_id: str
    requirement_id: str
    subtask_id: str
    agent_id: str
    artifact_path: Optional[str] = None
    test_id: Optional[str] = None
    acceptance_criterion_id: Optional[str] = None
    status: str = "VERIFIED"
    explanation: str = ""


class MissionKnowledge(BaseModel):
    knowledge_id: str
    category: str  # strategy, remediation, failure, decision, observation
    mission_id: str
    pattern: str
    details: Dict[str, Any] = {}
    outcome: str = "SUCCESS"
    timestamp: str


class MissionSubtask(BaseModel):
    subtask_id: str
    title: str
    description: str
    assigned_agent: str
    dependencies: List[str] = []
    target_files: List[str] = []
    risk_level: RiskLevel = RiskLevel.LOW
    status: str = "PENDING"  # PENDING, RUNNING, REMEDIATING, COMPLETED, FAILED, SKIPPED
    session_id: Optional[str] = None
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    remediation_rounds: int = 0
    max_remediation_rounds: int = 3
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    failure_category: Optional[FailureCategory] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    required_capabilities: List[str] = []
    linked_requirement_ids: List[str] = []
    tools_invoked: List[Dict[str, Any]] = []
    timeout_seconds: int = 60
    retry_count: int = 0


class MissionPlanRequest(BaseModel):
    goal: str
    project_id: Optional[str] = None
    repo_path: str = "/root/control-center"
    target_branch: str = "main"
    context_files: List[str] = []
    constraints: List[str] = []
    max_parallel_tasks: int = 3
    max_remediation_rounds: int = 3
    auto_merge: bool = True
    auto_deliver_github: bool = False
    idempotency_key: Optional[str] = None


class MissionRunRequest(BaseModel):
    goal: str
    project_id: Optional[str] = None
    repo_path: str = "/root/control-center"
    target_branch: str = "main"
    context_files: List[str] = []
    constraints: List[str] = []
    max_parallel_tasks: int = 3
    max_remediation_rounds: int = 3
    auto_merge: bool = True
    auto_deliver_github: bool = False
    background: bool = False
    idempotency_key: Optional[str] = None


class EngineeringMission(BaseModel):
    mission_id: str
    project_id: Optional[str] = None
    goal: str
    repo_path: str
    target_branch: str = "main"
    state: MissionState = MissionState.CREATED
    blueprint: Optional[EngineeringBlueprint] = None
    subtasks: List[MissionSubtask] = []
    execution_order: List[List[str]] = []
    max_parallel_tasks: int = 3
    max_remediation_rounds: int = 3
    auto_merge: bool = True
    auto_deliver_github: bool = False
    github_delivery_id: Optional[str] = None
    worktree_path: Optional[str] = None
    mission_branch: Optional[str] = None
    merge_id: Optional[str] = None
    merge_decision: Optional[Dict[str, Any]] = None
    telemetry: Dict[str, Any] = {}
    release_changelog: Optional[str] = None
    approval_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None

    # Phase 13 Extensions
    normalized_objective: Optional[str] = None
    requirements: List[MissionRequirement] = []
    acceptance_criteria: List[AcceptanceCriterion] = []
    assumptions: List[str] = []
    constraints: List[str] = []
    success_criteria: List[str] = []
    risk_profile: Dict[str, Any] = {}
    estimated_complexity: str = "MEDIUM"
    required_capabilities: List[str] = []
    dependencies: List[str] = []
    proposed_submissions: List[Dict[str, Any]] = []
    execution_strategy: Dict[str, Any] = {}
    verification_strategy: Dict[str, Any] = {}
    delivery_strategy: Dict[str, Any] = {}
    recovery_strategy: Dict[str, Any] = {}
    traceability: List[TraceabilityLink] = []
    checkpoints: List[MissionCheckpoint] = []
    events: List[Dict[str, Any]] = []
    retry_count: int = 0
    cost_estimate_usd: float = 0.0
    paused_from_state: Optional[str] = None
    factory_id: Optional[str] = None
    review_rounds: List[Dict[str, Any]] = []
    generated_artifacts: List[str] = []


class DeliveryState(str, Enum):
    LOCAL_READY = "LOCAL_READY"
    CANDIDATE_VALIDATED = "CANDIDATE_VALIDATED"
    PUBLISH_PENDING = "PUBLISH_PENDING"
    BRANCH_PUBLISHED = "BRANCH_PUBLISHED"
    PR_CREATED = "PR_CREATED"
    PR_REVIEWING = "PR_REVIEWING"
    QA_CHECKING = "QA_CHECKING"
    SECURITY_CHECKING = "SECURITY_CHECKING"
    GOVERNANCE_EVALUATION = "GOVERNANCE_EVALUATION"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    MERGE_READY = "MERGE_READY"
    MERGING = "MERGING"
    MERGED = "MERGED"
    POST_MERGE_VERIFYING = "POST_MERGE_VERIFYING"
    COMPLETED = "COMPLETED"
    # Failure & Recovery States
    PUBLISH_FAILED = "PUBLISH_FAILED"
    PR_FAILED = "PR_FAILED"
    REVIEW_FAILED = "REVIEW_FAILED"
    QA_FAILED = "QA_FAILED"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"
    GOVERNANCE_BLOCKED = "GOVERNANCE_BLOCKED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    MERGE_FAILED = "MERGE_FAILED"
    POST_MERGE_FAILED = "POST_MERGE_FAILED"
    STALE_REMOTE = "STALE_REMOTE"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    CANCELLED = "CANCELLED"


class GitHubClientMode(str, Enum):
    REAL = "REAL"
    MOCK = "MOCK"
    DRY_RUN = "DRY_RUN"


class GitHubHealthResponse(BaseModel):
    mode: GitHubClientMode
    configured: bool
    authenticated: bool
    status: str
    user: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[str] = None
    reason: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class GitHubPRMetadata(BaseModel):
    session_id: Optional[str] = None
    execution_id: Optional[str] = None
    candidate_id: Optional[str] = None
    source_commit: str
    candidate_commit: str
    candidate_tree_sha: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    verification_summary: str = "Verified"
    test_summary: str = "Passed"
    security_summary: str = "Clean"
    agents_provenance: List[str] = []
    finops_spend_usd: float = 0.0


class GitHubPRInfo(BaseModel):
    pr_number: int
    title: str
    body: str
    source_branch: str
    target_branch: str
    state: str = "open"
    html_url: str
    mergeable: bool = True
    merged: bool = False
    merge_commit_sha: Optional[str] = None
    labels: List[str] = []
    reviews: List[Dict[str, Any]] = []
    checks: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str


class StructuredReviewFinding(BaseModel):
    finding_id: str
    agent_id: str
    severity: str  # "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    category: str  # "ARCHITECTURE", "SYNTAX", "QUALITY", "SECURITY", "GOVERNANCE"
    file: Optional[str] = None
    line_range: Optional[str] = None
    finding: str
    evidence: str
    recommendation: str
    blocking: bool = False


class ApprovalBinding(BaseModel):
    session_id: str
    execution_id: str
    candidate_id: Optional[str] = None
    candidate_commit_sha: str
    candidate_tree_sha: Optional[str] = None
    target_branch: str
    risk_level: RiskLevel
    approval_id: str
    consumed: bool = False
    bound_at: str


class DeliveryRecord(BaseModel):
    delivery_id: str
    session_id: Optional[str] = None
    candidate_id: Optional[str] = None
    repo_name: str = "control-center"
    repo_path: str = "/root/control-center"
    source_branch: str
    target_branch: str = "main"
    published_branch: Optional[str] = None
    source_commit: Optional[str] = None
    candidate_commit: Optional[str] = None
    candidate_tree_sha: Optional[str] = None
    state: DeliveryState = DeliveryState.LOCAL_READY
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    approval_id: Optional[str] = None
    approval_binding: Optional[ApprovalBinding] = None
    structured_findings: List[StructuredReviewFinding] = []
    review_results: List[Dict[str, Any]] = []
    checks_results: List[Dict[str, Any]] = []
    governance_verdict: Optional[Dict[str, Any]] = None
    merge_commit_sha: Optional[str] = None
    post_merge_verified: bool = False
    transitions: List[TransitionRecord] = []
    error: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


class DeliveryPublishRequest(BaseModel):
    candidate_id: Optional[str] = None
    session_id: Optional[str] = None
    repo_path: str = "/root/control-center"
    repo_name: Optional[str] = None
    source_branch: Optional[str] = None
    target_branch: str = "main"
    dry_run: bool = False


class DeliveryPRCreateRequest(BaseModel):
    delivery_id: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    labels: List[str] = []
    auto_review: bool = True
    auto_merge: bool = False


class DeliveryMergeRequest(BaseModel):
    delivery_id: Optional[str] = None
    pr_number: Optional[int] = None
    merge_method: str = "squash"
    commit_title: Optional[str] = None
    commit_message: Optional[str] = None
    approval_id: Optional[str] = None


# =============================================================================
# Phase 14: Autonomous Software Factory Schemas
# =============================================================================

class ReviewRoundFinding(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    severity: str = "WARNING"  # INFO, WARNING, ERROR, CRITICAL
    category: str = "CODE_QUALITY"  # SYNTAX, LOGIC, SECURITY, TEST_FAILURE, LINT, CONTRACT
    message: str
    suggested_fix: Optional[str] = None


class ReviewRound(BaseModel):
    iteration: int
    reviewer_agent: str = "QA-VERIFIER"
    developer_agent: str = "DEVELOPER-02"
    verdict: str = "APPROVED"  # APPROVED, CHANGES_REQUESTED, FAILED
    summary: str
    findings: List[ReviewRoundFinding] = []
    diff_applied: Optional[str] = None
    tests_passed: bool = True
    security_clean: bool = True
    timestamp: str


class FactoryProjectCreateRequest(BaseModel):
    project_name: str
    project_id: Optional[str] = None
    goal: str
    template: str = "fastapi_service"  # fastapi_service, node_service, cli_tool, fullstack_app, data_pipeline, custom
    base_path: str = "/root/projects"
    init_git: bool = True
    autonomy_tier: str = "Autonomous"
    auto_merge: bool = True
    auto_deliver_github: bool = False
    max_parallel_tasks: int = 3
    max_remediation_rounds: int = 3
    requirements_override: Optional[List[str]] = None


class FactoryGoalExecuteRequest(BaseModel):
    goal: str
    project_id: Optional[str] = None
    target_path: Optional[str] = None
    target_branch: str = "main"
    template: str = "auto"
    autonomy_tier: str = "Autonomous"
    auto_merge: bool = True
    auto_deliver_github: bool = False
    max_parallel_tasks: int = 3
    max_remediation_rounds: int = 3
    background: bool = False


class FactoryMissionRecord(BaseModel):
    factory_id: str
    mission_id: str
    project_id: str
    project_name: str
    project_path: str
    goal: str
    template: str = "fastapi_service"
    stage: str = "PLANNING"  # PLANNING, SCAFFOLDING, SYNTHESIZING, REVIEWING, REMEDIATING, TESTING, ACCEPTANCE, MERGING, COMPLETED, FAILED, CANCELLED
    review_rounds: List[ReviewRound] = []
    generated_artifacts: List[str] = []
    acceptance_evidence: Dict[str, Any] = {}
    telemetry: Dict[str, Any] = {}
    error: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


# =============================================================================
# Phase 15: Universal Tool & App Integration Models
# =============================================================================

class ToolProtocolType(str, Enum):
    NATIVE_PYTHON = "NATIVE_PYTHON"
    REST_API = "REST_API"
    CLI_EXECUTABLE = "CLI_EXECUTABLE"
    MCP_STDIO = "MCP_STDIO"
    MCP_SSE = "MCP_SSE"
    MCP_HTTP = "MCP_HTTP"
    DATABASE_QUERY = "DATABASE_QUERY"
    WEBHOOK = "WEBHOOK"


class ToolCategory(str, Enum):
    FILESYSTEM = "FILESYSTEM"
    GIT_VCS = "GIT_VCS"
    DEPLOYMENT = "DEPLOYMENT"
    DATABASE = "DATABASE"
    SECURITY = "SECURITY"
    COMMUNICATION = "COMMUNICATION"
    WEB_BROWSER = "WEB_BROWSER"
    SYSTEM_OS = "SYSTEM_OS"
    AI_COGNITION = "AI_COGNITION"
    CUSTOM_PLUGIN = "CUSTOM_PLUGIN"


class UniversalToolManifest(BaseModel):
    tool_id: str
    name: str
    description: str
    protocol: ToolProtocolType = ToolProtocolType.NATIVE_PYTHON
    category: ToolCategory = ToolCategory.SYSTEM_OS
    endpoint: Optional[str] = None
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    required_capabilities: List[str] = []
    allowed_agents: List[str] = ["*"]
    timeout: int = 30
    write_capability: bool = False
    enabled: bool = True
    health_status: str = "HEALTHY"
    invocation_count: int = 0
    total_duration_ms: float = 0.0
    last_invoked: Optional[str] = None
    metadata: Dict[str, Any] = {}


class UniversalToolInvocationRequest(BaseModel):
    tool_id: str
    parameters: Dict[str, Any] = {}
    caller_agent_id: Optional[str] = "agent-user"
    caller_execution_id: Optional[str] = None
    async_execution: bool = False
    timeout_override: Optional[int] = None


class UniversalToolInvocationResult(BaseModel):
    invocation_id: str
    tool_id: str
    status: str  # SUCCESS, FAILED, TIMEOUT, APPROVAL_REQUIRED, BLOCKED
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    caller_agent_id: Optional[str] = None
    executed_at: str
    audit_id: Optional[str] = None


class ConnectedApp(BaseModel):
    app_id: str
    name: str
    category: str
    description: str
    status: str  # CONNECTED, DEGRADED, DISCONNECTED, AUTH_REQUIRED
    icon: Optional[str] = None
    capabilities: List[str] = []
    tools_provided: List[str] = []
    endpoint: Optional[str] = None
    health_check_url: Optional[str] = None
    last_health_check: Optional[str] = None
    auth_configured: bool = True
    metadata: Dict[str, Any] = {}


class MCPServerDefinition(BaseModel):
    server_id: str
    name: str
    description: Optional[str] = ""
    transport: str = "stdio"  # stdio, sse, http
    command_or_url: str
    env: Dict[str, str] = {}
    args: List[str] = []
    status: str = "DISCONNECTED"  # CONNECTED, DISCONNECTED, ERROR
    exposed_tools: List[Dict[str, Any]] = []
    connected_at: Optional[str] = None
    latency_ms: float = 0.0
    error: Optional[str] = None


class PluginManifest(BaseModel):
    plugin_id: str
    name: str
    version: str = "1.0.0"
    author: Optional[str] = "NEXUS"
    description: str = ""
    entrypoint: str
    category: str = "CUSTOM_PLUGIN"
    tools: List[UniversalToolManifest] = []
    enabled: bool = True
    installed_at: str


# ==============================================================================
# PHASE 16: PRODUCTION DEPLOYMENT ENGINE SCHEMAS
# ==============================================================================

class DeploymentTargetType(str, Enum):
    LOCAL_PROCESS = "LOCAL_PROCESS"
    DOCKER_CONTAINER = "DOCKER_CONTAINER"
    VERCEL_EDGE = "VERCEL_EDGE"
    GCP_CLOUD_RUN = "GCP_CLOUD_RUN"
    TERMUX_NODE = "TERMUX_NODE"
    STATIC_BUNDLE = "STATIC_BUNDLE"


class DeploymentEnvironment(str, Enum):
    LOCAL = "LOCAL"
    PREVIEW = "PREVIEW"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class DeploymentStrategy(str, Enum):
    ROLLING = "ROLLING"
    BLUE_GREEN = "BLUE_GREEN"
    CANARY = "CANARY"
    DIRECT_REPLACE = "DIRECT_REPLACE"
    INSTANT_RELOAD = "INSTANT_RELOAD"


class DeploymentStageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class DeploymentOverallStatus(str, Enum):
    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    DEPLOYING = "DEPLOYING"
    VERIFYING = "VERIFYING"
    LIVE = "LIVE"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"


class DeploymentStage(BaseModel):
    stage_name: str
    status: DeploymentStageStatus = DeploymentStageStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    logs: List[str] = []
    error: Optional[str] = None
    metrics: Dict[str, Any] = {}


class DeploymentManifest(BaseModel):
    deployment_id: str
    project_id: str = "control-center"
    service_name: str = "nexus-service"
    version: str = "1.0.0"
    commit_sha: str = "HEAD"
    environment: DeploymentEnvironment = DeploymentEnvironment.LOCAL
    target_type: DeploymentTargetType = DeploymentTargetType.LOCAL_PROCESS
    strategy: DeploymentStrategy = DeploymentStrategy.DIRECT_REPLACE
    canary_percentage: int = 100
    image_tag: Optional[str] = None
    config_env: Dict[str, str] = {}
    secrets_bound: List[str] = []
    health_check_path: str = "/api/health"
    timeout_seconds: int = 120
    created_at: str


class DeploymentRecord(BaseModel):
    deployment_id: str
    project_id: str
    service_name: str
    version: str
    commit_sha: str
    environment: DeploymentEnvironment
    target_type: DeploymentTargetType
    strategy: DeploymentStrategy
    status: DeploymentOverallStatus
    current_stage: str
    stages: List[DeploymentStage] = []
    deployed_url: Optional[str] = None
    canary_percentage: int = 100
    active_instances: int = 1
    health_status: str = "UNKNOWN"  # HEALTHY, UNHEALTHY, DEGRADED, UNKNOWN
    error: Optional[str] = None
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    requires_approval: bool = False
    approval_id: Optional[str] = None
    created_by: str = "system"
    created_at: str
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    rollback_target_id: Optional[str] = None
    changelog: List[str] = []
    dora_lead_time_seconds: float = 0.0
    metadata: Dict[str, Any] = {}


class DeploymentRequest(BaseModel):
    project_id: str = "control-center"
    service_name: Optional[str] = "nexus-core"
    version: Optional[str] = None
    commit_sha: Optional[str] = "HEAD"
    environment: DeploymentEnvironment = DeploymentEnvironment.LOCAL
    target_type: DeploymentTargetType = DeploymentTargetType.LOCAL_PROCESS
    strategy: DeploymentStrategy = DeploymentStrategy.DIRECT_REPLACE
    canary_percentage: Optional[int] = 100
    image_tag: Optional[str] = None
    config_env: Optional[Dict[str, str]] = {}
    health_check_path: Optional[str] = "/api/health"
    auto_rollback_on_failure: bool = True
    created_by: Optional[str] = "developer"
    notes: Optional[str] = None


class RollbackRequest(BaseModel):
    deployment_id: str
    target_version: Optional[str] = None
    reason: Optional[str] = "Manual rollback triggered"
    force: bool = False


class CanaryPromoteRequest(BaseModel):
    deployment_id: str
    target_percentage: int = 100
    auto_promote_delay_seconds: Optional[int] = 0


class DORAMetrics(BaseModel):
    deployment_frequency_per_week: float = 0.0
    lead_time_for_changes_minutes: float = 0.0
    change_failure_rate_percent: float = 0.0
    mean_time_to_recovery_minutes: float = 0.0
    total_deployments: int = 0
    successful_deployments: int = 0
    failed_deployments: int = 0
    rollbacks_count: int = 0
    calculated_at: str


class EnvironmentStatus(BaseModel):
    environment_name: str
    status: str  # ACTIVE, IDLE, DEGRADED, MAINTENANCE
    active_deployment_id: Optional[str] = None
    active_version: Optional[str] = None
    active_commit: Optional[str] = None
    target_type: Optional[str] = None
    url: Optional[str] = None
    traffic_split: Dict[str, int] = {}
    last_deployed_at: Optional[str] = None
    health_status: str = "HEALTHY"


# ==============================================================================
# PHASE 17: AUTONOMOUS SELF-HEALING OPERATIONS ENGINE SCHEMAS
# ==============================================================================

# FailureCategory is unified above in Phase 13 / Phase 17 schemas


class IncidentSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    # Backward compatible aliases
    SEV_1_CRITICAL = "CRITICAL"
    SEV_2_HIGH = "HIGH"
    SEV_3_MEDIUM = "MEDIUM"
    SEV_4_LOW = "LOW"


# Alias for backward compatibility
IncidentCategory = FailureCategory


class IncidentStatus(str, Enum):
    OBSERVED = "OBSERVED"
    DETECTED = "DETECTED"
    CORRELATED = "CORRELATED"
    CLASSIFIED = "CLASSIFIED"
    DIAGNOSING = "DIAGNOSING"
    PLANNING = "PLANNING"
    POLICY_CHECK = "POLICY_CHECK"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    REMEDIATING = "REMEDIATING"
    HEALING_EXECUTING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    ROLLED_BACK = "ROLLED_BACK"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    STOPPED = "STOPPED"
    PLANNING_REMEDIATION = "PLANNING"


class WatchdogType(str, Enum):
    PROCESS_SUPERVISOR = "PROCESS_SUPERVISOR"
    PORT_AVAILABILITY = "PORT_AVAILABILITY"
    RESOURCE_PRESSURE = "RESOURCE_PRESSURE"
    HTTP_SLA = "HTTP_SLA"
    SECURITY_SENTINEL = "SECURITY_SENTINEL"
    WORKTREE_HEALTH = "WORKTREE_HEALTH"


class WatchdogStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    ALERTING = "ALERTING"
    OFFLINE = "OFFLINE"


class WatchdogCheckResult(BaseModel):
    watchdog_id: str
    watchdog_type: WatchdogType
    name: str
    status: WatchdogStatus
    message: str
    metrics: Dict[str, Any] = {}
    timestamp: str
    incident_triggered: bool = False


class DiagnosisEvidence(BaseModel):
    observed_facts: List[str] = []
    hypotheses: List[str] = []
    evidence_sources: List[str] = []
    confidence_score: float = 1.0
    root_cause_candidate: str = "Unknown anomaly"


class HealingAction(BaseModel):
    action_id: str
    name: str
    playbook_id: str
    status: str = "PENDING"  # PENDING, RUNNING, SUCCESS, FAILED
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    logs: List[str] = []
    result: Optional[str] = None
    error: Optional[str] = None


class RemediationPlaybook(BaseModel):
    playbook_id: str
    name: str
    category: FailureCategory
    description: str
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    steps: List[str] = []
    success_rate: float = 100.0
    execution_count: int = 0
    estimated_cost_usd: float = 0.0


class RecoveryPolicy(BaseModel):
    max_recovery_attempts: int = 3
    backoff_base_seconds: float = 1.0
    cooldown_seconds: float = 30.0
    remediation_budget_usd: float = 0.0
    loop_window_seconds: float = 300.0
    max_loop_count: int = 3
    circuit_breaker_threshold: int = 5
    concurrent_recovery_limit: int = 2


class RecoveryHistoryRecord(BaseModel):
    recovery_id: str
    incident_id: str
    timestamp: str
    action: str
    result: str
    verification_passed: bool = True
    duration_seconds: float = 0.0
    operator: Optional[str] = "autonomous-operations-engine"
    notes: Optional[str] = None


class IncidentRecord(BaseModel):
    incident_id: str
    title: str
    category: FailureCategory
    severity: IncidentSeverity
    status: IncidentStatus
    source_watchdog: Optional[str] = None
    target_resource: str
    root_cause_analysis: Optional[str] = None
    diagnosis_evidence: Optional[DiagnosisEvidence] = None
    detected_at: str
    diagnosed_at: Optional[str] = None
    resolved_at: Optional[str] = None
    duration_seconds: float = 0.0
    remediation_playbook_id: Optional[str] = None
    healing_actions: List[HealingAction] = []
    requires_approval: bool = False
    approval_id: Optional[str] = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    deduplication_hash: Optional[str] = None
    correlation_id: Optional[str] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    post_mortem: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class TriggerIncidentRequest(BaseModel):
    category: FailureCategory = FailureCategory.PROCESS_FAILURE
    severity: Optional[IncidentSeverity] = IncidentSeverity.MEDIUM
    title: str
    target_resource: str = "nexus-system"
    details: Optional[Dict[str, Any]] = {}
    auto_remediate: bool = True


class RemediateIncidentRequest(BaseModel):
    playbook_id: Optional[str] = None
    force: bool = False
    operator_notes: Optional[str] = None


class OperationsMetrics(BaseModel):
    system_health: str = "HEALTHY"
    uptime_pct: float = 99.99
    active_incidents: int = 0
    resolved_incidents: int = 0
    escalated_incidents: int = 0
    mean_time_to_recover_seconds: float = 0.0
    remediation_success_rate_pct: float = 100.0
    incident_frequency_per_hour: float = 0.0
    failure_distribution: Dict[str, int] = {}
    active_circuit_breakers: List[str] = []
    daemon_loop_active: bool = True
    calculated_at: str = ""


class SelfHealingTelemetry(BaseModel):
    overall_uptime_pct: float = 99.99
    active_incidents_count: int = 0
    resolved_incidents_count: int = 0
    auto_remediation_success_rate_pct: float = 100.0
    mean_time_to_healing_seconds: float = 0.0
    watchdogs: List[WatchdogCheckResult] = []
    active_playbooks_count: int = 0
    calculated_at: str


# ==============================================================================
# PHASE 18: AUTONOMOUS SECURITY & COMPLIANCE OPERATIONS ENGINE SCHEMAS
# ==============================================================================

class ThreatSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class VulnerabilityCategory(str, Enum):
    SECRET_LEAK = "SECRET_LEAK"
    SAST_INJECTION = "SAST_INJECTION"
    DEPENDENCY_CVE = "DEPENDENCY_CVE"
    PERMISSIONS_WEAKENING = "PERMISSIONS_WEAKENING"
    INSECURE_COMMUNICATION = "INSECURE_COMMUNICATION"
    LICENSE_NONCOMPLIANCE = "LICENSE_NONCOMPLIANCE"
    SANDBOX_ESCAPE_RISK = "SANDBOX_ESCAPE_RISK"
    PROMPT_INJECTION = "PROMPT_INJECTION"


class ComplianceFramework(str, Enum):
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    CIS_BENCHMARK = "CIS_BENCHMARK"
    NIST_800_53 = "NIST_800_53"
    GDPR_PRIVACY = "GDPR_PRIVACY"
    FINOPS_ZERO_COST = "FINOPS_ZERO_COST"


class FindingStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    SCANNING = "SCANNING"
    ANALYZING = "ANALYZING"
    CLASSIFIED = "CLASSIFIED"
    POLICY_CHECK = "POLICY_CHECK"
    REMEDIATION_PENDING = "REMEDIATION_PENDING"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    QUARANTINED = "QUARANTINED"
    REMEDIATED = "REMEDIATED"
    SUPPRESSED = "SUPPRESSED"


class FindingConfidence(str, Enum):
    CONFIRMED_FINDING = "CONFIRMED_FINDING"
    HEURISTIC_FINDING = "HEURISTIC_FINDING"
    NOT_SCANNED = "NOT_SCANNED"


class ScannerAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    SCANNER_UNAVAILABLE = "SCANNER_UNAVAILABLE"
    EXTERNAL_INTELLIGENCE_UNAVAILABLE = "EXTERNAL_INTELLIGENCE_UNAVAILABLE"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"
    QUARANTINE = "QUARANTINE"


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NOT_ASSESSED = "NOT_ASSESSED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RiskDimensions(BaseModel):
    exploitability: float = 5.0      # 0.0 to 10.0
    exposure: float = 5.0            # 0.0 to 10.0
    affected_scope: str = "LOCAL"    # LOCAL, MODULE, REPO, SYSTEM, CLOUD
    privilege_level: str = "USER"    # USER, SERVICE, ADMIN, ROOT
    data_sensitivity: str = "NONE"   # NONE, INTERNAL, CONFIDENTIAL, SECRET
    production_impact: str = "NONE"  # NONE, DEGRADED, HIGH, CRITICAL
    reversibility: str = "HIGH"      # HIGH, MEDIUM, LOW, IRREVERSIBLE
    confidence: FindingConfidence = FindingConfidence.CONFIRMED_FINDING


class SecurityFinding(BaseModel):
    finding_id: str
    fingerprint: Optional[str] = None
    title: str
    category: VulnerabilityCategory
    severity: ThreatSeverity
    status: FindingStatus = FindingStatus.OPEN
    confidence: FindingConfidence = FindingConfidence.CONFIRMED_FINDING
    risk_dimensions: RiskDimensions = RiskDimensions()
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    snippet: Optional[str] = None
    remediation_advice: str = ""
    cve_id: Optional[str] = None
    cvss_score: float = 0.0
    detected_at: str
    resolved_at: Optional[str] = None
    details: Dict[str, Any] = {}
    policy_eval_id: Optional[str] = None
    correlation_id: Optional[str] = None


class ComplianceControlResult(BaseModel):
    control_id: str
    framework: ComplianceFramework
    title: str
    status: ComplianceStatus = ComplianceStatus.COMPLIANT
    passed: bool = True
    score: float = 100.0  # 0.0 to 100.0
    details: str
    evidence: List[str] = []
    remediation_guidance: Optional[str] = None
    assessed_at: Optional[str] = None


class SecurityScanRequest(BaseModel):
    target_path: Optional[str] = None
    scan_types: List[str] = ["SECRETS", "SAST", "DEPENDENCIES", "COMPLIANCE"]
    include_secrets: bool = True
    include_sast: bool = True
    include_dependencies: bool = True
    auto_quarantine_critical: bool = False
    deep_ast_scan: bool = True
    max_depth: int = 6
    session_id: Optional[str] = None


class SecurityScanReport(BaseModel):
    scan_id: str
    target_path: str
    started_at: str
    completed_at: str
    duration_seconds: float
    total_files_scanned: int
    findings: List[SecurityFinding] = []
    risk_score: float = 0.0  # 0.0 (clean) to 100.0 (high risk)
    pass_status: bool = True
    compliance_summary: Dict[str, float] = {}
    scanner_availability: Dict[str, str] = {}
    session_id: Optional[str] = None


class QuarantineRecord(BaseModel):
    quarantine_id: str
    finding_id: str
    source_mission_id: Optional[str] = None
    source_session_id: Optional[str] = None
    original_path: str
    quarantined_path: str
    permissions_applied: str = "0600"
    quarantined_at: str
    released_at: Optional[str] = None
    operator: str = "autonomous-secops-engine"
    reason: str = ""
    evidence: Dict[str, Any] = {}
    notes: Optional[str] = None


class SecurityPolicyRule(BaseModel):
    rule_id: str
    name: str
    category: str
    target_action: str
    decision: PolicyDecision
    condition: str
    rationale: str
    requires_approval_role: Optional[str] = None
    active: bool = True


class SecurityPolicyEvaluationRecord(BaseModel):
    eval_id: str
    rule_id: str
    decision: PolicyDecision
    target: str
    reason: str
    actor: str
    evaluated_at: str
    finding_ids: List[str] = []
    evidence: Dict[str, Any] = {}
    session_id: Optional[str] = None


class SecurityEvidenceRecord(BaseModel):
    evidence_id: str
    session_id: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    tree_sha: Optional[str] = None
    scan_id: str
    timestamp: str
    policy_version: str = "v1.0"
    findings_count: int = 0
    passed: bool = True
    details: Dict[str, Any] = {}


class SecurityAdvisory(BaseModel):
    advisory_id: str
    title: str
    severity: ThreatSeverity
    framework: Optional[ComplianceFramework] = None
    recommendations: List[str] = []
    created_at: str
    published: bool = True


class SecOpsTelemetry(BaseModel):
    overall_security_posture_score: float = 100.0  # 0.0 to 100.0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    quarantined_threats: int = 0
    compliance_scores: Dict[str, float] = {}
    active_scanners: List[str] = []
    zero_trust_status: str = "ENFORCED"
    last_verified_posture: str = "CLEAN"
    blocked_operations_count: int = 0
    calculated_at: str = ""


# =========================================================================
# PHASE 19: AUTONOMOUS KNOWLEDGE, LEARNING & OPTIMIZATION SCHEMAS
# =========================================================================

class KnowledgeTier(str, Enum):
    EPISODIC = "EPISODIC"       # Point-in-time mission/incident traces and execution logs
    SEMANTIC = "SEMANTIC"       # Abstract code concepts, error patterns, architectural heuristics
    PROCEDURAL = "PROCEDURAL"   # Step-by-step playbooks, DAG strategies, verification recipes
    META = "META"               # Learning heuristics, decay rates, model capability evaluations


class InsightCategory(str, Enum):
    ARCHITECTURE = "ARCHITECTURE"
    CODE_PATTERN = "CODE_PATTERN"
    REMEDIATION = "REMEDIATION"
    SECURITY = "SECURITY"
    DEPLOYMENT = "DEPLOYMENT"
    FINOPS = "FINOPS"
    TOOL_USAGE = "TOOL_USAGE"
    PERFORMANCE = "PERFORMANCE"
    QUALITY = "QUALITY"
    OPERATIONAL = "OPERATIONAL"



class InsightConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    EXPERIMENTAL = "EXPERIMENTAL"


class OptimizationStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class KnowledgeNode(BaseModel):
    node_id: str
    tier: KnowledgeTier
    category: InsightCategory
    title: str
    content: str
    tags: List[str] = []
    fingerprint: str = ""
    status: str = "ACTIVE"           # ACTIVE, ARCHIVED, RETIRED, STALE, CONTRADICTED
    source_mission_id: Optional[str] = None
    source_incident_id: Optional[str] = None
    source_finding_id: Optional[str] = None
    confidence: InsightConfidence = InsightConfidence.HIGH
    success_score: float = 1.0       # 0.0 to 1.0 reinforcement metric
    access_count: int = 0
    decay_factor: float = 1.0        # Multiplier applied during retrieval ranking
    revalidated_at: Optional[str] = None
    contradicted_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = {}


class KnowledgeGraphEdge(BaseModel):
    edge_id: str
    source_id: str
    target_id: str
    relation_type: str              # e.g. "REMEDIATES", "CAUSED_BY", "OPTIMIZES", "DERIVED_FROM"
    weight: float = 1.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class LearningInsight(BaseModel):
    insight_id: str
    title: str
    category: InsightCategory
    pattern: str
    rationale: str
    recommended_action: str
    supporting_evidence: List[str] = []
    confidence: InsightConfidence = InsightConfidence.HIGH
    recurrence_count: int = 1
    impacted_subsystems: List[str] = []
    source_references: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class OptimizationRecommendation(BaseModel):
    recommendation_id: str
    target_domain: str              # e.g. "DAG_SCHEDULING", "PROMPT_CONTEXT", "TOOL_ROUTING", "FINOPS_ZERO_COST"
    title: str
    description: str
    why: str = ""
    evidence: List[str] = []
    baseline_metric: str = ""
    projected_metric: str = ""
    confidence: InsightConfidence = InsightConfidence.HIGH
    scope: str = "LOCAL"
    expected_impact: str = ""
    risk: str = "LOW"
    reversibility: str = "HIGH"
    approval_required: bool = False
    suggested_strategy: str = ""
    status: OptimizationStatus = OptimizationStatus.PROPOSED
    applied_at: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ContextOptimizationRequest(BaseModel):
    query_context: str
    target_agent_role: str = "Engineer"
    max_token_budget: int = 2000
    category_filter: Optional[InsightCategory] = None
    tier_filter: Optional[KnowledgeTier] = None


class ContextOptimizationResponse(BaseModel):
    optimized_context: str
    selected_patterns: List[KnowledgeNode] = []
    estimated_tokens_used: int = 0
    tokens_saved: int = 0
    confidence: InsightConfidence = InsightConfidence.HIGH


class DAGOptimizationPlan(BaseModel):
    mission_id: str
    original_step_count: int
    critical_path_length: int
    parallelizable_groups: List[List[str]] = []
    recommended_execution_order: List[List[str]] = []
    estimated_speedup_percent: float = 0.0
    rationale: str = ""


class ToolPerformanceMetric(BaseModel):
    tool_id: str
    total_invocations: int = 0
    success_rate_percent: float = 100.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_patterns: List[str] = []
    reliability_tier: str = "HIGH"   # HIGH, MEDIUM, DEGRADED


class KnowledgeTelemetry(BaseModel):
    total_nodes: int = 0
    episodic_nodes: int = 0
    semantic_nodes: int = 0
    procedural_nodes: int = 0
    total_edges: int = 0
    total_insights: int = 0
    active_optimizations: int = 0
    average_retrieval_latency_ms: float = 0.0
    knowledge_health_score: float = 100.0
    finops_zero_cost_verified: bool = True
    last_learning_sweep_at: str = ""


# =============================================================================
# PHASE 20: AUTONOMOUS MISSION INTELLIGENCE & ADAPTIVE EXECUTION
# =============================================================================

class AdaptiveNodeState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ADAPTED = "ADAPTED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    DEGRADED = "DEGRADED"
    ESCALATED = "ESCALATED"


class AdaptationStrategy(str, Enum):
    RETRY_WITH_KNOWLEDGE = "RETRY_WITH_KNOWLEDGE"
    DYNAMIC_FALLBACK_BRANCH = "DYNAMIC_FALLBACK_BRANCH"
    INJECT_REMEDIATION_SUBDAG = "INJECT_REMEDIATION_SUBDAG"
    GRACEFUL_DEGRADATION = "GRACEFUL_DEGRADATION"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"


class IntentComplexity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    DERIVED_PATTERN = "DERIVED_PATTERN"
    HEURISTIC = "HEURISTIC"
    HYPOTHESIS = "HYPOTHESIS"


class RiskSignal(BaseModel):
    signal_id: str
    mission_id: str
    signal_type: str
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    evidence: List[str] = []
    affected_components: List[str] = []
    recommendation: str = ""
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SimilarMissionMatch(BaseModel):
    mission_id: str
    goal: str
    similarity_score: float = 0.0
    outcome: str = "COMPLETED"
    matching_factors: List[str] = []
    reusable_patterns: List[str] = []


class MissionIntelligenceContext(BaseModel):
    context_id: str
    mission_id: str
    goal: str
    similar_missions: List[SimilarMissionMatch] = []
    relevant_knowledge_nodes: List[Dict[str, Any]] = []
    risk_signals: List[RiskSignal] = []
    recommended_agents: Dict[str, float] = {}
    recommended_tools: List[str] = []
    token_budget: int = 4000
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MissionDecision(BaseModel):
    decision_id: str
    mission_id: str
    task_id: Optional[str] = None
    step_index: int = 0
    why: str
    evidence: List[str] = []
    confidence: ConfidenceLevel = ConfidenceLevel.OBSERVED_FACT
    risk: str = "LOW"
    alternatives_considered: List[str] = []
    expected_effect: str = ""
    traceability_link: Dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class KnowledgeFeedbackRecord(BaseModel):
    feedback_id: str
    mission_id: str
    insight_id: Optional[str] = None
    category: str = "OPERATIONAL"
    pattern: str = ""
    outcome: str = "SUCCESS"
    supporting_evidence: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MissionIntentAnalysis(BaseModel):
    intent_id: str
    raw_goal: str
    refined_objective: str
    complexity: IntentComplexity = IntentComplexity.MEDIUM
    explicit_constraints: List[str] = []
    implicit_assumptions: List[str] = []
    required_capabilities: List[str] = []
    target_subsystems: List[str] = []
    estimated_token_budget: int = 4000
    finops_zero_cost_required: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdaptiveTaskNode(BaseModel):
    task_id: str
    title: str
    description: str
    assigned_agent_role: str = "Engineer"
    depends_on: List[str] = []
    state: AdaptiveNodeState = AdaptiveNodeState.PENDING
    timeout_seconds: int = 60
    max_retries: int = 2
    retry_count: int = 0
    token_budget: int = 1000
    tokens_used: int = 0
    fallback_task_id: Optional[str] = None
    remediation_subdag_ids: List[str] = []
    execution_command: Optional[str] = None
    expected_artifacts: List[str] = []
    actual_artifacts: List[str] = []
    output: Optional[str] = None
    error_message: Optional[str] = None
    state_hash: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = {}


class MissionAdaptationEvent(BaseModel):
    event_id: str
    mission_id: str
    task_id: str
    trigger_reason: str
    strategy: AdaptationStrategy
    knowledge_node_id_used: Optional[str] = None
    why: str = ""
    evidence: List[str] = []
    injected_task_ids: List[str] = []
    resulting_state: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdaptiveMissionPlan(BaseModel):
    mission_id: str
    project_id: str = "control-center"
    goal: str
    intent_analysis: MissionIntentAnalysis
    tasks: Dict[str, AdaptiveTaskNode] = {}
    execution_waves: List[List[str]] = []
    overall_state: str = "DRAFT"  # DRAFT, READY, RUNNING, ADAPTING, COMPLETED, FAILED, PAUSED
    total_token_budget: int = 4000
    total_tokens_consumed: int = 0
    replan_count: int = 0
    max_replans: int = 3
    context_id: Optional[str] = None
    decisions: List[str] = []
    risk_signals: List[RiskSignal] = []
    adaptation_history: List[MissionAdaptationEvent] = []
    provenance_chain_hash: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MissionSynthesizeRequest(BaseModel):
    goal: str
    project_id: str = "control-center"
    context_hints: List[str] = []
    max_token_budget: int = 5000
    allow_speculative: bool = True


class MissionExecutionRequest(BaseModel):
    mission_id: Optional[str] = None
    dry_run: bool = False
    auto_remediate: bool = True
    concurrency_limit: int = 4


class DynamicAdaptRequest(BaseModel):
    task_id: str
    forced_strategy: Optional[AdaptationStrategy] = None
    reason: str = "Manual override / runtime anomaly"


class ReplanMissionRequest(BaseModel):
    mission_id: str
    reason: str
    failure_task_id: Optional[str] = None


class AdaptiveExecutionTelemetry(BaseModel):
    active_missions: int = 0
    completed_missions: int = 0
    total_adaptations: int = 0
    total_replans: int = 0
    successful_recoveries: int = 0
    average_task_latency_ms: float = 0.0
    tokens_saved_by_optimization: int = 0
    finops_zero_cost_verified: bool = True
    last_heartbeat: str = ""


# ==============================================================================
# PHASE 21: AUTONOMOUS SOFTWARE FACTORY & PRODUCT BUILDER SCHEMAS
# ==============================================================================

class ProductArchetype(str, Enum):
    FULLSTACK_WEB = "FULLSTACK_WEB"
    MICROSERVICE_API = "MICROSERVICE_API"
    CLI_TOOL = "CLI_TOOL"
    DATA_PIPELINE = "DATA_PIPELINE"
    AI_AGENT_SYSTEM = "AI_AGENT_SYSTEM"
    LIBRARY_SDK = "LIBRARY_SDK"


class ProductBuildStage(str, Enum):
    BLUEPRINT_SYNTHESIS = "BLUEPRINT_SYNTHESIS"
    SCAFFOLDING = "SCAFFOLDING"
    CODE_GENERATION = "CODE_GENERATION"
    TEST_SYNTHESIS = "TEST_SYNTHESIS"
    COMPILATION_AND_LINT = "COMPILATION_AND_LINT"
    TEST_EXECUTION = "TEST_EXECUTION"
    SECURITY_AUDIT = "SECURITY_AUDIT"
    SELF_CORRECTION = "SELF_CORRECTION"
    PACKAGING = "PACKAGING"
    DELIVERY_VERIFICATION = "DELIVERY_VERIFICATION"


class ProductBuildState(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SELF_CORRECTING = "SELF_CORRECTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProductComponent(BaseModel):
    component_id: str
    name: str
    archetype: ProductArchetype = ProductArchetype.FULLSTACK_WEB
    path: str
    language: str
    framework: str
    dependencies: List[str] = []
    generated_files: List[str] = []
    status: str = "PENDING"
    ast_verified: bool = False
    metadata: Dict[str, Any] = {}


class ProductSpecification(BaseModel):
    spec_id: str
    product_name: str
    summary: str
    archetype: ProductArchetype = ProductArchetype.FULLSTACK_WEB
    features: List[str] = []
    api_endpoints: List[Dict[str, Any]] = []
    data_models: List[Dict[str, Any]] = []
    security_requirements: List[str] = []
    test_requirements: List[str] = []
    target_stack: Dict[str, str] = {}
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductBuildRun(BaseModel):
    build_id: str
    product_name: str
    spec_id: str
    workspace_path: str
    current_stage: ProductBuildStage = ProductBuildStage.BLUEPRINT_SYNTHESIS
    state: ProductBuildState = ProductBuildState.PENDING
    components: List[ProductComponent] = []
    iteration: int = 1
    max_iterations: int = 5
    test_results: Dict[str, Any] = {}
    security_findings: List[Dict[str, Any]] = []
    corrections_applied: List[Dict[str, Any]] = []
    slsa_provenance_hash: str = ""
    provenance_chain_hash: str = ""
    total_tokens_consumed: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


class ProductSynthesizeRequest(BaseModel):
    prompt: str
    archetype: Optional[ProductArchetype] = None
    product_name: Optional[str] = None
    stack_preferences: Optional[Dict[str, str]] = None
    auto_build: bool = False


class ProductBuildRequest(BaseModel):
    spec_id: Optional[str] = None
    prompt: Optional[str] = None
    product_name: Optional[str] = None
    archetype: ProductArchetype = ProductArchetype.FULLSTACK_WEB
    dry_run: bool = False
    auto_repair: bool = True
    max_repair_iterations: int = 5


class ProductBuilderTelemetry(BaseModel):
    total_products_built: int = 0
    active_builds: int = 0
    successful_deliveries: int = 0
    auto_corrections_performed: int = 0
    average_build_time_seconds: float = 0.0
    finops_zero_cost_verified: bool = True
    last_heartbeat: str = ""


# ==============================================================================
# PHASE 21: AUTONOMOUS SOFTWARE FACTORY GRANULAR SCHEMAS
# ==============================================================================

class FactorySpecRequest(BaseModel):
    goal: str
    template: Optional[str] = "auto"
    archetype: Optional[str] = None
    project_name: Optional[str] = None
    target_stack: Optional[Dict[str, str]] = None


class FactorySpecResponse(BaseModel):
    spec_id: str
    project_name: str
    goal: str
    archetype: str
    template: str
    requirements: List[str] = []
    architecture: Dict[str, Any] = {}
    acceptance_criteria: List[str] = []
    api_endpoints: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FactoryBuildRequest(BaseModel):
    factory_id: Optional[str] = None
    spec_id: Optional[str] = None
    project_id: Optional[str] = None
    goal: Optional[str] = None
    target_path: Optional[str] = None
    use_worktree: bool = True
    dry_run: bool = False


class FactoryTestRequest(BaseModel):
    factory_id: str
    auto_repair: bool = True
    max_repair_iterations: int = 5


class FactoryReviewRequest(BaseModel):
    factory_id: str
    include_ast_security: bool = True
    max_rounds: int = 3


class FactoryDeliverRequest(BaseModel):
    factory_id: str
    target_branch: str = "main"
    auto_deploy: bool = True
    environment: str = "LOCAL"


class FactoryStatusResponse(BaseModel):
    factory_id: str
    stage: str
    state: str
    goal: str
    project_id: str
    project_name: str
    project_path: str
    mission_id: Optional[str] = None
    review_rounds: List[ReviewRound] = []
    test_results: Dict[str, Any] = {}
    security_findings: List[Dict[str, Any]] = []
    deployment_status: Optional[str] = None
    health_score: float = 100.0
    finops_zero_cost_verified: bool = True
    created_at: str
    updated_at: str


class FactoryArtifactsResponse(BaseModel):
    factory_id: str
    project_name: str
    project_path: str
    artifacts: List[Dict[str, Any]] = []
    provenance_chain_hash: str = ""
    slsa_attestation: Optional[Dict[str, Any]] = None


# =============================================================================
# Phase 22: Autonomous Project Operations & Lifecycle Control Schemas
# =============================================================================

class ProjectLifecycleState(str, Enum):
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    MAINTENANCE = "MAINTENANCE"
    UPGRADING = "UPGRADING"
    ROLLING_BACK = "ROLLING_BACK"
    DECOMMISSIONED = "DECOMMISSIONED"
    ARCHIVED = "ARCHIVED"


class ReleaseStrategy(str, Enum):
    CANARY = "CANARY"
    BLUE_GREEN = "BLUE_GREEN"
    DIRECT_ROLLOUT = "DIRECT_ROLLOUT"
    SHADOW = "SHADOW"


class ReleaseState(str, Enum):
    PREPARING = "PREPARING"
    CANARY_10 = "CANARY_10"
    CANARY_50 = "CANARY_50"
    CANARY_100 = "CANARY_100"
    STABLE = "STABLE"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    RETIRED = "RETIRED"


class DriftSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DriftType(str, Enum):
    CONFIG_DRIFT = "CONFIG_DRIFT"
    DEPENDENCY_DRIFT = "DEPENDENCY_DRIFT"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    CONTAINER_DRIFT = "CONTAINER_DRIFT"
    ENVIRONMENT_DRIFT = "ENVIRONMENT_DRIFT"


class MaintenanceTaskType(str, Enum):
    DEPENDENCY_SCAN = "DEPENDENCY_SCAN"
    SECURITY_PATCH = "SECURITY_PATCH"
    CERT_ROTATION = "CERT_ROTATION"
    LOG_ROTATE = "LOG_ROTATE"
    BACKUP = "BACKUP"
    CLEANUP = "CLEANUP"


class MaintenanceTaskStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProjectSLA(BaseModel):
    uptime_target_pct: float = 99.9
    observed_uptime_pct: float = 100.0
    p95_latency_target_ms: float = 150.0
    observed_p95_latency_ms: float = 12.0
    max_error_rate_pct: float = 0.1
    observed_error_rate_pct: float = 0.0
    error_budget_remaining_pct: float = 100.0
    burn_rate: float = 0.0
    sla_status: str = "COMPLIANT"  # COMPLIANT, WARNING, BREACHED
    last_evaluated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProjectRelease(BaseModel):
    release_id: str
    project_id: str
    version: str
    commit_hash: str
    strategy: ReleaseStrategy = ReleaseStrategy.CANARY
    state: ReleaseState = ReleaseState.PREPARING
    traffic_weight_pct: int = 0
    changelog: List[str] = []
    slsa_attestation_hash: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    promoted_at: Optional[str] = None
    retired_at: Optional[str] = None


class ProjectDriftRecord(BaseModel):
    drift_id: str
    project_id: str
    drift_type: DriftType
    severity: DriftSeverity = DriftSeverity.MEDIUM
    expected_state: str
    observed_state: str
    diff: str
    remediated: bool = False
    remediated_at: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MaintenanceTask(BaseModel):
    task_id: str
    project_id: str
    task_type: MaintenanceTaskType
    status: MaintenanceTaskStatus = MaintenanceTaskStatus.SCHEDULED
    scheduled_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    executed_at: Optional[str] = None
    result_summary: Optional[str] = None


class ProjectOperationsRecord(BaseModel):
    project_id: str
    project_name: str
    project_path: str
    lifecycle_state: ProjectLifecycleState = ProjectLifecycleState.ACTIVE
    health_score: float = 100.0
    current_version: str = "0.1.0"
    active_release_id: Optional[str] = None
    releases: List[ProjectRelease] = []
    sla: ProjectSLA = Field(default_factory=ProjectSLA)
    active_drifts: List[ProjectDriftRecord] = []
    maintenance_history: List[MaintenanceTask] = []
    resource_governance: Dict[str, Any] = Field(default_factory=lambda: {
        "max_local_memory_mb": 512,
        "max_cpu_cores": 1.0,
        "zero_cloud_cost": True,
        "finops_spend_usd": 0.00
    })
    tombstone: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FleetOverviewResponse(BaseModel):
    total_projects: int
    active_projects: int
    degraded_projects: int
    maintenance_projects: int
    decommissioned_projects: int
    fleet_health_score: float
    total_releases_active: int
    unresolved_drifts: int
    overall_sla_compliance_pct: float
    finops_zero_cost_verified: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CreateReleaseRequest(BaseModel):
    project_id: str
    version_bump: str = "patch"  # patch, minor, major, explicit
    explicit_version: Optional[str] = None
    strategy: ReleaseStrategy = ReleaseStrategy.CANARY
    changelog_summary: Optional[str] = None


class PromoteReleaseRequest(BaseModel):
    release_id: str
    target_traffic_pct: Optional[int] = None  # None for auto next stage


class RollbackReleaseRequest(BaseModel):
    project_id: str
    reason: str = "Manual operator rollback or SLA violation"
    target_release_id: Optional[str] = None


class DetectDriftRequest(BaseModel):
    project_id: Optional[str] = None  # None scans entire fleet
    auto_reconcile: bool = False


class ReconcileDriftRequest(BaseModel):
    drift_id: str
    force: bool = False


class ScheduleMaintenanceRequest(BaseModel):
    project_id: str
    task_type: MaintenanceTaskType
    scheduled_delay_seconds: int = 0


class ExecuteMaintenanceRequest(BaseModel):
    task_id: str


class DecommissionProjectRequest(BaseModel):
    project_id: str
    reason: str = "End of service lifecycle"
    drain_traffic_seconds: int = 0


class ArchiveProjectRequest(BaseModel):
    project_id: str
    preserve_git_bundle: bool = True


class DiscoveredProjectItem(BaseModel):
    project_id: str
    name: str
    path: str
    root_path: Optional[str] = None
    detected_type: str = "generic_git"  # fastapi, node, react_vite, python_package, cli_tool, generic_git
    archetype: Optional[str] = None
    has_git: bool = True
    is_git: bool = True
    branch: Optional[str] = None
    git_branch: Optional[str] = None
    git_remote_url: Optional[str] = None
    commit_hash: Optional[str] = None
    has_dockerfile: bool = False
    has_tests: bool = False
    is_registered: bool = False
    already_registered: bool = False
    build_config: Dict[str, Any] = {}


class ProjectDiscoveryResponse(BaseModel):
    scanned_roots: List[str]
    discovered_projects: List[DiscoveredProjectItem] = []
    total_discovered: int = 0
    registered_count: int
    unregistered_count: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProjectHealthDetail(BaseModel):
    project_id: str
    project_name: str
    path: str
    git_state: Dict[str, Any] = {}  # branch, commit, is_clean, dirty_files
    build_test_state: Dict[str, Any] = {}  # last_test_run, passed, exit_code, test_count
    runtime_process_state: Dict[str, Any] = {}  # is_running, pids, listening_ports
    deployment_state: Dict[str, Any] = {}  # active_deployment_id, environment, status
    security_state: Dict[str, Any] = {}  # ast_findings_count, secrets_clean
    recent_incidents: List[Dict[str, Any]] = []
    mission_state: Dict[str, Any] = {}  # active_missions, last_mission_id
    last_successful_operation: Optional[str] = None
    knowledge_optimization_signals: List[Dict[str, Any]] = []
    health_score: float = 100.0
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProjectOperationType(str, Enum):
    INSPECT = "inspect"
    TEST = "test"
    BUILD = "build"
    RUN = "run"
    STOP = "stop"
    RESTART = "restart"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"
    HEALTH_CHECK = "health-check"
    CREATE_MISSION = "create-mission"
    CREATE_FACTORY_BUILD = "create-factory-build"
    VIEW_INCIDENTS = "view-incidents"
    VIEW_OPTIMIZATIONS = "view-optimizations"


class ProjectOperationRequest(BaseModel):
    operation: ProjectOperationType
    params: Dict[str, Any] = Field(default_factory=dict)
    actor: str = "operator"
    approval_token: Optional[str] = None


class ProjectOperationResult(BaseModel):
    operation_id: str
    project_id: str
    operation: ProjectOperationType
    status: str  # SUCCESS, FAILED, REQUIRES_APPROVAL, BLOCKED
    result_data: Dict[str, Any] = {}
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DependencyRelationTier(str, Enum):
    OBSERVED_FACT = "OBSERVED_FACT"
    DERIVED_PATTERN = "DERIVED_PATTERN"
    HEURISTIC = "HEURISTIC"


class ProjectDependencyRelation(BaseModel):
    source_project_id: str
    target_project_id: str
    relation_type: str  # API, PACKAGE, SERVICE, DEPLOYMENT
    tier: DependencyRelationTier = DependencyRelationTier.OBSERVED_FACT
    evidence: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectDependencyGraph(BaseModel):
    projects: List[str] = []
    edges: List[ProjectDependencyRelation] = []
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProjectMissionRoutingResult(BaseModel):
    goal: str
    target_project_ids: List[str] = []
    routing_type: str  # EXISTING_PROJECT, NEW_PROJECT, MULTI_PROJECT, AMBIGUOUS
    confidence: float = 1.0
    rationale: str
    safe_to_execute: bool = True


# =========================================================================
# PHASE 23: UNIFIED AUTONOMOUS COMMAND & CONTROL PLANE SCHEMAS
# =========================================================================

class CommandDirectiveType(str, Enum):
    NATURAL_LANGUAGE = "NATURAL_LANGUAGE"
    STRUCTURED_ACTION = "STRUCTURED_ACTION"
    MISSION_DIRECTIVE = "MISSION_DIRECTIVE"
    FLEET_OPERATION = "FLEET_OPERATION"
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"
    SCHEDULED_TASK = "SCHEDULED_TASK"
    SYSTEM_OPTIMIZATION = "SYSTEM_OPTIMIZATION"
    TOOL_DIRECTIVE = "TOOL_DIRECTIVE"


class CommandExecutionState(str, Enum):
    PENDING = "PENDING"
    ARBITRATING = "ARBITRATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    ROLLED_BACK = "ROLLED_BACK"


class ExecutionTraceStep(BaseModel):
    step_index: int
    subsystem: str
    action: str
    status: str  # PENDING, RUNNING, SUCCESS, FAILED, SKIPPED
    duration_ms: float = 0.0
    detail: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CommandDirectiveRequest(BaseModel):
    directive_id: Optional[str] = None
    raw_prompt: str
    directive_type: CommandDirectiveType = CommandDirectiveType.NATURAL_LANGUAGE
    target_project_id: Optional[str] = None
    subsystem_hints: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    operator_context: str = "nexus-operator"
    dry_run: bool = False
    force_override: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CommandDirectiveResult(BaseModel):
    directive_id: str
    state: CommandExecutionState
    raw_prompt: str
    resolved_intent: str
    risk_level: RiskLevel = RiskLevel.LOW
    dispatched_subsystems: List[str] = Field(default_factory=list)
    execution_trace: List[ExecutionTraceStep] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    finops_cost_usd: float = 0.0
    duration_ms: float = 0.0
    requires_approval: bool = False
    approval_id: Optional[str] = None
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GlobalSystemState(BaseModel):
    fleet_summary: Dict[str, Any] = Field(default_factory=dict)
    active_missions_count: int = 0
    active_missions: List[Dict[str, Any]] = Field(default_factory=list)
    recent_incidents_count: int = 0
    recent_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    active_releases_count: int = 0
    knowledge_nodes_count: int = 0
    tool_metrics_summary: Dict[str, Any] = Field(default_factory=dict)
    finops_total_spend_usd: float = 0.0
    system_health_score: float = 100.0
    kill_switch_active: bool = False
    active_directives_count: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EmergencyKillSwitchRequest(BaseModel):
    operator: str = "nexus-operator"
    reason: str = "Emergency operator intervention requested"
    abort_active_missions: bool = True
    freeze_fleet: bool = True
    rollback_canaries: bool = True


class EmergencyKillSwitchResult(BaseModel):
    kill_switch_id: str
    status: str  # TRIGGERED, REVERTED, FAILED
    aborted_missions_count: int = 0
    frozen_projects_count: int = 0
    rolled_back_canaries_count: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detail: str = ""


class OperationsTimelineStage(str, Enum):
    COMMAND = "COMMAND"
    DECISION = "DECISION"
    ACTION = "ACTION"
    RESULT = "RESULT"
    EVIDENCE = "EVIDENCE"


class OperationsTimelineEntry(BaseModel):
    entry_id: str
    command_id: str
    stage: OperationsTimelineStage
    action: str
    actor: str = "nexus-operator"
    target_projects: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    data: Dict[str, Any] = Field(default_factory=dict)
    evidence: Optional[str] = None
    replayed: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CommandPlan(BaseModel):
    plan_id: str
    command_id: str
    raw_prompt: str
    resolved_intent: str
    target_projects: List[str] = Field(default_factory=list)
    planned_actions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    required_approvals: List[str] = Field(default_factory=list)
    affected_projects: List[str] = Field(default_factory=list)
    expected_artifacts: List[str] = Field(default_factory=list)
    rollback_recovery_path: List[str] = Field(default_factory=list)
    is_safe_to_execute: bool = True
    block_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GlobalOperationsState(BaseModel):
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    missions: List[Dict[str, Any]] = Field(default_factory=list)
    factory_runs: List[Dict[str, Any]] = Field(default_factory=list)
    deployments: List[Dict[str, Any]] = Field(default_factory=list)
    incidents: List[Dict[str, Any]] = Field(default_factory=list)
    security_findings: List[Dict[str, Any]] = Field(default_factory=list)
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    providers: List[Dict[str, Any]] = Field(default_factory=list)
    worktrees: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    approvals: List[Dict[str, Any]] = Field(default_factory=list)
    finops: Dict[str, Any] = Field(default_factory=dict)
    global_health_score: float = 100.0
    kill_switch_active: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GlobalEventBusMessage(BaseModel):
    event_id: str
    event_type: str
    source_subsystem: str
    project_id: Optional[str] = None
    mission_id: Optional[str] = None
    command_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    provenance_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# -----------------------------------------------------------------------------
# Phase 23+ Local Connector & Unified Project Dashboard Schemas
# -----------------------------------------------------------------------------

class ConnectorStatusResponse(BaseModel):
    connector_id: str
    status: str = "ONLINE"  # ONLINE, CONNECTED, DEGRADED
    os_environment: str     # Linux, Ubuntu, Termux, Android
    is_termux: bool = False
    hostname: str
    pid: int
    uptime_seconds: float
    listening_host: str
    listening_port: int
    bridge_auth_required: bool = False
    allowed_roots: List[str] = []
    connected_projects_count: int = 0
    active_missions_count: int = 0
    active_worktrees_count: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProjectOnboardRequest(BaseModel):
    project_id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    root_path: Optional[str] = None
    repository: Optional[str] = None
    git_remote_url: Optional[str] = None
    branch: Optional[str] = "main"
    git_branch: Optional[str] = "main"
    project_type: Optional[str] = "generic_git"
    description: Optional[str] = None
    owner: str = "knightriderisback"
    tags: List[str] = []
    auto_discover_git: bool = True


class ProjectDashboardGitStatus(BaseModel):
    branch: str = "main"
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    remote_url: Optional[str] = None
    is_clean: bool = True
    dirty_files_count: int = 0
    modified_files: List[str] = []
    untracked_files: List[str] = []
    ahead: int = 0
    behind: int = 0


class ProjectDashboardResponse(BaseModel):
    project: ProjectRegistryItem
    operations_record: Optional[ProjectOperationsRecord] = None
    git: ProjectDashboardGitStatus
    health: Optional[ProjectHealthDetail] = None
    missions: List[Dict[str, Any]] = []
    deployments: List[Dict[str, Any]] = []
    incidents: List[Dict[str, Any]] = []
    security_findings: List[Dict[str, Any]] = []
    knowledge_nodes: List[Dict[str, Any]] = []
    available_actions: List[str] = [
        "AUDIT", "TEST", "SECURITY_SCAN", "DEPLOY", "RUN_MISSION", "RECONCILE_DRIFT"
    ]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProjectActionRequest(BaseModel):
    action: str  # AUDIT, TEST, SECURITY_SCAN, DEPLOY, RUN_MISSION, RECONCILE_DRIFT
    payload: Dict[str, Any] = Field(default_factory=dict)
    operator: str = "cyber-operator"


class ProjectActionResult(BaseModel):
    project_id: str
    action: str
    status: str  # SUCCESS, FAILED, PENDING_APPROVAL, COMPLETED
    message: str = ""
    output: Optional[str] = None
    health_score_delta: Optional[int] = 0
    duration_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = []
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConnectorSyncRequest(BaseModel):
    project_ids: Optional[List[str]] = None  # None or empty means all discovered
    roots: Optional[List[str]] = None


class ConnectorSyncResponse(BaseModel):
    synced_count: int
    synced_projects: List[ProjectRegistryItem]
    skipped_count: int = 0
    errors: List[str] = []
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutoSyncConfig(BaseModel):
    enabled: bool = True
    interval_seconds: int = 30
    auto_register_discovered: bool = True
    reconcile_git_state: bool = True
    custom_roots: List[str] = []


class AutoSyncStatusResponse(BaseModel):
    enabled: bool = True
    interval_seconds: int = 30
    auto_register_discovered: bool = True
    reconcile_git_state: bool = True
    active_roots: List[str] = []
    status: str = "IDLE"  # RUNNING, IDLE, DISABLED, ERROR
    last_sync_timestamp: Optional[str] = None
    next_sync_timestamp: Optional[str] = None
    cycles_completed: int = 0
    total_discovered_count: int = 0
    total_registered_count: int = 0
    last_synced_count: int = 0
    last_reconciled_count: int = 0
    last_errors: List[str] = []
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReconcileFleetResponse(BaseModel):
    reconciled_count: int = 0
    drift_count: int = 0
    synced_projects: List[ProjectRegistryItem] = []
    drift_details: List[Dict[str, Any]] = []
    errors: List[str] = []
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())























