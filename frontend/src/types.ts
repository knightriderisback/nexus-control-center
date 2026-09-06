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
    monitoring: number;
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
