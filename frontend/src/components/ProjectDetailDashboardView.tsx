import React, { useState, useEffect } from 'react';
import { 
  FolderGit2, 
  GitBranch, 
  GitCommit, 
  GitFork, 
  ShieldCheck, 
  ShieldAlert, 
  Play, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Terminal, 
  Zap, 
  Layers, 
  Activity, 
  ArrowLeft, 
  Sparkles,
  Server,
  FileCode,
  Clock,
  ExternalLink
} from 'lucide-react';
import { nexusFetch } from '../utils/api';
import { sound } from '../utils/audio';

export interface ProjectDashboardData {
  project_id: string;
  name: string;
  root_path: string;
  git_status: {
    is_git: boolean;
    current_branch: string;
    remote_url?: string;
    latest_commit_hash?: string;
    latest_commit_message?: string;
    dirty: boolean;
    untracked_files_count: number;
    modified_files_count: number;
    status_summary?: string;
  };
  health_score: number;
  archetype: string;
  missions: any[];
  deployments: any[];
  incidents: any[];
  security_findings: any[];
  recent_operations: any[];
}

interface ProjectDetailDashboardViewProps {
  projectId: string;
  onBack: () => void;
  onCreateMissionForProject?: (projectId: string, projectName: string) => void;
}

type TabType = 'overview' | 'missions' | 'operations' | 'security' | 'deployments';

export const ProjectDetailDashboardView: React.FC<ProjectDetailDashboardViewProps> = ({
  projectId,
  onBack,
  onCreateMissionForProject
}) => {
  const [data, setData] = useState<ProjectDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [actionOutput, setActionOutput] = useState<{ action: string; output: string; status: string } | null>(null);

  const fetchDashboard = async () => {
    try {
      const res = await nexusFetch<ProjectDashboardData>(`/api/v1/connector/projects/${projectId}/dashboard`);
      setData(res);
    } catch (err) {
      console.error('Failed to load project dashboard', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchDashboard();
  }, [projectId]);

  const handleExecuteAction = async (action: string, payload: any = {}) => {
    setActionInProgress(action);
    sound.click();
    try {
      const res = await nexusFetch<{
        status: string;
        action: string;
        output: string;
        health_score_delta?: number;
      }>(`/api/v1/connector/projects/${projectId}/action`, {
        method: 'POST',
        body: JSON.stringify({ action, payload })
      });

      setActionOutput({
        action,
        output: res.output || 'Action completed successfully.',
        status: res.status
      });

      if (res.status === 'COMPLETED' || res.status === 'SUCCESS') {
        sound.beep(1000, 0.1, 'sine');
      } else {
        sound.beep(440, 0.1, 'square');
      }

      // Refresh dashboard data
      await fetchDashboard();
    } catch (err: any) {
      setActionOutput({
        action,
        output: `Action Failed: ${err.message}`,
        status: 'FAILED'
      });
      sound.beep(300, 0.15, 'sawtooth');
    } finally {
      setActionInProgress(null);
    }
  };

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400 gap-3 font-mono">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
        <p className="text-xs uppercase tracking-widest text-cyan-300">
          Aggregating Real-Time Telemetry for {projectId}...
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 text-center text-rose-400 space-y-4 font-mono">
        <AlertTriangle className="w-12 h-12 mx-auto" />
        <h3 className="text-lg font-bold">PROJECT NOT FOUND</h3>
        <p className="text-xs text-slate-400">Could not retrieve dashboard for ID "{projectId}".</p>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs"
        >
          Return to Projects Matrix
        </button>
      </div>
    );
  }

  const git = data.git_status;
  const isHealthy = data.health_score >= 80;

  return (
    <div className="space-y-6 font-mono pb-12">
      {/* Top Navigation & Back Bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:border-cyan-400 text-slate-300 hover:text-cyan-300 text-xs font-semibold transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects Matrix
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              sound.click();
              fetchDashboard();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            Refresh Telemetry
          </button>
          {onCreateMissionForProject && (
            <button
              onClick={() => {
                sound.beep(880, 0.1, 'sine');
                onCreateMissionForProject(data.project_id, data.name);
              }}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs shadow-lg shadow-cyan-500/20 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              New Mission
            </button>
          )}
        </div>
      </div>

      {/* Hero Project Header Card */}
      <div className="p-6 rounded-xl bg-gradient-to-r from-[#090f1d] to-[#0d1627] border-2 border-cyan-500/40 shadow-[0_0_30px_rgba(0,240,255,0.15)] relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black text-white tracking-wide flex items-center gap-2.5">
                <FolderGit2 className="w-6 h-6 text-cyan-400" />
                {data.name}
              </h1>
              <span className="text-xs px-2.5 py-0.5 rounded-md bg-cyan-950/80 text-cyan-300 border border-cyan-700 uppercase font-semibold">
                {data.archetype || 'Project'}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                ID: {data.project_id}
              </span>
            </div>

            <p className="text-xs text-slate-400 font-mono flex items-center gap-2">
              <Server className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-cyan-200">{data.root_path}</span>
            </p>

            {git.remote_url && (
              <p className="text-xs text-slate-400 flex items-center gap-2">
                <GitFork className="w-3.5 h-3.5 text-slate-500" />
                <a 
                  href={git.remote_url} 
                  target="_blank" 
                  rel="noreferrer"
                  className="text-cyan-400 hover:underline flex items-center gap-1"
                >
                  {git.remote_url}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </p>
            )}
          </div>

          {/* Health & Status Score */}
          <div className="flex items-center gap-4 self-start md:self-auto bg-black/40 p-4 rounded-xl border border-slate-800">
            <div className="text-right">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Health Metric</div>
              <div className={`text-2xl font-black ${isHealthy ? 'text-emerald-400' : 'text-amber-400'}`}>
                {data.health_score}%
              </div>
            </div>
            <div className={`w-12 h-12 rounded-full border-4 flex items-center justify-center ${
              isHealthy ? 'border-emerald-500 text-emerald-400 bg-emerald-950/20' : 'border-amber-500 text-amber-400 bg-amber-950/20'
            }`}>
              {isHealthy ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
            </div>
          </div>
        </div>

        {/* Quick Git Pill Bar */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
            <GitBranch className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Branch:</span>
            <span className="font-bold text-cyan-300">{git.current_branch || 'main'}</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
            <GitCommit className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-slate-400">Latest:</span>
            <span className="font-mono text-purple-300 truncate max-w-xs" title={git.latest_commit_message}>
              {git.latest_commit_hash ? git.latest_commit_hash.slice(0, 7) : 'HEAD'} - {git.latest_commit_message || 'Initial'}
            </span>
          </div>

          <div className={`flex items-center gap-1.5 px-3 py-1 rounded border text-xs font-semibold ${
            git.dirty 
              ? 'bg-amber-950/50 border-amber-800 text-amber-300' 
              : 'bg-emerald-950/50 border-emerald-800 text-emerald-300'
          }`}>
            <Activity className="w-3.5 h-3.5" />
            <span>{git.dirty ? `Dirty Tree (${git.modified_files_count} mod, ${git.untracked_files_count} untracked)` : 'Working Tree Clean'}</span>
          </div>
        </div>
      </div>

      {/* Governed Action Execution Bar */}
      <div className="p-4 rounded-xl bg-slate-950/90 border border-cyan-500/30 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold text-cyan-300 uppercase tracking-wider">
            <Zap className="w-4 h-4 text-cyan-400" />
            Direct Governed Operations Control
          </div>
          {actionInProgress && (
            <span className="text-xs text-amber-400 flex items-center gap-1 animate-pulse">
              <RefreshCw className="w-3 h-3 animate-spin" /> EXECUTING {actionInProgress}...
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
          <button
            onClick={() => handleExecuteAction('AUDIT')}
            disabled={!!actionInProgress}
            className="p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-cyan-400 text-xs font-bold text-slate-200 hover:text-cyan-300 flex flex-col items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <Activity className="w-4 h-4 text-cyan-400" />
            Audit
          </button>

          <button
            onClick={() => handleExecuteAction('TEST')}
            disabled={!!actionInProgress}
            className="p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-emerald-400 text-xs font-bold text-slate-200 hover:text-emerald-300 flex flex-col items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Run Tests
          </button>

          <button
            onClick={() => handleExecuteAction('SECURITY_SCAN')}
            disabled={!!actionInProgress}
            className="p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-rose-400 text-xs font-bold text-slate-200 hover:text-rose-300 flex flex-col items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4 text-rose-400" />
            Security Scan
          </button>

          <button
            onClick={() => handleExecuteAction('RECONCILE_DRIFT')}
            disabled={!!actionInProgress}
            className="p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-amber-400 text-xs font-bold text-slate-200 hover:text-amber-300 flex flex-col items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4 text-amber-400" />
            Reconcile Drift
          </button>

          <button
            onClick={() => handleExecuteAction('DEPLOY')}
            disabled={!!actionInProgress}
            className="p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-cyan-400 text-xs font-bold text-slate-200 hover:text-cyan-300 flex flex-col items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <Play className="w-4 h-4 text-cyan-400" />
            Deploy Gate
          </button>

          <button
            onClick={() => {
              if (onCreateMissionForProject) {
                onCreateMissionForProject(data.project_id, data.name);
              }
            }}
            className="p-2.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/80 border border-cyan-500/50 text-xs font-bold text-cyan-300 flex flex-col items-center gap-1.5 transition-all"
          >
            <Sparkles className="w-4 h-4 text-cyan-400" />
            Launch Mission
          </button>
        </div>

        {/* Action Output Console */}
        {actionOutput && (
          <div className="mt-3 p-3 rounded-lg bg-black border border-slate-800 space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-cyan-400 font-bold flex items-center gap-1">
                <Terminal className="w-3 h-3" /> ACTION RESULT: [{actionOutput.action}]
              </span>
              <span className={`font-bold ${actionOutput.status === 'COMPLETED' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {actionOutput.status}
              </span>
            </div>
            <pre className="text-[11px] text-slate-300 font-mono whitespace-pre-wrap max-h-36 overflow-y-auto bg-slate-950/70 p-2 rounded border border-slate-900">
              {actionOutput.output}
            </pre>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-cyan-500/20 bg-[#060a14] rounded-t-xl px-4 pt-2 gap-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'overview'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          Overview & Workspace
        </button>

        <button
          onClick={() => setActiveTab('missions')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'missions'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Missions ({data.missions?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('operations')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'operations'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          Operations Log ({data.recent_operations?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('security')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'security'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          Security & Findings ({data.security_findings?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('deployments')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'deployments'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Server className="w-4 h-4" />
          Deployments ({data.deployments?.length || 0})
        </button>
      </div>

      {/* Tab Panels */}
      <div className="p-6 rounded-b-xl bg-[#090f1d] border-x border-b border-cyan-500/20 min-h-[300px]">
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-2">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                  <FileCode className="w-4 h-4" /> Archetype & Stack
                </h4>
                <div className="text-xs text-slate-300 space-y-1">
                  <div><span className="text-slate-500">Architecture: </span>{data.archetype || 'Full Stack Application'}</div>
                  <div><span className="text-slate-500">Root Directory: </span><code className="text-cyan-300">{data.root_path}</code></div>
                  <div><span className="text-slate-500">Git Initialized: </span>{git.is_git ? 'Yes (Live Repository)' : 'No'}</div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 space-y-2">
                <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
                  <GitBranch className="w-4 h-4" /> Working Tree State
                </h4>
                <div className="text-xs text-slate-300 space-y-1">
                  <div><span className="text-slate-500">Active Branch: </span><span className="text-cyan-300 font-bold">{git.current_branch}</span></div>
                  <div><span className="text-slate-500">Modified Files: </span>{git.modified_files_count}</div>
                  <div><span className="text-slate-500">Untracked Files: </span>{git.untracked_files_count}</div>
                </div>
              </div>
            </div>

            {/* Git Status Output */}
            {git.status_summary && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-cyan-400" /> Git Status Delta
                </h4>
                <pre className="p-3 rounded-lg bg-black border border-slate-800 text-[11px] text-slate-300 font-mono overflow-x-auto">
                  {git.status_summary}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: MISSIONS */}
        {activeTab === 'missions' && (
          <div className="space-y-4">
            {(!data.missions || data.missions.length === 0) ? (
              <div className="py-12 text-center text-slate-400 space-y-3">
                <Sparkles className="w-10 h-10 text-slate-600 mx-auto" />
                <p className="text-xs">No autonomous missions created for this project yet.</p>
                {onCreateMissionForProject && (
                  <button
                    onClick={() => onCreateMissionForProject(data.project_id, data.name)}
                    className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded text-xs"
                  >
                    Launch First Mission
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {data.missions.map((mission: any, idx: number) => (
                  <div 
                    key={mission.mission_id || idx}
                    className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-cyan-300">
                          {mission.title || mission.mission_id}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                          mission.status === 'COMPLETED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-cyan-950 text-cyan-400 border border-cyan-800'
                        }`}>
                          {mission.status || 'PENDING'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">{mission.description || 'Autonomous Engineering Directive'}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: OPERATIONS */}
        {activeTab === 'operations' && (
          <div className="space-y-3">
            {(!data.recent_operations || data.recent_operations.length === 0) ? (
              <div className="py-12 text-center text-slate-400">
                <Activity className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                <p className="text-xs">No recent operations logged for this project.</p>
              </div>
            ) : (
              data.recent_operations.map((op: any, idx: number) => (
                <div 
                  key={idx} 
                  className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <Clock className="w-4 h-4 text-slate-500" />
                    <div>
                      <span className="font-bold text-cyan-300">{op.action || 'OPERATION'}</span>
                      <span className="text-slate-400 ml-2">{op.summary || op.details}</span>
                    </div>
                  </div>
                  <span className="text-slate-500 text-[10px]">{op.timestamp || 'Recent'}</span>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 4: SECURITY */}
        {activeTab === 'security' && (
          <div className="space-y-3">
            {(!data.security_findings || data.security_findings.length === 0) ? (
              <div className="p-6 text-center text-emerald-400 space-y-2 bg-emerald-950/10 border border-emerald-900/30 rounded-lg">
                <ShieldCheck className="w-10 h-10 mx-auto" />
                <p className="text-xs font-bold uppercase tracking-wider">Zero Security Vulnerabilities Detected</p>
                <p className="text-[11px] text-slate-400">Codebase meets strict Sentinel-X compliance standards.</p>
              </div>
            ) : (
              data.security_findings.map((f: any, idx: number) => (
                <div key={idx} className="p-3 rounded-lg bg-rose-950/30 border border-rose-900/50 flex items-center gap-3 text-xs text-rose-300">
                  <ShieldAlert className="w-4 h-4 text-rose-400 flex-shrink-0" />
                  <span>{f.message || f.title || JSON.stringify(f)}</span>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB 5: DEPLOYMENTS */}
        {activeTab === 'deployments' && (
          <div className="space-y-3">
            {(!data.deployments || data.deployments.length === 0) ? (
              <div className="py-12 text-center text-slate-400">
                <Server className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                <p className="text-xs">No active deployment records found.</p>
              </div>
            ) : (
              data.deployments.map((d: any, idx: number) => (
                <div key={idx} className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="font-bold text-white">{d.target || 'Production'}</span>
                    <span className="text-slate-400">({d.deployment_id || 'ID'})</span>
                  </div>
                  {d.url && (
                    <a href={d.url} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline flex items-center gap-1">
                      {d.url} <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};
