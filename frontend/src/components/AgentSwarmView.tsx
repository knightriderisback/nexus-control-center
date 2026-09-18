import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  ShieldAlert, 
  CheckCircle, 
  XCircle, 
  Flame, 
  Activity, 
  Layers, 
  Zap, 
  ShieldCheck, 
  Clock,
  Sparkles,
  ArrowRight,
  Workflow
} from 'lucide-react';
import type { Agent, Task, ApprovalRequest, EngineeringMission } from '../types';
import { sound } from '../utils/audio';

interface AgentSwarmViewProps {
  agents: Agent[];
  tasks: Task[];
  approvals: ApprovalRequest[];
  onDispatchTask: (agentId: string, title: string, instructions: string, tier: string) => Promise<void>;
  onDecideApproval: (id: string, decision: 'approved' | 'rejected') => Promise<void>;
}

export const AgentSwarmView: React.FC<AgentSwarmViewProps> = ({
  agents,
  tasks,
  approvals,
  onDispatchTask,
  onDecideApproval
}) => {
  const [selectedAgentId, setSelectedAgentId] = useState<string>(agents[0]?.id || 'agent-coder');
  const [missionTitle, setMissionTitle] = useState<string>('');
  const [missionInstructions, setMissionInstructions] = useState<string>('');
  const [autonomyTier, setAutonomyTier] = useState<string>('Guardrailed');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [missions, setMissions] = useState<EngineeringMission[]>([]);

  useEffect(() => {
    const fetchMissions = async () => {
      try {
        const res = await fetch('/api/v1/missions').then(r => r.json());
        if (Array.isArray(res)) setMissions(res);
      } catch (e) {
        // silent fallback
      }
    };
    fetchMissions();
    const iv = setInterval(fetchMissions, 4000);
    return () => clearInterval(iv);
  }, []);

  const pendingApprovals = approvals.filter(a => a.status === 'pending');

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!missionTitle.trim()) return;
    setIsSubmitting(true);
    sound.beep(650, 0.1, 'sine');
    try {
      await onDispatchTask(selectedAgentId, missionTitle, missionInstructions || missionTitle, autonomyTier);
      sound.success();
      setMissionTitle('');
      setMissionInstructions('');
    } catch (err) {
      sound.alert();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickPreset = (title: string, agentId: string) => {
    sound.click();
    setSelectedAgentId(agentId);
    setMissionTitle(title);
    setMissionInstructions(`Execute comprehensive tactical analysis for: ${title}`);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Guardrail Approvals Alert (if any pending) */}
      {pendingApprovals.length > 0 && (
        <div className="hud-panel hud-panel-alert p-4 bg-rose-950/30 border border-rose-500/50 rounded-lg">
          <div className="flex items-center gap-2 text-rose-400 font-mono text-sm font-bold mb-3">
            <ShieldAlert className="w-5 h-5 animate-pulse text-rose-400" />
            <span>OPERATOR GUARDRAIL REQUIRED // {pendingApprovals.length} PENDING SENSITIVE ACTION(S)</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {pendingApprovals.map((appr) => (
              <div key={appr.id} className="p-3 bg-black/60 rounded border border-rose-500/30 font-mono text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-bold flex items-center gap-1.5">
                    <Bot className="w-3.5 h-3.5" />
                    {appr.agent_name}
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase">
                    Risk: {appr.risk_level}
                  </span>
                </div>
                <div className="text-slate-200">{appr.action}</div>
                <div className="bg-[#050810] p-2 rounded border border-slate-800 text-[11px] text-slate-300 overflow-x-auto">
                  <code>$ {appr.command}</code>
                </div>
                <div className="flex items-center justify-end gap-2 pt-1">
                  <button
                    onClick={() => {
                      sound.alert();
                      onDecideApproval(appr.id, 'rejected');
                    }}
                    className="flex items-center gap-1 px-3 py-1 rounded bg-slate-800 text-rose-300 hover:bg-rose-950 border border-rose-500/30 transition-all text-xs"
                  >
                    <XCircle className="w-3.5 h-3.5" /> Deny
                  </button>
                  <button
                    onClick={() => {
                      sound.success();
                      onDecideApproval(appr.id, 'approved');
                    }}
                    className="flex items-center gap-1 px-3 py-1 rounded bg-emerald-950 text-emerald-300 hover:bg-emerald-900 border border-emerald-500/50 transition-all text-xs font-bold shadow-[0_0_10px_rgba(0,255,157,0.3)]"
                  >
                    <CheckCircle className="w-3.5 h-3.5" /> Authorize Execution
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agents Swarm Fleet Grid */}
      <div className="hud-panel p-4 rounded-lg">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono font-bold text-cyan-300 tracking-wider">
              AUTONOMOUS AGENT MATRIX // FLEET TELEMETRY
            </span>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {agents.filter(a => a.status === 'active' || a.status === 'running').length} ACTIVE / {agents.length} DEPLOYED
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          {agents.map((agent) => {
            const isSelected = selectedAgentId === agent.id;
            const isActive = agent.status === 'active' || agent.status === 'running';

            return (
              <div
                key={agent.id}
                onClick={() => {
                  sound.click();
                  setSelectedAgentId(agent.id);
                }}
                className={`p-3.5 rounded-lg border cursor-pointer transition-all duration-200 flex flex-col justify-between ${
                  isSelected
                    ? 'bg-cyan-950/40 border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.25)]'
                    : 'bg-[#080d1a]/80 border-cyan-500/20 hover:border-cyan-500/40 hover:bg-[#0c1426]'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{agent.avatar}</span>
                      <div>
                        <div className="text-xs font-mono font-bold text-slate-100 flex items-center gap-1.5">
                          {agent.name}
                        </div>
                        <div className="text-[10px] font-mono text-slate-400 truncate max-w-[130px]">
                          {agent.model.split('/')[0]}
                        </div>
                      </div>
                    </div>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase border ${
                        isActive
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse'
                          : agent.status === 'monitoring'
                          ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {agent.status}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-300 line-clamp-2 mb-3 min-h-[32px]">
                    {agent.role}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800/80 space-y-1.5 font-mono text-[10px]">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1">
                      <Flame className="w-3 h-3 text-amber-400" /> Velocity
                    </span>
                    <span className="text-amber-300 font-bold">{agent.token_velocity} t/s</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3 text-cyan-400" /> Autonomy
                    </span>
                    <span className="text-cyan-300">{agent.autonomy_tier}</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1">
                      <Zap className="w-3 h-3 text-emerald-400" /> Lifetime
                    </span>
                    <span className="text-slate-300">{agent.total_tokens.toLocaleString()} tok</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Split: Mission Dispatcher & Live Execution Trace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Mission Dispatcher (5 cols) */}
        <div className="lg:col-span-5 hud-panel p-5 rounded-lg space-y-4">
          <div className="flex items-center gap-2 border-b border-cyan-500/20 pb-3">
            <Zap className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono font-bold text-cyan-300 tracking-wider">
              DISPATCH MISSION OBJECTIVE
            </span>
          </div>

          {/* Quick Presets */}
          <div>
            <span className="text-[10px] font-mono text-slate-400 block mb-2">QUICK TACTICAL PRESETS:</span>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => handleQuickPreset('Codebase AST Vulnerability Audit', 'agent-sentinel')}
                className="text-[10px] font-mono px-2 py-1 rounded bg-slate-900 border border-cyan-500/30 text-cyan-300 hover:border-cyan-400 transition-all flex items-center gap-1"
              >
                <Sparkles className="w-2.5 h-2.5 text-cyan-400" /> Security Audit
              </button>
              <button
                type="button"
                onClick={() => handleQuickPreset('Synthesize High-Density HUD Widget', 'agent-coder')}
                className="text-[10px] font-mono px-2 py-1 rounded bg-slate-900 border border-cyan-500/30 text-cyan-300 hover:border-cyan-400 transition-all flex items-center gap-1"
              >
                <Sparkles className="w-2.5 h-2.5 text-cyan-400" /> Synthesize Widget
              </button>
              <button
                type="button"
                onClick={() => handleQuickPreset('Inspect Git Commits & Unmerged Diffs', 'agent-reviewer')}
                className="text-[10px] font-mono px-2 py-1 rounded bg-slate-900 border border-cyan-500/30 text-cyan-300 hover:border-cyan-400 transition-all flex items-center gap-1"
              >
                <Sparkles className="w-2.5 h-2.5 text-cyan-400" /> Git Diff Scan
              </button>
            </div>
          </div>

          <form onSubmit={handleDispatch} className="space-y-3 font-mono">
            <div>
              <label className="text-[10px] text-slate-400 block mb-1">TARGET AGENT</label>
              <select
                value={selectedAgentId}
                onChange={(e) => {
                  sound.click();
                  setSelectedAgentId(e.target.value);
                }}
                className="w-full bg-[#070c18] border border-cyan-500/30 rounded px-3 py-2 text-xs text-cyan-300 focus:outline-none focus:border-cyan-400"
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.avatar} {a.name} ({a.role})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-1">AUTONOMY PROTOCOL</label>
              <div className="grid grid-cols-3 gap-2">
                {['Guardrailed', 'Autonomous', 'Step-by-Step'].map((tier) => (
                  <button
                    key={tier}
                    type="button"
                    onClick={() => {
                      sound.click();
                      setAutonomyTier(tier);
                    }}
                    className={`py-1.5 text-[10px] rounded border transition-all ${
                      autonomyTier === tier
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-[0_0_8px_rgba(0,240,255,0.25)]'
                        : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {tier}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-1">MISSION TITLE</label>
              <input
                type="text"
                value={missionTitle}
                onChange={(e) => setMissionTitle(e.target.value)}
                placeholder="e.g. Optimize Telemetry WebSocket Ingestion"
                className="w-full bg-[#070c18] border border-cyan-500/30 rounded px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-1">NEURAL DIRECTIVES & INSTRUCTIONS</label>
              <textarea
                value={missionInstructions}
                onChange={(e) => setMissionInstructions(e.target.value)}
                placeholder="Enter technical constraints, tool requirements, or target files..."
                rows={3}
                className="w-full bg-[#070c18] border border-cyan-500/30 rounded px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !missionTitle.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded bg-cyan-500/20 border border-cyan-400 text-cyan-300 hover:bg-cyan-500/30 hover:shadow-[0_0_15px_rgba(0,240,255,0.4)] transition-all text-xs font-bold disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send className="w-3.5 h-3.5" />
              {isSubmitting ? 'TRANSMITTING DIRECTIVE...' : 'DISPATCH AGENT OBJECTIVE'}
            </button>
          </form>
        </div>

        {/* Right: Live Task Stream & Logs (7 cols) */}
        <div className="lg:col-span-7 hud-panel p-5 rounded-lg space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-mono font-bold text-emerald-300 tracking-wider">
                LIVE MISSION STREAM & THOUGHT TRACES
              </span>
            </div>
            <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3 text-cyan-400" /> STREAM SYNCED
            </span>
          </div>

          <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
            {tasks.map((task) => {
              const isRunning = task.status === 'running';

              return (
                <div
                  key={task.id}
                  className={`p-3.5 rounded-lg border font-mono ${
                    isRunning
                      ? 'bg-[#091122]/90 border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.15)]'
                      : 'bg-[#060a14]/90 border-slate-800'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="text-xs font-bold text-slate-100 flex items-center gap-2">
                        <span>{task.title}</span>
                      </div>
                      <div className="text-[10px] text-cyan-400 flex items-center gap-2 mt-0.5">
                        <Bot className="w-3 h-3" />
                        <span>{task.agent_name}</span>
                        <span className="text-slate-600">•</span>
                        <span className="text-amber-400">{task.tokens_spent.toLocaleString()} tok</span>
                      </div>
                    </div>

                    <span
                      className={`text-[9px] px-2 py-0.5 rounded uppercase font-bold border ${
                        isRunning
                          ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 animate-pulse'
                          : task.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                      }`}
                    >
                      {task.status}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                      <span>Execution Progress</span>
                      <span className="text-cyan-300">{task.progress}%</span>
                    </div>
                    <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
                        style={{ width: `${task.progress}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Terminal Log Output */}
                  <div className="bg-[#04060c] p-2.5 rounded border border-slate-900 text-[10px] space-y-1 max-h-32 overflow-y-auto">
                    {task.logs.map((log, idx) => (
                      <div key={idx} className="text-slate-300 flex items-start gap-2 leading-relaxed">
                        <ArrowRight className="w-2.5 h-2.5 text-cyan-400 mt-1 flex-shrink-0" />
                        <span className={log.includes('!!!') ? 'text-rose-400 font-bold' : ''}>
                          {log}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Autonomous Engineering Missions & DAG Tracker */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/20">
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <Workflow className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              AUTONOMOUS ENGINEERING MISSIONS & DAG EXECUTION ({missions.length})
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300">
            PHASE 12 MISSION ENGINE
          </span>
        </div>

        {missions.length === 0 ? (
          <div className="py-6 text-center font-mono text-xs text-slate-500">
            No active engineering missions planned. Dispatched goals will appear here with topological DAG progression.
          </div>
        ) : (
          <div className="space-y-3 font-mono text-xs">
            {missions.map((m) => (
              <div
                key={m.mission_id}
                className="p-3.5 rounded border border-slate-800 bg-slate-900/60 space-y-2.5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-cyan-300">{m.mission_id}</span>
                    <span className="text-slate-500">•</span>
                    <span className="text-slate-200 font-semibold truncate max-w-sm">{m.goal}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    m.state === 'COMPLETED'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/50'
                      : m.state === 'FAILED'
                      ? 'bg-rose-950 text-rose-400 border border-rose-500/50'
                      : 'bg-cyan-950 text-cyan-300 border border-cyan-500/50'
                  }`}>
                    {m.state}
                  </span>
                </div>

                {/* Subtask DAG Progression */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] text-slate-400 block">DAG SUBTASK PROGRESSION:</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                    {m.subtasks.map((st) => (
                      <div
                        key={st.subtask_id}
                        className="p-2 rounded bg-slate-950/70 border border-slate-800/80 space-y-1"
                      >
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-cyan-400 font-bold">{st.subtask_id}</span>
                          <span className={`px-1 rounded text-[9px] ${
                            st.status === 'COMPLETED'
                              ? 'text-emerald-400 bg-emerald-950/40'
                              : st.status === 'RUNNING'
                              ? 'text-cyan-300 bg-cyan-950/60 animate-pulse'
                              : 'text-slate-500'
                          }`}>
                            {st.status}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-300 truncate">{st.title}</div>
                        <div className="text-[9px] text-slate-500 flex justify-between">
                          <span>Agent: {st.assigned_agent}</span>
                          {st.remediation_rounds > 0 && (
                            <span className="text-amber-400">Rounds: {st.remediation_rounds}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
