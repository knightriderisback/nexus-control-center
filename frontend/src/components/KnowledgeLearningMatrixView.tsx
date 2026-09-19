import React, { useState, useEffect } from 'react';
import {
  Brain,
  Search,
  Sparkles,
  Cpu,
  Layers,
  Zap,
  TrendingUp,
  RefreshCw,
  Tag,
  ShieldCheck,
  Check,
  Archive,
  Trash2,
  Eye,
  XCircle,
  ArrowRightCircle
} from 'lucide-react';
import type {
  KnowledgeNodeItem,
  LearningInsightItem,
  OptimizationRecommendationItem,
  ToolPerformanceMetricItem,
  KnowledgeTelemetryItem,
  DAGOptimizationPlanItem
} from '../types';
import { nexusFetch } from '../utils/api';

interface KnowledgeLearningMatrixViewProps {
  onNotify?: (msg: string, type: 'info' | 'success' | 'warning' | 'error') => void;
}

export const KnowledgeLearningMatrixView: React.FC<KnowledgeLearningMatrixViewProps> = ({ onNotify }) => {
  const [activeTab, setActiveTab] = useState<'nodes' | 'insights' | 'optimizer' | 'playground'>('nodes');
  const [telemetry, setTelemetry] = useState<KnowledgeTelemetryItem | null>(null);
  const [nodes, setNodes] = useState<KnowledgeNodeItem[]>([]);
  const [insights, setInsights] = useState<LearningInsightItem[]>([]);
  const [optimizations, setOptimizations] = useState<OptimizationRecommendationItem[]>([]);
  const [toolMetrics, setToolMetrics] = useState<ToolPerformanceMetricItem[]>([]);
  
  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTier, setSelectedTier] = useState<string>('ALL');
  const [selectedNode, setSelectedNode] = useState<KnowledgeNodeItem | null>(null);
  const [provenanceData, setProvenanceData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isSweeping, setIsSweeping] = useState<boolean>(false);
  const [isRevalidating, setIsRevalidating] = useState<boolean>(false);

  // Playground state
  const [promptQuery, setPromptQuery] = useState('Optimize database connection pooling with zero-cost invariants');
  const [tokenBudget, setTokenBudget] = useState(1500);
  const [optimizedContext, setOptimizedContext] = useState<string>('');
  const [tokensSaved, setTokensSaved] = useState<number>(0);
  const [isOptimizingPrompt, setIsOptimizingPrompt] = useState<boolean>(false);

  // DAG Optimizer state
  const [dagPlan, setDagPlan] = useState<DAGOptimizationPlanItem | null>(null);

  const fetchTelemetryAndData = async () => {
    setLoading(true);
    try {
      const [telRes, nodesRes, insRes, optRes, toolsRes] = await Promise.all([
        nexusFetch<KnowledgeTelemetryItem>('/api/v1/knowledge/telemetry'),
        nexusFetch<KnowledgeNodeItem[]>('/api/v1/knowledge/nodes'),
        nexusFetch<LearningInsightItem[]>('/api/v1/learning/insights'),
        nexusFetch<OptimizationRecommendationItem[]>('/api/v1/optimization/recommendations'),
        nexusFetch<ToolPerformanceMetricItem[]>('/api/v1/optimization/tools/performance')
      ]);

      if (telRes) setTelemetry(telRes);
      if (nodesRes) setNodes(nodesRes);
      if (insRes) setInsights(insRes);
      if (optRes) setOptimizations(optRes);
      if (toolsRes) setToolMetrics(toolsRes);
    } catch (err) {
      console.error('Failed to load knowledge telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetryAndData();
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      fetchTelemetryAndData();
      return;
    }
    setLoading(true);
    try {
      const url = `/api/v1/knowledge/search?q=${encodeURIComponent(searchQuery)}${selectedTier !== 'ALL' ? `&tier=${selectedTier}` : ''}`;
      const res = await nexusFetch<KnowledgeNodeItem[]>(url);
      if (res) {
        setNodes(res);
      }
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerSweep = async () => {
    setIsSweeping(true);
    try {
      const newIns = await nexusFetch<LearningInsightItem[]>('/api/v1/learning/sweep', { method: 'POST' });
      if (newIns) {
        if (onNotify) onNotify(`Learning sweep complete: distilled ${newIns.length} insights`, 'success');
        fetchTelemetryAndData();
      }
    } catch (err) {
      if (onNotify) onNotify('Learning sweep failed', 'error');
    } finally {
      setIsSweeping(false);
    }
  };

  const handleRevalidate = async () => {
    setIsRevalidating(true);
    try {
      const data = await nexusFetch<any>('/api/v1/knowledge/revalidate', { method: 'POST' });
      if (data) {
        if (onNotify) onNotify(`Revalidation complete: ${data.revalidated_nodes_count} checked, ${data.stale_nodes_count} flagged stale`, 'success');
        fetchTelemetryAndData();
      }
    } catch (err) {
      if (onNotify) onNotify('Revalidation failed', 'error');
    } finally {
      setIsRevalidating(false);
    }
  };

  const handleArchiveNode = async (nodeId: string) => {
    try {
      await nexusFetch(`/api/v1/knowledge/${nodeId}/archive`, { method: 'POST' });
      if (onNotify) onNotify(`Node '${nodeId}' archived`, 'info');
      fetchTelemetryAndData();
    } catch (err) {
      if (onNotify) onNotify('Archive failed', 'error');
    }
  };

  const handleRetireNode = async (nodeId: string) => {
    try {
      await nexusFetch(`/api/v1/knowledge/${nodeId}/retire`, { method: 'POST' });
      if (onNotify) onNotify(`Node '${nodeId}' retired`, 'warning');
      fetchTelemetryAndData();
    } catch (err) {
      if (onNotify) onNotify('Retire failed', 'error');
    }
  };

  const handleInspectProvenance = async (itemId: string) => {
    try {
      const data = await nexusFetch(`/api/v1/knowledge/provenance/${itemId}`);
      if (data) {
        setProvenanceData(data);
      }
    } catch (err) {
      if (onNotify) onNotify('Failed to fetch provenance', 'error');
    }
  };

  const handleAcceptOptimization = async (optId: string) => {
    try {
      await nexusFetch(`/api/v1/optimization/${optId}/accept`, { method: 'POST' });
      if (onNotify) onNotify(`Optimization '${optId}' accepted and applied`, 'success');
      fetchTelemetryAndData();
    } catch (err) {
      if (onNotify) onNotify('Accept optimization failed', 'error');
    }
  };

  const handleRejectOptimization = async (optId: string) => {
    try {
      await nexusFetch(`/api/v1/optimization/${optId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Rejected by operator in Cyber-HUD' })
      });
      if (onNotify) onNotify(`Optimization '${optId}' rejected`, 'info');
      fetchTelemetryAndData();
    } catch (err) {
      if (onNotify) onNotify('Reject optimization failed', 'error');
    }
  };

  const handleCreateGovernedMission = async (optId: string) => {
    try {
      const proposal = await nexusFetch<any>(`/api/v1/optimization/${optId}/govern`, { method: 'POST' });
      if (proposal) {
        if (onNotify) onNotify(`Created governed mission proposal: ${proposal.proposal_id}`, 'success');
        fetchTelemetryAndData();
      }
    } catch (err) {
      if (onNotify) onNotify('Failed to create governed mission proposal', 'error');
    }
  };

  const handleOptimizePrompt = async () => {
    setIsOptimizingPrompt(true);
    try {
      const data = await nexusFetch<any>('/api/v1/knowledge/optimize-context', {
        method: 'POST',
        body: JSON.stringify({
          query_context: promptQuery,
          max_token_budget: tokenBudget,
          target_agent_role: 'Engineer'
        })
      });
      if (data) {
        setOptimizedContext(data.optimized_context);
        setTokensSaved(data.tokens_saved);
        if (onNotify) onNotify(`Context optimized! Saved approx ${data.tokens_saved} tokens`, 'success');
      }
    } catch (err) {
      if (onNotify) onNotify('Prompt context optimization failed', 'error');
    } finally {
      setIsOptimizingPrompt(false);
    }
  };

  const handleRunDagOptimizerDemo = async () => {
    try {
      const demoSubtasks = [
        { subtask_id: 'task-1-schema', dependencies: [] },
        { subtask_id: 'task-2-models', dependencies: ['task-1-schema'] },
        { subtask_id: 'task-3-router', dependencies: ['task-1-schema'] },
        { subtask_id: 'task-4-frontend', dependencies: ['task-2-models', 'task-3-router'] },
        { subtask_id: 'task-5-tests', dependencies: ['task-2-models', 'task-3-router'] },
        { subtask_id: 'task-6-deploy', dependencies: ['task-4-frontend', 'task-5-tests'] }
      ];
      const plan = await nexusFetch<any>('/api/v1/optimization/recommendations/dag', {
        method: 'POST',
        body: JSON.stringify({
          mission_id: 'demo-mission-dag',
          subtasks: demoSubtasks
        })
      });
      if (plan) {
        setDagPlan(plan);
        if (onNotify) onNotify(`DAG optimized: ${plan.estimated_speedup_percent}% critical path speedup`, 'success');
        fetchTelemetryAndData();
      }
    } catch (err) {
      if (onNotify) onNotify('DAG optimization failed', 'error');
    }
  };

  const filteredNodes = nodes.filter(n => {
    if (selectedTier !== 'ALL' && n.tier !== selectedTier) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full bg-[#0d1117] text-gray-200 font-sans p-4 space-y-4 overflow-y-auto">
      {/* 1. Header Telemetry Scorecard */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/40 rounded-lg text-indigo-400">
              <Brain className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-bold text-white tracking-wide">Autonomous Knowledge & Learning Control Plane</h2>
                <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800/60 rounded">
                  ZERO-COST FINOPS $0.00
                </span>
              </div>
              <p className="text-xs text-gray-400">Continuous Distillation • Multi-Tier Knowledge Graph • Strategy Optimization</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleRevalidate}
              disabled={isRevalidating}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRevalidating ? 'animate-spin' : ''}`} />
              <span>{isRevalidating ? 'Revalidating...' : 'Revalidate Knowledge'}</span>
            </button>
            <button
              onClick={handleTriggerSweep}
              disabled={isSweeping}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSweeping ? 'animate-spin' : ''}`} />
              <span>{isSweeping ? 'Sweeping Subsystems...' : 'Trigger Learning Sweep'}</span>
            </button>
            <button
              onClick={fetchTelemetryAndData}
              className="p-1.5 text-gray-400 hover:text-white bg-[#21262d] border border-[#30363d] rounded-lg transition-colors"
              title="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 mt-4">
          <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3">
            <div className="text-[11px] text-gray-400 flex items-center space-x-1">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Knowledge Score</span>
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {telemetry ? `${telemetry.knowledge_health_score.toFixed(1)}%` : '--'}
            </div>
            <div className="text-[10px] text-emerald-400 mt-0.5">Active Invariant</div>
          </div>

          <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3">
            <div className="text-[11px] text-gray-400 flex items-center space-x-1">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span>Total Nodes</span>
            </div>
            <div className="text-xl font-bold text-white mt-1">
              {telemetry ? telemetry.total_nodes : nodes.length}
            </div>
            <div className="text-[10px] text-purple-300 mt-0.5">Multi-Tier Graph</div>
          </div>

          <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3">
            <div className="text-[11px] text-gray-400 flex items-center space-x-1">
              <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
              <span>Learned Insights</span>
            </div>
            <div className="text-xl font-bold text-cyan-400 mt-1">
              {telemetry ? telemetry.total_insights : insights.length}
            </div>
            <div className="text-[10px] text-cyan-300 mt-0.5">Distilled Patterns</div>
          </div>

          <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3">
            <div className="text-[11px] text-gray-400 flex items-center space-x-1">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Optimizations</span>
            </div>
            <div className="text-xl font-bold text-amber-400 mt-1">
              {telemetry ? telemetry.active_optimizations : optimizations.length}
            </div>
            <div className="text-[10px] text-amber-300 mt-0.5">Active Proposals</div>
          </div>

          <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3">
            <div className="text-[11px] text-gray-400 flex items-center space-x-1">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              <span>Search Latency</span>
            </div>
            <div className="text-xl font-bold text-emerald-400 mt-1">
              {telemetry ? `${telemetry.average_retrieval_latency_ms}ms` : '<1ms'}
            </div>
            <div className="text-[10px] text-emerald-300 mt-0.5">Local BM25 + Index</div>
          </div>

          <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3">
            <div className="text-[11px] text-gray-400 flex items-center space-x-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>FinOps Spend</span>
            </div>
            <div className="text-xl font-bold text-emerald-400 mt-1">$0.00</div>
            <div className="text-[10px] text-emerald-300 mt-0.5">Zero-Cost Sealed</div>
          </div>
        </div>
      </div>

      {/* 2. Navigation Tabs */}
      <div className="flex border-b border-[#30363d] space-x-4 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('nodes')}
          className={`pb-2.5 px-1 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'nodes'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Knowledge Graph ({nodes.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('insights')}
          className={`pb-2.5 px-1 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'insights'
              ? 'border-purple-500 text-purple-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Autonomous Learning Insights ({insights.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('optimizer')}
          className={`pb-2.5 px-1 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'optimizer'
              ? 'border-amber-500 text-amber-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Zap className="w-4 h-4" />
          <span>Strategy & DAG Optimizer ({optimizations.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('playground')}
          className={`pb-2.5 px-1 flex items-center space-x-2 border-b-2 transition-colors ${
            activeTab === 'playground'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Context Optimizer Playground</span>
        </button>
      </div>

      {/* TAB 1: KNOWLEDGE GRAPH & HYBRID SEARCH */}
      {activeTab === 'nodes' && (
        <div className="space-y-4">
          {/* Search Bar & Tier Filter */}
          <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[240px]">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search knowledge by keyword, pattern, tag, or semantic description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#161b22] border border-[#30363d] rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center space-x-1 bg-[#161b22] border border-[#30363d] rounded-lg p-1 text-xs">
              {['ALL', 'PROCEDURAL', 'SEMANTIC', 'EPISODIC', 'META'].map((tier) => (
                <button
                  key={tier}
                  type="button"
                  onClick={() => setSelectedTier(tier)}
                  className={`px-2.5 py-1 rounded font-medium transition-colors ${
                    selectedTier === tier
                      ? 'bg-indigo-600 text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {tier}
                </button>
              ))}
            </div>

            <button
              type="submit"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors"
            >
              Search
            </button>
          </form>

          {/* Nodes Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredNodes.map((node) => (
              <div
                key={node.node_id}
                className="bg-[#161b22] border border-[#30363d] hover:border-indigo-500/60 rounded-xl p-4 flex flex-col justify-between space-y-3 transition-colors shadow"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                      node.tier === 'PROCEDURAL' ? 'bg-indigo-950 text-indigo-400 border-indigo-800' :
                      node.tier === 'SEMANTIC' ? 'bg-purple-950 text-purple-400 border-purple-800' :
                      node.tier === 'EPISODIC' ? 'bg-cyan-950 text-cyan-400 border-cyan-800' :
                      'bg-gray-800 text-gray-300 border-gray-700'
                    }`}>
                      {node.tier}
                    </span>
                    <div className="flex items-center space-x-1.5">
                      <span className="text-[10px] font-mono text-gray-400">{node.node_id}</span>
                      {node.status && node.status !== 'ACTIVE' && (
                        <span className="px-1.5 py-0.2 text-[9px] font-bold bg-amber-950 text-amber-400 rounded">
                          {node.status}
                        </span>
                      )}
                    </div>
                  </div>

                  <h4 className="text-sm font-bold text-white line-clamp-1">{node.title}</h4>
                  <p className="text-xs text-gray-300 line-clamp-3 leading-relaxed">{node.content}</p>
                </div>

                <div className="space-y-2 pt-2 border-t border-[#30363d]/60">
                  {node.tags && node.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {node.tags.slice(0, 3).map((tag, idx) => (
                        <span key={idx} className="bg-[#0d1117] text-gray-400 px-1.5 py-0.5 rounded text-[10px] flex items-center space-x-1">
                          <Tag className="w-2.5 h-2.5 text-indigo-400" />
                          <span>{tag}</span>
                        </span>
                      ))}
                      {node.tags.length > 3 && (
                        <span className="text-[10px] text-gray-500">+{node.tags.length - 3}</span>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-gray-400 pt-1">
                    <span className="text-emerald-400 font-semibold">{node.confidence} Confidence</span>
                    <div className="flex items-center space-x-1.5">
                      <button
                        onClick={() => handleInspectProvenance(node.node_id)}
                        className="p-1 hover:text-cyan-400"
                        title="Inspect Provenance"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleArchiveNode(node.node_id)}
                        className="p-1 hover:text-amber-400"
                        title="Archive Node"
                      >
                        <Archive className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleRetireNode(node.node_id)}
                        className="p-1 hover:text-red-400"
                        title="Retire Node"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setSelectedNode(node)}
                        className="text-indigo-400 hover:text-indigo-300 font-semibold text-xs ml-1"
                      >
                        Details →
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: AUTONOMOUS LEARNING INSIGHTS */}
      {activeTab === 'insights' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-purple-400" />
              <span>Cross-Subsystem Continuous Learning Distillations</span>
            </h3>
            <span className="text-xs text-gray-400">Total Insights: {insights.length}</span>
          </div>

          <div className="space-y-3">
            {insights.map((ins) => (
              <div key={ins.insight_id} className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-purple-950 text-purple-400 border border-purple-800 rounded">
                      {ins.category}
                    </span>
                    <h4 className="text-sm font-bold text-white">{ins.title}</h4>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 rounded">
                      Recurrence: {ins.recurrence_count}
                    </span>
                    <button
                      onClick={() => handleInspectProvenance(ins.insight_id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Provenance</span>
                    </button>
                  </div>
                </div>

                <div className="bg-[#0d1117] p-3 rounded-lg border border-[#30363d] space-y-2 text-xs">
                  <div>
                    <span className="text-gray-400 font-semibold">Observed Pattern: </span>
                    <span className="text-gray-200">{ins.pattern}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 font-semibold">Engineering Rationale: </span>
                    <span className="text-gray-300">{ins.rationale}</span>
                  </div>
                  <div>
                    <span className="text-emerald-400 font-semibold">Recommended Action: </span>
                    <span className="text-emerald-300">{ins.recommended_action}</span>
                  </div>
                </div>

                {ins.supporting_evidence && ins.supporting_evidence.length > 0 && (
                  <div className="text-[11px] text-gray-400 flex flex-wrap gap-2">
                    <span className="font-semibold text-gray-300">Evidence:</span>
                    {ins.supporting_evidence.map((ev, idx) => (
                      <span key={idx} className="bg-[#0d1117] px-2 py-0.5 rounded border border-[#30363d] text-gray-300 font-mono text-[10px]">
                        {ev}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: STRATEGY & DAG OPTIMIZER (SECTION 20 & 21) */}
      {activeTab === 'optimizer' && (
        <div className="flex flex-col space-y-4">
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <span>Autonomous Mission DAG Topology Optimizer</span>
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">Topological dependency analysis & critical path wave compression</p>
              </div>
              <button
                onClick={handleRunDagOptimizerDemo}
                className="px-3 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
              >
                Run DAG Analysis Demo
              </button>
            </div>

            {dagPlan && (
              <div className="mt-4 bg-[#0d1117] border border-emerald-500/40 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-emerald-400 font-bold">Estimated Critical Path Speedup: {dagPlan.estimated_speedup_percent}%</span>
                  <span className="text-gray-400">Sequential: {dagPlan.original_step_count} steps ➔ Parallel: {dagPlan.critical_path_length} waves</span>
                </div>
                <div className="space-y-1.5 mt-2">
                  {dagPlan.parallelizable_groups.map((group, idx) => (
                    <div key={idx} className="flex items-center space-x-2 text-xs bg-[#161b22] p-2 rounded border border-[#30363d]">
                      <span className="px-1.5 py-0.5 text-[10px] bg-indigo-950 text-indigo-400 rounded font-mono font-bold">Wave {idx + 1}</span>
                      <span className="text-gray-300">Parallel Tasks: {group.join(', ')}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Active Optimization Recommendations (Full 9 attributes - Section 20) */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-white">Active Optimization Proposals & Advisor</h4>
            {optimizations.map((opt) => (
              <div key={opt.recommendation_id} className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-800 rounded">
                      {opt.target_domain}
                    </span>
                    <h5 className="text-sm font-bold text-white">{opt.title}</h5>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${
                      opt.status === 'APPLIED' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' :
                      opt.status === 'REJECTED' ? 'bg-red-950 text-red-400 border-red-800' :
                      'bg-gray-800 text-gray-400 border-gray-700'
                    }`}>
                      {opt.status}
                    </span>
                    <button
                      onClick={() => handleInspectProvenance(opt.recommendation_id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Trace</span>
                    </button>
                  </div>
                </div>

                <p className="text-xs text-gray-300">{opt.description}</p>

                {/* Section 20 Complete 9 Attributes Breakdown */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs bg-[#0d1117] p-3 rounded-lg border border-[#30363d]">
                  <div>
                    <span className="text-gray-400 font-semibold block text-[10px]">WHY</span>
                    <span className="text-gray-200 text-xs">{opt.why || opt.description}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 font-semibold block text-[10px]">CONFIDENCE</span>
                    <span className="text-indigo-400 font-bold text-xs">{opt.confidence}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 font-semibold block text-[10px]">SCOPE & RISK</span>
                    <span className="text-gray-200 text-xs">{opt.scope || 'LOCAL'} • Risk: {opt.risk || 'LOW'}</span>
                  </div>
                  <div>
                    <span className="text-gray-400 font-semibold block text-[10px]">REVERSIBILITY</span>
                    <span className="text-emerald-400 text-xs">{opt.reversibility || 'HIGH'} (Approval: {opt.approval_required ? 'YES' : 'NO'})</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-[#0d1117] p-2.5 rounded border border-[#30363d]">
                  <div><span className="text-gray-400 font-semibold">Baseline: </span><span className="text-gray-200">{opt.baseline_metric}</span></div>
                  <div><span className="text-emerald-400 font-semibold">Projected: </span><span className="text-emerald-200">{opt.projected_metric}</span></div>
                </div>

                {/* Section 20 Action Controls */}
                <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-[#30363d]">
                  {opt.status === 'PROPOSED' && (
                    <>
                      <button
                        onClick={() => handleCreateGovernedMission(opt.recommendation_id)}
                        className="px-3 py-1 text-xs font-semibold bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 rounded transition-colors flex items-center space-x-1"
                      >
                        <ArrowRightCircle className="w-3.5 h-3.5" />
                        <span>Create Governed Mission</span>
                      </button>
                      <button
                        onClick={() => handleRejectOptimization(opt.recommendation_id)}
                        className="px-3 py-1 text-xs font-semibold bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/40 rounded transition-colors flex items-center space-x-1"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                      <button
                        onClick={() => handleAcceptOptimization(opt.recommendation_id)}
                        className="px-3 py-1 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded transition-colors flex items-center space-x-1"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Accept Recommendation</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Universal Tool Performance Metrics */}
          {toolMetrics.length > 0 && (
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 space-y-3">
              <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <span>Universal Tool Performance & Latency Metrics</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {toolMetrics.map((tm) => (
                  <div key={tm.tool_id} className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white font-mono">{tm.tool_id}</span>
                      <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded ${
                        tm.reliability_tier === 'HIGH' ? 'bg-emerald-950 text-emerald-400' : 'bg-amber-950 text-amber-400'
                      }`}>
                        {tm.reliability_tier}
                      </span>
                    </div>
                    <div className="text-gray-400">Invocations: {tm.total_invocations} | Success: {tm.success_rate_percent}%</div>
                    <div className="text-gray-400">Latency: P50 {tm.p50_latency_ms}ms | P95 {tm.p95_latency_ms}ms</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: CONTEXT OPTIMIZER PLAYGROUND */}
      {activeTab === 'playground' && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Context & Prompt Token Optimizer Playground</span>
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">Tests zero-cost distillation of few-shot patterns and architectural context</p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-400 font-semibold block mb-1">Agent Query / Mission Objective</label>
              <textarea
                value={promptQuery}
                onChange={(e) => setPromptQuery(e.target.value)}
                rows={3}
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex-1">
                <label className="text-xs text-gray-400 font-semibold block mb-1">
                  Token Budget Ceiling: <span className="text-cyan-400 font-bold">{tokenBudget} tokens</span>
                </label>
                <input
                  type="range"
                  min="500"
                  max="4000"
                  step="250"
                  value={tokenBudget}
                  onChange={(e) => setTokenBudget(parseInt(e.target.value))}
                  className="w-full accent-cyan-500"
                />
              </div>
              <button
                onClick={handleOptimizePrompt}
                disabled={isOptimizingPrompt}
                className="px-4 py-2 text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors disabled:opacity-50 mt-4"
              >
                {isOptimizingPrompt ? 'Distilling Context...' : 'Optimize Prompt Context'}
              </button>
            </div>

            {optimizedContext && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-emerald-400 font-bold flex items-center space-x-1">
                    <Check className="w-3.5 h-3.5" />
                    <span>Distilled Context Ready (Saved ~{tokensSaved} tokens)</span>
                  </span>
                </div>
                <pre className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3 text-xs text-cyan-300 font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
                  {optimizedContext}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Detail Modal for Selected Knowledge Node */}
      {selectedNode && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-[#30363d]">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 text-xs font-bold bg-indigo-950 text-indigo-400 border border-indigo-800 rounded">
                  {selectedNode.tier}
                </span>
                <h3 className="text-base font-bold text-white">{selectedNode.title}</h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-4 text-xs">
              <div>
                <span className="text-gray-400 font-semibold block mb-1">Knowledge Content:</span>
                <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-3 text-gray-200 whitespace-pre-wrap leading-relaxed">
                  {selectedNode.content}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#0d1117] p-2.5 rounded border border-[#30363d]">
                  <span className="text-gray-400 font-semibold block">Category</span>
                  <span className="text-white font-bold">{selectedNode.category}</span>
                </div>
                <div className="bg-[#0d1117] p-2.5 rounded border border-[#30363d]">
                  <span className="text-gray-400 font-semibold block">Fingerprint</span>
                  <span className="text-indigo-400 font-mono">{selectedNode.fingerprint}</span>
                </div>
              </div>

              {selectedNode.tags && selectedNode.tags.length > 0 && (
                <div>
                  <span className="text-gray-400 font-semibold block mb-1">Semantic Tags:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedNode.tags.map((t, idx) => (
                      <span key={idx} className="bg-[#21262d] text-indigo-300 px-2 py-0.5 rounded text-[11px] flex items-center space-x-1">
                        <Tag className="w-3 h-3" />
                        <span>{t}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end p-4 border-t border-[#30363d]">
              <button
                onClick={() => setSelectedNode(null)}
                className="px-4 py-1.5 bg-[#21262d] hover:bg-[#30363d] text-white rounded-lg text-xs font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provenance Trace Modal (Section 19 & 20) */}
      {provenanceData && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-[#30363d]">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 text-xs font-bold bg-cyan-950 text-cyan-400 border border-cyan-800 rounded">
                  {provenanceData.item_type}
                </span>
                <h3 className="text-base font-bold text-white">Provenance Trace & Evidence</h3>
              </div>
              <button
                onClick={() => setProvenanceData(null)}
                className="text-gray-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-4 text-xs">
              <div className="bg-[#0d1117] p-3 rounded-lg border border-[#30363d] space-y-2">
                <div className="text-gray-300 font-bold text-sm">{provenanceData.title}</div>
                <div className="text-gray-400">ID: <span className="font-mono text-cyan-300">{provenanceData.item_id}</span></div>
                {provenanceData.fingerprint && (
                  <div className="text-gray-400">Fingerprint: <span className="font-mono text-indigo-300">{provenanceData.fingerprint}</span></div>
                )}
                {provenanceData.why && (
                  <div className="text-gray-300"><span className="text-gray-400 font-semibold">Why: </span>{provenanceData.why}</div>
                )}
              </div>

              <div className="space-y-1">
                <span className="text-gray-400 font-semibold">Traceability Chain:</span>
                <div className="bg-[#0d1117] p-3 rounded border border-[#30363d] space-y-1 font-mono text-[11px] text-gray-300">
                  <div>Created At: {provenanceData.created_at}</div>
                  {provenanceData.updated_at && <div>Updated At: {provenanceData.updated_at}</div>}
                  {provenanceData.source_mission_id && <div>Source Mission: {provenanceData.source_mission_id}</div>}
                  {provenanceData.source_incident_id && <div>Source Incident: {provenanceData.source_incident_id}</div>}
                  {provenanceData.source_finding_id && <div>Source Finding: {provenanceData.source_finding_id}</div>}
                  {provenanceData.status && <div>Current Status: {provenanceData.status}</div>}
                </div>
              </div>
            </div>

            <div className="flex justify-end p-4 border-t border-[#30363d]">
              <button
                onClick={() => setProvenanceData(null)}
                className="px-4 py-1.5 bg-[#21262d] hover:bg-[#30363d] text-white rounded-lg text-xs font-semibold transition-colors"
              >
                Close Trace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
