import React, { useState, useEffect } from 'react';
import { 
  Terminal, 
  Bot, 
  Cpu, 
  FolderGit2, 
  ShieldAlert, 
  Tv, 
  Volume2, 
  Zap,
  ArrowRight
} from 'lucide-react';
import { sound } from '../utils/audio';
import type { TabType } from './HeaderHUD';

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  setActiveTab: (tab: TabType) => void;
  onRunMacro: (macroId: string) => Promise<any>;
  onTriggerPanic: () => void;
  toggleScanlines: () => void;
  toggleAudio: () => void;
  onQuickDispatch: (agentId: string, title: string) => Promise<void>;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  isOpen,
  onClose,
  setActiveTab,
  onRunMacro,
  onTriggerPanic,
  toggleScanlines,
  toggleAudio,
  onQuickDispatch
}) => {
  const [query, setQuery] = useState<string>('');
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  const commandList = [
    {
      id: 'tab-hud',
      label: 'Switch View: Cyber-HUD Live Operations Control Plane',
      category: 'Navigation',
      icon: <Terminal className="w-4 h-4 text-cyan-400" />,
      action: () => setActiveTab('hud')
    },
    {
      id: 'tab-missions',
      label: 'Switch View: Autonomous Mission Control & DAG Planner (Phase 13)',
      category: 'Navigation',
      icon: <Terminal className="w-4 h-4 text-emerald-400" />,
      action: () => setActiveTab('missions')
    },
    {
      id: 'tab-swarm',
      label: 'Switch View: Agent Fleet & Engineering Missions',
      category: 'Navigation',
      icon: <Bot className="w-4 h-4 text-cyan-400" />,
      action: () => setActiveTab('swarm')
    },
    {
      id: 'tab-delivery',
      label: 'Switch View: GitHub Delivery & Merge Governance',
      category: 'Navigation',
      icon: <FolderGit2 className="w-4 h-4 text-cyan-400" />,
      action: () => setActiveTab('delivery')
    },
    {
      id: 'tab-providers',
      label: 'Switch View: AI Providers Cluster & FinOps Ledger',
      category: 'Navigation',
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      action: () => setActiveTab('providers')
    },
    {
      id: 'tab-recovery',
      label: 'Switch View: Recovery Center & Audit Explorer',
      category: 'Navigation',
      icon: <ShieldAlert className="w-4 h-4 text-purple-400" />,
      action: () => setActiveTab('recovery')
    },
    {
      id: 'tab-approvals',
      label: 'Switch View: Security Approvals Matrix',
      category: 'Navigation',
      icon: <ShieldAlert className="w-4 h-4 text-amber-400" />,
      action: () => setActiveTab('approvals')
    },
    {
      id: 'tab-telem',
      label: 'Switch View: Hardware & Host Telemetry',
      category: 'Navigation',
      icon: <Cpu className="w-4 h-4 text-emerald-400" />,
      action: () => setActiveTab('telemetry')
    },
    {
      id: 'tab-projects',
      label: 'Switch View: Registered Projects Matrix',
      category: 'Navigation',
      icon: <FolderGit2 className="w-4 h-4 text-slate-400" />,
      action: () => setActiveTab('projects')
    },
    {
      id: 'macro-git',
      label: 'Macro: Git Status & Working Tree Delta',
      category: 'Macro',
      icon: <Zap className="w-4 h-4 text-cyan-400" />,
      action: () => {
        setActiveTab('workspace');
        onRunMacro('git:status');
      }
    },
    {
      id: 'macro-diag',
      label: 'Macro: Full Host Hardware Diagnostics',
      category: 'Macro',
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      action: () => {
        setActiveTab('workspace');
        onRunMacro('system:diagnostics');
      }
    },
    {
      id: 'macro-ports',
      label: 'Macro: Probe Active Listening Sockets',
      category: 'Macro',
      icon: <Zap className="w-4 h-4 text-emerald-400" />,
      action: () => {
        setActiveTab('workspace');
        onRunMacro('network:scan-ports');
      }
    },
    {
      id: 'macro-gc',
      label: 'Macro: Purge Cache & Run Garbage Collection',
      category: 'Macro',
      icon: <Zap className="w-4 h-4 text-purple-400" />,
      action: () => {
        setActiveTab('workspace');
        onRunMacro('memory:purge-cache');
      }
    },
    {
      id: 'dispatch-sentinel',
      label: 'Dispatch: SENTINEL-X Vulnerability Scan',
      category: 'Agent Task',
      icon: <Bot className="w-4 h-4 text-rose-400" />,
      action: () => {
        setActiveTab('swarm');
        onQuickDispatch('agent-sentinel', 'Autonomous Codebase Security & Secret Scan');
      }
    },
    {
      id: 'dispatch-coder',
      label: 'Dispatch: NEURAL-CODER Feature Synthesis',
      category: 'Agent Task',
      icon: <Bot className="w-4 h-4 text-emerald-400" />,
      action: () => {
        setActiveTab('swarm');
        onQuickDispatch('agent-coder', 'Synthesize New Visualizer Widget');
      }
    },
    {
      id: 'hud-scanlines',
      label: 'HUD: Toggle CRT Scanlines Overlay',
      category: 'Display',
      icon: <Tv className="w-4 h-4 text-cyan-400" />,
      action: () => toggleScanlines()
    },
    {
      id: 'hud-audio',
      label: 'HUD: Toggle Web Audio Synthesizer SFX',
      category: 'Audio',
      icon: <Volume2 className="w-4 h-4 text-cyan-400" />,
      action: () => toggleAudio()
    },
    {
      id: 'panic-protocol',
      label: 'Emergency: Trigger Panic Protocol (Abort All)',
      category: 'Emergency',
      icon: <ShieldAlert className="w-4 h-4 text-rose-500 animate-pulse" />,
      action: () => onTriggerPanic()
    }
  ];

  const filtered = commandList.filter(cmd =>
    cmd.label.toLowerCase().includes(query.toLowerCase()) ||
    cmd.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        sound.click();
        setSelectedIndex(prev => (prev + 1) % (filtered.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        sound.click();
        setSelectedIndex(prev => (prev - 1 + filtered.length) % (filtered.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          sound.beep(800, 0.08, 'sine');
          filtered[selectedIndex].action();
          onClose();
        }
      } else if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/80 backdrop-blur-md font-mono">
      <div 
        className="w-full max-w-2xl bg-[#090f1d] border-2 border-cyan-400 rounded-lg shadow-[0_0_30px_rgba(0,240,255,0.35)] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-cyan-500/30 bg-[#060a14]">
          <Terminal className="w-5 h-5 text-cyan-400" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command, macro, or agent directive..."
            className="flex-1 bg-transparent text-sm text-cyan-200 placeholder-slate-500 focus:outline-none"
          />
          <kbd className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400">
            ESC
          </kbd>
        </div>

        {/* Command List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              NO COMMANDS MATCHED MATRIX QUERY
            </div>
          ) : (
            filtered.map((cmd, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={cmd.id}
                  onClick={() => {
                    sound.beep(800, 0.08, 'sine');
                    cmd.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/60 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                      : 'text-slate-300 hover:bg-slate-900/60 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-1 rounded bg-black/40">
                      {cmd.icon}
                    </div>
                    <span className="text-xs font-bold">{cmd.label}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 uppercase">
                      {cmd.category}
                    </span>
                    {isSelected && (
                      <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-cyan-500/20 bg-[#050812] flex items-center justify-between text-[10px] text-slate-400">
          <div className="flex items-center gap-3">
            <span>Use <kbd className="text-cyan-400">↑</kbd> <kbd className="text-cyan-400">↓</kbd> to navigate</span>
            <span><kbd className="text-cyan-400">Enter</kbd> to execute</span>
          </div>
          <span className="text-cyan-400">NEXUS OMNIBAR</span>
        </div>
      </div>
    </div>
  );
};
