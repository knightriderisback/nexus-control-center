import React, { useState } from 'react';
import { 
  FolderGit2, 
  Play, 
  Terminal, 
  GitBranch, 
  GitCommit, 
  FileCode, 
  Zap, 
  CheckCircle2, 
  RotateCcw,
  Sparkles
} from 'lucide-react';
import { sound } from '../utils/audio';

interface WorkspaceProject {
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

interface WorkspaceMissionControlProps {
  projects: WorkspaceProject[];
  onRunMacro: (macroId: string) => Promise<any>;
}

export const WorkspaceMissionControl: React.FC<WorkspaceMissionControlProps> = ({
  projects,
  onRunMacro
}) => {
  const [activeMacro, setActiveMacro] = useState<string | null>(null);
  const [macroOutput, setMacroOutput] = useState<string>(
    '# NEXUS Tactical Macro Console Ready\n# Select an operational macro below to execute live on the host system.'
  );
  const [isRunning, setIsRunning] = useState<boolean>(false);

  const macros = [
    {
      id: 'git:status',
      name: 'Git Status & Delta Audit',
      desc: 'Inspect modified files and commit tree in /root/portfolio',
      icon: <GitBranch className="w-4 h-4 text-cyan-400" />
    },
    {
      id: 'system:diagnostics',
      name: 'Full Hardware Diagnostics',
      desc: 'Probe CPU core balance, memory footprint & port availability',
      icon: <Zap className="w-4 h-4 text-amber-400" />
    },
    {
      id: 'network:scan-ports',
      name: 'Local Port & Socket Scan',
      desc: 'Detect listening TCP sockets across common development ports',
      icon: <Terminal className="w-4 h-4 text-emerald-400" />
    },
    {
      id: 'memory:purge-cache',
      name: 'Memory Garbage Collection',
      desc: 'Execute Python cyclic garbage collector and free memory blocks',
      icon: <RotateCcw className="w-4 h-4 text-purple-400" />
    }
  ];

  const handleExecuteMacro = async (macroId: string) => {
    sound.beep(700, 0.1, 'sine');
    setActiveMacro(macroId);
    setIsRunning(true);
    setMacroOutput(`[EXEC] Running macro: ${macroId}...\nWaiting for host kernel response...`);

    try {
      const res = await onRunMacro(macroId);
      sound.success();
      const outputText = typeof res.output === 'object' 
        ? JSON.stringify(res.output, null, 2) 
        : res.output || JSON.stringify(res, null, 2);

      setMacroOutput(`[SUCCESS] Macro ${macroId} executed successfully:\n\n${outputText}`);
    } catch (err: any) {
      sound.alert();
      setMacroOutput(`[ERROR] Macro ${macroId} failed:\n${err.message || String(err)}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Workspace Repositories Overview */}
      <div className="hud-panel p-5 rounded-lg space-y-4">
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <FolderGit2 className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold text-cyan-300 tracking-wider">
              WORKSPACE MISSION CONTROL & REPOSITORY MATRIX
            </span>
          </div>
          <span className="text-[10px] text-slate-400">
            ROOT: /root
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((proj, idx) => (
            <div
              key={idx}
              className="p-4 rounded-lg bg-[#070b16] border border-cyan-500/20 hover:border-cyan-500/40 transition-all space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-cyan-400" />
                    <span>{proj.name}</span>
                  </div>
                  <div className="text-[10px] text-slate-400">{proj.path}</div>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                  {proj.type}
                </span>
              </div>

              {proj.git && proj.git.has_repo ? (
                <div className="pt-2 border-t border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center gap-1.5 text-[11px] text-slate-400">
                      <GitBranch className="w-3.5 h-3.5 text-cyan-400" /> Branch
                    </span>
                    <span className="text-cyan-300 font-bold">{proj.git.branch}</span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center gap-1.5 text-[11px] text-slate-400">
                      <GitCommit className="w-3.5 h-3.5 text-emerald-400" /> Last Commit
                    </span>
                    <span className="text-slate-300 truncate max-w-[220px] text-[10px]">
                      {proj.git.last_commit || 'Initial commit'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="flex items-center gap-1.5 text-[11px] text-slate-400">
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Modified Diffs
                    </span>
                    <span className="text-amber-300 font-bold">
                      {proj.git.modified_files_count || 0} files
                    </span>
                  </div>
                </div>
              ) : (
                <div className="pt-2 border-t border-slate-800 text-[11px] text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Direct Workspace Mounted
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Split: Macro Actions Launcher & Terminal Output */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Macros List (5 cols) */}
        <div className="lg:col-span-5 hud-panel p-5 rounded-lg space-y-3">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-bold text-amber-300 tracking-wider">
                OPERATIONAL MACROS
              </span>
            </div>
            {activeMacro && (
              <span className="text-[10px] text-cyan-400">LAST: {activeMacro}</span>
            )}
          </div>

          <div className="space-y-2">
            {macros.map((m) => (
              <div
                key={m.id}
                className="p-3 rounded bg-[#070c18] border border-cyan-500/20 hover:border-cyan-400 transition-all flex items-center justify-between group"
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 mt-0.5">
                    {m.icon}
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors">
                      {m.name}
                    </div>
                    <div className="text-[10px] text-slate-400 leading-tight mt-0.5">
                      {m.desc}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleExecuteMacro(m.id)}
                  disabled={isRunning}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-cyan-500/20 border border-cyan-400/50 text-cyan-300 hover:bg-cyan-500/30 hover:shadow-[0_0_10px_rgba(0,240,255,0.3)] transition-all text-xs font-bold disabled:opacity-40"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>RUN</span>
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Tactical Terminal Console (7 cols) */}
        <div className="lg:col-span-7 hud-panel p-5 rounded-lg space-y-3">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-cyan-300 tracking-wider">
                TACTICAL SHELL & EXECUTION CONSOLE
              </span>
            </div>
            {isRunning && (
              <span className="text-[10px] text-amber-400 animate-pulse">
                STREAMING OUTPUT...
              </span>
            )}
          </div>

          <div className="bg-[#04060c] p-3.5 rounded border border-slate-900 h-64 overflow-y-auto text-xs font-mono text-cyan-300/90 whitespace-pre-wrap leading-relaxed shadow-inner">
            {macroOutput}
          </div>
        </div>
      </div>
    </div>
  );
};
