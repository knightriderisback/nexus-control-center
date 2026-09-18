import React, { useState, useEffect } from 'react';
import type {
  DeploymentRecord,
  DeploymentRequest,
  DORAMetrics,
  EnvironmentStatus,
  DeploymentStage,
} from '../types';
import {
  Rocket,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Activity,
  Terminal,
  RefreshCw,
  ExternalLink,
  TrendingUp,
  Layers,
  Globe,
  ArrowUpRight
} from 'lucide-react';

export const ProductionDeploymentMatrixView: React.FC = () => {
  const [deployments, setDeployments] = useState<DeploymentRecord[]>([]);
  const [environments, setEnvironments] = useState<EnvironmentStatus[]>([]);
  const [dora, setDora] = useState<DORAMetrics | null>(null);
  const [selectedDeployment, setSelectedDeployment] = useState<DeploymentRecord | null>(null);
  const [selectedStage, setSelectedStage] = useState<DeploymentStage | null>(null);
  const [activeFilterEnv, setActiveFilterEnv] = useState<string>('ALL');
  const [showDeployModal, setShowDeployModal] = useState<boolean>(false);
  const [isDeploying, setIsDeploying] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // New Deployment Form State
  const [newDeployProject, setNewDeployProject] = useState<string>('control-center');
  const [newDeployService, setNewDeployService] = useState<string>('nexus-core');
  const [newDeployEnv, setNewDeployEnv] = useState<'LOCAL' | 'PREVIEW' | 'STAGING' | 'PRODUCTION'>('LOCAL');
  const [newDeployTarget, setNewDeployTarget] = useState<'LOCAL_PROCESS' | 'STATIC_BUNDLE' | 'VERCEL_EDGE' | 'GCP_CLOUD_RUN' | 'TERMUX_NODE'>('LOCAL_PROCESS');
  const [newDeployStrategy, setNewDeployStrategy] = useState<'DIRECT_REPLACE' | 'CANARY' | 'BLUE_GREEN' | 'ROLLING'>('DIRECT_REPLACE');
  const [newDeployCanaryPct, setNewDeployCanaryPct] = useState<number>(100);
  const [newDeployVersion, setNewDeployVersion] = useState<string>('');

  const fetchData = async () => {
    try {
      const [depRes, envRes, doraRes] = await Promise.all([
        fetch('/api/v1/deployments'),
        fetch('/api/v1/deployments/environments'),
        fetch('/api/v1/deployments/dora'),
      ]);

      if (depRes.ok) {
        const depData: DeploymentRecord[] = await depRes.json();
        setDeployments(depData);
        if (!selectedDeployment && depData.length > 0) {
          setSelectedDeployment(depData[0]);
          if (depData[0].stages.length > 0) {
            setSelectedStage(depData[0].stages[0]);
          }
        } else if (selectedDeployment) {
          const updated = depData.find((d) => d.deployment_id === selectedDeployment.deployment_id);
          if (updated) setSelectedDeployment(updated);
        }
      }

      if (envRes.ok) {
        const envData: EnvironmentStatus[] = await envRes.json();
        setEnvironments(envData);
      }

      if (doraRes.ok) {
        const doraData: DORAMetrics = await doraRes.json();
        setDora(doraData);
      }
    } catch (err) {
      console.error('Error fetching deployment telemetry:', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleTriggerDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsDeploying(true);
    setFeedbackMsg(null);

    const payload: DeploymentRequest = {
      project_id: newDeployProject,
      service_name: newDeployService,
      version: newDeployVersion.trim() || undefined,
      environment: newDeployEnv,
      target_type: newDeployTarget,
      strategy: newDeployStrategy,
      canary_percentage: newDeployStrategy === 'CANARY' ? newDeployCanaryPct : 100,
      auto_rollback_on_failure: true,
      created_by: 'cyber-hud-operator',
      notes: `Triggered from Cyber-HUD matrix (${newDeployEnv})`,
    };

    try {
      const res = await fetch('/api/v1/deployments/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const newRecord: DeploymentRecord = await res.json();
        setFeedbackMsg({ text: `Deployment ${newRecord.deployment_id} launched successfully!`, type: 'success' });
        setShowDeployModal(false);
        fetchData();
        setSelectedDeployment(newRecord);
        if (newRecord.stages.length > 0) {
          setSelectedStage(newRecord.stages[0]);
        }
      } else {
        const err = await res.json();
        setFeedbackMsg({ text: err.detail || 'Deployment failed to launch.', type: 'error' });
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message || 'Network error.', type: 'error' });
    } finally {
      setIsDeploying(false);
    }
  };

  const handleRollback = async (deploymentId: string) => {
    if (!confirm(`Trigger instant atomic rollback for deployment ${deploymentId}?`)) return;
    try {
      const res = await fetch(`/api/v1/deployments/${deploymentId}/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deployment_id: deploymentId, reason: 'Operator manual rollback from Cyber-HUD' }),
      });
      if (res.ok) {
        setFeedbackMsg({ text: `Deployment ${deploymentId} rolled back successfully!`, type: 'success' });
        fetchData();
      } else {
        const err = await res.json();
        setFeedbackMsg({ text: err.detail || 'Rollback failed.', type: 'error' });
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message || 'Rollback error.', type: 'error' });
    }
  };

  const handlePromoteCanary = async (deploymentId: string, pct: number) => {
    try {
      const res = await fetch(`/api/v1/deployments/${deploymentId}/promote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deployment_id: deploymentId, target_percentage: pct }),
      });
      if (res.ok) {
        setFeedbackMsg({ text: `Canary traffic promoted to ${pct}%!`, type: 'success' });
        fetchData();
      } else {
        const err = await res.json();
        setFeedbackMsg({ text: err.detail || 'Promotion failed.', type: 'error' });
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message || 'Promotion error.', type: 'error' });
    }
  };

  const handleApprove = async (deploymentId: string) => {
    try {
      const res = await fetch(`/api/v1/deployments/${deploymentId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        setFeedbackMsg({ text: `Deployment ${deploymentId} approved & resumed!`, type: 'success' });
        fetchData();
      } else {
        const err = await res.json();
        setFeedbackMsg({ text: err.detail || 'Approval failed.', type: 'error' });
      }
    } catch (err: any) {
      setFeedbackMsg({ text: err.message || 'Approval error.', type: 'error' });
    }
  };

  const filteredDeployments = deployments.filter((d) => {
    if (activeFilterEnv === 'ALL') return true;
    return d.environment === activeFilterEnv;
  });

  const getEnvBadgeColor = (env: string) => {
    switch (env) {
      case 'PRODUCTION':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'STAGING':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'PREVIEW':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'LIVE':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'BUILDING':
      case 'DEPLOYING':
      case 'VERIFYING':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30 animate-pulse';
      case 'APPROVAL_PENDING':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse';
      case 'ROLLED_BACK':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-red-500/10 text-red-400 border-red-500/30';
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Top Banner & Quick Trigger */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 p-5 rounded-2xl border border-cyan-500/20 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Rocket className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2 tracking-wide font-mono">
                PRODUCTION DEPLOYMENT ENGINE
                <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  PHASE 16
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Multi-Target Orchestration • Zero-Downtime Rollouts • Synthetic Health Probes • Instant Rollback
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 text-xs font-mono flex items-center gap-1.5 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            SYNC
          </button>
          <button
            onClick={() => setShowDeployModal(true)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs font-mono flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all cursor-pointer"
          >
            <Rocket className="w-4 h-4" />
            LAUNCH DEPLOYMENT
          </button>
        </div>
      </div>

      {feedbackMsg && (
        <div
          className={`p-3.5 rounded-xl border text-xs font-mono flex items-center justify-between ${
            feedbackMsg.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} className="text-slate-400 hover:text-slate-200">
            ×
          </button>
        </div>
      )}

      {/* DORA Operational Metrics */}
      {dora && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-mono">DEPLOY FREQUENCY</span>
              <Activity className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-cyan-400">
              {dora.deployment_frequency_per_week} <span className="text-xs font-normal text-slate-400">/ week</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Total {dora.total_deployments} recorded</div>
          </div>

          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-blue-500/40 transition-all">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-mono">LEAD TIME FOR CHANGES</span>
              <Clock className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-blue-400">
              {dora.lead_time_for_changes_minutes} <span className="text-xs font-normal text-slate-400">min</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Commit to Live verification</div>
          </div>

          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-amber-500/40 transition-all">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-mono">CHANGE FAILURE RATE</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-amber-400">
              {dora.change_failure_rate_percent}%
            </div>
            <div className="text-[11px] text-slate-400 mt-1">{dora.failed_deployments + dora.rollbacks_count} failed / rolled back</div>
          </div>

          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-mono">TIME TO RECOVER (MTTR)</span>
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-400">
              {dora.mean_time_to_recovery_minutes} <span className="text-xs font-normal text-slate-400">min</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Instant atomic rollback ready</div>
          </div>
        </div>
      )}

      {/* Environments Matrix */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold font-mono text-slate-300 flex items-center gap-2">
            <Globe className="w-4 h-4 text-cyan-400" />
            ENVIRONMENT TOPOLOGY
          </h2>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            ALL SYSTEMS ACTIVE
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {environments.map((env) => (
            <div
              key={env.environment_name}
              className="bg-slate-900/50 p-4 rounded-xl border border-slate-800 hover:border-cyan-500/30 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${getEnvBadgeColor(env.environment_name)}`}>
                    {env.environment_name}
                  </span>
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    {env.health_status}
                  </div>
                </div>

                <div className="space-y-1.5 mt-3 text-xs font-mono">
                  <div className="text-slate-300 flex items-center justify-between">
                    <span className="text-slate-500">Release:</span>
                    <span className="text-cyan-400 font-semibold">{env.active_version || 'None'}</span>
                  </div>
                  <div className="text-slate-300 flex items-center justify-between">
                    <span className="text-slate-500">Target:</span>
                    <span className="text-slate-300">{env.target_type || 'N/A'}</span>
                  </div>
                  <div className="text-slate-300 flex items-center justify-between">
                    <span className="text-slate-500">Commit:</span>
                    <span className="text-slate-400">{env.active_commit?.slice(0, 7) || 'HEAD'}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                {env.url ? (
                  <a
                    href={env.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1 truncate max-w-[180px]"
                  >
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                    {env.url.replace(/^https?:\/\//, '')}
                  </a>
                ) : (
                  <span className="text-[11px] font-mono text-slate-500">Local Only</span>
                )}
                <span className="text-[10px] font-mono text-slate-500">100% Traffic</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Deployment Pipeline & Stage Inspector */}
      {selectedDeployment && (
        <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-3">
                <span className="text-lg font-bold font-mono text-slate-100">
                  {selectedDeployment.service_name}
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  {selectedDeployment.version}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${getStatusBadgeColor(selectedDeployment.status)}`}>
                  {selectedDeployment.status}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs font-mono border ${getEnvBadgeColor(selectedDeployment.environment)}`}>
                  {selectedDeployment.environment}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-1">
                ID: {selectedDeployment.deployment_id} • Strategy: {selectedDeployment.strategy} • Target: {selectedDeployment.target_type} • Lead Time: {selectedDeployment.duration_seconds}s
              </p>
            </div>

            <div className="flex items-center gap-2">
              {selectedDeployment.status === 'APPROVAL_PENDING' && (
                <button
                  onClick={() => handleApprove(selectedDeployment.deployment_id)}
                  className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs font-mono flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <ShieldCheck className="w-4 h-4" />
                  APPROVE PROD DEPLOY
                </button>
              )}

              {selectedDeployment.strategy === 'CANARY' && selectedDeployment.canary_percentage < 100 && (
                <button
                  onClick={() => handlePromoteCanary(selectedDeployment.deployment_id, 100)}
                  className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-slate-100 text-xs font-mono flex items-center gap-1.5 transition-all"
                >
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  PROMOTE TO 100%
                </button>
              )}

              <button
                onClick={() => handleRollback(selectedDeployment.deployment_id)}
                className="px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-mono flex items-center gap-1.5 transition-all"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                ROLLBACK
              </button>
            </div>
          </div>

          {/* Pipeline Stage DAG */}
          <div>
            <div className="text-xs font-mono text-slate-400 mb-2">PIPELINE EXECUTION DAG</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
              {selectedDeployment.stages.map((stg, idx) => {
                const isSelected = selectedStage?.stage_name === stg.stage_name;
                return (
                  <button
                    key={stg.stage_name}
                    onClick={() => setSelectedStage(stg)}
                    className={`p-3 rounded-xl border text-left font-mono transition-all ${
                      isSelected
                        ? 'bg-cyan-500/10 border-cyan-400 text-cyan-300'
                        : stg.status === 'SUCCESS'
                        ? 'bg-slate-900/40 border-emerald-500/30 text-emerald-400 hover:border-emerald-500/60'
                        : stg.status === 'FAILED'
                        ? 'bg-red-500/10 border-red-500/40 text-red-400'
                        : stg.status === 'RUNNING'
                        ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400 animate-pulse'
                        : 'bg-slate-900/30 border-slate-800 text-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] opacity-70">0{idx + 1}</span>
                      {stg.status === 'SUCCESS' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : stg.status === 'FAILED' ? (
                        <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                      ) : (
                        <Clock className="w-3.5 h-3.5 opacity-60" />
                      )}
                    </div>
                    <div className="text-xs font-bold truncate">{stg.stage_name}</div>
                    <div className="text-[10px] opacity-60 mt-1">{stg.duration_ms}ms</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Stage Detail & Terminal Logs */}
          {selectedStage && (
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs space-y-2">
              <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-slate-800">
                <span className="text-cyan-400 font-bold flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5" />
                  STAGE LOGS: {selectedStage.stage_name}
                </span>
                <span>
                  Status: <strong className="text-slate-200">{selectedStage.status}</strong> • Duration:{' '}
                  {selectedStage.duration_ms}ms
                </span>
              </div>

              <div className="space-y-1 max-h-48 overflow-y-auto text-slate-300 pt-1">
                {selectedStage.logs.length > 0 ? (
                  selectedStage.logs.map((log, i) => (
                    <div key={i} className="flex gap-2">
                      <span className="text-slate-600 select-none">›</span>
                      <span className={log.startsWith('[FAIL]') || log.startsWith('[ERROR]') ? 'text-red-400' : log.startsWith('[PASS]') ? 'text-emerald-400' : 'text-slate-300'}>
                        {log}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-600">No logs generated for this stage.</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Deployment History Table */}
      <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="text-sm font-bold font-mono text-slate-300 flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            DEPLOYMENT HISTORY & RELEASES
          </h2>

          <div className="flex items-center gap-2 overflow-x-auto">
            {['ALL', 'PRODUCTION', 'STAGING', 'PREVIEW', 'LOCAL'].map((env) => (
              <button
                key={env}
                onClick={() => setActiveFilterEnv(env)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                  activeFilterEnv === env
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-slate-700/60'
                }`}
              >
                {env}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500 pb-2">
                <th className="pb-2">RELEASE</th>
                <th className="pb-2">SERVICE</th>
                <th className="pb-2">ENV</th>
                <th className="pb-2">TARGET</th>
                <th className="pb-2">STATUS</th>
                <th className="pb-2">DURATION</th>
                <th className="pb-2">TIMESTAMP</th>
                <th className="pb-2 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredDeployments.length > 0 ? (
                filteredDeployments.map((dep) => (
                  <tr
                    key={dep.deployment_id}
                    onClick={() => {
                      setSelectedDeployment(dep);
                      if (dep.stages.length > 0) setSelectedStage(dep.stages[0]);
                    }}
                    className={`hover:bg-slate-800/40 transition-colors cursor-pointer ${
                      selectedDeployment?.deployment_id === dep.deployment_id ? 'bg-cyan-500/5' : ''
                    }`}
                  >
                    <td className="py-3 font-semibold text-cyan-400 flex items-center gap-1.5">
                      <Rocket className="w-3.5 h-3.5 text-slate-500" />
                      {dep.version}
                    </td>
                    <td className="py-3 text-slate-300">{dep.service_name}</td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getEnvBadgeColor(dep.environment)}`}>
                        {dep.environment}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400">{dep.target_type}</td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusBadgeColor(dep.status)}`}>
                        {dep.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400">{dep.duration_seconds}s</td>
                    <td className="py-3 text-slate-500">{new Date(dep.created_at).toLocaleTimeString()}</td>
                    <td className="py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRollback(dep.deployment_id);
                        }}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-slate-700 hover:border-red-500/30 text-[11px] transition-all"
                      >
                        Rollback
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 font-mono">
                    No deployment records found for environment '{activeFilterEnv}'.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Launch Deployment Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-cyan-500/30 w-full max-w-xl rounded-2xl p-6 space-y-5 shadow-2xl font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-cyan-400 font-bold">
                <Rocket className="w-5 h-5" />
                <span>LAUNCH PRODUCTION DEPLOYMENT PIPELINE</span>
              </div>
              <button onClick={() => setShowDeployModal(false)} className="text-slate-400 hover:text-slate-200">
                ×
              </button>
            </div>

            <form onSubmit={handleTriggerDeploy} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 mb-1">PROJECT ID</label>
                  <input
                    type="text"
                    value={newDeployProject}
                    onChange={(e) => setNewDeployProject(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:border-cyan-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">SERVICE NAME</label>
                  <input
                    type="text"
                    value={newDeployService}
                    onChange={(e) => setNewDeployService(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:border-cyan-500 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 mb-1">TARGET ENVIRONMENT</label>
                  <select
                    value={newDeployEnv}
                    onChange={(e) => setNewDeployEnv(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:border-cyan-500 outline-none"
                  >
                    <option value="LOCAL">LOCAL (Port 8000)</option>
                    <option value="PREVIEW">PREVIEW (Vercel Preview)</option>
                    <option value="STAGING">STAGING (Cloud Run Staging)</option>
                    <option value="PRODUCTION">PRODUCTION (Production Cloud Run / Vercel)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">TARGET DISPATCHER</label>
                  <select
                    value={newDeployTarget}
                    onChange={(e) => setNewDeployTarget(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:border-cyan-500 outline-none"
                  >
                    <option value="LOCAL_PROCESS">LOCAL_PROCESS (Host Service)</option>
                    <option value="STATIC_BUNDLE">STATIC_BUNDLE (Vite SPA)</option>
                    <option value="VERCEL_EDGE">VERCEL_EDGE (Edge Serverless)</option>
                    <option value="GCP_CLOUD_RUN">GCP_CLOUD_RUN (Keyless Container)</option>
                    <option value="TERMUX_NODE">TERMUX_NODE (Mobile Edge)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-400 mb-1">DEPLOYMENT STRATEGY</label>
                  <select
                    value={newDeployStrategy}
                    onChange={(e) => setNewDeployStrategy(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:border-cyan-500 outline-none"
                  >
                    <option value="DIRECT_REPLACE">DIRECT_REPLACE (Instant Switch)</option>
                    <option value="CANARY">CANARY (Traffic Split)</option>
                    <option value="BLUE_GREEN">BLUE_GREEN (Zero-Downtime Swap)</option>
                    <option value="ROLLING">ROLLING (Gradual Update)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">CUSTOM VERSION TAG (Optional)</label>
                  <input
                    type="text"
                    value={newDeployVersion}
                    placeholder="e.g. v2.4.0"
                    onChange={(e) => setNewDeployVersion(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:border-cyan-500 outline-none"
                  />
                </div>
              </div>

              {newDeployStrategy === 'CANARY' && (
                <div>
                  <label className="block text-slate-400 mb-1">
                    CANARY TRAFFIC ALLOCATION: <span className="text-cyan-400 font-bold">{newDeployCanaryPct}%</span>
                  </label>
                  <input
                    type="range"
                    min={5}
                    max={95}
                    step={5}
                    value={newDeployCanaryPct}
                    onChange={(e) => setNewDeployCanaryPct(Number(e.target.value))}
                    className="w-full accent-cyan-500"
                  />
                </div>
              )}

              <div className="p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/20 text-slate-400 text-[11px] space-y-1">
                <div className="text-cyan-400 font-semibold flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  GOVERNANCE & FINOPS CONTROLS
                </div>
                <div>• Automatic zero-cost FinOps policy check active ($0.00 guaranteed).</div>
                <div>• Synthetic SLA health probe verifies uptime before traffic promotion.</div>
                <div>• Instant auto-rollback triggers automatically if health probe fails.</div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowDeployModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-400 hover:text-slate-200 font-mono"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={isDeploying}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold font-mono shadow-lg shadow-cyan-500/20 transition-all flex items-center gap-1.5"
                >
                  {isDeploying ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      DEPLOYING...
                    </>
                  ) : (
                    <>
                      <Rocket className="w-4 h-4" />
                      EXECUTE DEPLOYMENT
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
