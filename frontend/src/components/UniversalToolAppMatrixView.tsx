import React, { useState, useEffect } from 'react';
import {
  Wrench,
  Layers,
  Activity,
  Play,
  CheckCircle2,
  Database,
  GitPullRequest,
  Zap,
  Smartphone,
  Server,
  Terminal,
  Search,
  Filter,
  RefreshCw,
  Plus,
  Radio,
  Code
} from 'lucide-react';
import type {
  UniversalToolManifest,
  UniversalToolInvocationResult,
  ConnectedApp,
  MCPServerDefinition,
  ToolsTelemetryData
} from '../types';

export const UniversalToolAppMatrixView: React.FC = () => {
  const [tools, setTools] = useState<UniversalToolManifest[]>([]);
  const [apps, setApps] = useState<ConnectedApp[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServerDefinition[]>([]);
  const [telemetry, setTelemetry] = useState<ToolsTelemetryData | null>(null);
  const [selectedTool, setSelectedTool] = useState<UniversalToolManifest | null>(null);
  const [activeTab, setActiveTab] = useState<'tools' | 'playground' | 'apps' | 'mcp' | 'telemetry'>('tools');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [playgroundParams, setPlaygroundParams] = useState<string>('{}');
  const [invocationResult, setInvocationResult] = useState<UniversalToolInvocationResult | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // New MCP Server Form
  const [mcpName, setMcpName] = useState('');
  const [mcpCommand, setMcpCommand] = useState('');
  const [mcpTransport, setMcpTransport] = useState<'stdio' | 'http' | 'sse'>('stdio');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tRes, aRes, mRes, telemRes] = await Promise.all([
        fetch('/api/v1/tools'),
        fetch('/api/v1/tools/apps'),
        fetch('/api/v1/tools/mcp/servers'),
        fetch('/api/v1/tools/telemetry')
      ]);

      if (tRes.ok) {
        const tData: UniversalToolManifest[] = await tRes.json();
        setTools(tData);
        if (tData.length > 0 && !selectedTool) {
          setSelectedTool(tData[0]);
          setPlaygroundParams(JSON.stringify(tData[0].input_schema || {}, null, 2));
        }
      }
      if (aRes.ok) setApps(await aRes.json());
      if (mRes.ok) setMcpServers(await mRes.json());
      if (telemRes.ok) setTelemetry(await telemRes.json());
    } catch (err: any) {
      console.error('Failed to load Universal Tools data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectTool = (tool: UniversalToolManifest) => {
    setSelectedTool(tool);
    // Generate sample params from schema
    const defaultParams: Record<string, any> = {};
    if (tool.input_schema) {
      Object.keys(tool.input_schema).forEach(key => {
        if (key.includes('path')) defaultParams[key] = '/root/control-center';
        else if (key.includes('owner')) defaultParams[key] = 'knightriderisback';
        else if (key.includes('repo')) defaultParams[key] = 'control-center';
        else if (key.includes('sql')) defaultParams[key] = 'SELECT sqlite_version();';
        else if (key.includes('url')) defaultParams[key] = 'http://127.0.0.1:8000/api/health';
        else defaultParams[key] = 'test_value';
      });
    }
    setPlaygroundParams(JSON.stringify(defaultParams, null, 2));
    setInvocationResult(null);
  };

  const handleExecuteTool = async () => {
    if (!selectedTool) return;
    try {
      setExecuting(true);
      let parsedParams = {};
      try {
        parsedParams = JSON.parse(playgroundParams);
      } catch {
        setNotification('Invalid JSON in parameters.');
        return;
      }

      const res = await fetch(`/api/v1/tools/${selectedTool.tool_id}/invoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_id: selectedTool.tool_id,
          parameters: parsedParams,
          caller_agent_id: 'agent-cyber-hud'
        })
      });

      const data: UniversalToolInvocationResult = await res.json();
      setInvocationResult(data);
      if (data.status === 'SUCCESS') {
        setNotification(`Tool ${selectedTool.name} executed in ${data.duration_ms}ms`);
      } else {
        setNotification(`Execution notice: ${data.status} - ${data.error || 'Check details'}`);
      }
      fetchData();
    } catch (err: any) {
      setNotification(`Execution error: ${err.message}`);
    } finally {
      setExecuting(false);
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleTestApp = async (appId: string) => {
    try {
      setNotification(`Testing connectivity for ${appId}...`);
      const res = await fetch(`/api/v1/tools/apps/${appId}/test`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setNotification(`App ${data.name} is ONLINE (${data.latency_ms}ms)`);
        fetchData();
      }
    } catch (err: any) {
      setNotification(`Test failed: ${err.message}`);
    } finally {
      setTimeout(() => setNotification(null), 4000);
    }
  };

  const handleAddMcpServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mcpName.trim() || !mcpCommand.trim()) return;
    try {
      const serverId = `mcp-${mcpName.toLowerCase().replace(/\s+/g, '-')}`;
      const res = await fetch('/api/v1/tools/mcp/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          server_id: serverId,
          name: mcpName,
          transport: mcpTransport,
          command_or_url: mcpCommand,
          status: 'CONNECTED'
        })
      });
      if (res.ok) {
        setNotification(`Registered MCP Server: ${mcpName}`);
        setMcpName('');
        setMcpCommand('');
        fetchData();
      }
    } catch (err: any) {
      setNotification(`Failed to register MCP server: ${err.message}`);
    }
  };

  const filteredTools = tools.filter(t => {
    const matchesSearch = t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          t.tool_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          t.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCat = selectedCategory === 'ALL' || t.category.toUpperCase() === selectedCategory.toUpperCase();
    return matchesSearch && matchesCat;
  });

  const categories = ['ALL', 'FILESYSTEM', 'GIT_VCS', 'DEPLOYMENT', 'DATABASE', 'SECURITY', 'COMMUNICATION', 'WEB_BROWSER', 'SYSTEM_OS'];

  const getRiskBadge = (risk: string) => {
    switch (risk.toUpperCase()) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-red-950 text-red-400 border border-red-800">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-orange-950 text-orange-400 border border-orange-800">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-yellow-950 text-yellow-400 border border-yellow-800">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-mono rounded bg-emerald-950 text-emerald-400 border border-emerald-800">LOW</span>;
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-black text-gray-200 overflow-hidden font-sans border-t border-cyan-900/40">
      {/* Top Header & Telemetry Bar */}
      <div className="bg-gray-950 border-b border-cyan-900/50 p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-cyan-950 border border-cyan-500/50 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.3)]">
            <Wrench className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-lg font-bold font-mono tracking-wider text-cyan-400 flex items-center gap-2">
              NEXUS // UNIVERSAL TOOL & APP MATRIX
              <span className="text-xs bg-cyan-900/60 text-cyan-300 px-2 py-0.5 rounded border border-cyan-700/50 font-mono">PHASE 15</span>
            </h2>
            <p className="text-xs text-gray-400 font-mono">
              Universal MCP Protocol Bridge • Dynamic Dispatch • App Ecosystem • FinOps $0.00 Governed
            </p>
          </div>
        </div>

        {/* Global Metric Counters */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="px-3 py-1.5 rounded bg-gray-900 border border-cyan-800/40 flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span className="text-gray-400">Tools:</span>
            <span className="text-cyan-300 font-bold">{tools.length}</span>
          </div>
          <div className="px-3 py-1.5 rounded bg-gray-900 border border-emerald-800/40 flex items-center gap-2">
            <Zap className="w-4 h-4 text-emerald-400" />
            <span className="text-gray-400">Connected Apps:</span>
            <span className="text-emerald-300 font-bold">{apps.length}</span>
          </div>
          <div className="px-3 py-1.5 rounded bg-gray-900 border border-purple-800/40 flex items-center gap-2">
            <Radio className="w-4 h-4 text-purple-400" />
            <span className="text-gray-400">MCP Servers:</span>
            <span className="text-purple-300 font-bold">{mcpServers.length}</span>
          </div>
          <div className="px-3 py-1.5 rounded bg-gray-900 border border-amber-800/40 flex items-center gap-2">
            <Activity className="w-4 h-4 text-amber-400" />
            <span className="text-gray-400">Invocations:</span>
            <span className="text-amber-300 font-bold">{telemetry?.total_invocations || 0}</span>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-1.5 rounded bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-cyan-400 border border-gray-700 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notifications Toast */}
      {notification && (
        <div className="bg-cyan-950/90 border-b border-cyan-500/60 px-4 py-2 text-xs font-mono text-cyan-300 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400 animate-spin" />
            <span>{notification}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-gray-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-gray-800 bg-gray-950/60 px-4 gap-2 pt-2">
        <button
          onClick={() => setActiveTab('tools')}
          className={`px-4 py-2 font-mono text-xs rounded-t border-t border-x transition flex items-center gap-2 ${
            activeTab === 'tools'
              ? 'bg-gray-900 border-cyan-500/60 text-cyan-400 font-bold'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          TOOL CATALOG ({tools.length})
        </button>
        <button
          onClick={() => setActiveTab('playground')}
          className={`px-4 py-2 font-mono text-xs rounded-t border-t border-x transition flex items-center gap-2 ${
            activeTab === 'playground'
              ? 'bg-gray-900 border-cyan-500/60 text-cyan-400 font-bold'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Play className="w-3.5 h-3.5" />
          TESTING PLAYGROUND
        </button>
        <button
          onClick={() => setActiveTab('apps')}
          className={`px-4 py-2 font-mono text-xs rounded-t border-t border-x transition flex items-center gap-2 ${
            activeTab === 'apps'
              ? 'bg-gray-900 border-cyan-500/60 text-cyan-400 font-bold'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          CONNECTED APPS ({apps.length})
        </button>
        <button
          onClick={() => setActiveTab('mcp')}
          className={`px-4 py-2 font-mono text-xs rounded-t border-t border-x transition flex items-center gap-2 ${
            activeTab === 'mcp'
              ? 'bg-gray-900 border-cyan-500/60 text-cyan-400 font-bold'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Radio className="w-3.5 h-3.5" />
          MCP PROTOCOL & PLUGINS
        </button>
        <button
          onClick={() => setActiveTab('telemetry')}
          className={`px-4 py-2 font-mono text-xs rounded-t border-t border-x transition flex items-center gap-2 ${
            activeTab === 'telemetry'
              ? 'bg-gray-900 border-cyan-500/60 text-cyan-400 font-bold'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          TELEMETRY & LOGS
        </button>
      </div>

      {/* Main View Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* ================================================================= */}
        {/* TAB 1: TOOL CATALOG & MATRIX */}
        {/* ================================================================= */}
        {activeTab === 'tools' && (
          <div className="space-y-4">
            {/* Search and Category Filters */}
            <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-900/80 p-3 rounded border border-gray-800">
              <div className="flex items-center gap-2 flex-1 min-w-[240px]">
                <Search className="w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tool by name, id, or capability..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-gray-950 border border-gray-700 rounded px-3 py-1.5 text-xs text-gray-200 w-full focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
              <div className="flex items-center gap-1 overflow-x-auto pb-1 max-w-full">
                <Filter className="w-3.5 h-3.5 text-gray-400 mr-1" />
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-2.5 py-1 text-xs font-mono rounded transition ${
                      selectedCategory === cat
                        ? 'bg-cyan-900/70 text-cyan-300 border border-cyan-500'
                        : 'bg-gray-950 text-gray-400 border border-gray-800 hover:border-gray-700'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Tools Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredTools.map((tool) => (
                <div
                  key={tool.tool_id}
                  onClick={() => handleSelectTool(tool)}
                  className={`p-4 rounded border cursor-pointer transition flex flex-col justify-between ${
                    selectedTool?.tool_id === tool.tool_id
                      ? 'bg-cyan-950/30 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                      : 'bg-gray-950 border-gray-800 hover:border-gray-700'
                  }`}
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-sm text-cyan-400 font-mono flex items-center gap-1.5">
                        <Wrench className="w-4 h-4 text-cyan-500" />
                        {tool.name}
                      </h3>
                      {getRiskBadge(tool.risk_level)}
                    </div>
                    <p className="text-xs text-gray-400 leading-relaxed line-clamp-2">{tool.description}</p>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-gray-900 text-gray-300 border border-gray-800">
                        {tool.category}
                      </span>
                      <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-cyan-950/80 text-cyan-300 border border-cyan-900">
                        {tool.protocol}
                      </span>
                      {tool.write_capability && (
                        <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-950/80 text-amber-300 border border-amber-900">
                          WRITE
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-gray-900 flex items-center justify-between text-[11px] font-mono text-gray-500">
                    <span>ID: <code className="text-gray-400">{tool.tool_id}</code></span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectTool(tool);
                        setActiveTab('playground');
                      }}
                      className="px-2.5 py-1 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-400 border border-cyan-800 flex items-center gap-1"
                    >
                      <Play className="w-3 h-3" /> Test
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 2: LIVE TESTING PLAYGROUND */}
        {/* ================================================================= */}
        {activeTab === 'playground' && selectedTool && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Tool Manifest & Parameter Editor */}
            <div className="bg-gray-950 border border-cyan-900/40 rounded p-4 space-y-4">
              <div className="flex items-start justify-between gap-2 border-b border-gray-800 pb-3">
                <div>
                  <h3 className="font-bold text-base text-cyan-400 font-mono flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-cyan-500" />
                    {selectedTool.name}
                  </h3>
                  <p className="text-xs text-gray-400 font-mono">{selectedTool.tool_id}</p>
                </div>
                {getRiskBadge(selectedTool.risk_level)}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-mono text-gray-400 flex items-center justify-between">
                  <span>Input JSON Parameters:</span>
                  <span className="text-[11px] text-cyan-400">Protocol: {selectedTool.protocol}</span>
                </label>
                <textarea
                  rows={8}
                  value={playgroundParams}
                  onChange={(e) => setPlaygroundParams(e.target.value)}
                  className="w-full bg-black border border-gray-800 rounded p-3 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="bg-gray-900/60 p-3 rounded border border-gray-800 space-y-2 text-xs font-mono">
                <div className="text-gray-400 font-bold">Input Schema Definition:</div>
                <pre className="text-[11px] text-gray-300 overflow-x-auto">{JSON.stringify(selectedTool.input_schema, null, 2)}</pre>
              </div>

              <button
                onClick={handleExecuteTool}
                disabled={executing}
                className="w-full py-2.5 rounded bg-cyan-900 hover:bg-cyan-800 text-cyan-300 border border-cyan-500 font-mono text-xs font-bold tracking-wider flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition"
              >
                <Play className={`w-4 h-4 ${executing ? 'animate-spin' : ''}`} />
                {executing ? 'EXECUTING UNIVERSAL TOOL...' : 'INVOKE TOOL NOW'}
              </button>
            </div>

            {/* Live Invocation Output */}
            <div className="bg-gray-950 border border-gray-800 rounded p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                <h3 className="font-bold text-sm text-gray-200 font-mono flex items-center gap-2">
                  <Code className="w-4 h-4 text-emerald-400" />
                  INVOCATION OUTPUT & TELEMETRY
                </h3>
                {invocationResult && (
                  <span className={`px-2 py-0.5 text-xs font-mono rounded ${
                    invocationResult.status === 'SUCCESS' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'
                  }`}>
                    {invocationResult.status} ({invocationResult.duration_ms}ms)
                  </span>
                )}
              </div>

              {invocationResult ? (
                <div className="space-y-3 font-mono text-xs">
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="p-2 bg-gray-900 rounded border border-gray-800">
                      <span className="text-gray-500">Invocation ID:</span>
                      <p className="text-gray-300 font-bold">{invocationResult.invocation_id}</p>
                    </div>
                    <div className="p-2 bg-gray-900 rounded border border-gray-800">
                      <span className="text-gray-500">Executed At:</span>
                      <p className="text-gray-300">{invocationResult.executed_at.split('T')[1]?.split('.')[0] || ''}</p>
                    </div>
                  </div>

                  {invocationResult.error && (
                    <div className="p-3 bg-red-950/50 border border-red-800 rounded text-red-300">
                      <strong>Error:</strong> {invocationResult.error}
                    </div>
                  )}

                  <div className="space-y-1">
                    <label className="text-gray-400">Response Payload:</label>
                    <pre className="p-3 bg-black border border-gray-800 rounded text-emerald-300 overflow-x-auto max-h-72 text-xs">
                      {JSON.stringify(invocationResult.output, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-gray-600 font-mono text-xs space-y-2">
                  <Wrench className="w-8 h-8 opacity-30" />
                  <span>Ready for tool execution. Configure parameters and click Invoke.</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 3: CONNECTED APPS ECOSYSTEM */}
        {/* ================================================================= */}
        {activeTab === 'apps' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {apps.map((app) => (
                <div key={app.app_id} className="bg-gray-950 border border-gray-800 rounded p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded bg-cyan-950 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
                        {app.app_id.includes('github') && <GitPullRequest className="w-4 h-4" />}
                        {app.app_id.includes('vercel') && <Zap className="w-4 h-4" />}
                        {app.app_id.includes('sqlite') && <Database className="w-4 h-4" />}
                        {app.app_id.includes('termux') && <Smartphone className="w-4 h-4" />}
                        {app.app_id.includes('system') && <Server className="w-4 h-4" />}
                      </div>
                      <div>
                        <h3 className="font-bold text-sm text-gray-200 font-mono">{app.name}</h3>
                        <p className="text-[11px] text-gray-500 font-mono">{app.category}</p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 text-xs font-mono rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> {app.status}
                    </span>
                  </div>

                  <p className="text-xs text-gray-400 leading-relaxed">{app.description}</p>

                  <div className="space-y-1 text-xs font-mono">
                    <div className="text-gray-500 text-[11px]">Capabilities:</div>
                    <div className="flex flex-wrap gap-1">
                      {app.capabilities.map((cap) => (
                        <span key={cap} className="px-1.5 py-0.5 rounded bg-gray-900 text-gray-300 border border-gray-800 text-[10px]">
                          {cap}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-gray-900 flex items-center justify-between">
                    <span className="text-[11px] font-mono text-gray-500">
                      Tools: <strong className="text-cyan-400">{app.tools_provided.length}</strong>
                    </span>
                    <button
                      onClick={() => handleTestApp(app.app_id)}
                      className="px-2.5 py-1 text-xs font-mono rounded bg-gray-900 hover:bg-gray-800 text-cyan-400 border border-gray-700 transition flex items-center gap-1"
                    >
                      <Activity className="w-3 h-3" /> Test App
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 4: MCP PROTOCOL & PLUGINS */}
        {/* ================================================================= */}
        {activeTab === 'mcp' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Register MCP Server Form */}
            <div className="bg-gray-950 border border-gray-800 rounded p-4 space-y-4">
              <h3 className="font-bold text-sm text-cyan-400 font-mono flex items-center gap-2">
                <Plus className="w-4 h-4 text-cyan-500" />
                REGISTER MCP SERVER
              </h3>
              <form onSubmit={handleAddMcpServer} className="space-y-3 font-mono text-xs">
                <div>
                  <label className="text-gray-400">Server Name:</label>
                  <input
                    type="text"
                    placeholder="e.g. Postgres MCP or Filesystem MCP"
                    value={mcpName}
                    onChange={(e) => setMcpName(e.target.value)}
                    className="w-full bg-black border border-gray-800 rounded p-2 text-gray-200 mt-1 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-gray-400">Transport:</label>
                  <select
                    value={mcpTransport}
                    onChange={(e: any) => setMcpTransport(e.target.value)}
                    className="w-full bg-black border border-gray-800 rounded p-2 text-gray-200 mt-1 focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="stdio">stdio (Local Subprocess)</option>
                    <option value="http">http (REST / JSON-RPC)</option>
                    <option value="sse">sse (Server-Sent Events)</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400">Command / URL:</label>
                  <input
                    type="text"
                    placeholder="npx -y @modelcontextprotocol/server-postgres or http://..."
                    value={mcpCommand}
                    onChange={(e) => setMcpCommand(e.target.value)}
                    className="w-full bg-black border border-gray-800 rounded p-2 text-gray-200 mt-1 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-2 bg-cyan-950 hover:bg-cyan-900 border border-cyan-600 text-cyan-300 font-bold rounded mt-2"
                >
                  CONNECT MCP SERVER
                </button>
              </form>
            </div>

            {/* Active MCP Servers */}
            <div className="lg:col-span-2 space-y-3">
              <h3 className="font-bold text-sm text-gray-300 font-mono">ACTIVE MODEL CONTEXT PROTOCOL (MCP) SERVERS</h3>
              {mcpServers.length === 0 ? (
                <div className="p-8 text-center bg-gray-950 border border-gray-800 rounded font-mono text-xs text-gray-500">
                  No external MCP servers configured. Register one using the form.
                </div>
              ) : (
                mcpServers.map((server) => (
                  <div key={server.server_id} className="p-4 bg-gray-950 border border-gray-800 rounded space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-cyan-400">{server.name}</span>
                      <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                        {server.status}
                      </span>
                    </div>
                    <p className="text-gray-400">{server.command_or_url}</p>
                    <div className="text-[11px] text-gray-500 flex items-center gap-4 pt-2">
                      <span>Transport: <strong className="text-gray-300">{server.transport}</strong></span>
                      <span>Latency: <strong className="text-gray-300">{server.latency_ms}ms</strong></span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* TAB 5: TELEMETRY & INVOCATION LOGS */}
        {/* ================================================================= */}
        {activeTab === 'telemetry' && telemetry && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="p-4 bg-gray-950 border border-gray-800 rounded font-mono">
                <span className="text-xs text-gray-400">Total Invocations</span>
                <p className="text-2xl font-bold text-cyan-400 mt-1">{telemetry.total_invocations}</p>
              </div>
              <div className="p-4 bg-gray-950 border border-gray-800 rounded font-mono">
                <span className="text-xs text-gray-400">Successful Invocations</span>
                <p className="text-2xl font-bold text-emerald-400 mt-1">{telemetry.successful_invocations}</p>
              </div>
              <div className="p-4 bg-gray-950 border border-gray-800 rounded font-mono">
                <span className="text-xs text-gray-400">Failed Invocations</span>
                <p className="text-2xl font-bold text-red-400 mt-1">{telemetry.failed_invocations}</p>
              </div>
              <div className="p-4 bg-gray-950 border border-gray-800 rounded font-mono">
                <span className="text-xs text-gray-400">Average Duration</span>
                <p className="text-2xl font-bold text-amber-400 mt-1">{telemetry.avg_latency_ms} ms</p>
              </div>
            </div>

            <div className="bg-gray-950 border border-gray-800 rounded p-4 space-y-3 font-mono text-xs">
              <h3 className="font-bold text-sm text-gray-200">RECENT TOOL INVOCATION AUDIT STREAM</h3>
              <div className="divide-y divide-gray-900 max-h-80 overflow-y-auto">
                {telemetry.recent_invocations.map((inv) => (
                  <div key={inv.invocation_id} className="py-2.5 flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        inv.status === 'SUCCESS' ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'
                      }`}>
                        {inv.status}
                      </span>
                      <strong className="text-cyan-300">{inv.tool_id}</strong>
                      <span className="text-gray-500">by {inv.caller_agent_id || 'system'}</span>
                    </div>
                    <div className="flex items-center gap-3 text-gray-400">
                      <span>{inv.duration_ms}ms</span>
                      <span className="text-gray-600">{inv.executed_at.split('T')[1]?.split('.')[0] || ''}</span>
                    </div>
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
