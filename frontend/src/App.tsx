import { useState, useEffect, useCallback } from 'react';
import { HeaderHUD, type TabType } from './components/HeaderHUD';
import { AgentSwarmView } from './components/AgentSwarmView';
import { TelemetryCockpit } from './components/TelemetryCockpit';
import { WorkspaceMissionControl } from './components/WorkspaceMissionControl';
import { KnowledgeMatrix } from './components/KnowledgeMatrix';
import { CloudControlView } from './components/CloudControlView';
import { ProjectsMatrixView } from './components/ProjectsMatrixView';
import { ApprovalsMatrixView } from './components/ApprovalsMatrixView';
import { AuditTrailView } from './components/AuditTrailView';
import { CommandPaletteModal } from './components/CommandPaletteModal';
import type { Agent, Task, Telemetry, ApprovalRequest, MemoryNode, WorkspaceProject } from './types';
import { sound } from './utils/audio';

export function App() {
  const [activeTab, setActiveTab] = useState<TabType>('swarm');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [scanlines, setScanlines] = useState<boolean>(true);
  const [audioEnabled, setAudioEnabled] = useState<boolean>(false);

  // Core Matrix State
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [memories, setMemories] = useState<MemoryNode[]>([]);
  const [workspaceProjects, setWorkspaceProjects] = useState<WorkspaceProject[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  // Fetch initial REST data
  const fetchData = useCallback(async () => {
    try {
      const [resTelem, resAgents, resTasks, resApprovals, resMems, resWork] = await Promise.all([
        fetch('/api/telemetry').then(r => r.json()),
        fetch('/api/agents').then(r => r.json()),
        fetch('/api/tasks').then(r => r.json()),
        fetch('/api/approvals').then(r => r.json()),
        fetch('/api/memories').then(r => r.json()),
        fetch('/api/workspace').then(r => r.json())
      ]);

      setTelemetry(resTelem);
      setAgents(resAgents);
      setTasks(resTasks);
      setApprovals(resApprovals);
      setMemories(resMems);
      setWorkspaceProjects(resWork.active_projects || []);
      setIsConnected(true);
    } catch (err) {
      console.warn('REST poll fallback error:', err);
    }
  }, []);

  // WebSocket Live Stream Connection
  useEffect(() => {
    fetchData();

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
    let socket: WebSocket | null = null;
    let pollInterval: ReturnType<typeof setInterval> | null = null;

    const connectWs = () => {
      try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
          setIsConnected(true);
        };

        socket.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'telemetry_tick') {
              setTelemetry(msg.data);
              if (msg.agents) setAgents(msg.agents);
              if (msg.tasks) setTasks(msg.tasks);
              if (msg.pending_approvals) setApprovals(msg.pending_approvals);
            }
          } catch (e) {
            console.error('Failed to parse websocket message:', e);
          }
        };

        socket.onclose = () => {
          setIsConnected(false);
          // Fallback to REST polling if socket closes
          if (!pollInterval) {
            pollInterval = setInterval(fetchData, 2000);
          }
        };

        socket.onerror = () => {
          socket?.close();
        };
      } catch (e) {
        if (!pollInterval) {
          pollInterval = setInterval(fetchData, 2000);
        }
      }
    };

    connectWs();

    return () => {
      if (socket) socket.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [fetchData]);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+K or Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        sound.beep(850, 0.08, 'sine');
        setIsCommandPaletteOpen(prev => !prev);
      }

      // Quick numbers for tabs when not in input
      const target = e.target as HTMLElement;
      if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA' && !isCommandPaletteOpen) {
        if (e.key === '1') {
          sound.click();
          setActiveTab('swarm');
        } else if (e.key === '2') {
          sound.click();
          setActiveTab('projects');
        } else if (e.key === '3') {
          sound.click();
          setActiveTab('approvals');
        } else if (e.key === '4') {
          sound.click();
          setActiveTab('cloud');
        } else if (e.key === '5') {
          sound.click();
          setActiveTab('audit');
        } else if (e.key === '6') {
          sound.click();
          setActiveTab('telemetry');
        } else if (e.key === '7') {
          sound.click();
          setActiveTab('memory');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCommandPaletteOpen]);

  // Task Dispatch
  const handleDispatchTask = async (agentId: string, title: string, instructions: string, tier: string) => {
    const res = await fetch('/api/tasks/dispatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        agent_id: agentId,
        autonomy_tier: tier,
        instructions
      })
    });
    const data = await res.json();
    if (data.task) {
      setTasks(prev => [data.task, ...prev]);
    }
  };

  // Quick Dispatch from command palette
  const handleQuickDispatch = async (agentId: string, title: string) => {
    await handleDispatchTask(agentId, title, `Quick objective dispatched via Omnibar: ${title}`, 'Guardrailed');
  };

  // Approval Decision
  const handleDecideApproval = async (id: string, decision: 'approved' | 'rejected') => {
    await fetch('/api/approvals/decide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approval_id: id, decision })
    });
    setApprovals(prev => prev.map(a => a.id === id ? { ...a, status: decision } : a));
  };

  // Emergency Panic Protocol
  const handleTriggerPanic = async () => {
    const res = await fetch('/api/panic', { method: 'POST' });
    const data = await res.json();
    sound.panic();
    fetchData();
    alert(`[EMERGENCY PANIC PROTOCOL ACTIVE]\nHalted ${data.missions_aborted || 0} active agent missions. Systems locked in safe state.`);
  };

  // Run Macro
  const handleRunMacro = async (macroId: string) => {
    const res = await fetch('/api/macros/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ macro_id: macroId })
    });
    return await res.json();
  };

  // Create Memory
  const handleCreateMemory = async (
    title: string, 
    category: string, 
    content: string, 
    tags: string[], 
    pinned: boolean
  ) => {
    const res = await fetch('/api/memories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, category, content, tags, pinned })
    });
    const newMem = await res.json();
    setMemories(prev => [newMem, ...prev]);
  };

  // Delete Memory
  const handleDeleteMemory = async (id: string) => {
    await fetch(`/api/memories/${id}`, { method: 'DELETE' });
    setMemories(prev => prev.filter(m => m.id !== id));
  };

  return (
    <div className="min-h-screen bg-[#060910] text-slate-100 cyber-grid relative selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Optional CRT Scanlines Layer */}
      {scanlines && <div className="scanlines" />}

      {/* Main HUD Header */}
      <HeaderHUD
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onTriggerPanic={handleTriggerPanic}
        scanlines={scanlines}
        setScanlines={setScanlines}
        audioEnabled={audioEnabled}
        setAudioEnabled={setAudioEnabled}
        pendingApprovalsCount={approvals.filter(a => a.status === 'pending').length}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'swarm' && (
          <AgentSwarmView
            agents={agents}
            tasks={tasks}
            approvals={approvals}
            onDispatchTask={handleDispatchTask}
            onDecideApproval={handleDecideApproval}
          />
        )}

        {activeTab === 'projects' && (
          <ProjectsMatrixView />
        )}

        {activeTab === 'approvals' && (
          <ApprovalsMatrixView />
        )}

        {activeTab === 'cloud' && (
          <CloudControlView />
        )}

        {activeTab === 'audit' && (
          <AuditTrailView />
        )}

        {activeTab === 'telemetry' && (
          <TelemetryCockpit telemetry={telemetry} />
        )}

        {activeTab === 'workspace' && (
          <WorkspaceMissionControl
            projects={workspaceProjects}
            onRunMacro={handleRunMacro}
          />
        )}

        {activeTab === 'memory' && (
          <KnowledgeMatrix
            memories={memories}
            onCreateMemory={handleCreateMemory}
            onDeleteMemory={handleDeleteMemory}
          />
        )}
      </main>

      {/* Omnibar / Command Palette Modal */}
      <CommandPaletteModal
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        setActiveTab={setActiveTab}
        onRunMacro={handleRunMacro}
        onTriggerPanic={handleTriggerPanic}
        toggleScanlines={() => setScanlines(p => !p)}
        toggleAudio={() => {
          const next = sound.toggle();
          setAudioEnabled(next);
        }}
        onQuickDispatch={handleQuickDispatch}
      />

      {/* Bottom Status Ticker */}
      <footer className="hud-panel border-t border-cyan-500/20 py-2 px-4 fixed bottom-0 left-0 right-0 z-40 bg-[#060910]/95 flex items-center justify-between text-[10px] font-mono text-slate-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className={isConnected ? 'text-emerald-400' : 'text-rose-400'}>
              {isConnected ? 'WEBSOCKET TELEMETRY STREAM ONLINE' : 'TELEMETRY DISCONNECTED'}
            </span>
          </span>
          <span>•</span>
          <span className="text-slate-400">HOST: LOCALHOST</span>
          <span>•</span>
          <span className="text-cyan-400">{telemetry?.agent_summary.active || 2} NEURAL THREADS ENGAGED</span>
        </div>

        <div className="hidden sm:flex items-center gap-4">
          <span>Shortcuts: <kbd className="text-cyan-400">Ctrl+K</kbd> Omnibar | <kbd className="text-cyan-400">1-5</kbd> Tabs</span>
          <span className="text-slate-600">NEXUS PERSONAL ENGINEERING SYSTEM</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
