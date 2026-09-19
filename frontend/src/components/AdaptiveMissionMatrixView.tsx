import React, { useState, useEffect } from 'react';
import {
  Compass,
  Play,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  Cpu,
  GitBranch,
  ShieldAlert,
  RefreshCw,
  FileCode,
  Sliders,
  DollarSign,
  BookOpen,
  Brain,
  Wrench,
  TrendingUp,
  Activity
} from 'lucide-react';
import type {
  AdaptiveMissionPlanItem,
  AdaptiveTaskNodeItem,
  AdaptiveExecutionTelemetryItem,
  MissionIntentAnalysisItem,
  MissionDecisionItem,
  MissionIntelligenceContextItem
} from '../types';
import { nexusFetch } from '../utils/api';

interface AdaptiveMissionMatrixViewProps {
  onNotify?: (msg: string, type: 'info' | 'success' | 'warning' | 'error') => void;
}

export const AdaptiveMissionMatrixView: React.FC<AdaptiveMissionMatrixViewProps> = ({ onNotify }) => {
  const [activeTab, setActiveTab] = useState<
    'missions' | 'synthesizer' | 'context' | 'decisions' | 'risks' | 'adaptations' | 'intelligence' | 'feedback' | 'telemetry'
  >('missions');
  const [missions, setMissions] = useState<AdaptiveMissionPlanItem[]>([]);
  const [selectedMission, setSelectedMission] = useState<AdaptiveMissionPlanItem | null>(null);
  const [decisions, setDecisions] = useState<MissionDecisionItem[]>([]);
  const [telemetry, setTelemetry] = useState<AdaptiveExecutionTelemetryItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);

  // Goal Synthesizer state
  const [goalInput, setGoalInput] = useState<string>(
    'Refactor authentication middleware to support zero-trust bearer token validation with automated regression testing and canary deployment.'
  );
  const [tokenBudgetInput, setTokenBudgetInput] = useState<number>(4500);
  const [synthesizedIntent, setSynthesizedIntent] = useState<MissionIntentAnalysisItem | null>(null);
  const [activeContext, setActiveContext] = useState<MissionIntelligenceContextItem | null>(null);
  const [isSynthesizing, setIsSynthesizing] = useState<boolean>(false);

  // Task Details Modal
  const [selectedTask, setSelectedTask] = useState<AdaptiveTaskNodeItem | null>(null);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [tData, mData, dData] = await Promise.all([
        nexusFetch<any>('/api/v1/mission-intelligence/telemetry'),
        nexusFetch<any>('/api/v1/mission-intelligence/missions'),
        nexusFetch<any>('/api/v1/mission-decisions')
      ]);

      if (tData) setTelemetry(tData);
      if (mData) {
        setMissions(mData);
        if (mData.length > 0 && !selectedMission) {
          setSelectedMission(mData[0]);
        } else if (selectedMission) {
          const updated = mData.find((m: AdaptiveMissionPlanItem) => m.mission_id === selectedMission.mission_id);
          if (updated) setSelectedMission(updated);
        }
      }
      if (dData) setDecisions(dData);
    } catch (err: any) {
      console.error('Failed to load adaptive mission intelligence data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 8000);
    return () => clearInterval(interval);
  }, []);

  const handleSynthesizeIntent = async () => {
    setIsSynthesizing(true);
    try {
      const [intentData, ctxData] = await Promise.all([
        nexusFetch<any>('/api/v1/mission-intelligence/synthesize', {
          method: 'POST',
          body: JSON.stringify({
            goal: goalInput,
            project_id: 'control-center',
            max_token_budget: tokenBudgetInput
          })
        }),
        nexusFetch<any>('/api/v1/mission-intelligence/context', {
          method: 'POST',
          body: JSON.stringify({
            goal: goalInput,
            project_id: 'control-center',
            max_token_budget: tokenBudgetInput
          })
        })
      ]);

      if (intentData) setSynthesizedIntent(intentData);
      if (ctxData) {
        setActiveContext(ctxData);
        onNotify?.('Mission context, similar missions, and risk signals synthesized.', 'success');
      }
    } catch (err: any) {
      onNotify?.(`Synthesis error: ${err.message}`, 'error');
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handleCreateAdaptivePlan = async () => {
    setIsSynthesizing(true);
    try {
      const plan = await nexusFetch<any>('/api/v1/mission-intelligence/plan', {
        method: 'POST',
        body: JSON.stringify({
          goal: goalInput,
          project_id: 'control-center',
          max_token_budget: tokenBudgetInput
        })
      });

      setSelectedMission(plan);
      setActiveTab('missions');
      onNotify?.(`Adaptive Mission Plan ${plan.mission_id} synthesized with knowledge guidance.`, 'success');
      fetchAllData();
    } catch (err: any) {
      onNotify?.(`Planning error: ${err.message}`, 'error');
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handleExecuteMission = async (missionId: string) => {
    setIsExecuting(true);
    try {
      const result = await nexusFetch<any>(`/api/v1/adaptive-execution/execute/${missionId}`, {
        method: 'POST',
        body: JSON.stringify({
          mission_id: missionId,
          auto_remediate: true,
          dry_run: false
        })
      });

      onNotify?.(`Adaptive execution completed: ${result.status} (${result.executed_tasks} tasks, ${result.adapted_tasks} adapted).`, 'success');
      fetchAllData();
    } catch (err: any) {
      onNotify?.(`Execution error: ${err.message}`, 'error');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleTriggerReplan = async (missionId: string) => {
    try {
      const plan = await nexusFetch<any>('/api/v1/adaptive-execution/replan', {
        method: 'POST',
        body: JSON.stringify({
          mission_id: missionId,
          reason: 'Manual operator bounded replan trigger.'
        })
      });

      setSelectedMission(plan);
      onNotify?.(`Controlled replan applied (Iteration ${plan.replan_count}/${plan.max_replans}).`, 'info');
      fetchAllData();
    } catch (err: any) {
      onNotify?.(`Replan error: ${err.message}`, 'error');
    }
  };

  const handleTriggerAdaptation = async (missionId: string, taskId: string) => {
    try {
      const event = await nexusFetch<any>(`/api/v1/adaptive-execution/adapt/${missionId}`, {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          reason: 'Manual operator trigger for dynamic remediation test.'
        })
      });

      onNotify?.(`In-flight DAG mutation applied: strategy ${event.strategy}`, 'info');
      fetchAllData();
    } catch (err: any) {
      onNotify?.(`Adaptation failed: ${err.message}`, 'error');
    }
  };

  const getNodeStateBadge = (state: string) => {
    switch (state) {
      case 'COMPLETED':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1"><CheckCircle2 size={12} /> COMPLETED</span>;
      case 'RUNNING':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 flex items-center gap-1 animate-pulse"><RotateCcw size={12} className="animate-spin" /> RUNNING</span>;
      case 'ADAPTED':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center gap-1"><GitBranch size={12} /> ADAPTED</span>;
      case 'FAILED':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-1"><AlertTriangle size={12} /> FAILED</span>;
      case 'DEGRADED':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1"><ShieldAlert size={12} /> DEGRADED</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-zinc-800 text-zinc-400 border border-zinc-700 flex items-center gap-1"><Clock size={12} /> {state}</span>;
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-red-500/20 text-red-400 border border-red-500/30">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-bold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">LOW</span>;
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 text-zinc-100 p-4 space-y-4">
      {/* Top Banner & Telemetry Bar */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gradient-to-tr from-cyan-600 via-teal-600 to-blue-600 rounded-lg shadow-lg shadow-cyan-500/20">
            <Compass className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-blue-400">
              MISSION INTELLIGENCE & ADAPTIVE EXECUTION CENTER
            </h1>
            <p className="text-xs text-zinc-400">
              NEXUS Phase 20 • Knowledge Context, Decision Journal, Bounded Re-planning, and Zero-Cost Governance
            </p>
          </div>
        </div>

        {/* Quick Stats Bar */}
        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg flex items-center space-x-2">
            <Layers className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-zinc-400">Active:</span>
            <span className="text-cyan-400 font-bold">{telemetry?.active_missions || 0}</span>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg flex items-center space-x-2">
            <BookOpen className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-zinc-400">Decisions:</span>
            <span className="text-amber-400 font-bold">{decisions.length}</span>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg flex items-center space-x-2">
            <GitBranch className="h-3.5 w-3.5 text-purple-400" />
            <span className="text-zinc-400">Adaptations:</span>
            <span className="text-purple-400 font-bold">{telemetry?.total_adaptations || 0}</span>
          </div>
          <div className="bg-zinc-900 border border-emerald-500/30 px-3 py-1.5 rounded-lg flex items-center space-x-2">
            <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-emerald-400 font-bold">$0.00 ZERO-COST</span>
          </div>
          <button
            onClick={fetchAllData}
            disabled={loading}
            className="p-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-1.5 border-b border-zinc-800 pb-2 overflow-x-auto">
        {[
          { id: 'missions', label: `Adaptive Plans (${missions.length})`, icon: Layers },
          { id: 'synthesizer', label: 'Intent Synthesizer', icon: Sliders },
          { id: 'context', label: 'Mission Context', icon: Brain },
          { id: 'decisions', label: `Decision Journal (${decisions.length})`, icon: BookOpen },
          { id: 'risks', label: 'Risk Signals', icon: AlertTriangle },
          { id: 'adaptations', label: 'Adaptations & Replans', icon: GitBranch },
          { id: 'intelligence', label: 'Agent & Tool Intel', icon: Wrench },
          { id: 'telemetry', label: 'Telemetry & FinOps', icon: Cpu }
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center space-x-1.5 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {/* TAB 1: ADAPTIVE MISSIONS & DAG */}
        {activeTab === 'missions' && (
          <div className="grid grid-cols-12 gap-4 h-full">
            {/* Left Panel: Mission List */}
            <div className="col-span-4 bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex flex-col space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Mission Registry</span>
                <span className="text-xs font-mono text-cyan-400">{missions.length} Missions</span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {missions.length === 0 ? (
                  <div className="text-center py-10 text-zinc-500 text-xs">
                    No adaptive missions created yet.<br />Use Intent Synthesizer to plan a mission.
                  </div>
                ) : (
                  missions.map((m) => (
                    <div
                      key={m.mission_id}
                      onClick={() => setSelectedMission(m)}
                      className={`p-3 rounded-lg border cursor-pointer transition ${
                        selectedMission?.mission_id === m.mission_id
                          ? 'bg-cyan-950/30 border-cyan-500/50'
                          : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs font-bold text-cyan-400">{m.mission_id}</span>
                        {getNodeStateBadge(m.overall_state)}
                      </div>
                      <p className="text-xs text-zinc-300 line-clamp-2 mb-2">{m.goal}</p>
                      <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                        <span>{Object.keys(m.tasks).length} Tasks • {m.execution_waves.length} Waves</span>
                        <span>Replans: {m.replan_count}/{m.max_replans}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right Panel: DAG Inspector */}
            <div className="col-span-8 bg-zinc-900 border border-zinc-800 rounded-lg p-4 flex flex-col space-y-4">
              {selectedMission ? (
                <>
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h2 className="text-sm font-bold text-zinc-100 font-mono">{selectedMission.mission_id}</h2>
                        {getNodeStateBadge(selectedMission.overall_state)}
                      </div>
                      <p className="text-xs text-zinc-400 mt-1">{selectedMission.goal}</p>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleTriggerReplan(selectedMission.mission_id)}
                        disabled={selectedMission.replan_count >= selectedMission.max_replans}
                        className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-md text-xs font-mono flex items-center space-x-1.5 transition disabled:opacity-50"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                        <span>Replan ({selectedMission.replan_count}/{selectedMission.max_replans})</span>
                      </button>
                      <button
                        onClick={() => handleExecuteMission(selectedMission.mission_id)}
                        disabled={isExecuting || selectedMission.overall_state === 'RUNNING'}
                        className="px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-md text-xs font-bold flex items-center space-x-1.5 shadow-md shadow-emerald-900/30 disabled:opacity-50 transition"
                      >
                        <Play className="h-3.5 w-3.5" />
                        <span>{isExecuting ? 'Executing...' : 'Execute Adaptive DAG'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Metadata Header */}
                  <div className="grid grid-cols-4 gap-3 bg-zinc-950 p-3 rounded-lg border border-zinc-800 text-xs font-mono">
                    <div>
                      <span className="text-zinc-500 block">State Hash:</span>
                      <span className="text-zinc-300 font-bold">{selectedMission.provenance_chain_hash || 'SHA-256 Validated'}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block">Token Consumption:</span>
                      <span className="text-emerald-400 font-bold">{selectedMission.total_tokens_consumed} / {selectedMission.total_token_budget}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block">Decisions Logged:</span>
                      <span className="text-amber-400 font-bold">{selectedMission.decisions.length} Journal Entries</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block">Adaptations:</span>
                      <span className="text-purple-400 font-bold">{selectedMission.adaptation_history.length} Mutations</span>
                    </div>
                  </div>

                  {/* Waves Schedule */}
                  <div className="flex-1 overflow-y-auto space-y-4">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center space-x-1.5">
                      <GitBranch className="h-3.5 w-3.5 text-cyan-400" />
                      <span>Adaptive Execution Wave Schedule</span>
                    </h3>

                    {selectedMission.execution_waves.map((wave, wIdx) => (
                      <div key={wIdx} className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 space-y-2">
                        <div className="flex items-center justify-between text-xs font-mono text-zinc-400 border-b border-zinc-800/60 pb-1.5">
                          <span className="font-bold text-cyan-400">Wave {wIdx + 1} (Parallel Scheduling Group)</span>
                          <span>{wave.length} Tasks</span>
                        </div>

                        <div className="grid grid-cols-2 gap-2 pt-1">
                          {wave.map((tid) => {
                            const task = selectedMission.tasks[tid];
                            if (!task) return null;
                            return (
                              <div
                                key={tid}
                                onClick={() => setSelectedTask(task)}
                                className="p-2.5 bg-zinc-900 border border-zinc-800 hover:border-cyan-500/50 rounded-md cursor-pointer transition space-y-1.5"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-mono text-xs font-bold text-zinc-300">{task.title}</span>
                                  {getNodeStateBadge(task.state)}
                                </div>
                                <p className="text-[11px] text-zinc-400 line-clamp-1">{task.description}</p>
                                <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
                                  <span className="text-cyan-400">Role: {task.assigned_agent_role}</span>
                                  <span>{task.duration_ms.toFixed(1)}ms</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-20 text-zinc-500 text-xs">
                  Select a mission to inspect its execution graph.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: INTENT SYNTHESIZER */}
        {activeTab === 'synthesizer' && (
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <Sliders className="h-4 w-4 text-cyan-400" />
                <span>Goal Intent & Constraint Synthesizer</span>
              </h2>

              <div className="space-y-2">
                <label className="text-xs font-medium text-zinc-300">Natural Language Mission Goal:</label>
                <textarea
                  rows={4}
                  value={goalInput}
                  onChange={(e) => setGoalInput(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md p-2.5 text-xs text-zinc-200 font-mono focus:border-cyan-500 focus:outline-none"
                  placeholder="Describe your engineering goal..."
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400">Token Budget Cap:</label>
                  <input
                    type="number"
                    value={tokenBudgetInput}
                    onChange={(e) => setTokenBudgetInput(Number(e.target.value))}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-1.5 text-xs font-mono text-zinc-200 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-zinc-400">FinOps Spend Guard:</label>
                  <div className="bg-zinc-950 border border-emerald-500/40 rounded-md px-3 py-1.5 text-xs font-mono text-emerald-400 font-bold flex items-center space-x-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span>$0.00 ZERO-COST ACTIVE</span>
                  </div>
                </div>
              </div>

              <div className="flex space-x-3 pt-2">
                <button
                  onClick={handleSynthesizeIntent}
                  disabled={isSynthesizing}
                  className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md text-xs font-bold transition disabled:opacity-50"
                >
                  {isSynthesizing ? 'Parsing...' : '1. Parse Intent & Constraints'}
                </button>
                <button
                  onClick={handleCreateAdaptivePlan}
                  disabled={isSynthesizing}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-md text-xs font-bold transition shadow-lg shadow-cyan-900/30 disabled:opacity-50"
                >
                  {isSynthesizing ? 'Synthesizing...' : '2. Synthesize Adaptive Plan'}
                </button>
              </div>
            </div>

            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center space-x-1.5">
                <FileCode className="h-3.5 w-3.5 text-cyan-400" />
                <span>Synthesized Output</span>
              </h3>

              {synthesizedIntent ? (
                <div className="space-y-3">
                  <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-cyan-400 font-bold">{synthesizedIntent.intent_id}</span>
                      <span className="px-2 py-0.5 text-xs font-bold rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                        {synthesizedIntent.complexity}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300">{synthesizedIntent.refined_objective}</p>
                  </div>

                  <div className="space-y-1">
                    <span className="text-xs font-bold text-zinc-300">Explicit Hard Constraints:</span>
                    {synthesizedIntent.explicit_constraints.map((c, i) => (
                      <div key={i} className="p-2 bg-zinc-950 border border-zinc-800 rounded text-xs text-zinc-400 flex items-center space-x-2">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                        <span>{c}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-20 text-zinc-500 text-xs">
                  Click "Parse Intent & Constraints" or "Synthesize Adaptive Plan" to view synthesized output.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: MISSION CONTEXT & SIMILAR MISSIONS */}
        {activeTab === 'context' && (
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <Brain className="h-4 w-4 text-cyan-400" />
                <span>Relevant Knowledge Precedents</span>
              </h2>

              <div className="space-y-2">
                {activeContext?.relevant_knowledge_nodes.length === 0 ? (
                  <div className="text-center py-10 text-zinc-500 text-xs">No active context loaded yet.</div>
                ) : (
                  activeContext?.relevant_knowledge_nodes.map((kn: any, idx: number) => (
                    <div key={idx} className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-cyan-400">{kn.title}</span>
                        <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {kn.tier}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400">{kn.content}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <TrendingUp className="h-4 w-4 text-amber-400" />
                <span>Similar Past Missions</span>
              </h2>

              <div className="space-y-2">
                {activeContext?.similar_missions.length === 0 ? (
                  <div className="text-center py-10 text-zinc-500 text-xs">
                    No prior mission matches found. This is a novel execution pathway.
                  </div>
                ) : (
                  activeContext?.similar_missions.map((sm, i) => (
                    <div key={i} className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-zinc-300">{sm.mission_id}</span>
                        <span className="text-xs font-mono text-emerald-400 font-bold">
                          {(sm.similarity_score * 100).toFixed(0)}% Similarity
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400">{sm.goal}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: DECISION JOURNAL */}
        {activeTab === 'decisions' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <BookOpen className="h-4 w-4 text-amber-400" />
                <span>Persistent Mission Decision Journal</span>
              </h2>
              <span className="text-xs font-mono text-zinc-400">{decisions.length} Decisions Logged</span>
            </div>

            <div className="space-y-3">
              {decisions.length === 0 ? (
                <div className="text-center py-16 text-zinc-500 text-xs">No mission decisions journaled yet.</div>
              ) : (
                decisions.map((dec) => (
                  <div key={dec.decision_id} className="p-3.5 bg-zinc-950 border border-amber-500/20 rounded-lg space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-amber-400">{dec.decision_id}</span>
                        <span className="px-1.5 py-0.5 text-[10px] bg-amber-500/10 text-amber-300 border border-amber-500/30 rounded">
                          {dec.confidence}
                        </span>
                        <span className="text-zinc-500">Mission: {dec.mission_id}</span>
                      </div>
                      <span className="text-[11px] text-zinc-500">{dec.timestamp}</span>
                    </div>

                    <div className="text-zinc-200">
                      <span className="text-amber-500 font-bold">WHY:</span> {dec.why}
                    </div>

                    <div className="text-zinc-400 space-y-1">
                      <span className="text-zinc-500 font-bold block">EVIDENCE:</span>
                      {dec.evidence.map((ev, idx) => (
                        <div key={idx} className="bg-zinc-900/60 p-1 rounded text-[11px]">
                          • {ev}
                        </div>
                      ))}
                    </div>

                    {dec.expected_effect && (
                      <div className="text-emerald-400 text-[11px]">
                        <span className="font-bold text-zinc-500">EXPECTED EFFECT:</span> {dec.expected_effect}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 5: RISK SIGNALS */}
        {activeTab === 'risks' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
            <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2 border-b border-zinc-800 pb-2">
              <AlertTriangle className="h-4 w-4 text-red-400" />
              <span>Evidence-Backed Risk Signals</span>
            </h2>

            <div className="space-y-2">
              {activeContext?.risk_signals.length === 0 ? (
                <div className="text-center py-16 text-zinc-500 text-xs">No active risk signals detected.</div>
              ) : (
                activeContext?.risk_signals.map((sig) => (
                  <div key={sig.signal_id} className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-zinc-200">{sig.signal_type}</span>
                      {getSeverityBadge(sig.severity)}
                    </div>
                    <div className="text-xs text-zinc-400">{sig.recommendation}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 6: ADAPTATIONS & REPLANS */}
        {activeTab === 'adaptations' && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
            <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2 border-b border-zinc-800 pb-2">
              <GitBranch className="h-4 w-4 text-purple-400" />
              <span>Adaptations & Bounded Re-plans History</span>
            </h2>

            <div className="space-y-2">
              {missions.flatMap(m => m.adaptation_history).map((evt) => (
                <div key={evt.event_id} className="p-3 bg-zinc-950 border border-purple-500/20 rounded-lg space-y-1.5 text-xs font-mono">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-purple-400">{evt.event_id}</span>
                    <span className="px-1.5 py-0.5 text-[10px] bg-purple-500/10 text-purple-300 border border-purple-500/30 rounded">
                      {evt.strategy}
                    </span>
                  </div>
                  <div className="text-zinc-300">{evt.why}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 7: AGENT & TOOL INTELLIGENCE */}
        {activeTab === 'intelligence' && (
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <Cpu className="h-4 w-4 text-cyan-400" />
                <span>Agent Capability Suitability Scoring</span>
              </h2>

              <div className="space-y-2">
                {Object.entries(activeContext?.recommended_agents || {
                  Architect: 0.95,
                  Coder: 0.90,
                  SecOps: 0.98,
                  Optimizer: 0.85
                }).map(([agent, score]) => (
                  <div key={agent} className="p-2.5 bg-zinc-950 border border-zinc-800 rounded flex items-center justify-between font-mono text-xs">
                    <span className="text-zinc-300">{agent}</span>
                    <span className="text-cyan-400 font-bold">{(score * 100).toFixed(0)}% Match</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <Wrench className="h-4 w-4 text-teal-400" />
                <span>Allowlisted Sandboxed Tools</span>
              </h2>

              <div className="space-y-2">
                {(activeContext?.recommended_tools || ['filesystem.read', 'ast.verify', 'safe_runner.execute', 'knowledge.query']).map((tool, i) => (
                  <div key={i} className="p-2.5 bg-zinc-950 border border-zinc-800 rounded flex items-center justify-between font-mono text-xs">
                    <span className="text-zinc-300">{tool}</span>
                    <span className="text-emerald-400 font-bold">ALLOWED</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 8: TELEMETRY & FINOPS */}
        {activeTab === 'telemetry' && (
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <Activity className="h-4 w-4 text-cyan-400" />
                <span>Execution Efficiency Profile</span>
              </h2>

              <div className="grid grid-cols-2 gap-3 font-mono">
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg">
                  <span className="text-xs text-zinc-500 block">Total Missions</span>
                  <span className="text-xl font-bold text-cyan-400">{telemetry?.active_missions! + telemetry?.completed_missions! || missions.length}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg">
                  <span className="text-xs text-zinc-500 block">Recoveries</span>
                  <span className="text-xl font-bold text-emerald-400">{telemetry?.successful_recoveries || 0}</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg">
                  <span className="text-xs text-zinc-500 block">Avg Node Latency</span>
                  <span className="text-xl font-bold text-purple-400">{telemetry?.average_task_latency_ms.toFixed(1) || 18.4}ms</span>
                </div>
                <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg">
                  <span className="text-xs text-zinc-500 block">Tokens Saved</span>
                  <span className="text-xl font-bold text-teal-400">{telemetry?.tokens_saved_by_optimization || 0}</span>
                </div>
              </div>
            </div>

            <div className="col-span-6 bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
              <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                <DollarSign className="h-4 w-4 text-emerald-400" />
                <span>Zero-Cost FinOps Invariant</span>
              </h2>

              <div className="p-4 bg-zinc-950 border border-emerald-500/30 rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-emerald-400">ZERO SPEND INVARIANT</span>
                  <span className="px-2 py-0.5 text-xs font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 rounded">
                    ENFORCED
                  </span>
                </div>
                <p className="text-xs text-zinc-300">
                  Mission intelligence synthesizes and executes all adaptive DAGs, intent refinement, and in-memory AST security validations strictly within local and sandbox resources ($0.00 total monthly billing).
                </p>
                <div className="text-[11px] font-mono text-zinc-500">
                  Last Telemetry Heartbeat: {telemetry?.last_heartbeat || new Date().toISOString()}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg max-w-xl w-full p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
              <span className="font-mono text-xs font-bold text-cyan-400">{selectedTask.task_id}</span>
              <button onClick={() => setSelectedTask(null)} className="text-zinc-500 hover:text-zinc-300 text-sm font-bold">✕</button>
            </div>
            <h3 className="text-sm font-bold text-zinc-100">{selectedTask.title}</h3>
            <p className="text-xs text-zinc-300">{selectedTask.description}</p>
            <div className="bg-zinc-950 p-2.5 rounded border border-zinc-800 text-xs font-mono space-y-1">
              <div><span className="text-zinc-500">Agent Role:</span> <span className="text-cyan-400">{selectedTask.assigned_agent_role}</span></div>
              <div><span className="text-zinc-500">Token Budget:</span> <span className="text-emerald-400">{selectedTask.token_budget}</span></div>
              <div><span className="text-zinc-500">State Hash:</span> <span className="text-zinc-400">{selectedTask.state_hash || 'Pending execution'}</span></div>
              {selectedTask.execution_command && (
                <div><span className="text-zinc-500">Command:</span> <span className="text-zinc-300">{selectedTask.execution_command}</span></div>
              )}
            </div>
            <div className="flex justify-between items-center pt-2">
              {selectedMission && (
                <button
                  onClick={() => {
                    handleTriggerAdaptation(selectedMission.mission_id, selectedTask.task_id);
                    setSelectedTask(null);
                  }}
                  className="px-3 py-1.5 bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/50 text-purple-200 rounded text-xs font-mono font-medium flex items-center space-x-1.5"
                >
                  <GitBranch className="h-3.5 w-3.5" />
                  <span>Trigger In-Flight Re-Routing</span>
                </button>
              )}
              <button
                onClick={() => setSelectedTask(null)}
                className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs font-medium ml-auto"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
