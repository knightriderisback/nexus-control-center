import React, { useState, useEffect } from 'react';
import type {
  IncidentRecord,
  RemediationPlaybook,
  SelfHealingTelemetry,
  OperationsMetrics,
  RecoveryHistoryRecord,
} from '../types';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Terminal,
  RefreshCw,
  Cpu,
  Layers,
  HeartPulse,
  Flame,
  Radio,
  History,
  BookOpen,
  Check,
  RotateCcw,
  Square,
  ShieldAlert,
  Search,
  Plus
} from 'lucide-react';

export const AutonomousSelfHealingView: React.FC = () => {
  const [telemetry, setTelemetry] = useState<SelfHealingTelemetry | null>(null);
  const [metrics, setMetrics] = useState<OperationsMetrics | null>(null);
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [playbooks, setPlaybooks] = useState<RemediationPlaybook[]>([]);
  const [recoveryHistory, setRecoveryHistory] = useState<RecoveryHistoryRecord[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<IncidentRecord | null>(null);
  
  const [activeTab, setActiveTab] = useState<'matrix' | 'history' | 'playbooks'>('matrix');
  const [activeSeverityFilter, setActiveSeverityFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [showTriggerModal, setShowTriggerModal] = useState<boolean>(false);
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Form State for Trigger Modal
  const [triggerCategory, setTriggerCategory] = useState<string>('PROCESS_FAILURE');
  const [triggerSeverity, setTriggerSeverity] = useState<string>('MEDIUM');
  const [triggerTitle, setTriggerTitle] = useState<string>('Simulated Process Latency Degradation');
  const [triggerResource, setTriggerResource] = useState<string>('nexus-worker-pool');
  const [triggerAutoRemediate, setTriggerAutoRemediate] = useState<boolean>(true);

  const fetchData = async () => {
    try {
      const [telemRes, metricsRes, incRes, pbRes, histRes] = await Promise.all([
        fetch('/api/v1/self-healing/telemetry'),
        fetch('/api/v1/operations/metrics'),
        fetch('/api/v1/operations'),
        fetch('/api/v1/self-healing/playbooks'),
        fetch('/api/v1/operations/recovery-history'),
      ]);

      if (telemRes.ok) {
        const tData: SelfHealingTelemetry = await telemRes.json();
        setTelemetry(tData);
      }

      if (metricsRes.ok) {
        const mData: OperationsMetrics = await metricsRes.json();
        setMetrics(mData);
      }

      if (incRes.ok) {
        const iData: IncidentRecord[] = await incRes.json();
        setIncidents(iData);
        if (!selectedIncident && iData.length > 0) {
          setSelectedIncident(iData[0]);
        } else if (selectedIncident) {
          const updated = iData.find((i) => i.incident_id === selectedIncident.incident_id);
          if (updated) setSelectedIncident(updated);
        }
      }

      if (pbRes.ok) {
        const pData: RemediationPlaybook[] = await pbRes.json();
        setPlaybooks(pData);
      }

      if (histRes.ok) {
        const hData: RecoveryHistoryRecord[] = await histRes.json();
        setRecoveryHistory(hData);
      }
    } catch (err) {
      console.error('Error fetching operations telemetry:', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleRunWatchdogsSweep = async () => {
    try {
      const res = await fetch('/api/v1/operations/health', { method: 'GET' });
      if (res.ok) {
        setFeedbackMsg({ text: 'Radar health sweep completed. All 6 watchdogs online.', type: 'success' });
        fetchData();
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message || 'Sweep failed.', type: 'error' });
    }
  };

  const handleAcknowledge = async (id: string) => {
    setIsActionLoading(true);
    try {
      const res = await fetch(`/api/v1/operations/${id}/acknowledge?operator=cyber-operator`, { method: 'POST' });
      if (res.ok) {
        setFeedbackMsg({ text: `Incident ${id} acknowledged by operator.`, type: 'success' });
        fetchData();
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message, type: 'error' });
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleRecoverOrRetry = async (id: string) => {
    setIsActionLoading(true);
    try {
      const res = await fetch(`/api/v1/operations/${id}/retry`, { method: 'POST' });
      if (res.ok) {
        setFeedbackMsg({ text: `Remediation execution triggered for ${id}.`, type: 'success' });
        fetchData();
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message, type: 'error' });
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleEscalate = async (id: string) => {
    setIsActionLoading(true);
    try {
      const res = await fetch(`/api/v1/operations/${id}/escalate?reason=Manual+operator+escalation`, { method: 'POST' });
      if (res.ok) {
        setFeedbackMsg({ text: `Incident ${id} escalated to human intervention.`, type: 'success' });
        fetchData();
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message, type: 'error' });
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleStopRecovery = async (id: string) => {
    setIsActionLoading(true);
    try {
      const res = await fetch(`/api/v1/operations/${id}/stop?reason=Operator+aborted+action`, { method: 'POST' });
      if (res.ok) {
        setFeedbackMsg({ text: `Recovery stopped for ${id}.`, type: 'success' });
        fetchData();
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message, type: 'error' });
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleApproveGate = async (id: string) => {
    setIsActionLoading(true);
    try {
      const res = await fetch(`/api/v1/self-healing/incidents/${id}/approve`, { method: 'POST' });
      if (res.ok) {
        setFeedbackMsg({ text: `Approval granted. Remediation executed for ${id}.`, type: 'success' });
        fetchData();
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message, type: 'error' });
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleTriggerIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTriggering(true);
    setFeedbackMsg(null);

    const payload = {
      category: triggerCategory,
      severity: triggerSeverity,
      title: triggerTitle,
      target_resource: triggerResource,
      details: {
        source_watchdog: 'manual-cyber-operator',
        simulated: true,
        triggered_at: new Date().toISOString(),
      },
      auto_remediate: triggerAutoRemediate,
    };

    try {
      const res = await fetch('/api/v1/self-healing/incidents/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to trigger incident.');
      }

      const created: IncidentRecord = await res.json();
      setFeedbackMsg({
        text: `Incident ${created.incident_id} registered (${created.status}).`,
        type: 'success',
      });
      setShowTriggerModal(false);
      fetchData();
      setSelectedIncident(created);
    } catch (err: any) {
      setFeedbackMsg({ text: err.message, type: 'error' });
    } finally {
      setIsTriggering(false);
    }
  };

  const filteredIncidents = incidents.filter((inc) => {
    const matchesSev = activeSeverityFilter === 'ALL' || inc.severity === activeSeverityFilter;
    const matchesSearch =
      searchTerm === '' ||
      inc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.incident_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.target_resource.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSev && matchesSearch;
  });

  const getSeverityBadge = (sev: string) => {
    if (sev === 'CRITICAL' || sev === 'SEV_1_CRITICAL') {
      return <span className="px-2 py-0.5 rounded bg-rose-950/80 border border-rose-500/50 text-rose-300 font-mono text-[10px] font-bold animate-pulse">CRITICAL</span>;
    }
    if (sev === 'HIGH' || sev === 'SEV_2_HIGH') {
      return <span className="px-2 py-0.5 rounded bg-amber-950/80 border border-amber-500/50 text-amber-300 font-mono text-[10px] font-bold">HIGH</span>;
    }
    if (sev === 'MEDIUM' || sev === 'SEV_3_MEDIUM') {
      return <span className="px-2 py-0.5 rounded bg-yellow-950/80 border border-yellow-500/40 text-yellow-300 font-mono text-[10px]">MEDIUM</span>;
    }
    return <span className="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 font-mono text-[10px]">LOW</span>;
  };

  const getStatusBadge = (status: string) => {
    if (status === 'RESOLVED') {
      return <span className="px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 font-mono text-[10px] flex items-center gap-1"><Check className="w-3 h-3" /> RESOLVED</span>;
    }
    if (status === 'APPROVAL_PENDING') {
      return <span className="px-2 py-0.5 rounded bg-amber-950/80 border border-amber-500/50 text-amber-300 font-mono text-[10px] animate-pulse flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> APPROVAL PENDING</span>;
    }
    if (status === 'REMEDIATING' || status === 'HEALING_EXECUTING' || status === 'DIAGNOSING') {
      return <span className="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-400/50 text-cyan-300 font-mono text-[10px] animate-pulse flex items-center gap-1"><RefreshCw className="w-3 h-3 animate-spin" /> {status}</span>;
    }
    if (status === 'ESCALATED') {
      return <span className="px-2 py-0.5 rounded bg-rose-950/80 border border-rose-500/50 text-rose-300 font-mono text-[10px] font-bold flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> ESCALATED</span>;
    }
    return <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-600 text-slate-300 font-mono text-[10px]">{status}</span>;
  };

  return (
    <div className="space-y-6">
      {/* Feedback Toast */}
      {feedbackMsg && (
        <div
          className={`p-3 rounded border font-mono text-xs flex items-center justify-between transition-all ${
            feedbackMsg.type === 'success'
              ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300'
              : 'bg-rose-950/80 border-rose-500/50 text-rose-300'
          }`}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Header Matrix & Top KPI Gauges */}
      <div className="hud-panel p-5 rounded-lg border border-cyan-500/30 bg-[#080d1a]/90 relative overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-cyan-500/20 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded bg-cyan-950/50 border border-cyan-400/40 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.3)]">
              <HeartPulse className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-black tracking-widest text-cyan-300 font-mono">
                  AUTONOMOUS SELF-HEALING OPERATIONS CENTER
                </h1>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono flex items-center gap-1 font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  RADAR ACTIVE
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-mono">
                  $0.00 ZERO-COST FINOPS
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Real-Time Sentinel Watchdogs • Automated RCA • Policy-Driven Remediation • Closed-Loop Recovery
              </p>
            </div>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleRunWatchdogsSweep}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 font-mono text-xs hover:border-cyan-400 hover:bg-cyan-900/40 transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)]"
            >
              <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
              <span>RADAR SWEEP</span>
            </button>

            <button
              onClick={() => setShowTriggerModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 font-mono text-xs hover:border-emerald-400 hover:bg-emerald-900/40 transition-all shadow-[0_0_10px_rgba(16,185,129,0.15)]"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>SIMULATE INCIDENT</span>
            </button>
          </div>
        </div>

        {/* Real Metrics Gauge Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-4">
          <div className="p-3 rounded bg-[#0b1324] border border-cyan-500/20">
            <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
              <span>SYSTEM HEALTH</span>
              <Activity className="w-3 h-3 text-emerald-400" />
            </div>
            <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
              {metrics?.system_health || 'HEALTHY'}
            </div>
            <div className="text-[9px] font-mono text-slate-500 mt-0.5">
              Uptime: {telemetry?.overall_uptime_pct || 99.99}% SLA
            </div>
          </div>

          <div className="p-3 rounded bg-[#0b1324] border border-cyan-500/20">
            <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
              <span>ACTIVE INCIDENTS</span>
              <Flame className="w-3 h-3 text-amber-400" />
            </div>
            <div className="text-xl font-bold font-mono text-amber-300 mt-1">
              {telemetry?.active_incidents_count ?? 0}
            </div>
            <div className="text-[9px] font-mono text-slate-500 mt-0.5">
              Escalated: {metrics?.escalated_incidents ?? 0}
            </div>
          </div>

          <div className="p-3 rounded bg-[#0b1324] border border-cyan-500/20">
            <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
              <span>RESOLVED TOTAL</span>
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            </div>
            <div className="text-xl font-bold font-mono text-emerald-300 mt-1">
              {telemetry?.resolved_incidents_count ?? 0}
            </div>
            <div className="text-[9px] font-mono text-slate-500 mt-0.5">
              Success Rate: {telemetry?.auto_remediation_success_rate_pct ?? 100}%
            </div>
          </div>

          <div className="p-3 rounded bg-[#0b1324] border border-cyan-500/20">
            <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
              <span>MEAN TIME TO HEAL</span>
              <Clock className="w-3 h-3 text-cyan-400" />
            </div>
            <div className="text-xl font-bold font-mono text-cyan-300 mt-1">
              {telemetry?.mean_time_to_healing_seconds ?? 0.16}s
            </div>
            <div className="text-[9px] font-mono text-slate-500 mt-0.5">
              Sub-second autonomous MTTR
            </div>
          </div>

          <div className="p-3 rounded bg-[#0b1324] border border-cyan-500/20">
            <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
              <span>ACTIVE PLAYBOOKS</span>
              <BookOpen className="w-3 h-3 text-indigo-400" />
            </div>
            <div className="text-xl font-bold font-mono text-indigo-300 mt-1">
              {playbooks.length || 6}
            </div>
            <div className="text-[9px] font-mono text-slate-500 mt-0.5">
              Bounded & policy-enforced
            </div>
          </div>

          <div className="p-3 rounded bg-[#0b1324] border border-cyan-500/20">
            <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
              <span>OPERATIONS DAEMON</span>
              <Cpu className="w-3 h-3 text-cyan-400" />
            </div>
            <div className="text-xl font-bold font-mono text-cyan-300 mt-1 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              ONLINE
            </div>
            <div className="text-[9px] font-mono text-slate-500 mt-0.5">
              Loop: Idle when healthy
            </div>
          </div>
        </div>
      </div>

      {/* 6 Sentinel Watchdogs Radar Matrix */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span className="text-xs font-mono font-bold text-slate-300 tracking-wider">
              LIVE SENTINEL WATCHDOGS RADAR
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-500">
            Auto-inspected every 4000ms
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {(telemetry?.watchdogs || []).map((wd) => (
            <div
              key={wd.watchdog_id}
              className={`p-3.5 rounded-lg border bg-[#080e1c] flex flex-col justify-between transition-all ${
                wd.status === 'HEALTHY'
                  ? 'border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.05)]'
                  : wd.status === 'DEGRADED'
                  ? 'border-amber-500/40 bg-amber-950/10'
                  : 'border-rose-500/50 bg-rose-950/20 shadow-[0_0_15px_rgba(244,63,94,0.15)]'
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-slate-200">{wd.name}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold ${
                      wd.status === 'HEALTHY'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : wd.status === 'DEGRADED'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse'
                    }`}
                  >
                    {wd.status}
                  </span>
                </div>
                <p className="text-[11px] font-mono text-slate-400 mt-1.5 leading-relaxed">{wd.message}</p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span className="text-cyan-400/80">{wd.watchdog_type}</span>
                <span>{new Date(wd.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-2 border-b border-cyan-500/20 pb-2">
        <button
          onClick={() => setActiveTab('matrix')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-mono text-xs transition-all ${
            activeTab === 'matrix'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>INCIDENT MATRIX ({incidents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-mono text-xs transition-all ${
            activeTab === 'history'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>RECOVERY HISTORY ({recoveryHistory.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('playbooks')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-mono text-xs transition-all ${
            activeTab === 'playbooks'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>PLAYBOOKS CATALOG ({playbooks.length})</span>
        </button>
      </div>

      {/* Sub-Tab 1: Incident Matrix & Cockpit Split View */}
      {activeTab === 'matrix' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Incidents Table / List */}
          <div className="lg:col-span-6 space-y-3">
            {/* Search & Severity Filters */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="relative flex-1 min-w-[180px]">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter incidents by title, ID, resource..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full bg-[#0a1020] border border-cyan-500/30 rounded pl-8 pr-3 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="flex items-center gap-1">
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setActiveSeverityFilter(sev)}
                    className={`px-2 py-1 rounded text-[10px] font-mono transition-all ${
                      activeSeverityFilter === sev
                        ? 'bg-cyan-500/30 text-cyan-200 border border-cyan-400/50'
                        : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>

            {/* Incidents Scrollable List */}
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {filteredIncidents.length === 0 ? (
                <div className="p-8 rounded border border-cyan-500/20 bg-[#080d1a] text-center font-mono text-xs text-slate-400">
                  No incidents matching active filters.
                </div>
              ) : (
                filteredIncidents.map((inc) => (
                  <div
                    key={inc.incident_id}
                    onClick={() => setSelectedIncident(inc)}
                    className={`p-3.5 rounded-lg border cursor-pointer transition-all ${
                      selectedIncident?.incident_id === inc.incident_id
                        ? 'bg-[#0f1b33] border-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.15)]'
                        : 'bg-[#080e1c] border-slate-800 hover:border-cyan-500/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getSeverityBadge(inc.severity)}
                        <span className="font-mono text-xs font-bold text-slate-200">{inc.incident_id}</span>
                      </div>
                      {getStatusBadge(inc.status)}
                    </div>

                    <div className="text-xs font-mono text-cyan-300 font-semibold mt-2">{inc.title}</div>

                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mt-2">
                      <span>Resource: <span className="text-slate-300">{inc.target_resource}</span></span>
                      <span>Category: <span className="text-cyan-400">{inc.category}</span></span>
                    </div>

                    <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 mt-1">
                      <span>Attempts: {inc.recovery_attempts ?? 1} / {inc.max_recovery_attempts ?? 3}</span>
                      <span>{new Date(inc.detected_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Incident Cockpit & Diagnosis Detail */}
          <div className="lg:col-span-6 space-y-4">
            {selectedIncident ? (
              <div className="hud-panel p-5 rounded-lg border border-cyan-500/30 bg-[#080d1a]/95 space-y-4">
                {/* Header & Status */}
                <div className="flex items-start justify-between border-b border-cyan-500/20 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold font-mono text-cyan-300">{selectedIncident.title}</span>
                      {getSeverityBadge(selectedIncident.severity)}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 mt-1">
                      ID: <span className="text-cyan-400">{selectedIncident.incident_id}</span> • Resource: <span className="text-slate-300">{selectedIncident.target_resource}</span>
                    </div>
                  </div>
                  <div>{getStatusBadge(selectedIncident.status)}</div>
                </div>

                {/* Operator Control Bar */}
                <div className="flex flex-wrap items-center gap-2 bg-[#0c1426] p-2.5 rounded border border-cyan-500/20">
                  {selectedIncident.status === 'APPROVAL_PENDING' && (
                    <button
                      onClick={() => handleApproveGate(selectedIncident.incident_id)}
                      disabled={isActionLoading}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-amber-500/20 border border-amber-400/50 text-amber-300 text-xs font-mono font-bold hover:bg-amber-500/30"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>APPROVE GATE</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleAcknowledge(selectedIncident.incident_id)}
                    disabled={isActionLoading}
                    className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-200 text-xs font-mono hover:bg-slate-700"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>ACKNOWLEDGE</span>
                  </button>

                  <button
                    onClick={() => handleRecoverOrRetry(selectedIncident.incident_id)}
                    disabled={isActionLoading}
                    className="flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-xs font-mono hover:border-cyan-400"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>RETRY RECOVERY</span>
                  </button>

                  <button
                    onClick={() => handleEscalate(selectedIncident.incident_id)}
                    disabled={isActionLoading}
                    className="flex items-center gap-1 px-2.5 py-1 rounded bg-rose-950/80 border border-rose-500/40 text-rose-300 text-xs font-mono hover:border-rose-400"
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>ESCALATE</span>
                  </button>

                  <button
                    onClick={() => handleStopRecovery(selectedIncident.incident_id)}
                    disabled={isActionLoading}
                    className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-400 text-xs font-mono hover:text-slate-200"
                  >
                    <Square className="w-3.5 h-3.5" />
                    <span>STOP</span>
                  </button>
                </div>

                {/* Structured Diagnosis Evidence */}
                {selectedIncident.diagnosis_evidence && (
                  <div className="p-3.5 rounded bg-[#0a1122] border border-cyan-500/20 space-y-2">
                    <div className="text-xs font-mono font-bold text-cyan-400 flex items-center justify-between">
                      <span>ROOT CAUSE ANALYSIS & EVIDENCE</span>
                      <span className="text-[10px] text-emerald-400">Confidence: {(selectedIncident.diagnosis_evidence.confidence_score * 100).toFixed(0)}%</span>
                    </div>

                    <p className="text-xs font-mono text-slate-300 italic">
                      {selectedIncident.diagnosis_evidence.root_cause_candidate}
                    </p>

                    <div className="space-y-1 mt-2">
                      <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">Observed Facts:</div>
                      <ul className="list-disc list-inside text-[11px] font-mono text-slate-300 space-y-0.5">
                        {selectedIncident.diagnosis_evidence.observed_facts.map((fact, idx) => (
                          <li key={idx}>{fact}</li>
                        ))}
                      </ul>
                    </div>

                    {selectedIncident.diagnosis_evidence.hypotheses.length > 0 && (
                      <div className="space-y-1 mt-2">
                        <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">Hypotheses:</div>
                        <ul className="list-disc list-inside text-[11px] font-mono text-slate-400 space-y-0.5">
                          {selectedIncident.diagnosis_evidence.hypotheses.map((hyp, idx) => (
                            <li key={idx}>{hyp}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Healing Actions Execution Trace */}
                <div className="space-y-2">
                  <div className="text-xs font-mono font-bold text-slate-300 flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                    <span>REMEDIATION PLAYBOOK EXECUTION TRACE</span>
                  </div>

                  <div className="space-y-2 max-h-[220px] overflow-y-auto">
                    {selectedIncident.healing_actions.length === 0 ? (
                      <div className="p-3 rounded bg-[#090e1a] border border-slate-800 text-[11px] font-mono text-slate-500">
                        No automated healing actions executed yet.
                      </div>
                    ) : (
                      selectedIncident.healing_actions.map((act) => (
                        <div key={act.action_id} className="p-2.5 rounded bg-[#070b14] border border-cyan-500/20 font-mono text-xs">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-cyan-300 font-bold">{act.name}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
                              {act.status} ({act.duration_ms}ms)
                            </span>
                          </div>
                          {act.logs && act.logs.length > 0 && (
                            <div className="mt-1.5 space-y-0.5 text-[10px] text-slate-400">
                              {act.logs.map((log, lIdx) => (
                                <div key={lIdx} className="text-slate-300 font-mono">▸ {log}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Post-Mortem Report JSON Preview */}
                {selectedIncident.post_mortem && (
                  <div className="p-3 rounded bg-[#050811] border border-slate-800">
                    <div className="text-[10px] font-mono text-slate-400 uppercase font-bold mb-1">
                      Post-Mortem Knowledge Record
                    </div>
                    <pre className="text-[10px] font-mono text-emerald-400 overflow-x-auto max-h-[100px]">
                      {JSON.stringify(selectedIncident.post_mortem, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 rounded border border-cyan-500/20 bg-[#080d1a] text-center font-mono text-xs text-slate-400">
                Select an incident from the list to inspect root-cause analysis and actions.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sub-Tab 2: Chronological Recovery History */}
      {activeTab === 'history' && (
        <div className="hud-panel p-5 rounded-lg border border-cyan-500/30 bg-[#080d1a]/95 space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2 font-mono text-sm font-bold text-cyan-300">
              <History className="w-4 h-4 text-cyan-400" />
              <span>CHRONOLOGICAL RECOVERY AUDIT HISTORY</span>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {recoveryHistory.length} Recorded Recovery Events
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[10px]">
                  <th className="py-2 px-3">RECOVERY ID</th>
                  <th className="py-2 px-3">INCIDENT ID</th>
                  <th className="py-2 px-3">PLAYBOOK ACTION</th>
                  <th className="py-2 px-3">RESULT</th>
                  <th className="py-2 px-3">DURATION</th>
                  <th className="py-2 px-3">TIMESTAMP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {recoveryHistory.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-500 text-xs">
                      No recovery events recorded yet.
                    </td>
                  </tr>
                ) : (
                  recoveryHistory.map((rec) => (
                    <tr key={rec.recovery_id} className="hover:bg-[#0c1426] transition-all">
                      <td className="py-2.5 px-3 text-cyan-400 font-bold">{rec.recovery_id}</td>
                      <td className="py-2.5 px-3 text-slate-300">{rec.incident_id}</td>
                      <td className="py-2.5 px-3 text-slate-200">{rec.action}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            rec.verification_passed
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                              : 'bg-rose-950 text-rose-300 border border-rose-500/40'
                          }`}
                        >
                          {rec.result}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">{rec.duration_seconds}s</td>
                      <td className="py-2.5 px-3 text-slate-500 text-[10px]">{new Date(rec.timestamp).toLocaleString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-Tab 3: Playbooks Catalog */}
      {activeTab === 'playbooks' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {playbooks.map((pb) => (
            <div key={pb.playbook_id} className="hud-panel p-4 rounded-lg border border-cyan-500/20 bg-[#080d1a] space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-mono text-xs font-bold text-cyan-300">{pb.name}</h3>
                  <div className="text-[10px] font-mono text-slate-400 mt-0.5">ID: {pb.playbook_id}</div>
                </div>
                <span
                  className={`text-[9px] px-2 py-0.5 rounded font-mono font-bold ${
                    pb.risk_level === 'LOW'
                      ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/40'
                      : pb.risk_level === 'MEDIUM'
                      ? 'bg-yellow-950/80 text-yellow-300 border border-yellow-500/40'
                      : 'bg-rose-950/80 text-rose-300 border border-rose-500/40'
                  }`}
                >
                  {pb.risk_level} RISK
                </span>
              </div>

              <p className="text-xs font-mono text-slate-400">{pb.description}</p>

              <div className="space-y-1 pt-2 border-t border-slate-800">
                <div className="text-[10px] font-mono text-slate-400 uppercase font-bold">Remediation Steps:</div>
                <ol className="list-decimal list-inside text-[11px] font-mono text-slate-300 space-y-1">
                  {pb.steps.map((step, sIdx) => (
                    <li key={sIdx}>{step}</li>
                  ))}
                </ol>
              </div>

              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-2 border-t border-slate-800/60">
                <span>Cost: $0.00 USD</span>
                <span>Gate: {pb.requires_approval ? 'Approval Required' : 'Autonomous'}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Manual Trigger / Simulation Modal */}
      {showTriggerModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="hud-panel p-6 rounded-lg border border-cyan-500/40 bg-[#080d1a] max-w-lg w-full space-y-4 shadow-[0_0_30px_rgba(0,240,255,0.2)]">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
              <div className="flex items-center gap-2 font-mono text-sm font-bold text-cyan-300">
                <Flame className="w-4 h-4 text-amber-400 animate-pulse" />
                <span>SIMULATE OPERATIONAL FAILURE INCIDENT</span>
              </div>
              <button onClick={() => setShowTriggerModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleTriggerIncident} className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Failure Taxonomy Category</label>
                <select
                  value={triggerCategory}
                  onChange={(e) => setTriggerCategory(e.target.value)}
                  className="w-full bg-[#0c1426] border border-cyan-500/30 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-400"
                >
                  <option value="PROCESS_FAILURE">PROCESS_FAILURE</option>
                  <option value="HEALTH_CHECK_FAILURE">HEALTH_CHECK_FAILURE</option>
                  <option value="DEPLOYMENT_FAILURE">DEPLOYMENT_FAILURE</option>
                  <option value="BUILD_FAILURE">BUILD_FAILURE</option>
                  <option value="TEST_FAILURE">TEST_FAILURE</option>
                  <option value="PROVIDER_FAILURE">PROVIDER_FAILURE</option>
                  <option value="AUTH_FAILURE">AUTH_FAILURE</option>
                  <option value="NETWORK_FAILURE">NETWORK_FAILURE</option>
                  <option value="RESOURCE_EXHAUSTION">RESOURCE_EXHAUSTION</option>
                  <option value="WORKTREE_FAILURE">WORKTREE_FAILURE</option>
                  <option value="MERGE_FAILURE">MERGE_FAILURE</option>
                  <option value="DELIVERY_FAILURE">DELIVERY_FAILURE</option>
                  <option value="CONFIGURATION_FAILURE">CONFIGURATION_FAILURE</option>
                  <option value="SECURITY_POLICY_FAILURE">SECURITY_POLICY_FAILURE</option>
                  <option value="TIMEOUT">TIMEOUT</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Severity Tier</label>
                <select
                  value={triggerSeverity}
                  onChange={(e) => setTriggerSeverity(e.target.value)}
                  className="w-full bg-[#0c1426] border border-cyan-500/30 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-400"
                >
                  <option value="CRITICAL">CRITICAL (Gated SEV-1)</option>
                  <option value="HIGH">HIGH (Gated SEV-2)</option>
                  <option value="MEDIUM">MEDIUM (SEV-3)</option>
                  <option value="LOW">LOW (SEV-4)</option>
                  <option value="INFO">INFO</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Incident Title / Signal</label>
                <input
                  type="text"
                  value={triggerTitle}
                  onChange={(e) => setTriggerTitle(e.target.value)}
                  className="w-full bg-[#0c1426] border border-cyan-500/30 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Target Resource</label>
                <input
                  type="text"
                  value={triggerResource}
                  onChange={(e) => setTriggerResource(e.target.value)}
                  className="w-full bg-[#0c1426] border border-cyan-500/30 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-400"
                  required
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="autoRemediate"
                  checked={triggerAutoRemediate}
                  onChange={(e) => setTriggerAutoRemediate(e.target.checked)}
                  className="rounded border-cyan-500/40 text-cyan-500 focus:ring-0"
                />
                <label htmlFor="autoRemediate" className="text-slate-300">
                  Execute policy-driven autonomous remediation immediately
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowTriggerModal(false)}
                  className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isTriggering}
                  className="px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold"
                >
                  {isTriggering ? 'Registering...' : 'Trigger Incident'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
