import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Volume2, 
  VolumeX, 
  Tv, 
  Terminal, 
  Radio, 
  Cpu, 
  Bot, 
  FolderGit2, 
  GitPullRequest,
  Zap,
  RotateCcw,
  Target,
  Wrench,
  Rocket,
  HeartPulse,
  ShieldCheck,
  Brain,
  Compass,
  Boxes,
  Server,
  Globe,
  FolderPlus
} from 'lucide-react';
import { sound } from '../utils/audio';

export type TabType = 'c2' | 'hud' | 'missions' | 'adaptive' | 'products' | 'operations' | 'deployments' | 'healing' | 'security' | 'knowledge' | 'tools' | 'swarm' | 'delivery' | 'providers' | 'approvals' | 'recovery' | 'audit' | 'telemetry' | 'projects' | 'cloud' | 'workspace' | 'memory';


interface HeaderHUDProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  onOpenCommandPalette: () => void;
  onTriggerPanic: () => void;
  scanlines: boolean;
  setScanlines: React.Dispatch<React.SetStateAction<boolean>>;
  audioEnabled: boolean;
  setAudioEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  pendingApprovalsCount: number;
  onOpenBridgeSettings?: () => void;
  onOpenAddProject?: () => void;
}

export const HeaderHUD = ({
  activeTab,
  setActiveTab,
  onOpenCommandPalette,
  onTriggerPanic,
  scanlines,
  setScanlines,
  audioEnabled,
  setAudioEnabled,
  pendingApprovalsCount,
  onOpenBridgeSettings,
  onOpenAddProject
}: HeaderHUDProps) => {
  const [time, setTime] = useState<string>('');
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-US', { hour12: false }));
      setUtcTime(now.toUTCString().split(' ')[4] + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleAudioToggle = () => {
    const nextState = sound.toggle();
    setAudioEnabled(nextState);
  };

  const handleTabChange = (tab: TabType) => {
    sound.click();
    setActiveTab(tab);
  };

  return (
    <header className="hud-panel border-b border-cyan-500/30 bg-[#060910]/95 px-4 py-2.5 sticky top-0 z-50 flex flex-wrap items-center justify-between gap-4">
      {/* Brand & Status */}
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-8 h-8 rounded border border-cyan-400/40 bg-cyan-950/40 text-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.4)]">
          <Radio className="w-5 h-5 animate-pulse" />
          <span className="absolute -top-1 -right-1 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
          </span>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-black tracking-widest text-cyan-400 text-glow-cyan font-mono">
              NEXUS
            </span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-mono">
              v1.2.0-HUD
            </span>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              CORE ONLINE
            </span>
          </div>
          <div className="text-[10px] text-slate-400 tracking-wider font-mono">
            CYBER-HUD LIVE OPERATIONS CONTROL PLANE
          </div>
        </div>
      </div>

      {/* Navigation Matrix */}
      <nav className="flex items-center gap-1 bg-[#0c1220] p-1 rounded border border-cyan-500/20 overflow-x-auto max-w-full no-scrollbar">
        <button
          onClick={() => handleTabChange('c2')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'c2'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Terminal className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>COMMAND & CONTROL</span>
        </button>

        <button
          onClick={() => handleTabChange('hud')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'hud'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Tv className="w-3.5 h-3.5 text-cyan-400" />
          <span>CYBER-HUD</span>
        </button>

        <button
          onClick={() => handleTabChange('missions')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'missions'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Target className="w-3.5 h-3.5 text-emerald-400" />
          <span>MISSIONS</span>
        </button>

        <button
          onClick={() => handleTabChange('adaptive')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'adaptive'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Compass className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>ADAPTIVE MISSION</span>
        </button>

        <button
          onClick={() => handleTabChange('products')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'products'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Boxes className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>PRODUCT BUILDER</span>
        </button>

        <button
          onClick={() => handleTabChange('operations')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'operations'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Server className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>PROJECT OPERATIONS</span>
        </button>


        <button
          onClick={() => handleTabChange('deployments')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'deployments'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Rocket className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>DEPLOYMENTS</span>
        </button>

        <button
          onClick={() => handleTabChange('healing')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'healing'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <HeartPulse className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
          <span>SELF-HEALING</span>
        </button>

        <button
          onClick={() => handleTabChange('security')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'security'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          <span>SECURITY & COMPLIANCE</span>
        </button>

        <button
          onClick={() => handleTabChange('knowledge')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'knowledge'
              ? 'bg-purple-500/20 text-purple-300 border border-purple-400/50 shadow-[0_0_10px_rgba(168,85,247,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Brain className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
          <span>KNOWLEDGE & LEARNING</span>
        </button>

        <button
          onClick={() => handleTabChange('tools')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'tools'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Wrench className="w-3.5 h-3.5 text-cyan-400" />
          <span>TOOLS & APPS</span>
        </button>

        <button
          onClick={() => handleTabChange('swarm')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'swarm'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Bot className="w-3.5 h-3.5" />
          <span>AGENTS & DAG</span>
        </button>

        <button
          onClick={() => handleTabChange('delivery')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'delivery'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <GitPullRequest className="w-3.5 h-3.5" />
          <span>DELIVERY & MERGES</span>
        </button>

        <button
          onClick={() => handleTabChange('providers')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'providers'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-400/50 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span>AI & FINOPS</span>
        </button>

        <button
          onClick={() => handleTabChange('approvals')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'approvals'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-400/50 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
          <span>APPROVALS</span>
          {pendingApprovalsCount > 0 && (
            <span className="bg-amber-500/30 text-amber-300 text-[10px] px-1 rounded-full font-bold border border-amber-500/50 animate-pulse">
              {pendingApprovalsCount}
            </span>
          )}
        </button>

        <button
          onClick={() => handleTabChange('recovery')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'recovery'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>RECOVERY & AUDIT</span>
        </button>

        <button
          onClick={() => handleTabChange('telemetry')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'telemetry'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>TELEMETRY</span>
        </button>

        <button
          onClick={() => handleTabChange('projects')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-mono whitespace-nowrap transition-all ${
            activeTab === 'projects'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <FolderGit2 className="w-3.5 h-3.5" />
          <span>PROJECTS</span>
        </button>
      </nav>

      {/* Mission Chronometer & Controls */}
      <div className="flex items-center gap-2.5">
        {/* Onboard Project Button */}
        {onOpenAddProject && (
          <button
            onClick={() => {
              sound.click();
              onOpenAddProject();
            }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/50 text-xs font-mono font-bold text-cyan-300 hover:text-cyan-200 transition-all shadow-[0_0_10px_rgba(0,240,255,0.2)]"
            title="Onboard or Auto-Discover Projects"
          >
            <FolderPlus className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">+ PROJECT</span>
          </button>
        )}

        {/* Local Bridge Settings Button */}
        {onOpenBridgeSettings && (
          <button
            onClick={() => {
              sound.click();
              onOpenBridgeSettings();
            }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-slate-900/90 hover:bg-slate-800 border border-cyan-500/30 text-xs font-mono text-cyan-300 hover:border-cyan-400 transition-all"
            title="Configure Local Backend Bridge URL & Auth"
          >
            <Globe className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">BRIDGE</span>
          </button>
        )}

        {/* Quick Command Launcher */}
        <button
          onClick={() => {
            sound.click();
            onOpenCommandPalette();
          }}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-slate-900/90 border border-cyan-500/30 text-xs font-mono text-cyan-300 hover:border-cyan-400 transition-all hover:shadow-[0_0_10px_rgba(0,240,255,0.25)]"
          title="Command Palette (Ctrl+K)"
        >
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span className="hidden sm:inline">COMMANDS</span>
          <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-400">
            Ctrl+K
          </kbd>
        </button>

        {/* SFX Audio Synthesizer */}
        <button
          onClick={handleAudioToggle}
          className={`p-1.5 rounded border transition-all ${
            audioEnabled
              ? 'bg-cyan-950/60 border-cyan-400/60 text-cyan-300 shadow-[0_0_8px_rgba(0,240,255,0.3)]'
              : 'bg-slate-900 border-slate-700 text-slate-500 hover:text-slate-300'
          }`}
          title={audioEnabled ? 'Audio SFX Enabled (Web Audio Synthesizer)' : 'Audio SFX Muted'}
        >
          {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
        </button>

        {/* CRT Scanline Toggle */}
        <button
          onClick={() => {
            sound.click();
            setScanlines(prev => !prev);
          }}
          className={`p-1.5 rounded border transition-all ${
            scanlines
              ? 'bg-cyan-950/60 border-cyan-400/60 text-cyan-300 shadow-[0_0_8px_rgba(0,240,255,0.3)]'
              : 'bg-slate-900 border-slate-700 text-slate-500 hover:text-slate-300'
          }`}
          title={scanlines ? 'CRT Scanlines Active' : 'CRT Scanlines Off'}
        >
          <Tv className="w-4 h-4" />
        </button>

        {/* Clock Readout */}
        <div className="hidden md:flex flex-col items-end font-mono leading-tight">
          <span className="text-xs text-cyan-300 font-bold tracking-wider">{time}</span>
          <span className="text-[9px] text-slate-400">{utcTime}</span>
        </div>

        {/* Emergency Panic Protocol */}
        <button
          onClick={() => {
            sound.panic();
            onTriggerPanic();
          }}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-crimson-950/80 border border-rose-600/70 text-rose-400 text-xs font-mono font-bold hover:bg-rose-900/60 hover:text-rose-200 transition-all hover:shadow-[0_0_12px_rgba(255,51,102,0.5)]"
          title="Emergency Abort All Agent Missions"
        >
          <ShieldAlert className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
          <span>PANIC</span>
        </button>
      </div>
    </header>
  );
};
