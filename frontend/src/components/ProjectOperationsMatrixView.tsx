import React, { useState, useEffect } from 'react';
import {
  Server,
  Activity,
  GitCommit,
  RotateCcw,
  CheckCircle,
  Archive,
  RefreshCw,
  Zap,
  TrendingUp,
  Sliders
} from 'lucide-react';
import type {
  FleetOverviewItem,
  ProjectOperationsRecordItem
} from '../types';
import { nexusFetch } from '../utils/api';

export const ProjectOperationsMatrixView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'fleet' | 'releases' | 'drifts' | 'sla' | 'maintenance'>('fleet');
  const [fleetOverview, setFleetOverview] = useState<FleetOverviewItem | null>(null);
  const [projects, setProjects] = useState<ProjectOperationsRecordItem[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectOperationsRecordItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Form states
  const [versionBump, setVersionBump] = useState<'patch' | 'minor' | 'major'>('patch');
  const [releaseStrategy, setReleaseStrategy] = useState<'CANARY' | 'BLUE_GREEN' | 'DIRECT_ROLLOUT'>('CANARY');
  const [maintTaskType, setMaintTaskType] = useState<string>('DEPENDENCY_SCAN');

  const fetchFleetData = async () => {
    setLoading(true);
    try {
      const [fData, pData] = await Promise.all([
        nexusFetch<FleetOverviewItem>('/api/v1/project-operations/fleet'),
        nexusFetch<ProjectOperationsRecordItem[]>('/api/v1/project-operations/projects')
      ]);

      if (fData) setFleetOverview(fData);
      if (pData) {
        setProjects(pData);
        if (pData.length > 0 && !selectedProject) {
          setSelectedProject(pData[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch fleet data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFleetData();
    const interval = setInterval(fetchFleetData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleCreateRelease = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      await nexusFetch('/api/v1/project-operations/releases', {
        method: 'POST',
        body: JSON.stringify({
          project_id: selectedProject.project_id,
          version_bump: versionBump,
          strategy: releaseStrategy,
          changelog_summary: `Manual release triggered via Cyber-HUD`
        })
      });
      setActionMessage(`Release initiated successfully for ${selectedProject.project_name}`);
      fetchFleetData();
    } catch (err: any) {
      console.error(err);
      setActionMessage(`Release error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePromoteRelease = async (releaseId: string) => {
    setLoading(true);
    try {
      await nexusFetch('/api/v1/project-operations/releases/promote', {
        method: 'POST',
        body: JSON.stringify({ release_id: releaseId })
      });
      setActionMessage(`Release ${releaseId} promoted to next stage`);
      fetchFleetData();
    } catch (err: any) {
      console.error(err);
      setActionMessage(`Promote error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRollbackRelease = async (projectId: string) => {
    setLoading(true);
    try {
      await nexusFetch('/api/v1/project-operations/releases/rollback', {
        method: 'POST',
        body: JSON.stringify({
          project_id: projectId,
          reason: 'Manual operator rollback from Cyber-HUD'
        })
      });
      setActionMessage(`Rollback executed cleanly for ${projectId}`);
      fetchFleetData();
    } catch (err: any) {
      console.error(err);
      setActionMessage(`Rollback error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReconcileDrift = async (driftId: string) => {
    setLoading(true);
    try {
      await nexusFetch('/api/v1/project-operations/drift/reconcile', {
        method: 'POST',
        body: JSON.stringify({ drift_id: driftId })
      });
      setActionMessage(`Drift ${driftId} reconciled autonomously`);
      fetchFleetData();
    } catch (err: any) {
      console.error(err);
      setActionMessage(`Reconcile error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleMaintenance = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const task = await nexusFetch<{ task_id: string }>('/api/v1/project-operations/maintenance/schedule', {
        method: 'POST',
        body: JSON.stringify({
          project_id: selectedProject.project_id,
          task_type: maintTaskType
        })
      });
      // Immediately execute task
      await nexusFetch('/api/v1/project-operations/maintenance/execute', {
        method: 'POST',
        body: JSON.stringify({ task_id: task.task_id })
      });
      setActionMessage(`Maintenance task ${maintTaskType} completed.`);
      fetchFleetData();
    } catch (err: any) {
      console.error(err);
      setActionMessage(`Maintenance error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleArchiveProject = async (projectId: string) => {
    if (!confirm(`Are you sure you want to archive project ${projectId} into tombstone vault?`)) return;
    setLoading(true);
    try {
      await nexusFetch(`/api/v1/project-operations/projects/${projectId}/archive`, {
        method: 'POST',
        body: JSON.stringify({ project_id: projectId })
      });
      setActionMessage(`Project ${projectId} archived into tombstone vault`);
      fetchFleetData();
    } catch (err: any) {
      console.error(err);
      setActionMessage(`Archive error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 font-mono">
      {/* Top Banner HUD */}
      <div className="border-b border-cyan-900/40 bg-slate-900/70 p-4 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-cyan-950 border border-cyan-500/50 rounded-lg text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
              <Server className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-wider text-cyan-300 uppercase flex items-center gap-2">
                NEXUS PHASE 22 // Project Operations & Lifecycle Control
                <span className="px-2 py-0.5 text-xs rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 font-mono">
                  $0.00 ZERO-COST
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Fleet Governance • Canary Rollouts • SLA Watchdogs • Drift Auto-Reconcile • Tombstone Vault
              </p>
            </div>
          </div>

          {/* Quick Fleet Stats */}
          {fleetOverview && (
            <div className="flex items-center space-x-6 text-xs bg-slate-950/80 px-4 py-2 rounded-lg border border-slate-800">
              <div>
                <span className="text-slate-500 block">FLEET TOTAL</span>
                <span className="text-cyan-400 font-bold">{fleetOverview.total_projects} Projects</span>
              </div>
              <div>
                <span className="text-slate-500 block">FLEET HEALTH</span>
                <span className="text-emerald-400 font-bold">{fleetOverview.fleet_health_score}%</span>
              </div>
              <div>
                <span className="text-slate-500 block">SLA COMPLIANCE</span>
                <span className="text-blue-400 font-bold">{fleetOverview.overall_sla_compliance_pct}%</span>
              </div>
              <div>
                <span className="text-slate-500 block">ACTIVE DRIFTS</span>
                <span className={`font-bold ${fleetOverview.unresolved_drifts > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                  {fleetOverview.unresolved_drifts} Unresolved
                </span>
              </div>
              <button
                onClick={fetchFleetData}
                disabled={loading}
                className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-cyan-300 transition-colors"
                title="Refresh Fleet"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
              </button>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-2 mt-4 border-t border-slate-800/80 pt-3">
          {[
            { id: 'fleet', label: 'Fleet Radar & Lifecycle', icon: Server },
            { id: 'releases', label: 'Release & Canary Governor', icon: GitCommit },
            { id: 'drifts', label: 'Drift & Compliance Radar', icon: Sliders },
            { id: 'sla', label: 'SLA & Error Budget', icon: Activity },
            { id: 'maintenance', label: 'Maintenance & Vault', icon: Archive }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {actionMessage && (
        <div className="bg-cyan-950/60 border-b border-cyan-800 px-4 py-2 text-xs text-cyan-300 flex justify-between items-center">
          <span>✓ {actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Main View Area */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* TAB 1: FLEET RADAR & LIFECYCLE */}
        {activeTab === 'fleet' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Project List */}
            <div className="md:col-span-1 bg-slate-900/60 border border-slate-800 rounded-lg p-3 space-y-2">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Managed Fleet Inventory</span>
                <span className="text-cyan-400 font-mono">{projects.length}</span>
              </h2>
              <div className="space-y-2 overflow-y-auto max-h-[600px]">
                {projects.map((proj) => {
                  const isSelected = selectedProject?.project_id === proj.project_id;
                  return (
                    <div
                      key={proj.project_id}
                      onClick={() => setSelectedProject(proj)}
                      className={`p-3 rounded border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-cyan-950/40 border-cyan-500/60 shadow-[0_0_10px_rgba(6,182,212,0.15)]'
                          : 'bg-slate-950/50 border-slate-800/80 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="font-bold text-sm text-slate-200">{proj.project_name}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded border ${
                            proj.lifecycle_state === 'ACTIVE'
                              ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/30'
                              : proj.lifecycle_state === 'UPGRADING'
                              ? 'bg-cyan-950/80 text-cyan-400 border-cyan-500/30'
                              : proj.lifecycle_state === 'DEGRADED'
                              ? 'bg-rose-950/80 text-rose-400 border-rose-500/30'
                              : 'bg-slate-900 text-slate-400 border-slate-700'
                          }`}
                        >
                          {proj.lifecycle_state}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1 flex justify-between">
                        <span>v{proj.current_version}</span>
                        <span className="text-emerald-400 font-semibold">{proj.health_score}% Health</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selected Project Lifecycle Details */}
            <div className="md:col-span-2 bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-4">
              {selectedProject ? (
                <>
                  <div className="flex justify-between items-start border-b border-slate-800 pb-3">
                    <div>
                      <h2 className="text-base font-bold text-cyan-300">{selectedProject.project_name}</h2>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">{selectedProject.project_path}</p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleArchiveProject(selectedProject.project_id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-rose-950/60 text-slate-300 hover:text-rose-300 text-xs rounded border border-slate-700 hover:border-rose-700/50 flex items-center space-x-1"
                      >
                        <Archive className="w-3.5 h-3.5" />
                        <span>Archive</span>
                      </button>
                    </div>
                  </div>

                  {/* Operational Metrics Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-slate-950/80 border border-slate-800 p-3 rounded">
                      <span className="text-[10px] text-slate-500 uppercase block">Current Version</span>
                      <span className="text-base font-bold text-cyan-400 font-mono">v{selectedProject.current_version}</span>
                    </div>
                    <div className="bg-slate-950/80 border border-slate-800 p-3 rounded">
                      <span className="text-[10px] text-slate-500 uppercase block">Observed Uptime</span>
                      <span className="text-base font-bold text-emerald-400 font-mono">{selectedProject.sla.observed_uptime_pct}%</span>
                    </div>
                    <div className="bg-slate-950/80 border border-slate-800 p-3 rounded">
                      <span className="text-[10px] text-slate-500 uppercase block">p95 Latency</span>
                      <span className="text-base font-bold text-blue-400 font-mono">{selectedProject.sla.observed_p95_latency_ms}ms</span>
                    </div>
                    <div className="bg-slate-950/80 border border-slate-800 p-3 rounded">
                      <span className="text-[10px] text-slate-500 uppercase block">FinOps Cost</span>
                      <span className="text-base font-bold text-emerald-400 font-mono">$0.00</span>
                    </div>
                  </div>

                  {/* Active Releases & Drift Snapshot */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-slate-950/50 border border-slate-800 p-3 rounded space-y-2">
                      <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Release Status</h3>
                      {selectedProject.releases.length > 0 ? (
                        <div className="space-y-1.5 text-xs">
                          {selectedProject.releases.slice(-3).map((r) => (
                            <div key={r.release_id} className="p-2 bg-slate-900/80 rounded border border-slate-800 flex justify-between items-center">
                              <div>
                                <span className="font-bold text-slate-200">v{r.version}</span>
                                <span className="text-[10px] text-slate-500 ml-2">({r.strategy})</span>
                              </div>
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-950 text-cyan-400 border border-cyan-800">
                                {r.state} ({r.traffic_weight_pct}%)
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No active release candidates</p>
                      )}
                    </div>

                    <div className="bg-slate-950/50 border border-slate-800 p-3 rounded space-y-2">
                      <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Active Drifts</h3>
                      {selectedProject.active_drifts.filter(d => !d.remediated).length > 0 ? (
                        <div className="space-y-1.5 text-xs">
                          {selectedProject.active_drifts.filter(d => !d.remediated).map((d) => (
                            <div key={d.drift_id} className="p-2 bg-slate-900/80 rounded border border-amber-900/40 flex justify-between items-center">
                              <span className="text-amber-300">{d.drift_type}</span>
                              <button
                                onClick={() => handleReconcileDrift(d.drift_id)}
                                className="px-2 py-0.5 bg-amber-950 hover:bg-amber-900 text-amber-300 text-[10px] rounded border border-amber-700/50"
                              >
                                Reconcile
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex items-center space-x-2 text-xs text-emerald-400 p-2">
                          <CheckCircle className="w-4 h-4" />
                          <span>Zero configuration or dependency drift</span>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="p-8 text-center text-slate-500 text-xs">Select a project to inspect operations.</div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: RELEASE & CANARY GOVERNOR */}
        {activeTab === 'releases' && selectedProject && (
          <div className="space-y-4">
            {/* New Release Trigger */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
              <h2 className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-2">
                <GitCommit className="w-4 h-4" />
                <span>Initiate Autonomous Release // {selectedProject.project_name}</span>
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] text-slate-400 block mb-1">VERSION BUMP</label>
                  <select
                    value={versionBump}
                    onChange={(e) => setVersionBump(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200"
                  >
                    <option value="patch">Patch (Bugfix / Security)</option>
                    <option value="minor">Minor (New Features)</option>
                    <option value="major">Major (Breaking API)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 block mb-1">DEPLOYMENT STRATEGY</label>
                  <select
                    value={releaseStrategy}
                    onChange={(e) => setReleaseStrategy(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200"
                  >
                    <option value="CANARY">Canary Rollout (10% → 50% → 100%)</option>
                    <option value="BLUE_GREEN">Blue/Green Standby</option>
                    <option value="DIRECT_ROLLOUT">Direct Local Deployment</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleCreateRelease}
                    disabled={loading}
                    className="w-full bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/50 p-2 rounded text-xs font-bold flex items-center justify-center space-x-2 transition-all"
                  >
                    <Zap className="w-4 h-4" />
                    <span>Deploy Release</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Active Releases List */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
              <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Release Candidates & History</h2>
              <div className="space-y-2">
                {selectedProject.releases.map((rel) => (
                  <div key={rel.release_id} className="p-3 bg-slate-950/80 border border-slate-800 rounded flex flex-wrap justify-between items-center gap-3">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-sm text-cyan-300">v{rel.version}</span>
                        <span className="text-xs text-slate-400">({rel.commit_hash.slice(0, 8)})</span>
                        <span className="px-2 py-0.5 text-[10px] rounded bg-slate-900 border border-slate-700 text-slate-300 font-mono">
                          {rel.strategy}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        State: <span className="text-slate-300">{rel.state}</span> | Traffic: <span className="text-cyan-400 font-bold">{rel.traffic_weight_pct}%</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {rel.state !== 'STABLE' && rel.state !== 'ROLLED_BACK' && (
                        <button
                          onClick={() => handlePromoteRelease(rel.release_id)}
                          className="px-3 py-1 bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/50 rounded text-xs flex items-center space-x-1"
                        >
                          <TrendingUp className="w-3.5 h-3.5" />
                          <span>Promote Canary</span>
                        </button>
                      )}
                      <button
                        onClick={() => handleRollbackRelease(selectedProject.project_id)}
                        className="px-3 py-1 bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-700/50 rounded text-xs flex items-center space-x-1"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Rollback</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: DRIFT & COMPLIANCE RADAR */}
        {activeTab === 'drifts' && selectedProject && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Live Workspace & Configuration Drift Radar</h2>
                <p className="text-xs text-slate-500">Autonomous reconciliation of config, dependency, and workspace discrepancies</p>
              </div>
            </div>

            <div className="space-y-3">
              {selectedProject.active_drifts.length > 0 ? (
                selectedProject.active_drifts.map((d) => (
                  <div key={d.drift_id} className="p-3 bg-slate-950/80 border border-slate-800 rounded space-y-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="font-bold text-sm text-amber-400">{d.drift_type}</span>
                        <span className="text-xs text-slate-500 ml-2">Severity: {d.severity}</span>
                      </div>
                      <span className={`text-[10px] px-2 py-0.5 rounded border ${d.remediated ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 'bg-amber-950 text-amber-400 border-amber-800'}`}>
                        {d.remediated ? 'REMEDIATED' : 'ACTIVE DRIFT'}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 bg-slate-900 p-2 rounded font-mono">
                      Diff: {d.diff}
                    </div>
                    {!d.remediated && (
                      <button
                        onClick={() => handleReconcileDrift(d.drift_id)}
                        className="px-3 py-1 bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-700/50 rounded text-xs"
                      >
                        Autonomously Reconcile
                      </button>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-emerald-400 text-xs border border-emerald-900/30 rounded bg-emerald-950/20">
                  <CheckCircle className="w-6 h-6 mx-auto mb-2 text-emerald-400" />
                  <span>All configurations and dependencies match specification baseline.</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: SLA & ERROR BUDGET */}
        {activeTab === 'sla' && selectedProject && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-4">
            <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">SLA, Latency & Error Budget Governor</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-slate-950/80 border border-slate-800 p-4 rounded text-center">
                <span className="text-xs text-slate-500 block mb-1">ERROR BUDGET REMAINING</span>
                <span className="text-2xl font-bold text-emerald-400 font-mono">{selectedProject.sla.error_budget_remaining_pct}%</span>
              </div>
              <div className="bg-slate-950/80 border border-slate-800 p-4 rounded text-center">
                <span className="text-xs text-slate-500 block mb-1">BURN RATE</span>
                <span className="text-2xl font-bold text-cyan-400 font-mono">{selectedProject.sla.burn_rate}x</span>
              </div>
              <div className="bg-slate-950/80 border border-slate-800 p-4 rounded text-center">
                <span className="text-xs text-slate-500 block mb-1">SLA COMPLIANCE STATUS</span>
                <span className={`text-2xl font-bold font-mono ${selectedProject.sla.sla_status === 'COMPLIANT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {selectedProject.sla.sla_status}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: MAINTENANCE & VAULT */}
        {activeTab === 'maintenance' && selectedProject && (
          <div className="space-y-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
              <h2 className="text-xs font-bold text-cyan-300 uppercase tracking-wider">Execute Autonomous Maintenance</h2>
              <div className="flex space-x-3">
                <select
                  value={maintTaskType}
                  onChange={(e) => setMaintTaskType(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200"
                >
                  <option value="DEPENDENCY_SCAN">Dependency Audit & Scan</option>
                  <option value="LOG_ROTATE">Log Buffer Rotation</option>
                  <option value="BACKUP">Git Snapshot Backup</option>
                  <option value="CLEANUP">Cache & Build Artifact Purge</option>
                </select>
                <button
                  onClick={handleScheduleMaintenance}
                  className="px-4 py-2 bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/50 rounded text-xs font-bold"
                >
                  Run Maintenance Task
                </button>
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 space-y-3">
              <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Maintenance History</h2>
              <div className="space-y-2">
                {selectedProject.maintenance_history.map((t) => (
                  <div key={t.task_id} className="p-3 bg-slate-950/80 border border-slate-800 rounded flex justify-between items-center text-xs">
                    <div>
                      <span className="font-bold text-slate-200">{t.task_type}</span>
                      <p className="text-slate-500 text-[10px]">{t.result_summary || 'Pending'}</p>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      {t.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
