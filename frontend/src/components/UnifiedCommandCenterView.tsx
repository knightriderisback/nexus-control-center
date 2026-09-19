import React, { useState, useEffect, useCallback } from 'react';
import {
  Terminal,
  ShieldAlert,
  ShieldCheck,
  Zap,
  Play,
  Eye,
  RefreshCw,
  Cpu,
  Layers,
  Activity,
  AlertTriangle,
  Clock,
  Sliders,
  Database,
  Wrench,
  RotateCcw,
  Boxes,
  FileCheck2
} from 'lucide-react';
import { sound } from '../utils/audio';
import { nexusFetch } from '../utils/api';

interface ExecutionTraceStep {
  step_index: number;
  subsystem: string;
  action: string;
  status: string;
  duration_ms: number;
  detail: string;
  timestamp: string;
}

interface CommandDirectiveResult {
  directive_id: string;
  state: string;
  raw_prompt: string;
  resolved_intent: string;
  risk_level: string;
  dispatched_subsystems: string[];
  execution_trace: ExecutionTraceStep[];
  artifacts?: string[];
  stdout?: string;
  stderr?: string;
  finops_cost_usd?: number;
  duration_ms?: number;
  requires_approval?: boolean;
  approval_id?: string;
  governance_approval_required?: boolean;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

interface GlobalOperationsState {
  projects?: any[];
  missions?: any[];
  factory_runs?: any[];
  deployments?: any[];
  incidents?: any[];
  security_findings?: any[];
  agents?: any[];
  tools?: any[];
  providers?: any[];
  worktrees?: any[];
  knowledge_nodes?: any[];
  approvals?: any[];
  finops?: any;
  global_health_score?: number;
  fleet_health_score?: number;
  kill_switch_active?: boolean;
  system_state?: string;
  system_alert?: boolean;
  alert_level?: string;
  active_missions_count?: number;
  active_deployments_count?: number;
  unresolved_incidents_count?: number;
  registered_projects_count?: number;
  idle_agents_count?: number;
  registered_tools_count?: number;
  finops_total_spend?: number;
  finops_policy_invariant_held?: boolean;
  unresolved_security_findings?: number;
  pending_approvals_count?: number;
  timestamp?: string;
}

interface OperationsTimelineEntry {
  entry_id?: string;
  timeline_id?: string;
  command_id?: string;
  stage?: string;
  action?: string;
  actor?: string;
  target_projects?: string[];
  target_project_id?: string;
  event_type?: string;
  source_subsystem?: string;
  risk_level?: string;
  status?: string;
  summary?: string;
  data?: any;
  evidence?: string;
  timestamp: string;
}

interface GlobalEventBusMessage {
  event_id: string;
  event_type?: string;
  source_subsystem?: string;
  project_id?: string;
  mission_id?: string;
  command_id?: string;
  topic?: string;
  publisher?: string;
  payload?: any;
  provenance_hash?: string;
  timestamp: string;
}

export const UnifiedCommandCenterView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'console' | 'timeline' | 'events' | 'grid' | 'approvals'>('console');
  const [promptInput, setPromptInput] = useState<string>('');
  const [targetProject, setTargetProject] = useState<string>('');
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [latestResult, setLatestResult] = useState<CommandDirectiveResult | null>(null);
  const [globalState, setGlobalState] = useState<GlobalOperationsState | null>(null);
  const [timeline, setTimeline] = useState<OperationsTimelineEntry[]>([]);
  const [events, setEvents] = useState<GlobalEventBusMessage[]>([]);
  const [showKillModal, setShowKillModal] = useState<boolean>(false);
  const [killReason, setKillReason] = useState<string>('Emergency operator manual intervention');

  const fetchUnifiedData = useCallback(async () => {
    try {
      const [resState, resTimeline, resEvents] = await Promise.all([
        nexusFetch<any>('/api/v1/operations/global'),
        nexusFetch<any[]>('/api/v1/operations/timeline?limit=40'),
        nexusFetch<any[]>('/api/v1/operations/events?limit=30')
      ]);

      if (resState && !resState.detail) setGlobalState(resState);
      if (Array.isArray(resTimeline)) setTimeline(resTimeline);
      if (Array.isArray(resEvents)) setEvents(resEvents);
    } catch (err) {
      console.warn('Unified command center data fetch error:', err);
    }
  }, []);

  useEffect(() => {
    fetchUnifiedData();
    const interval = setInterval(fetchUnifiedData, 5000);
    return () => clearInterval(interval);
  }, [fetchUnifiedData]);

  const handleDispatch = async (dryRun: boolean = false) => {
    if (!promptInput.trim()) return;
    setIsExecuting(true);
    sound.click();

    try {
      const endpoint = dryRun ? '/api/v1/command/preview' : '/api/v1/command';
      const data = await nexusFetch<CommandDirectiveResult>(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          raw_prompt: promptInput,
          target_project_id: targetProject || undefined,
          dry_run: dryRun,
          operator_context: 'nexus-operator'
        })
      });

      setLatestResult(data);
      if (data.state === 'COMPLETED') {
        sound.success();
      } else {
        sound.alert();
      }
      fetchUnifiedData();
    } catch (err) {
      console.error('Dispatch failed:', err);
      sound.alert();
    } finally {
      setIsExecuting(false);
    }
  };

  const handleEmergencyKill = async () => {
    try {
      sound.panic();
      await nexusFetch('/api/v1/c2/emergency/kill', {
        method: 'POST',
        body: JSON.stringify({
          operator: 'nexus-operator',
          reason: killReason,
          abort_active_missions: true,
          freeze_fleet: true,
          rollback_canaries: true
        })
      });
      setShowKillModal(false);
      fetchUnifiedData();
    } catch (err) {
      console.error('Kill switch failed:', err);
    }
  };

  const handleEmergencyReset = async () => {
    try {
      sound.click();
      await nexusFetch('/api/v1/c2/emergency/reset', {
        method: 'POST',
        body: JSON.stringify({ operator: 'nexus-operator' })
      });
      fetchUnifiedData();
    } catch (err) {
      console.error('Reset failed:', err);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in p-6 bg-black text-cyan-400 font-mono min-h-screen">
      {/* 1. TOP GLOBAL TELEMETRY BAR */}
      <div className="border border-cyan-500/40 bg-zinc-950/90 p-4 rounded backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-950/60 border border-cyan-500/50 rounded">
              <Terminal className="w-6 h-6 text-cyan-400 animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-wider text-cyan-300">
                UNIFIED COMMAND & CONTROL CENTER
              </h1>
              <div className="text-xs text-zinc-400 flex items-center gap-2">
                <span>PHASE 23 AUTONOMOUS C2</span>
                <span>•</span>
                <span className="text-emerald-400 font-bold">FINOPS: $0.00 ZERO-COST ENFORCED</span>
                <span>•</span>
                <span className={globalState?.kill_switch_active ? 'text-rose-500 font-bold' : 'text-cyan-400'}>
                  MODE: {globalState?.kill_switch_active ? 'EMERGENCY FREEZE LOCK' : 'NOMINAL GOVERNANCE'}
                </span>
              </div>
            </div>
          </div>

          {/* Key Metric Meters */}
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-[10px] text-zinc-400">GLOBAL HEALTH</div>
              <div className="text-base font-bold text-emerald-400">
                {globalState?.global_health_score || 100}%
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-zinc-400">PROJECTS</div>
              <div className="text-base font-bold text-cyan-400">
                {globalState?.projects?.length || 0}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-zinc-400">MISSIONS</div>
              <div className="text-base font-bold text-indigo-400">
                {globalState?.missions?.length || 0}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-zinc-400">INCIDENTS</div>
              <div className="text-base font-bold text-amber-400">
                {globalState?.incidents?.length || 0}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] text-zinc-400">KNOWLEDGE</div>
              <div className="text-base font-bold text-purple-400">
                {globalState?.knowledge_nodes?.length || 0}
              </div>
            </div>

            {globalState?.kill_switch_active ? (
              <button
                onClick={handleEmergencyReset}
                className="px-3 py-1.5 bg-amber-600/30 border border-amber-500 hover:bg-amber-600/50 text-amber-300 font-bold text-xs rounded flex items-center gap-1.5 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                RESET LOCK
              </button>
            ) : (
              <button
                onClick={() => setShowKillModal(true)}
                className="px-3 py-1.5 bg-rose-600/30 border border-rose-500 hover:bg-rose-600/50 text-rose-300 font-bold text-xs rounded flex items-center gap-1.5 transition animate-pulse"
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                EMERGENCY FREEZE
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2. NATURAL LANGUAGE COMMAND CONSOLE */}
      <div className="border border-cyan-500/30 bg-zinc-950/80 p-4 rounded space-y-3">
        <div className="text-xs font-bold text-cyan-400 tracking-wider flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyan-400" />
          <span>NATURAL LANGUAGE COMMAND & CONTROL CONSOLE</span>
        </div>

        <div className="flex flex-col md:flex-row gap-3">
          <input
            type="text"
            placeholder="Type directive (e.g. 'Inspect fleet health and reconcile drift', 'Scaffold payment service', 'Canary release v0.2.0', 'Run AST security audit')..."
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleDispatch(false); }}
            className="flex-1 bg-black/80 border border-cyan-500/50 rounded px-4 py-2.5 text-cyan-200 placeholder-zinc-500 focus:outline-none focus:border-cyan-400 text-xs"
          />

          <input
            type="text"
            placeholder="Target Project (optional)"
            value={targetProject}
            onChange={(e) => setTargetProject(e.target.value)}
            className="md:w-56 bg-black/80 border border-cyan-500/50 rounded px-3 py-2.5 text-cyan-200 placeholder-zinc-500 focus:outline-none focus:border-cyan-400 text-xs"
          />

          <div className="flex gap-2">
            <button
              onClick={() => handleDispatch(false)}
              disabled={isExecuting || !promptInput.trim()}
              className="px-4 py-2.5 bg-cyan-600/30 border border-cyan-400 hover:bg-cyan-500/40 text-cyan-200 font-bold text-xs rounded flex items-center gap-1.5 disabled:opacity-50 transition"
            >
              {isExecuting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              EXECUTE
            </button>

            <button
              onClick={() => handleDispatch(true)}
              disabled={isExecuting || !promptInput.trim()}
              className="px-3 py-2.5 bg-zinc-800 border border-zinc-600 hover:bg-zinc-700 text-zinc-300 font-bold text-xs rounded flex items-center gap-1.5 disabled:opacity-50 transition"
            >
              <Eye className="w-3.5 h-3.5" />
              PREVIEW
            </button>
          </div>
        </div>

        {/* Preset quick action buttons */}
        <div className="flex flex-wrap gap-2 text-[11px] text-zinc-400">
          <span className="text-zinc-500">Quick Actions:</span>
          {[
            'Inspect fleet health and drift radar',
            'Run AST security audit on control-center',
            'Trigger scheduled maintenance routine',
            'Decompose mission: Build telemetry exporter'
          ].map((act, i) => (
            <button
              key={i}
              onClick={() => setPromptInput(act)}
              className="px-2 py-0.5 bg-zinc-900 border border-zinc-800 hover:border-cyan-500 rounded text-zinc-300 transition"
            >
              {act}
            </button>
          ))}
        </div>
      </div>

      {/* 3. NAVIGATION SUB-TABS */}
      <div className="flex border-b border-cyan-500/30 space-x-1">
        {[
          { id: 'console', label: 'EXECUTION TRACE', icon: Terminal },
          { id: 'timeline', label: 'OPERATIONS TIMELINE', icon: Clock },
          { id: 'events', label: 'GLOBAL EVENT BUS', icon: Activity },
          { id: 'grid', label: 'SUBSYSTEM GRID', icon: Cpu },
          { id: 'approvals', label: 'APPROVAL CENTER', icon: FileCheck2 }
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id as any)}
              className={`px-3.5 py-1.5 border-t border-l border-r rounded-t text-xs font-bold flex items-center gap-1.5 transition ${
                active
                  ? 'border-cyan-400 bg-zinc-900 text-cyan-300'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:bg-zinc-950'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* 4. TAB PANELS */}
      {activeSubTab === 'console' && (
        <div className="space-y-4">
          {latestResult ? (
            <div className="border border-cyan-500/40 bg-zinc-950 p-5 rounded space-y-4">
              <div className="flex flex-wrap items-center justify-between border-b border-cyan-500/20 pb-3 gap-2">
                <div>
                  <div className="text-[10px] text-zinc-400 font-mono">COMMAND ID: {latestResult.directive_id}</div>
                  <div className="text-base font-bold text-cyan-300">{latestResult.raw_prompt}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold border ${
                    latestResult.state === 'COMPLETED'
                      ? 'border-emerald-500 bg-emerald-950/40 text-emerald-400'
                      : latestResult.state === 'AWAITING_APPROVAL'
                      ? 'border-amber-500 bg-amber-950/40 text-amber-400'
                      : 'border-rose-500 bg-rose-950/40 text-rose-400'
                  }`}>
                    {latestResult.state}
                  </span>
                  <span className="text-xs text-zinc-400">INTENT: {latestResult.resolved_intent}</span>
                  <span className="text-xs text-emerald-400">{latestResult.duration_ms}ms</span>
                </div>
              </div>

              {/* Execution Trace */}
              <div>
                <h3 className="text-xs font-bold text-zinc-400 mb-2">MULTI-STAGE EXECUTION TRACE</h3>
                <div className="space-y-1.5">
                  {latestResult.execution_trace.map((st, i) => (
                    <div
                      key={i}
                      className="p-2.5 bg-black/60 border border-zinc-800 rounded flex items-start justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.2 bg-cyan-950 border border-cyan-600 rounded text-cyan-300 text-[10px] font-bold">
                            STEP {st.step_index}
                          </span>
                          <span className="text-zinc-300 font-bold">{st.subsystem}</span>
                          <span className="text-zinc-500">→</span>
                          <span className="text-cyan-400">{st.action}</span>
                        </div>
                        <div className="text-zinc-400 pl-8">{st.detail}</div>
                      </div>
                      <div className="text-right">
                        <span className="text-emerald-400">{st.status}</span>
                        <div className="text-zinc-600">{st.duration_ms}ms</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Output log */}
              {latestResult.stdout && (
                <div>
                  <h3 className="text-xs font-bold text-zinc-400 mb-1">STDOUT LOG</h3>
                  <pre className="p-3 bg-black border border-zinc-800 rounded text-xs text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                    {latestResult.stdout}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center border border-zinc-800 bg-zinc-950/40 rounded text-zinc-500 text-xs">
              <Terminal className="w-10 h-10 mx-auto mb-2 opacity-30 text-cyan-400" />
              Unified Command Center ready. Execute a natural language directive above to stream real-time execution trace.
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'timeline' && (
        <div className="border border-zinc-800 bg-zinc-950 rounded p-4 space-y-3">
          <h2 className="text-xs font-bold text-cyan-300 tracking-wider">
            OPERATIONS TIMELINE (COMMAND → DECISION → ACTION → RESULT → EVIDENCE)
          </h2>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {timeline.map((entry, idx) => (
              <div key={idx} className="p-2.5 bg-black/60 border border-zinc-800 rounded flex items-start justify-between text-xs">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      entry.stage === 'COMMAND' ? 'bg-cyan-950 text-cyan-300 border border-cyan-600' :
                      entry.stage === 'DECISION' ? 'bg-indigo-950 text-indigo-300 border border-indigo-600' :
                      entry.stage === 'ACTION' ? 'bg-amber-950 text-amber-300 border border-amber-600' :
                      entry.stage === 'RESULT' ? 'bg-emerald-950 text-emerald-300 border border-emerald-600' :
                      'bg-purple-950 text-purple-300 border border-purple-600'
                    }`}>
                      {entry.stage}
                    </span>
                    <span className="text-zinc-300 font-bold">{entry.action}</span>
                    {entry.target_projects && entry.target_projects.length > 0 && (
                      <span className="text-zinc-500 text-[10px]">[{entry.target_projects.join(', ')}]</span>
                    )}
                  </div>
                  {entry.evidence && (
                    <div className="text-purple-300/80 text-[11px] pl-6 font-mono">
                      Evidence: {entry.evidence}
                    </div>
                  )}
                </div>
                <div className="text-right text-zinc-500 text-[10px]">
                  <div>{new Date(entry.timestamp).toLocaleTimeString()}</div>
                  <div className="text-zinc-600">{entry.command_id}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeSubTab === 'events' && (
        <div className="border border-zinc-800 bg-zinc-950 rounded p-4 space-y-3">
          <h2 className="text-xs font-bold text-cyan-300 tracking-wider">GLOBAL EVENT BUS LIVE STREAM</h2>
          <div className="space-y-2 max-h-[500px] overflow-y-auto font-mono text-xs">
            {events.map((evt, idx) => (
              <div key={idx} className="p-2 bg-black border border-zinc-900 rounded flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-cyan-400 font-bold">[{evt.event_type}]</span>
                  <span className="text-zinc-400">src: {evt.source_subsystem}</span>
                  <span className="text-zinc-500 text-[10px]">hash: {evt.provenance_hash}</span>
                </div>
                <span className="text-zinc-500 text-[10px]">{new Date(evt.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeSubTab === 'grid' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { name: 'Software Factory', items: `${globalState?.factory_runs?.length || 0} runs`, status: 'ONLINE', icon: Boxes, color: 'text-cyan-400' },
            { name: 'Missions & DAG', items: `${globalState?.missions?.length || 0} missions`, status: 'ONLINE', icon: Layers, color: 'text-indigo-400' },
            { name: 'Universal Tools', items: `${globalState?.tools?.length || 0} tools`, status: 'ONLINE', icon: Wrench, color: 'text-amber-400' },
            { name: 'Deployments', items: `${globalState?.deployments?.length || 0} active`, status: 'ONLINE', icon: Zap, color: 'text-emerald-400' },
            { name: 'Self-Healing', items: `${globalState?.incidents?.length || 0} incidents`, status: 'ONLINE', icon: Activity, color: 'text-teal-400' },
            { name: 'Security AST', items: `${globalState?.security_findings?.length || 0} findings`, status: 'ONLINE', icon: ShieldCheck, color: 'text-rose-400' },
            { name: 'Knowledge Brain', items: `${globalState?.knowledge_nodes?.length || 0} nodes`, status: 'ONLINE', icon: Database, color: 'text-purple-400' },
            { name: 'Project Fleet', items: `${globalState?.projects?.length || 0} projects`, status: 'ONLINE', icon: Sliders, color: 'text-blue-400' }
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <div key={idx} className="p-3 bg-zinc-950 border border-zinc-800 rounded space-y-2">
                <div className="flex items-center justify-between">
                  <Icon className={`w-4 h-4 ${item.color}`} />
                  <span className="text-[10px] text-zinc-500 font-bold">{item.status}</span>
                </div>
                <div className="text-xs font-bold text-zinc-200">{item.name}</div>
                <div className="text-[11px] text-zinc-400">{item.items}</div>
              </div>
            );
          })}
        </div>
      )}

      {activeSubTab === 'approvals' && (
        <div className="border border-zinc-800 bg-zinc-950 rounded p-4 space-y-3">
          <h2 className="text-xs font-bold text-cyan-300 tracking-wider">APPROVAL CENTER (GOVERNANCE GATES)</h2>
          <div className="space-y-2">
            {globalState?.approvals && globalState.approvals.length > 0 ? (
              globalState.approvals.map((appr, idx) => (
                <div key={idx} className="p-3 bg-black border border-zinc-800 rounded flex items-center justify-between text-xs">
                  <div>
                    <div className="font-bold text-zinc-200">{appr.action}</div>
                    <div className="text-zinc-400 text-[11px]">Reason: {appr.reason}</div>
                    <div className="text-zinc-500 text-[10px]">Target: {appr.target_project || 'fleet'}</div>
                  </div>
                  <div className="text-right">
                    <span className="px-2 py-0.5 bg-amber-950 border border-amber-600 text-amber-300 rounded text-[10px] font-bold">
                      {appr.status}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-zinc-500 text-xs">
                Zero pending approval gates. All operational subsystems are running nominally.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Emergency Kill Modal */}
      {showKillModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="border border-rose-500 bg-zinc-950 p-6 rounded-lg max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle className="w-6 h-6" />
              <h2 className="text-base font-bold">TRIGGER SYSTEM-WIDE EMERGENCY FREEZE</h2>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed">
              This will immediately abort all running agent missions, freeze the fleet state, and trigger automatic rollback of any active canaries.
            </p>
            <div>
              <label className="text-xs text-zinc-400 block mb-1">Intervention Reason:</label>
              <input
                type="text"
                value={killReason}
                onChange={(e) => setKillReason(e.target.value)}
                className="w-full bg-black border border-rose-500/50 rounded px-3 py-2 text-xs text-rose-200"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowKillModal(false)}
                className="px-4 py-2 border border-zinc-700 hover:bg-zinc-900 text-zinc-300 text-xs rounded"
              >
                CANCEL
              </button>
              <button
                onClick={handleEmergencyKill}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded"
              >
                CONFIRM FREEZE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
