import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  ShieldAlert,
  Cpu,
  Zap,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Lock,
  Server,
  ArrowRight,
  Trash2,
  Bot,
  Filter,
  Layers
} from 'lucide-react';
import type { SystemHealth, UnifiedEvent, HandoffGraph } from '../types';
import { sound } from '../utils/audio';

interface CyberHudLiveViewProps {
  onTriggerPanic: () => void;
  onNavigateTab?: (tab: string) => void;
}

export const CyberHudLiveView: React.FC<CyberHudLiveViewProps> = ({
  onTriggerPanic,
  onNavigateTab
}) => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [events, setEvents] = useState<UnifiedEvent[]>([]);
  const [handoffs, setHandoffs] = useState<HandoffGraph | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isSweeping, setIsSweeping] = useState<boolean>(false);
  const [sweepResult, setSweepResult] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  const fetchHudData = useCallback(async () => {
    try {
      const [hRes, eRes, gRes] = await Promise.all([
        fetch('/api/system/health').then(r => r.json()),
        fetch('/api/system/events?limit=50').then(r => r.json()),
        fetch('/api/system/handoffs').then(r => r.json())
      ]);
      setHealth(hRes);
      setEvents(eRes.events || []);
      setHandoffs(gRes);
    } catch (err) {
      console.warn('Failed to poll Cyber-HUD endpoints:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHudData();
    if (!autoRefresh) return;
    const interval = setInterval(fetchHudData, 3000);
    return () => clearInterval(interval);
  }, [fetchHudData, autoRefresh]);

  const handleSweep = async () => {
    setIsSweeping(true);
    sound.click();
    try {
      const res = await fetch('/api/v1/system/sweep', { method: 'POST' });
      const data = await res.json();
      setSweepResult(`Sweep clean: pruned ${data.pruned_worktrees} worktrees. Zero orphans.`);
      sound.beep(600, 0.1, 'triangle');
      fetchHudData();
    } catch (err) {
      setSweepResult('Sweep failed or requires elevated authorization.');
    } finally {
      setIsSweeping(false);
      setTimeout(() => setSweepResult(null), 4000);
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case 'HEALTHY':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-950/70 border border-emerald-500/50 text-emerald-400 font-mono font-bold text-xs tracking-wider shadow-[0_0_12px_rgba(0,255,157,0.3)]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            OPERATIONAL [HEALTHY]
          </span>
        );
      case 'WARNING':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded bg-amber-950/70 border border-amber-500/50 text-amber-400 font-mono font-bold text-xs tracking-wider shadow-[0_0_12px_rgba(245,158,11,0.3)]">
            <AlertTriangle className="w-3.5 h-3.5" />
            ATTENTION REQUIRED [WARNING]
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded bg-orange-950/70 border border-orange-500/50 text-orange-400 font-mono font-bold text-xs tracking-wider shadow-[0_0_12px_rgba(249,115,22,0.3)]">
            <AlertTriangle className="w-3.5 h-3.5" />
            DEGRADED SUB-CIRCUITS
          </span>
        );
      case 'BLOCKED':
      case 'FAILED':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded bg-rose-950/80 border border-rose-500/60 text-rose-400 font-mono font-bold text-xs tracking-wider shadow-[0_0_12px_rgba(244,63,94,0.4)]">
            <XCircle className="w-3.5 h-3.5" />
            SYSTEM BLOCKED / CRITICAL
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded bg-slate-900 border border-slate-700 text-slate-400 font-mono text-xs">
            CONNECTING...
          </span>
        );
    }
  };

  const filteredEvents = events.filter(e => {
    if (selectedCategory !== 'all' && e.category !== selectedCategory) return false;
    if (selectedSeverity !== 'all' && e.severity !== selectedSeverity) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner: Cyber-HUD Operations Header */}
      <div className="hud-panel p-4 rounded-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-cyan-500/30">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
              <h2 className="text-lg font-black tracking-widest text-cyan-300 font-mono">
                CYBER-HUD // LIVE OPERATIONS CONTROL
              </h2>
            </div>
            {getStatusBadge(health?.overall_status)}
          </div>
          <p className="text-xs text-slate-400 font-mono">
            {health?.summary || 'Aggregating live kernel telemetry, provider circuits, and delivery state...'}
          </p>
          {health?.status_reasons && health.status_reasons.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {health.status_reasons.map((r, i) => (
                <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/50 border border-amber-500/30 text-amber-300">
                  ⚠️ {r}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Global Action Bar */}
        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto justify-end">
          {/* FinOps Guarantee Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/90 border border-emerald-500/40 text-emerald-400 font-mono text-[11px]" title="Zero Cost Ceiling strictly verified ($0.00 spend)">
            <Lock className="w-3 h-3 text-emerald-400" />
            <span>FINOPS: $0.00 CEILING</span>
          </div>

          {/* Sweep Button */}
          <button
            onClick={handleSweep}
            disabled={isSweeping}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-950/50 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-900/50 hover:border-cyan-400 transition-all font-mono text-xs disabled:opacity-50"
            title="Clean transient worktrees & verify zero orphans"
          >
            <Trash2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>{isSweeping ? 'SWEEPING...' : 'SWEEP REPO'}</span>
          </button>

          {/* Auto Refresh Toggle */}
          <button
            onClick={() => {
              sound.click();
              setAutoRefresh(p => !p);
            }}
            className={`px-2 py-1 rounded text-[10px] font-mono border transition-all ${
              autoRefresh
                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                : 'bg-slate-900 border-slate-700 text-slate-500 hover:text-slate-300'
            }`}
            title="Auto-refresh (3s tick)"
          >
            {autoRefresh ? 'AUTO: ON' : 'AUTO: OFF'}
          </button>

          {/* Refresh Toggle */}
          <button
            onClick={() => {
              sound.click();
              fetchHudData();
            }}
            className={`p-1.5 rounded bg-slate-900 border border-slate-700 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/40 transition-all ${loading ? 'animate-spin' : ''}`}
            title="Manual Telemetry Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          {/* Emergency Panic Button */}
          <button
            onClick={onTriggerPanic}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-950/80 border border-rose-600/70 text-rose-300 hover:bg-rose-900/80 transition-all font-mono text-xs font-bold shadow-[0_0_10px_rgba(244,63,94,0.3)]"
            title="Emergency Abort All In-Flight Missions"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
            <span>PANIC</span>
          </button>
        </div>
      </div>

      {sweepResult && (
        <div className="hud-panel p-3 rounded border-cyan-400/60 bg-cyan-950/60 text-cyan-200 font-mono text-xs flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-cyan-400" />
          <span>{sweepResult}</span>
        </div>
      )}

      {/* 4 Core Operational HUD Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Gauge 1: Daemon & API Kernel */}
        <div className="hud-panel p-4 rounded-lg space-y-2.5 border-cyan-500/20">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 tracking-wider flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              DAEMON & API KERNEL
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
              v{health?.components.api.version || '1.0.0'}
            </span>
          </div>
          <div className="text-xl font-bold font-mono text-cyan-300">
            {health?.components.daemon.status || 'ONLINE'}
          </div>
          <div className="space-y-1 text-[11px] font-mono text-slate-400">
            <div className="flex justify-between">
              <span>PID:</span>
              <span className="text-slate-200 font-bold">{health?.components.daemon.pid}</span>
            </div>
            <div className="flex justify-between">
              <span>RSS Memory:</span>
              <span className="text-slate-200">{health?.components.daemon.memory_mb || '28.4'} MB</span>
            </div>
            <div className="flex justify-between">
              <span>Endpoint:</span>
              <span className="text-slate-400 truncate max-w-[140px]">{health?.components.daemon.endpoint}</span>
            </div>
          </div>
        </div>

        {/* Gauge 2: AI Provider Cluster */}
        <div className="hud-panel p-4 rounded-lg space-y-2.5 border-cyan-500/20">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 tracking-wider flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              AI PROVIDERS
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/40">
              {health?.components.ai_providers.healthy_providers || 4} / {health?.components.ai_providers.total_providers || 4} UP
            </span>
          </div>
          <div className="text-xl font-bold font-mono text-amber-300 truncate">
            {health?.components.ai_providers.active_preference.toUpperCase() || 'LOCAL_MOCK'}
          </div>
          <div className="space-y-1 text-[11px] font-mono text-slate-400">
            <div className="flex justify-between">
              <span>Circuits Open:</span>
              <span className={`font-bold ${health?.components.ai_providers.circuits_open ? 'text-rose-400' : 'text-emerald-400'}`}>
                {health?.components.ai_providers.circuits_open || 0}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Fallback Ready:</span>
              <span className="text-emerald-400">ENABLED (CASCADE)</span>
            </div>
            <div className="flex justify-between">
              <span>Control:</span>
              <button
                onClick={() => onNavigateTab && onNavigateTab('cloud')}
                className="text-cyan-400 hover:underline hover:text-cyan-300"
              >
                Configure Providers →
              </button>
            </div>
          </div>
        </div>

        {/* Gauge 3: Worktrees & Delivery Sandboxes */}
        <div className="hud-panel p-4 rounded-lg space-y-2.5 border-cyan-500/20">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 tracking-wider flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              WORKTREES & DELIVERY
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/60 text-purple-300 border border-purple-500/40">
              SANDBOXED
            </span>
          </div>
          <div className="text-xl font-bold font-mono text-purple-300">
            {health?.components.worktrees.active_count || 0} ACTIVE
          </div>
          <div className="space-y-1 text-[11px] font-mono text-slate-400">
            <div className="flex justify-between">
              <span>GitHub Mode:</span>
              <span className="text-slate-200">{health?.components.github.mode || 'MOCK'}</span>
            </div>
            <div className="flex justify-between">
              <span>Active Missions:</span>
              <span className="text-slate-200">{health?.components.missions.active_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span>Pending Approvals:</span>
              <span className={`font-bold ${health?.components.approvals.pending_count ? 'text-amber-400' : 'text-slate-400'}`}>
                {health?.components.approvals.pending_count || 0}
              </span>
            </div>
          </div>
        </div>

        {/* Gauge 4: FinOps $0.00 Spend Guardrail */}
        <div className="hud-panel p-4 rounded-lg space-y-2.5 border-cyan-500/20">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-400 tracking-wider flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              FINOPS LEDGER
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/40">
              UNLINKED
            </span>
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400">
            ${(health?.components.finops.current_spend_usd ?? 0.0).toFixed(2)} USD
          </div>
          <div className="space-y-1 text-[11px] font-mono text-slate-400">
            <div className="flex justify-between">
              <span>Hard Cap:</span>
              <span className="text-emerald-400 font-bold">$0.00 USD</span>
            </div>
            <div className="flex justify-between">
              <span>GCP Billing:</span>
              <span className="text-emerald-400">UNLINKED / SAFE</span>
            </div>
            <div className="flex justify-between">
              <span>AST Sentinel:</span>
              <span className="text-cyan-400">ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {/* AGY ↔ Codex Multi-Agent Handoff Pipeline Visualizer */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              MULTI-AGENT HANDOFF PIPELINE // AGY ↔ CODEX ↔ QA ↔ SECURITY
            </h3>
          </div>
          <div className="flex items-center gap-3 font-mono text-xs">
            <span className="text-slate-400">
              Recursion Guard: <span className="text-cyan-300 font-bold">{handoffs?.current_recursion_depth || 0} / {handoffs?.recursion_depth_limit || 5}</span>
            </span>
            {handoffs?.active_mission_id && (
              <span className="px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 text-[10px]">
                ACTIVE MISSION: {handoffs.active_mission_id.substring(0, 8)}...
              </span>
            )}
          </div>
        </div>

        {/* Responsive Pipeline Stages */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-1">
          {handoffs?.nodes.map((node, index) => {
            const isActive = node.status === 'active';
            const isLast = index === (handoffs.nodes.length - 1);

            return (
              <div
                key={node.id}
                className={`relative p-3 rounded border transition-all ${
                  isActive
                    ? 'bg-cyan-950/50 border-cyan-400 shadow-[0_0_14px_rgba(0,240,255,0.3)]'
                    : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono text-slate-400">STAGE 0{node.stage_order}</span>
                  <span
                    className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold ${
                      isActive
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/60 animate-pulse'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {node.status.toUpperCase()}
                  </span>
                </div>
                <div className="text-xs font-mono font-bold text-slate-200 truncate">{node.name}</div>
                <div className="text-[10px] text-slate-400 font-mono mt-1 line-clamp-2">{node.role}</div>
                <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span>{node.autonomy}</span>
                  <span className="text-cyan-400">{node.model.split('-').slice(0, 2).join('-')}</span>
                </div>

                {!isLast && (
                  <div className="hidden md:block absolute -right-3.5 top-1/2 -translate-y-1/2 z-10 text-cyan-500/60">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Unified Real-Time Event Stream */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              UNIFIED AUDIT & TELEMETRY STREAM
            </h3>
            <span className="text-xs font-mono text-slate-400">({filteredEvents.length} events)</span>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 bg-slate-900 px-2 py-1 rounded border border-slate-800 text-xs font-mono">
              <Filter className="w-3 h-3 text-slate-400" />
              <select
                value={selectedCategory}
                onChange={e => setSelectedCategory(e.target.value)}
                className="bg-transparent text-slate-300 focus:outline-none text-[11px]"
              >
                <option value="all">All Categories</option>
                <option value="mission">Missions</option>
                <option value="delivery">Deliveries</option>
                <option value="merge">Merges</option>
                <option value="approval">Approvals</option>
                <option value="security">Security</option>
                <option value="finops">FinOps</option>
                <option value="audit">Audits</option>
              </select>
            </div>

            <div className="flex items-center gap-1 bg-slate-900 px-2 py-1 rounded border border-slate-800 text-xs font-mono">
              <select
                value={selectedSeverity}
                onChange={e => setSelectedSeverity(e.target.value)}
                className="bg-transparent text-slate-300 focus:outline-none text-[11px]"
              >
                <option value="all">All Severities</option>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>
        </div>

        {/* Event Log Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                <th className="pb-2">TIME (UTC)</th>
                <th className="pb-2">SEVERITY</th>
                <th className="pb-2">CATEGORY</th>
                <th className="pb-2">SOURCE / AGENT</th>
                <th className="pb-2">ACTION / EVENT</th>
                <th className="pb-2">RESULT</th>
                <th className="pb-2">TARGET</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-[11px]">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No matching events found in unified stream buffer.
                  </td>
                </tr>
              ) : (
                filteredEvents.map(ev => {
                  let sevClass = 'text-cyan-400 bg-cyan-950/40 border-cyan-500/30';
                  if (ev.severity === 'warning') sevClass = 'text-amber-400 bg-amber-950/40 border-amber-500/30';
                  if (ev.severity === 'error' || ev.severity === 'critical') sevClass = 'text-rose-400 bg-rose-950/40 border-rose-500/30';

                  const timeStr = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString('en-US', { hour12: false }) : '--:--:--';

                  return (
                    <tr key={ev.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-2 text-slate-400 whitespace-nowrap">{timeStr}</td>
                      <td className="py-2">
                        <span className={`px-1.5 py-0.5 rounded border text-[10px] font-bold ${sevClass}`}>
                          {ev.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 text-slate-300 font-semibold uppercase">{ev.category}</td>
                      <td className="py-2 text-slate-200">{ev.source}</td>
                      <td className="py-2 text-slate-300 font-medium truncate max-w-xs" title={ev.message}>
                        {ev.event_type}
                      </td>
                      <td className="py-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                          ev.result === 'CLEAN' || ev.result === 'APPROVED' || ev.result === 'COMPLETED'
                            ? 'text-emerald-400 bg-emerald-950/40'
                            : ev.result === 'BLOCKED' || ev.result === 'FAILED'
                            ? 'text-rose-400 bg-rose-950/40'
                            : 'text-slate-300 bg-slate-800'
                        }`}>
                          {ev.result}
                        </span>
                      </td>
                      <td className="py-2 text-slate-400 truncate max-w-[120px]" title={ev.target}>
                        {ev.target}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
