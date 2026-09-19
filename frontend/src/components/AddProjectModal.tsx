import React, { useState, useEffect } from 'react';
import { 
  FolderPlus, 
  FolderGit2, 
  GitFork, 
  Search, 
  AlertTriangle, 
  RefreshCw, 
  X,
  Layers,
  GitBranch,
  Terminal,
  ShieldCheck,
  Check
} from 'lucide-react';
import { nexusFetch } from '../utils/api';
import { sound } from '../utils/audio';

interface DiscoveredProject {
  project_id: string;
  name: string;
  root_path: string;
  git_remote_url?: string;
  git_branch?: string;
  archetype?: string;
  is_git: boolean;
  already_registered: boolean;
}

interface AddProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectAdded?: (projectId: string) => void;
}

type TabMode = 'discover' | 'local' | 'github';

export const AddProjectModal: React.FC<AddProjectModalProps> = ({
  isOpen,
  onClose,
  onProjectAdded
}) => {
  const [activeTab, setActiveTab] = useState<TabMode>('discover');
  
  // Discover Tab State
  const [discovering, setDiscovering] = useState<boolean>(false);
  const [discoveredProjects, setDiscoveredProjects] = useState<DiscoveredProject[]>([]);
  const [scannedRoots, setScannedRoots] = useState<string[]>([]);
  const [syncingAll, setSyncingAll] = useState<boolean>(false);
  const [registeringId, setRegisteringId] = useState<string | null>(null);

  // Manual Local Form State
  const [localPath, setLocalPath] = useState<string>('');
  const [projectName, setProjectName] = useState<string>('');
  const [localBranch, setLocalBranch] = useState<string>('main');
  const [localSubmitting, setLocalSubmitting] = useState<boolean>(false);
  const [localError, setLocalError] = useState<string | null>(null);

  // GitHub Form State
  const [githubUrl, setGithubUrl] = useState<string>('');
  const [githubTargetDir, setGithubTargetDir] = useState<string>('');
  const [githubBranch, setGithubBranch] = useState<string>('main');
  const [githubSubmitting, setGithubSubmitting] = useState<boolean>(false);
  const [githubError, setGithubError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setLocalError(null);
      setGithubError(null);
      if (activeTab === 'discover') {
        handleRunDiscovery();
      }
    }
  }, [isOpen]);

  const handleRunDiscovery = async () => {
    setDiscovering(true);
    sound.click();
    try {
      const res = await nexusFetch<{
        scanned_roots: string[];
        discovered: DiscoveredProject[];
        total_discovered: number;
      }>('/api/v1/connector/discover');
      
      setDiscoveredProjects(res.discovered || []);
      setScannedRoots(res.scanned_roots || []);
      sound.beep(800, 0.08, 'sine');
    } catch (err: any) {
      console.error('Discovery failed', err);
    } finally {
      setDiscovering(false);
    }
  };

  const handleOnboardDiscovered = async (proj: DiscoveredProject) => {
    setRegisteringId(proj.project_id);
    sound.click();
    try {
      const res = await nexusFetch('/api/v1/connector/onboard', {
        method: 'POST',
        body: JSON.stringify({
          name: proj.name,
          root_path: proj.root_path,
          git_branch: proj.git_branch || 'main',
          git_remote_url: proj.git_remote_url
        })
      });
      sound.beep(1000, 0.1, 'sine');
      // Update local state
      setDiscoveredProjects(prev =>
        prev.map(p => p.project_id === proj.project_id ? { ...p, already_registered: true } : p)
      );
      if (onProjectAdded) {
        onProjectAdded(res.project_id || proj.project_id);
      }
    } catch (err: any) {
      alert(`Failed to onboard project: ${err.message}`);
    } finally {
      setRegisteringId(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    sound.click();
    try {
      await nexusFetch<{ added_count: number; updated_count: number }>(
        '/api/v1/connector/sync-all',
        { method: 'POST', body: JSON.stringify({ auto_register: true }) }
      );
      sound.beep(1200, 0.15, 'sine');
      await handleRunDiscovery();
      if (onProjectAdded) {
        onProjectAdded('all');
      }
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncingAll(false);
    }
  };

  const handleLocalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localPath.trim()) {
      setLocalError('Please provide a valid workspace root path.');
      return;
    }
    setLocalSubmitting(true);
    setLocalError(null);
    sound.click();
    try {
      const res = await nexusFetch('/api/v1/connector/onboard', {
        method: 'POST',
        body: JSON.stringify({
          name: projectName.trim() || undefined,
          root_path: localPath.trim(),
          git_branch: localBranch.trim() || 'main'
        })
      });
      sound.beep(1000, 0.1, 'sine');
      if (onProjectAdded) {
        onProjectAdded(res.project_id);
      }
      onClose();
    } catch (err: any) {
      setLocalError(err.message || 'Failed to onboard local project');
    } finally {
      setLocalSubmitting(false);
    }
  };

  const handleGithubSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!githubUrl.trim()) {
      setGithubError('Please provide a valid GitHub repository URL.');
      return;
    }
    setGithubSubmitting(true);
    setGithubError(null);
    sound.click();
    try {
      // Derive repo name from URL if name not given
      const urlParts = githubUrl.trim().replace(/\.git$/, '').split('/');
      const repoName = urlParts[urlParts.length - 1] || 'github-repo';
      const targetPath = githubTargetDir.trim() || `/root/projects/${repoName}`;

      const res = await nexusFetch('/api/v1/connector/onboard', {
        method: 'POST',
        body: JSON.stringify({
          name: projectName.trim() || repoName,
          root_path: targetPath,
          git_remote_url: githubUrl.trim(),
          git_branch: githubBranch.trim() || 'main'
        })
      });
      sound.beep(1000, 0.1, 'sine');
      if (onProjectAdded) {
        onProjectAdded(res.project_id);
      }
      onClose();
    } catch (err: any) {
      setGithubError(err.message || 'Failed to register GitHub project');
    } finally {
      setGithubSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const unregisteredCount = discoveredProjects.filter(p => !p.already_registered).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md font-mono">
      <div 
        className="w-full max-w-3xl bg-[#090f1d] border-2 border-cyan-500/80 rounded-xl shadow-[0_0_50px_rgba(0,240,255,0.3)] overflow-hidden animate-in fade-in zoom-in duration-200 flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/30 bg-[#060a14]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <FolderPlus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wider flex items-center gap-2">
                ONBOARD PROJECT TO NEXUS
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                  REGISTRY & CONTROL MATRIX
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Discover local repositories automatically or register arbitrary paths / GitHub remotes.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-cyan-500/20 bg-[#050812] px-6 pt-3 gap-2">
          <button
            onClick={() => {
              setActiveTab('discover');
              handleRunDiscovery();
            }}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'discover'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Search className="w-4 h-4" />
            Auto-Discover Workspaces
            {unregisteredCount > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-cyan-500 text-slate-950 font-extrabold">
                {unregisteredCount} new
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('local')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'local'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FolderGit2 className="w-4 h-4" />
            Local Workspace Path
          </button>

          <button
            onClick={() => setActiveTab('github')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'github'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10 rounded-t'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitFork className="w-4 h-4" />
            GitHub Repository
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {/* TAB 1: AUTO-DISCOVER */}
          {activeTab === 'discover' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                <div className="text-xs text-slate-300">
                  <span className="text-cyan-400 font-semibold">Active Scanners: </span>
                  {scannedRoots.join(', ') || '/root, Termux Home'}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRunDiscovery}
                    disabled={discovering}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs flex items-center gap-1.5 transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${discovering ? 'animate-spin' : ''}`} />
                    Rescan
                  </button>
                  {unregisteredCount > 0 && (
                    <button
                      onClick={handleSyncAll}
                      disabled={syncingAll}
                      className="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded text-xs flex items-center gap-1.5 transition-colors shadow-md"
                    >
                      <Layers className="w-3.5 h-3.5" />
                      {syncingAll ? 'Registering...' : `Add All (${unregisteredCount})`}
                    </button>
                  )}
                </div>
              </div>

              {discovering ? (
                <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-3">
                  <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                  <p className="text-xs tracking-wider uppercase text-cyan-300">
                    Scanning workspace roots for Git repositories & projects...
                  </p>
                </div>
              ) : discoveredProjects.length === 0 ? (
                <div className="py-12 text-center text-slate-400 space-y-2">
                  <FolderGit2 className="w-10 h-10 text-slate-600 mx-auto" />
                  <p className="text-sm">No Git repositories discovered in scanned roots.</p>
                  <p className="text-xs text-slate-500">
                    Use the "Local Workspace Path" tab to register a project directory manually.
                  </p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {discoveredProjects.map((proj) => (
                    <div
                      key={proj.project_id}
                      className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-cyan-500/50 transition-all flex items-center justify-between gap-4"
                    >
                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-cyan-300 truncate">
                            {proj.name}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300 uppercase">
                            {proj.archetype || 'Project'}
                          </span>
                          {proj.git_branch && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 flex items-center gap-1">
                              <GitBranch className="w-3 h-3" />
                              {proj.git_branch}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 truncate font-mono">
                          {proj.root_path}
                        </p>
                        {proj.git_remote_url && (
                          <p className="text-[11px] text-slate-500 truncate flex items-center gap-1">
                            <GitFork className="w-3 h-3" />
                            {proj.git_remote_url}
                          </p>
                        )}
                      </div>

                      <div>
                        {proj.already_registered ? (
                          <span className="px-3 py-1.5 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-400 text-xs font-semibold flex items-center gap-1">
                            <Check className="w-3.5 h-3.5" /> Registered
                          </span>
                        ) : (
                          <button
                            onClick={() => handleOnboardDiscovered(proj)}
                            disabled={registeringId === proj.project_id}
                            className="px-3.5 py-1.5 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/60 text-cyan-300 rounded text-xs font-bold flex items-center gap-1.5 transition-all"
                          >
                            {registeringId === proj.project_id ? (
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <FolderPlus className="w-3.5 h-3.5" />
                            )}
                            Add to NEXUS
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: LOCAL WORKSPACE PATH */}
          {activeTab === 'local' && (
            <form onSubmit={handleLocalSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-cyan-300 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                  WORKSPACE ROOT DIRECTORY PATH *
                </label>
                <input
                  type="text"
                  required
                  value={localPath}
                  onChange={(e) => setLocalPath(e.target.value)}
                  placeholder="e.g. /root/control-center or /root/portfolio"
                  className="w-full bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
                />
                <p className="text-[11px] text-slate-500">
                  NEXUS will automatically inspect Git remote, branch, commit history, and stack archetype.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    PROJECT DISPLAY NAME (OPTIONAL)
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="e.g. Control Center"
                    className="w-full bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    DEFAULT GIT BRANCH
                  </label>
                  <input
                    type="text"
                    value={localBranch}
                    onChange={(e) => setLocalBranch(e.target.value)}
                    placeholder="main"
                    className="w-full bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {localError && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>{localError}</span>
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={localSubmitting}
                  className="px-5 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg text-xs flex items-center gap-2 transition-all shadow-lg shadow-cyan-500/20"
                >
                  {localSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Inspecting & Registering...
                    </>
                  ) : (
                    <>
                      <FolderPlus className="w-4 h-4" />
                      Register Project
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: GITHUB REPO */}
          {activeTab === 'github' && (
            <form onSubmit={handleGithubSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-cyan-300 flex items-center gap-1.5">
                  <GitFork className="w-3.5 h-3.5 text-cyan-400" />
                  GITHUB REPOSITORY URL *
                </label>
                <input
                  type="text"
                  required
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="e.g. https://github.com/knightriderisback/my-project"
                  className="w-full bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    TARGET LOCAL PATH
                  </label>
                  <input
                    type="text"
                    value={githubTargetDir}
                    onChange={(e) => setGithubTargetDir(e.target.value)}
                    placeholder="Defaults to /root/projects/<repo-name>"
                    className="w-full bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    DEFAULT BRANCH
                  </label>
                  <input
                    type="text"
                    value={githubBranch}
                    onChange={(e) => setGithubBranch(e.target.value)}
                    placeholder="main"
                    className="w-full bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {githubError && (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>{githubError}</span>
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={githubSubmitting}
                  className="px-5 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg text-xs flex items-center gap-2 transition-all shadow-lg shadow-cyan-500/20"
                >
                  {githubSubmitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Registering Remote Repo...
                    </>
                  ) : (
                    <>
                      <FolderPlus className="w-4 h-4" />
                      Connect GitHub Repository
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-cyan-500/20 bg-[#060a14] flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span>Multi-project isolation and strict governance active</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
