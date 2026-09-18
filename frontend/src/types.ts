export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'active' | 'running' | 'thinking' | 'monitoring' | 'failed';
  model: string;
  autonomy_tier: 'Autonomous' | 'Guardrailed' | 'Step-by-Step';
  task_count: number;
  token_velocity: number;
  total_tokens: number;
  current_task: string;
  avatar: string;
  color: string;
}

export interface Task {
  id: string;
  title: string;
  agent_id: string;
  agent_name: string;
  status: 'running' | 'completed' | 'aborted' | 'failed';
  progress: number;
  tokens_spent: number;
  started_at: string;
  logs: string[];
}

export interface Telemetry {
  timestamp: string;
  cpu: {
    overall: number;
    cores: number[];
    core_count: number;
  };
  memory: {
    total_gb: number;
    used_gb: number;
    available_gb: number;
    percent: number;
    swap_percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  network: {
    bytes_sent_mb: number;
    bytes_recv_mb: number;
    packets_sent: number;
    packets_recv: number;
  };
  uptime: string;
  processes: {
    pid: number;
    name: string;
    cpu: number;
    memory: number;
  }[];
  open_ports: {
    port: number;
    ip: string;
    service?: string;
    state?: string;
  }[];
  agent_summary: {
    total: number;
    active: number;
    idle: number;
    monitoring?: number;
  };
}

export interface ApprovalRequest {
  id: string;
  agent_id: string;
  agent_name: string;
  action: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  command: string;
  status: 'pending' | 'approved' | 'rejected';
  reason?: string;
  binding_hash?: string;
}

export interface MemoryNode {
  id: string;
  title: string;
  category: string;
  tags: string[];
  content: string;
  pinned: boolean;
  created_at: string;
}

export interface WorkspaceProject {
  name: string;
  path: string;
  type: string;
  status?: string;
  git?: {
    has_repo: boolean;
    branch: string;
    status: string;
    last_commit: string;
    modified_files_count?: number;
  };
}

export interface ProjectItem {
  id: string;
  name: string;
  path: string;
  github_repo?: string;
  environment: string;
  deployment_provider: string;
  domain?: string;
  status: string;
  health_score: number;
  last_audit?: string;
  last_test?: string;
  last_security_scan?: string;
  documentation_url?: string;
  owner: string;
  risk: string;
  description?: string;
}

export interface AuditEventItem {
  id: string;
  correlation_id: string;
  timestamp: string;
  actor: string;
  agent?: string;
  user: string;
  action: string;
  project: string;
  target: string;
  reason: string;
  risk_level: string;
  approval_id?: string;
  result: string;
  error?: string;
}

/* -------------------------------------------------------------------------
 * CYBER-HUD OPERATIONAL TYPES (Phase 12)
 * ------------------------------------------------------------------------- */

export type HealthStatusLevel = 'HEALTHY' | 'DEGRADED' | 'WARNING' | 'BLOCKED' | 'FAILED' | 'OFFLINE';

export interface SystemHealth {
  overall_status: HealthStatusLevel;
  status_reasons: string[];
  timestamp: string;
  summary: string;
  components: {
    api: {
      status: string;
      pid: number;
      version: string;
      uptime: string;
    };
    daemon: {
      status: string;
      running: boolean;
      pid: number;
      memory_mb: number;
      endpoint: string;
    };
    ai_providers: {
      status: string;
      active_preference: string;
      total_providers: number;
      healthy_providers: number;
      circuits_open: number;
    };
    github: {
      status: string;
      mode: string;
      configured: boolean;
      authenticated: boolean;
    };
    worktrees: {
      status: string;
      active_count: number;
      isolated_root: string;
    };
    finops: {
      status: string;
      current_spend_usd: number;
      spend_ceiling_usd: number;
      billing_linked: boolean;
      guardrail_active: boolean;
    };
    approvals: {
      status: string;
      pending_count: number;
      critical_count: number;
    };
    security: {
      status: string;
      ast_scanner: string;
      prompt_injection_defense: string;
      zero_cost_sentinel: string;
    };
    missions: {
      status: string;
      total_count: number;
      active_count: number;
      failed_count: number;
    };
  };
}

export interface UnifiedEvent {
  id: string;
  timestamp: string;
  category: 'audit' | 'mission' | 'delivery' | 'merge' | 'approval' | 'security' | 'finops';
  source: string;
  event_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  result: string;
  target: string;
  risk_level: string;
  correlation_id?: string;
}

export interface HandoffNode {
  id: string;
  name: string;
  role: string;
  model: string;
  status: 'idle' | 'active' | 'completed';
  autonomy: string;
  stage_order: number;
}

export interface HandoffEdge {
  from: string;
  to: string;
  protocol: string;
  conditional?: boolean;
}

export interface HandoffGraph {
  nodes: HandoffNode[];
  edges: HandoffEdge[];
  recursion_depth_limit: number;
  current_recursion_depth: number;
  active_mission_id?: string | null;
  active_step?: {
    step_id: string;
    agent: string;
    description: string;
    state: string;
  } | null;
  timestamp: string;
}

export interface RecoverableMission {
  mission_id: string;
  goal: string;
  state: string;
  worktree_path?: string;
  error?: string;
  remediation_attempts: number;
  can_remediate: boolean;
  can_resume: boolean;
}

export interface DisputedCandidate {
  candidate_id: string;
  source_branch: string;
  target_branch: string;
  state: string;
  risk_level: string;
  conflict_type: string;
  requires_arbitration: boolean;
}

export interface RecoveryStatus {
  recoverable_missions: RecoverableMission[];
  disputed_candidates: DisputedCandidate[];
  open_circuits: {
    provider: string;
    circuit_state: string;
    failure_count: number;
  }[];
  active_worktrees: number;
  total_recovery_items: number;
  timestamp: string;
}

export interface WorktreeInfo {
  session_id: string;
  branch_name: string;
  worktree_path: string;
  base_commit: string;
  created_at: string;
  is_locked: boolean;
  is_dirty: boolean;
}

export interface MergeCandidate {
  candidate_id: string;
  source_branch: string;
  target_branch: string;
  strategy: string;
  state: string;
  risk_level: string;
  conflict_type: string;
  source_sha?: string;
  target_sha?: string;
  merge_commit_sha?: string;
  approval_id?: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface DeliveryRecord {
  delivery_id: string;
  source_branch: string;
  published_branch?: string;
  pr_number?: number;
  pr_url?: string;
  state: string;
  risk_level: string;
  checks_results: {
    check: string;
    conclusion: string;
    details?: string;
  }[];
  reviews: {
    reviewer: string;
    verdict: string;
    summary?: string;
  }[];
  approval_id?: string;
  merge_commit_sha?: string;
  target_branch: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface ProviderInfo {
  name: string;
  provider_type: string;
  is_fallback: boolean;
  health: {
    status: string;
    latency_ms: number;
    circuit_state: string;
    failure_count: number;
    last_error?: string;
  };
}

export interface FinOpsSummary {
  current_spend_usd: number;
  billing_linked: boolean;
  zero_cost_guardrail_active: boolean;
  hard_spend_limit_usd: number;
  free_tier_status: {
    [key: string]: {
      used_requests?: number;
      used_gb?: number;
      used_queries_tb?: number;
      used_minutes?: number;
      limit: number;
      unit: string;
    };
  };
}

export interface MissionRequirement {
  requirement_id: string;
  category: string;
  description: string;
  acceptance_criteria: string[];
  priority: string;
  status: string;
  assigned_subtask_ids: string[];
}

export interface AcceptanceCriterion {
  criterion_id: string;
  requirement_id?: string;
  description: string;
  evaluator: string;
  params: Record<string, any>;
  status: string;
  evidence?: string;
  timestamp?: string;
}

export interface TraceabilityLink {
  link_id: string;
  requirement_id: string;
  subtask_id: string;
  agent_id: string;
  artifact_path?: string;
  test_id?: string;
  acceptance_criterion_id?: string;
  status: string;
  explanation: string;
}

export interface MissionCheckpoint {
  checkpoint_id: string;
  mission_id: string;
  timestamp: string;
  state: string;
  graph_state: Record<string, any>;
  node_states: Record<string, any>;
  artifacts: string[];
  current_workspace?: string;
  retry_counters: Record<string, number>;
  acceptance_results: Record<string, any>;
  risk_state: Record<string, any>;
}

export interface MissionGraphData {
  mission_id: string;
  goal: string;
  state: string;
  execution_order: string[][];
  nodes: {
    id: string;
    title: string;
    assigned_agent: string;
    status: string;
    risk_level: string;
    dependencies: string[];
    target_files: string[];
    remediation_rounds: number;
    required_capabilities?: string[];
    error?: string;
  }[];
  edges: { source: string; target: string }[];
  total_nodes: number;
  completed_nodes: number;
  failed_nodes: number;
}

export interface EngineeringMission {
  mission_id: string;
  goal: string;
  normalized_objective?: string;
  repo_path: string;
  target_branch: string;
  state: string;
  max_parallel_tasks: number;
  max_remediation_rounds: number;
  auto_merge: boolean;
  auto_deliver_github: boolean;
  worktree_path?: string;
  mission_branch?: string;
  merge_id?: string;
  approval_id?: string;
  error?: string;
  created_at: string;
  completed_at?: string;
  execution_order?: string[][];
  requirements?: MissionRequirement[];
  acceptance_criteria?: AcceptanceCriterion[];
  traceability?: TraceabilityLink[];
  checkpoints?: MissionCheckpoint[];
  subtasks: {
    subtask_id: string;
    title: string;
    description: string;
    assigned_agent: string;
    dependencies: string[];
    risk_level: string;
    status: string;
    worktree_path?: string;
    remediation_rounds: number;
    target_files?: string[];
    required_capabilities?: string[];
    error?: string;
  }[];
  telemetry?: Record<string, any>;
  factory_id?: string;
  review_rounds?: ReviewRound[];
  generated_artifacts?: string[];
}

export interface ReviewRoundFinding {
  file_path: string;
  line_number?: number;
  severity: string;
  category: string;
  message: string;
  suggested_fix?: string;
}

export interface ReviewRound {
  iteration: number;
  reviewer_agent: string;
  developer_agent: string;
  verdict: string;
  summary: string;
  findings: ReviewRoundFinding[];
  diff_applied?: string;
  tests_passed: boolean;
  security_clean: boolean;
  timestamp: string;
}

export interface FactoryMissionRecord {
  factory_id: string;
  mission_id: string;
  project_id: string;
  project_name: string;
  project_path: string;
  goal: string;
  template: string;
  stage: string;
  review_rounds: ReviewRound[];
  generated_artifacts: string[];
  acceptance_evidence: Record<string, any>;
  telemetry: Record<string, any>;
  error?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

// Phase 15: Universal Tool & App Integration Types
export interface UniversalToolManifest {
  tool_id: string;
  name: string;
  description: string;
  protocol: string;
  category: string;
  endpoint?: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  requires_approval: boolean;
  required_capabilities: string[];
  allowed_agents: string[];
  timeout: number;
  write_capability: boolean;
  enabled: boolean;
  health_status: string;
  invocation_count: number;
  total_duration_ms: number;
  last_invoked?: string;
  metadata?: Record<string, any>;
}

export interface UniversalToolInvocationResult {
  invocation_id: string;
  tool_id: string;
  status: string;
  output?: any;
  error?: string;
  duration_ms: number;
  caller_agent_id?: string;
  executed_at: string;
  audit_id?: string;
}

export interface ConnectedApp {
  app_id: string;
  name: string;
  category: string;
  description: string;
  status: string;
  icon?: string;
  capabilities: string[];
  tools_provided: string[];
  endpoint?: string;
  health_check_url?: string;
  last_health_check?: string;
  auth_configured: boolean;
  metadata?: Record<string, any>;
}

export interface MCPServerDefinition {
  server_id: string;
  name: string;
  description?: string;
  transport: string;
  command_or_url: string;
  env?: Record<string, string>;
  args?: string[];
  status: string;
  exposed_tools: Array<Record<string, any>>;
  connected_at?: string;
  latency_ms: number;
  error?: string;
}

export interface ToolsTelemetryData {
  total_tools: number;
  categories: Record<string, number>;
  connected_apps_count: number;
  mcp_servers_count: number;
  total_invocations: number;
  successful_invocations: number;
  failed_invocations: number;
  avg_latency_ms: number;
  top_tools: Array<{
    tool_id: string;
    name: string;
    count: number;
    avg_ms: number;
  }>;
  recent_invocations: UniversalToolInvocationResult[];
}

// Phase 16: Production Deployment Engine Types
export interface DeploymentStage {
  stage_name: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'SKIPPED';
  started_at?: string;
  completed_at?: string;
  duration_ms: number;
  logs: string[];
  error?: string;
  metrics?: Record<string, any>;
}

export interface DeploymentRecord {
  deployment_id: string;
  project_id: string;
  service_name: string;
  version: string;
  commit_sha: string;
  environment: 'LOCAL' | 'PREVIEW' | 'STAGING' | 'PRODUCTION';
  target_type: 'LOCAL_PROCESS' | 'DOCKER_CONTAINER' | 'VERCEL_EDGE' | 'GCP_CLOUD_RUN' | 'TERMUX_NODE' | 'STATIC_BUNDLE';
  strategy: 'ROLLING' | 'BLUE_GREEN' | 'CANARY' | 'DIRECT_REPLACE' | 'INSTANT_RELOAD';
  status: 'QUEUED' | 'BUILDING' | 'TESTING' | 'APPROVAL_PENDING' | 'DEPLOYING' | 'VERIFYING' | 'LIVE' | 'FAILED' | 'ROLLED_BACK' | 'CANCELLED';
  current_stage: string;
  stages: DeploymentStage[];
  deployed_url?: string;
  canary_percentage: number;
  active_instances: number;
  health_status: 'HEALTHY' | 'UNHEALTHY' | 'DEGRADED' | 'UNKNOWN' | 'ROLLED_BACK';
  error?: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  requires_approval: boolean;
  approval_id?: string;
  created_by: string;
  created_at: string;
  completed_at?: string;
  duration_seconds: number;
  rollback_target_id?: string;
  changelog: string[];
  dora_lead_time_seconds: number;
  metadata?: Record<string, any>;
}

export interface DeploymentRequest {
  project_id: string;
  service_name?: string;
  version?: string;
  commit_sha?: string;
  environment: 'LOCAL' | 'PREVIEW' | 'STAGING' | 'PRODUCTION';
  target_type: 'LOCAL_PROCESS' | 'DOCKER_CONTAINER' | 'VERCEL_EDGE' | 'GCP_CLOUD_RUN' | 'TERMUX_NODE' | 'STATIC_BUNDLE';
  strategy: 'ROLLING' | 'BLUE_GREEN' | 'CANARY' | 'DIRECT_REPLACE' | 'INSTANT_RELOAD';
  canary_percentage?: number;
  image_tag?: string;
  config_env?: Record<string, string>;
  health_check_path?: string;
  auto_rollback_on_failure?: boolean;
  created_by?: string;
  notes?: string;
}

export interface DORAMetrics {
  deployment_frequency_per_week: number;
  lead_time_for_changes_minutes: number;
  change_failure_rate_percent: number;
  mean_time_to_recovery_minutes: number;
  total_deployments: number;
  successful_deployments: number;
  failed_deployments: number;
  rollbacks_count: number;
  calculated_at: string;
}

export interface EnvironmentStatus {
  environment_name: string;
  status: string;
  active_deployment_id?: string;
  active_version?: string;
  active_commit?: string;
  target_type?: string;
  url?: string;
  traffic_split: Record<string, number>;
  last_deployed_at?: string;
  health_status: string;
}

// Phase 17: Autonomous Self-Healing Operations Types
export interface WatchdogCheckResult {
  watchdog_id: string;
  watchdog_type: 'PROCESS_SUPERVISOR' | 'PORT_AVAILABILITY' | 'RESOURCE_PRESSURE' | 'HTTP_SLA' | 'SECURITY_SENTINEL' | 'WORKTREE_HEALTH';
  name: string;
  status: 'HEALTHY' | 'DEGRADED' | 'ALERTING' | 'OFFLINE';
  message: string;
  metrics: Record<string, any>;
  timestamp: string;
  incident_triggered: boolean;
}

export interface DiagnosisEvidence {
  observed_facts: string[];
  hypotheses: string[];
  evidence_sources: string[];
  confidence_score: number;
  root_cause_candidate: string;
}

export interface HealingAction {
  action_id: string;
  name: string;
  playbook_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  duration_ms: number;
  logs: string[];
  result?: string;
  error?: string;
}

export interface RemediationPlaybook {
  playbook_id: string;
  name: string;
  category: string;
  description: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  requires_approval: boolean;
  steps: string[];
  success_rate: number;
  execution_count: number;
  estimated_cost_usd?: number;
}

export interface RecoveryHistoryRecord {
  recovery_id: string;
  incident_id: string;
  timestamp: string;
  action: string;
  result: string;
  verification_passed: boolean;
  duration_seconds: number;
  operator?: string;
  notes?: string;
}

export interface IncidentRecord {
  incident_id: string;
  title: string;
  category: string;
  severity: string;
  status: string;
  source_watchdog?: string;
  target_resource: string;
  root_cause_analysis?: string;
  diagnosis_evidence?: DiagnosisEvidence;
  detected_at: string;
  diagnosed_at?: string;
  resolved_at?: string;
  duration_seconds: number;
  remediation_playbook_id?: string;
  healing_actions: HealingAction[];
  requires_approval: boolean;
  approval_id?: string;
  recovery_attempts?: number;
  max_recovery_attempts?: number;
  deduplication_hash?: string;
  correlation_id?: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  post_mortem?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface OperationsMetrics {
  system_health: string;
  uptime_pct: number;
  active_incidents: number;
  resolved_incidents: number;
  escalated_incidents: number;
  mean_time_to_recover_seconds: number;
  remediation_success_rate_pct: number;
  incident_frequency_per_hour: number;
  failure_distribution: Record<string, number>;
  active_circuit_breakers: string[];
  daemon_loop_active: boolean;
  calculated_at: string;
}

export interface SelfHealingTelemetry {
  overall_uptime_pct: number;
  active_incidents_count: number;
  resolved_incidents_count: number;
  auto_remediation_success_rate_pct: number;
  mean_time_to_healing_seconds: number;
  watchdogs: WatchdogCheckResult[];
  active_playbooks_count: number;
  calculated_at: string;
}

// Phase 18: Autonomous Security & Compliance Operations Types
export interface SecurityFinding {
  finding_id: string;
  title: string;
  category: 'SECRET_LEAK' | 'SAST_INJECTION' | 'DEPENDENCY_CVE' | 'PERMISSIONS_WEAKENING' | 'INSECURE_COMMUNICATION' | 'LICENSE_NONCOMPLIANCE' | 'SANDBOX_ESCAPE_RISK' | 'PROMPT_INJECTION' | string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO' | string;
  status: 'OPEN' | 'INVESTIGATING' | 'QUARANTINED' | 'REMEDIATED' | 'SUPPRESSED' | 'RESOLVED' | string;
  file_path?: string;
  line_number?: number;
  snippet?: string;
  remediation_advice: string;
  cve_id?: string;
  cvss_score: number;
  detected_at: string;
  resolved_at?: string;
  details?: Record<string, any>;
}

export interface ComplianceControlResult {
  control_id: string;
  framework: 'SOC2' | 'ISO27001' | 'CIS_BENCHMARK' | 'NIST_800_53' | 'GDPR_PRIVACY' | 'FINOPS_ZERO_COST' | string;
  title: string;
  passed: boolean;
  score: number;
  details: string;
  evidence: string[];
  remediation_guidance?: string;
}

export interface SecurityScanReport {
  scan_id: string;
  target_path: string;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  total_files_scanned: number;
  findings: SecurityFinding[];
  risk_score: number;
  pass_status: boolean;
  compliance_summary: Record<string, number>;
}

export interface QuarantineRecord {
  quarantine_id: string;
  finding_id: string;
  original_path: string;
  quarantined_path: string;
  permissions_applied: string;
  quarantined_at: string;
  released_at?: string;
  operator: string;
  notes?: string;
}

export interface SecOpsTelemetry {
  overall_security_posture_score: number;
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  quarantined_threats: number;
  compliance_scores: Record<string, number>;
  active_scanners: string[];
  zero_trust_status: string;
  calculated_at: string;
}
export interface SecurityPolicyRule {
  rule_id: string;
  name: string;
  category: string;
  target_action: string;
  decision: 'ALLOW' | 'WARN' | 'BLOCK' | 'REQUIRES_HUMAN_APPROVAL' | 'QUARANTINE';
  condition: string;
  rationale: string;
  requires_approval_role?: string;
  active: boolean;
}

export interface SecurityPolicyEvaluationRecord {
  eval_id: string;
  rule_id: string;
  decision: 'ALLOW' | 'WARN' | 'BLOCK' | 'REQUIRES_HUMAN_APPROVAL' | 'QUARANTINE';
  target: string;
  reason: string;
  actor: string;
  evaluated_at: string;
  finding_ids: string[];
  evidence: Record<string, any>;
  session_id?: string;
}

export interface SecurityEvidenceRecord {
  evidence_id: string;
  session_id?: string;
  branch?: string;
  commit_sha?: string;
  tree_sha?: string;
  scan_id: string;
  timestamp: string;
  policy_version: string;
  findings_count: number;
  passed: boolean;
  details: Record<string, any>;
}

// =========================================================================
// PHASE 19: AUTONOMOUS KNOWLEDGE, LEARNING & OPTIMIZATION TYPES
// =========================================================================

export interface KnowledgeNodeItem {
  node_id: string;
  tier: 'EPISODIC' | 'SEMANTIC' | 'PROCEDURAL' | 'META';
  category: 'ARCHITECTURE' | 'CODE_PATTERN' | 'REMEDIATION' | 'SECURITY' | 'DEPLOYMENT' | 'FINOPS' | 'TOOL_USAGE' | 'PERFORMANCE' | 'QUALITY';
  title: string;
  content: string;
  tags: string[];
  fingerprint: string;
  status?: string;
  source_mission_id?: string;
  source_incident_id?: string;
  source_finding_id?: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'EXPERIMENTAL';
  success_score: number;
  access_count: number;
  decay_factor: number;
  revalidated_at?: string;
  contradicted_by?: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface LearningInsightItem {
  insight_id: string;
  title: string;
  category: string;
  pattern: string;
  rationale: string;
  recommended_action: string;
  supporting_evidence: string[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'EXPERIMENTAL';
  recurrence_count: number;
  impacted_subsystems: string[];
  created_at: string;
}

export interface OptimizationRecommendationItem {
  recommendation_id: string;
  target_domain: string;
  title: string;
  description: string;
  why?: string;
  evidence?: string[];
  baseline_metric: string;
  projected_metric: string;
  confidence: string;
  scope?: string;
  expected_impact?: string;
  risk?: string;
  reversibility?: string;
  approval_required?: boolean;
  suggested_strategy: string;
  status: 'PROPOSED' | 'APPLIED' | 'VERIFIED' | 'REJECTED';
  applied_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at?: string;
}

export interface DAGOptimizationPlanItem {
  mission_id: string;
  original_step_count: number;
  critical_path_length: number;
  parallelizable_groups: string[][];
  recommended_execution_order: string[][];
  estimated_speedup_percent: number;
  rationale: string;
}

export interface ToolPerformanceMetricItem {
  tool_id: string;
  total_invocations: number;
  success_rate_percent: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  error_patterns: string[];
  reliability_tier: 'HIGH' | 'MEDIUM' | 'DEGRADED';
}

export interface KnowledgeTelemetryItem {
  total_nodes: number;
  episodic_nodes: number;
  semantic_nodes: number;
  procedural_nodes: number;
  total_edges: number;
  total_insights: number;
  active_optimizations: number;
  average_retrieval_latency_ms: number;
  knowledge_health_score: number;
  finops_zero_cost_verified: boolean;
  last_learning_sweep_at: string;
}

// Phase 20: Autonomous Mission Intelligence & Adaptive Execution Types
export interface MissionIntentAnalysisItem {
  intent_id: string;
  raw_goal: string;
  refined_objective: string;
  complexity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  explicit_constraints: string[];
  implicit_assumptions: string[];
  required_capabilities: string[];
  target_subsystems: string[];
  estimated_token_budget: number;
  finops_zero_cost_required: boolean;
  created_at: string;
}

export interface AdaptiveTaskNodeItem {
  task_id: string;
  title: string;
  description: string;
  assigned_agent_role: string;
  depends_on: string[];
  state: 'PENDING' | 'READY' | 'RUNNING' | 'COMPLETED' | 'ADAPTED' | 'FAILED' | 'SKIPPED' | 'DEGRADED' | 'ESCALATED';
  timeout_seconds: number;
  max_retries: number;
  retry_count: number;
  token_budget: number;
  tokens_used: number;
  fallback_task_id?: string;
  remediation_subdag_ids: string[];
  execution_command?: string;
  expected_artifacts: string[];
  actual_artifacts: string[];
  output?: string;
  error_message?: string;
  state_hash: string;
  started_at?: string;
  completed_at?: string;
  duration_ms: number;
  metadata: Record<string, any>;
}

export interface MissionAdaptationEventItem {
  event_id: string;
  mission_id: string;
  task_id: string;
  trigger_reason: string;
  strategy: 'RETRY_WITH_KNOWLEDGE' | 'DYNAMIC_FALLBACK_BRANCH' | 'INJECT_REMEDIATION_SUBDAG' | 'GRACEFUL_DEGRADATION' | 'ESCALATE_HUMAN';
  knowledge_node_id_used?: string;
  why: string;
  evidence: string[];
  injected_task_ids: string[];
  resulting_state: string;
  timestamp: string;
}

export interface RiskSignalItem {
  signal_id: string;
  mission_id: string;
  signal_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  evidence: string[];
  affected_components: string[];
  recommendation: string;
  detected_at: string;
}

export interface SimilarMissionMatchItem {
  mission_id: string;
  goal: string;
  similarity_score: number;
  outcome: string;
  matching_factors: string[];
  reusable_patterns: string[];
}

export interface MissionIntelligenceContextItem {
  context_id: string;
  mission_id: string;
  goal: string;
  similar_missions: SimilarMissionMatchItem[];
  relevant_knowledge_nodes: Array<Record<string, any>>;
  risk_signals: RiskSignalItem[];
  recommended_agents: Record<string, number>;
  recommended_tools: string[];
  token_budget: number;
  created_at: string;
}

export interface MissionDecisionItem {
  decision_id: string;
  mission_id: string;
  task_id?: string;
  step_index: number;
  why: string;
  evidence: string[];
  confidence: 'OBSERVED_FACT' | 'DERIVED_PATTERN' | 'HEURISTIC' | 'HYPOTHESIS';
  risk: string;
  alternatives_considered: string[];
  expected_effect: string;
  traceability_link: Record<string, any>;
  timestamp: string;
}

export interface AdaptiveMissionPlanItem {
  mission_id: string;
  project_id: string;
  goal: string;
  intent_analysis: MissionIntentAnalysisItem;
  tasks: Record<string, AdaptiveTaskNodeItem>;
  execution_waves: string[][];
  overall_state: string;
  total_token_budget: number;
  total_tokens_consumed: number;
  replan_count: number;
  max_replans: number;
  context_id?: string;
  decisions: string[];
  risk_signals: RiskSignalItem[];
  adaptation_history: MissionAdaptationEventItem[];
  provenance_chain_hash: string;
  created_at: string;
  updated_at: string;
}

export interface AdaptiveExecutionTelemetryItem {
  active_missions: number;
  completed_missions: number;
  total_adaptations: number;
  total_replans: number;
  successful_recoveries: number;
  average_task_latency_ms: number;
  tokens_saved_by_optimization: number;
  finops_zero_cost_verified: boolean;
  last_heartbeat: string;
}

// ==============================================================================
// PHASE 21: PRODUCT BUILDER TYPES
// ==============================================================================

export type ProductArchetype = 'FULLSTACK_WEB' | 'MICROSERVICE_API' | 'CLI_TOOL' | 'DATA_PIPELINE' | 'AI_AGENT_SYSTEM' | 'LIBRARY_SDK';
export type ProductBuildStage = 'BLUEPRINT_SYNTHESIS' | 'SCAFFOLDING' | 'CODE_GENERATION' | 'TEST_SYNTHESIS' | 'COMPILATION_AND_LINT' | 'TEST_EXECUTION' | 'SECURITY_AUDIT' | 'SELF_CORRECTION' | 'PACKAGING' | 'DELIVERY_VERIFICATION';
export type ProductBuildState = 'PENDING' | 'IN_PROGRESS' | 'SELF_CORRECTING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface ProductComponentItem {
  component_id: string;
  name: string;
  archetype: ProductArchetype;
  path: string;
  language: string;
  framework: string;
  dependencies: string[];
  generated_files: string[];
  status: string;
  ast_verified: boolean;
  metadata?: Record<string, any>;
}

export interface ProductSpecificationItem {
  spec_id: string;
  product_name: string;
  summary: string;
  archetype: ProductArchetype;
  features: string[];
  api_endpoints: Array<{ path: string; method: string; summary: string }>;
  data_models: Array<{ name: string; fields: Record<string, string> }>;
  security_requirements: string[];
  test_requirements: string[];
  target_stack: Record<string, string>;
  created_at: string;
}

export interface ProductBuildRunItem {
  build_id: string;
  product_name: string;
  spec_id: string;
  workspace_path: string;
  current_stage: ProductBuildStage;
  state: ProductBuildState;
  components: ProductComponentItem[];
  iteration: number;
  max_iterations: number;
  test_results: {
    status?: string;
    passed?: number;
    failed?: number;
    exit_code?: number;
    stdout_summary?: string;
    error_details?: string[];
  };
  security_findings: Array<{
    severity: string;
    file: string;
    line: number;
    finding: string;
  }>;
  corrections_applied: Array<{
    iteration: number;
    reason: string;
    error_details: string[];
    action_taken: string;
    timestamp: string;
  }>;
  slsa_provenance_hash: string;
  provenance_chain_hash: string;
  total_tokens_consumed: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface ProductCatalogItem {
  product_id: string;
  product_name: string;
  archetype: string;
  spec_id: string;
  build_id: string;
  workspace_path: string;
  version: string;
  status: string;
  slsa_provenance_hash: string;
  provenance_chain_hash: string;
  delivered_at: string;
}

export interface ProductBuilderTelemetryItem {
  total_products_built: number;
  active_builds: number;
  successful_deliveries: number;
  auto_corrections_performed: number;
  average_build_time_seconds: number;
  finops_zero_cost_verified: boolean;
  last_heartbeat: string;
}

// =============================================================================
// Phase 22: Autonomous Project Operations & Lifecycle Control Types
// =============================================================================

export type ProjectLifecycleStateType = 
  | 'PROVISIONING'
  | 'ACTIVE'
  | 'DEGRADED'
  | 'MAINTENANCE'
  | 'UPGRADING'
  | 'ROLLING_BACK'
  | 'DECOMMISSIONED'
  | 'ARCHIVED';

export type ReleaseStrategyType = 'CANARY' | 'BLUE_GREEN' | 'DIRECT_ROLLOUT' | 'SHADOW';

export type ReleaseStateType = 
  | 'PREPARING'
  | 'CANARY_10'
  | 'CANARY_50'
  | 'CANARY_100'
  | 'STABLE'
  | 'ROLLING_BACK'
  | 'ROLLED_BACK'
  | 'RETIRED';

export interface ProjectSLAItem {
  uptime_target_pct: number;
  observed_uptime_pct: number;
  p95_latency_target_ms: number;
  observed_p95_latency_ms: number;
  max_error_rate_pct: number;
  observed_error_rate_pct: number;
  error_budget_remaining_pct: number;
  burn_rate: number;
  sla_status: 'COMPLIANT' | 'WARNING' | 'BREACHED';
  last_evaluated: string;
}

export interface ProjectReleaseItem {
  release_id: string;
  project_id: string;
  version: string;
  commit_hash: string;
  strategy: ReleaseStrategyType;
  state: ReleaseStateType;
  traffic_weight_pct: number;
  changelog: string[];
  slsa_attestation_hash?: string;
  created_at: string;
  promoted_at?: string;
  retired_at?: string;
}

export interface ProjectDriftItem {
  drift_id: string;
  project_id: string;
  drift_type: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  expected_state: string;
  observed_state: string;
  diff: string;
  remediated: boolean;
  remediated_at?: string;
  timestamp: string;
}

export interface MaintenanceTaskItem {
  task_id: string;
  project_id: string;
  task_type: string;
  status: 'SCHEDULED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  scheduled_time: string;
  executed_at?: string;
  result_summary?: string;
}

export interface ProjectOperationsRecordItem {
  project_id: string;
  project_name: string;
  project_path: string;
  lifecycle_state: ProjectLifecycleStateType;
  health_score: number;
  current_version: string;
  active_release_id?: string;
  releases: ProjectReleaseItem[];
  sla: ProjectSLAItem;
  active_drifts: ProjectDriftItem[];
  maintenance_history: MaintenanceTaskItem[];
  resource_governance: {
    max_local_memory_mb: number;
    max_cpu_cores: number;
    zero_cloud_cost: boolean;
    finops_spend_usd: number;
  };
  tombstone?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface FleetOverviewItem {
  total_projects: number;
  active_projects: number;
  degraded_projects: number;
  maintenance_projects: number;
  decommissioned_projects: number;
  fleet_health_score: number;
  total_releases_active: number;
  unresolved_drifts: number;
  overall_sla_compliance_pct: number;
  finops_zero_cost_verified: boolean;
  timestamp: string;
}




