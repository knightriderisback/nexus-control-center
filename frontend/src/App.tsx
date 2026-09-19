import { useState, useEffect, useCallback } from 'react';
import { HeaderHUD, type TabType } from './components/HeaderHUD';
import { UnifiedCommandCenterView } from './components/UnifiedCommandCenterView';
import { CyberHudLiveView } from './components/CyberHudLiveView';
import { CyberHudMissionControlView } from './components/CyberHudMissionControlView';
import { AdaptiveMissionMatrixView } from './components/AdaptiveMissionMatrixView';
import { ProductBuilderMatrixView } from './components/ProductBuilderMatrixView';
import { ProjectOperationsMatrixView } from './components/ProjectOperationsMatrixView';
import { ProductionDeploymentMatrixView } from './components/ProductionDeploymentMatrixView';
import { AutonomousSelfHealingView } from './components/AutonomousSelfHealingView';
import { SecurityComplianceMatrixView } from './components/SecurityComplianceMatrixView';
import { KnowledgeLearningMatrixView } from './components/KnowledgeLearningMatrixView';
import { UniversalToolAppMatrixView } from './components/UniversalToolAppMatrixView';
import { AgentSwarmView } from './components/AgentSwarmView';
import { DeliveryMatrixView } from './components/DeliveryMatrixView';
import { ProvidersControlView } from './components/ProvidersControlView';
import { RecoveryControlView } from './components/RecoveryControlView';
import { TelemetryCockpit } from './components/TelemetryCockpit';
import { WorkspaceMissionControl } from './components/WorkspaceMissionControl';
import { KnowledgeMatrix } from './components/KnowledgeMatrix';
import { CloudControlView } from './components/CloudControlView';
import { ProjectsMatrixView } from './components/ProjectsMatrixView';
import { ProjectDetailDashboardView } from './components/ProjectDetailDashboardView';
import { ApprovalsMatrixView } from './components/ApprovalsMatrixView';
import { AuditTrailView } from './components/AuditTrailView';
import { CommandPaletteModal } from './components/CommandPaletteModal';
import { BridgeSettingsModal } from './components/BridgeSettingsModal';
import { AddProjectModal } from './components/AddProjectModal';
import type { Agent, Task, Telemetry, ApprovalRequest, MemoryNode, WorkspaceProject } from './types';
import { sound } from './utils/audio';
import { nexusFetch, getWsUrl, getApiBaseUrl } from './utils/api';

export function App() {
  const [activeTab, setActiveTab] = useState<TabType>('hud');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [isBridgeModalOpen, setIsBridgeModalOpen] = useState<boolean>(false);
  const [isAddProjectModalOpen, setIsAddProjectModalOpen] = useState<boolean>(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
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
  const [bridgeRevision, setBridgeRevision] = useState<number>(0);

  // Fetch initial REST data via dynamic nexusFetch
  const fetchData = useCallback(async () => {
    try {
      const [resTelem, resAgents, resTasks, resApprovals, resMems, resWork] = await Promise.all([
        nexusFetch<any>('/api/telemetry').catch(() => null),
        nexusFetch<any[]>('/api/agents').catch(() => []),
        nexusFetch<any[]>('/api/tasks').catch(() => []),
        nexusFetch<any[]>('/api/approvals').catch(() => []),
        nexusFetch<any[]>('/api/memories').catch(() => []),
        nexusFetch<any>('/api/workspace').catch(() => ({ active_projects: [] }))
      ]);

      if (resTelem) setTelemetry(resTelem);
      if (resAgents) setAgents(resAgents);
      if (resTasks) setTasks(resTasks);
      if (resApprovals) setApprovals(resApprovals);
      if (resMems) setMemories(resMems);
      if (resWork?.active_projects) setWorkspaceProjects(resWork.active_projects);
      setIsConnected(true);
    } catch (err) {
      console.warn('REST poll fallback error:', err);
      setIsConnected(false);
    }
  }, []);

  // WebSocket Live Stream Connection
  useEffect(() => {
    fetchData();

    const wsUrl = getWsUrl();
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
            pollInterval = setInterval(fetchData, 3000);
          }
        };

        socket.onerror = () => {
          socket?.close();
        };
      } catch (e) {
        if (!pollInterval) {
          pollInterval = setInterval(fetchData, 3000);
        }
      }
    };

    connectWs();

    return () => {
      if (socket) socket.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [fetchData, bridgeRevision]);

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
          setActiveTab('hud');
        } else if (e.key === '2') {
          sound.click();
          setActiveTab('swarm');
        } else if (e.key === '3') {
          sound.click();
          setActiveTab('delivery');
        } else if (e.key === '4') {
          sound.click();
          setActiveTab('providers');
        } else if (e.key === '5') {
          sound.click();
          setActiveTab('approvals');
        } else if (e.key === '6') {
          sound.click();
          setActiveTab('recovery');
        } else if (e.key === '7') {
          sound.click();
          setActiveTab('telemetry');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCommandPaletteOpen]);

  // Task Dispatch
  const handleDispatchTask = async (agentId: string, title: string, instructions: string, tier: string) => {
    const data = await nexusFetch<{ task: Task }>('/api/tasks/dispatch', {
      method: 'POST',
      body: JSON.stringify({
        title,
        agent_id: agentId,
        autonomy_tier: tier,
        instructions
      })
    });
    if (data?.task) {
      setTasks(prev => [data.task, ...prev]);
    }
  };

  // Quick Dispatch from command palette
  const handleQuickDispatch = async (agentId: string, title: string) => {
    await handleDispatchTask(agentId, title, `Quick objective dispatched via Omnibar: ${title}`, 'Guardrailed');
  };

  // Approval Decision
  const handleDecideApproval = async (id: string, decision: 'approved' | 'rejected') => {
    await nexusFetch('/api/approvals/decide', {
      method: 'POST',
      body: JSON.stringify({ approval_id: id, decision })
    });
    setApprovals(prev => prev.map(a => a.id === id ? { ...a, status: decision } : a));
  };

  // Emergency Panic Protocol
  const handleTriggerPanic = async () => {
    const data = await nexusFetch<{ missions_aborted?: number }>('/api/panic', { method: 'POST' });
    sound.panic();
    fetchData();
    alert(`[EMERGENCY PANIC PROTOCOL ACTIVE]\nHalted ${data?.missions_aborted || 0} active agent missions. Systems locked in safe state.`);
  };

  // Run Macro
  const handleRunMacro = async (macroId: string) => {
    return await nexusFetch('/api/macros/run', {
      method: 'POST',
      body: JSON.stringify({ macro_id: macroId })
    });
  };

  // Create Memory
  const handleCreateMemory = async (
    title: string, 
    category: string, 
    content: string, 
    tags: string[], 
    pinned: boolean
  ) => {
    const newMem = await nexusFetch('/api/memories', {
      method: 'POST',
      body: JSON.stringify({ title, category, content, tags, pinned })
    });
    if (newMem) {
      setMemories(prev => [newMem, ...prev]);
    }
  };

  // Delete Memory
  const handleDeleteMemory = async (id: string) => {
    await nexusFetch(`/api/memories/${id}`, { method: 'DELETE' });
    setMemories(prev => prev.filter(m => m.id !== id));
  };

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    if (tab !== 'projects') {
      setSelectedProjectId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#060910] text-slate-100 cyber-grid relative selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Optional CRT Scanlines Layer */}
      {scanlines && <div className="scanlines" />}

      {/* Main HUD Header */}
      <HeaderHUD
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onOpenBridgeSettings={() => setIsBridgeModalOpen(true)}
        onOpenAddProject={() => setIsAddProjectModalOpen(true)}
        onTriggerPanic={handleTriggerPanic}
        scanlines={scanlines}
        setScanlines={setScanlines}
        audioEnabled={audioEnabled}
        setAudioEnabled={setAudioEnabled}
        pendingApprovalsCount={approvals.filter(a => a.status === 'pending').length}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'c2' && (
          <UnifiedCommandCenterView />
        )}

        {activeTab === 'hud' && (
          <CyberHudLiveView
            onTriggerPanic={handleTriggerPanic}
            onNavigateTab={(tab) => handleTabChange(tab as TabType)}
          />
        )}

        {activeTab === 'missions' && (
          <CyberHudMissionControlView />
        )}

        {activeTab === 'adaptive' && (
          <AdaptiveMissionMatrixView />
        )}

        {activeTab === 'products' && (
          <ProductBuilderMatrixView />
        )}

        {activeTab === 'operations' && (
          <ProjectOperationsMatrixView />
        )}

        {activeTab === 'deployments' && (
          <ProductionDeploymentMatrixView />
        )}

        {activeTab === 'healing' && (
          <AutonomousSelfHealingView />
        )}

        {activeTab === 'security' && (
          <SecurityComplianceMatrixView />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeLearningMatrixView />
        )}

        {activeTab === 'tools' && (
          <UniversalToolAppMatrixView />
        )}

        {activeTab === 'swarm' && (
          <AgentSwarmView
            agents={agents}
            tasks={tasks}
            approvals={approvals}
            onDispatchTask={handleDispatchTask}
            onDecideApproval={handleDecideApproval}
          />
        )}

        {activeTab === 'delivery' && (
          <DeliveryMatrixView />
        )}

        {activeTab === 'providers' && (
          <ProvidersControlView />
        )}

        {activeTab === 'approvals' && (
          <ApprovalsMatrixView />
        )}

        {activeTab === 'recovery' && (
          <RecoveryControlView />
        )}

        {activeTab === 'telemetry' && (
          <TelemetryCockpit telemetry={telemetry} />
        )}

        {activeTab === 'projects' && (
          selectedProjectId ? (
            <ProjectDetailDashboardView
              projectId={selectedProjectId}
              onBack={() => setSelectedProjectId(null)}
              onCreateMissionForProject={(_pid, _name) => {
                handleTabChange('missions');
              }}
            />
          ) : (
            <ProjectsMatrixView
              onSelectProject={(id) => setSelectedProjectId(id)}
              onOpenAddProject={() => setIsAddProjectModalOpen(true)}
              onCreateMission={() => handleTabChange('missions')}
            />
          )
        )}

        {activeTab === 'cloud' && (
          <CloudControlView />
        )}

        {activeTab === 'audit' && (
          <AuditTrailView />
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
        setActiveTab={handleTabChange}
        onRunMacro={handleRunMacro}
        onTriggerPanic={handleTriggerPanic}
        toggleScanlines={() => setScanlines(p => !p)}
        toggleAudio={() => {
          const next = sound.toggle();
          setAudioEnabled(next);
        }}
        onQuickDispatch={handleQuickDispatch}
      />

      {/* Bridge Settings Modal */}
      <BridgeSettingsModal
        isOpen={isBridgeModalOpen}
        onClose={() => setIsBridgeModalOpen(false)}
        onBridgeUpdated={() => {
          setBridgeRevision(prev => prev + 1);
          fetchData();
        }}
      />

      {/* Add Project Modal */}
      <AddProjectModal
        isOpen={isAddProjectModalOpen}
        onClose={() => setIsAddProjectModalOpen(false)}
        onProjectAdded={(newProjId) => {
          setIsAddProjectModalOpen(false);
          handleTabChange('projects');
          if (newProjId && newProjId !== 'all') {
            setSelectedProjectId(newProjId);
          }
        }}
      />

      {/* Bottom Status Ticker */}
      <footer className="hud-panel border-t border-cyan-500/20 py-2 px-4 fixed bottom-0 left-0 right-0 z-40 bg-[#060910]/95 flex items-center justify-between text-[10px] font-mono text-slate-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className={isConnected ? 'text-emerald-400' : 'text-rose-400'}>
              {isConnected ? 'TELEMETRY BRIDGE ONLINE' : 'BRIDGE DISCONNECTED'}
            </span>
          </span>
          <span>•</span>
          <span className="text-slate-400">
            BRIDGE: {getApiBaseUrl() ? getApiBaseUrl() : 'DIRECT LOCAL DAEMON'}
          </span>
          <span>•</span>
          <span className="text-cyan-400">{telemetry?.agent_summary?.active || 2} NEURAL THREADS ENGAGED</span>
        </div>

        <div className="hidden sm:flex items-center gap-4">
          <button 
            onClick={() => setIsBridgeModalOpen(true)}
            className="text-cyan-400 hover:underline flex items-center gap-1 cursor-pointer"
          >
            ⚙ BRIDGE CONFIG
          </button>
          <span>Shortcuts: <kbd className="text-cyan-400">Ctrl+K</kbd> Omnibar</span>
          <span className="text-slate-600">NEXUS PERSONAL ENGINEERING SYSTEM</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
