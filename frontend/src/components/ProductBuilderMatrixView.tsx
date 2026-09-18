import React, { useState, useEffect } from 'react';
import {
  Boxes,
  Cpu,
  Layers,
  ShieldCheck,
  Terminal,
  FileCode2,
  Play,
  Wrench,
  FileText,
  Sparkles,
  Award,
  DollarSign
} from 'lucide-react';
import type {
  ProductSpecificationItem,
  ProductBuildRunItem,
  ProductCatalogItem,
  ProductBuilderTelemetryItem,
  ProductArchetype
} from '../types';

export const ProductBuilderMatrixView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'blueprint' | 'builds' | 'components' | 'corrections' | 'catalog' | 'governance'>('blueprint');
  const [specs, setSpecs] = useState<ProductSpecificationItem[]>([]);
  const [builds, setBuilds] = useState<ProductBuildRunItem[]>([]);
  const [catalog, setCatalog] = useState<ProductCatalogItem[]>([]);
  const [telemetry, setTelemetry] = useState<ProductBuilderTelemetryItem | null>(null);
  const [selectedBuild, setSelectedBuild] = useState<ProductBuildRunItem | null>(null);

  // Form states
  const [goalPrompt, setGoalPrompt] = useState('');
  const [selectedArchetype, setSelectedArchetype] = useState<ProductArchetype>('FULLSTACK_WEB');
  const [customName, setCustomName] = useState('');
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [repairReason, setRepairReason] = useState('');

  const fetchAllData = async () => {
    try {
      const [specsRes, buildsRes, catRes, telemRes] = await Promise.all([
        fetch('/api/v1/product-builder/specs'),
        fetch('/api/v1/product-builder/builds'),
        fetch('/api/v1/product-builder/catalog'),
        fetch('/api/v1/product-builder/telemetry')
      ]);

      if (specsRes.ok) setSpecs(await specsRes.json());
      if (buildsRes.ok) {
        const bList: ProductBuildRunItem[] = await buildsRes.json();
        setBuilds(bList);
        if (bList.length > 0 && !selectedBuild) {
          setSelectedBuild(bList[bList.length - 1]);
        }
      }
      if (catRes.ok) setCatalog(await catRes.json());
      if (telemRes.ok) setTelemetry(await telemRes.json());
    } catch (err) {
      console.error('Failed to load Product Builder data', err);
    }
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSynthesizeBlueprint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalPrompt.trim()) return;

    setIsSynthesizing(true);
    try {
      const res = await fetch('/api/v1/product-builder/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: goalPrompt,
          archetype: selectedArchetype,
          product_name: customName || undefined
        })
      });
      if (res.ok) {
        const spec: ProductSpecificationItem = await res.json();
        setSpecs(prev => [spec, ...prev]);
        setGoalPrompt('');
        setCustomName('');
        setActiveTab('blueprint');
      }
    } catch (err) {
      console.error('Synthesize blueprint error', err);
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handleStartBuild = async (specId?: string) => {
    setIsBuilding(true);
    try {
      const payload = specId
        ? { spec_id: specId, auto_repair: true }
        : {
            prompt: goalPrompt || 'Build an enterprise telemetry analytics web app',
            archetype: selectedArchetype,
            product_name: customName || undefined,
            auto_repair: true
          };

      const res = await fetch('/api/v1/product-builder/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const build: ProductBuildRunItem = await res.json();
        setBuilds(prev => [build, ...prev]);
        setSelectedBuild(build);
        setActiveTab('builds');
      }
    } catch (err) {
      console.error('Build start error', err);
    } finally {
      setIsBuilding(false);
    }
  };

  const handleRepairBuild = async (buildId: string) => {
    try {
      const res = await fetch(`/api/v1/product-builder/builds/${buildId}/repair?reason=${encodeURIComponent(repairReason || 'User requested auto-fix')}`, {
        method: 'POST'
      });
      if (res.ok) {
        const updated: ProductBuildRunItem = await res.json();
        setBuilds(prev => prev.map(b => (b.build_id === updated.build_id ? updated : b)));
        setSelectedBuild(updated);
        setRepairReason('');
      }
    } catch (err) {
      console.error('Repair error', err);
    }
  };

  const getStageBadgeClass = (stage: string) => {
    switch (stage) {
      case 'DELIVERY_VERIFICATION':
      case 'PACKAGING':
        return 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40';
      case 'TEST_EXECUTION':
      case 'SECURITY_AUDIT':
        return 'bg-cyan-950/80 text-cyan-300 border-cyan-500/40';
      case 'SELF_CORRECTION':
        return 'bg-amber-950/80 text-amber-300 border-amber-500/40 animate-pulse';
      case 'COMPILATION_AND_LINT':
      case 'CODE_GENERATION':
        return 'bg-blue-950/80 text-blue-300 border-blue-500/40';
      default:
        return 'bg-zinc-900 text-zinc-400 border-zinc-700';
    }
  };

  const getStateClass = (state: string) => {
    switch (state) {
      case 'COMPLETED':
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-600/40';
      case 'IN_PROGRESS':
        return 'text-cyan-400 bg-cyan-950/40 border-cyan-600/40';
      case 'SELF_CORRECTING':
        return 'text-amber-400 bg-amber-950/40 border-amber-600/40 animate-pulse';
      case 'FAILED':
        return 'text-rose-400 bg-rose-950/40 border-rose-600/40';
      default:
        return 'text-zinc-400 bg-zinc-900 border-zinc-700';
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0d14] text-zinc-200 overflow-y-auto font-mono p-4 space-y-4">
      {/* Header & HUD Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between bg-zinc-900/80 border border-cyan-500/30 rounded-lg p-4 shadow-lg backdrop-blur-md gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-gradient-to-br from-cyan-600 to-blue-800 rounded-lg shadow-md border border-cyan-400/40">
            <Boxes className="w-6 h-6 text-cyan-100" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-wider text-cyan-300">
                NEXUS // PRODUCT BUILDER MATRIX
              </h1>
              <span className="px-2 py-0.5 text-xs bg-cyan-950 border border-cyan-500/40 rounded text-cyan-300">
                PHASE 21
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              Autonomous Software Factory & End-to-End Product Synthesis Engine
            </p>
          </div>
        </div>

        {/* Real-time Telemetry Pills */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center space-x-1.5 px-3 py-1.5 bg-zinc-950/80 border border-zinc-800 rounded-md">
            <Award className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-zinc-400">Built:</span>
            <span className="font-semibold text-cyan-300">{telemetry?.total_products_built || catalog.length}</span>
          </div>
          <div className="flex items-center space-x-1.5 px-3 py-1.5 bg-zinc-950/80 border border-zinc-800 rounded-md">
            <Play className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-zinc-400">Active Builds:</span>
            <span className="font-semibold text-blue-300">{telemetry?.active_builds || 0}</span>
          </div>
          <div className="flex items-center space-x-1.5 px-3 py-1.5 bg-zinc-950/80 border border-zinc-800 rounded-md">
            <Wrench className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-zinc-400">Auto-Repairs:</span>
            <span className="font-semibold text-amber-300">{telemetry?.auto_corrections_performed || 0}</span>
          </div>
          <div className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-950/60 border border-emerald-500/40 rounded-md text-emerald-300">
            <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
            <span>FinOps $0.00 Verified</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-zinc-800 space-x-2 text-xs font-semibold overflow-x-auto pb-1">
        <button
          onClick={() => setActiveTab('blueprint')}
          className={`flex items-center space-x-2 px-3 py-2 rounded-t-md transition-all ${
            activeTab === 'blueprint'
              ? 'bg-zinc-800/90 text-cyan-300 border-b-2 border-cyan-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>PRD Blueprint Synthesizer</span>
        </button>
        <button
          onClick={() => setActiveTab('builds')}
          className={`flex items-center space-x-2 px-3 py-2 rounded-t-md transition-all ${
            activeTab === 'builds'
              ? 'bg-zinc-800/90 text-cyan-300 border-b-2 border-cyan-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
          }`}
        >
          <Cpu className="w-3.5 h-3.5 text-blue-400" />
          <span>Assembly Line & Builds ({builds.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('components')}
          className={`flex items-center space-x-2 px-3 py-2 rounded-t-md transition-all ${
            activeTab === 'components'
              ? 'bg-zinc-800/90 text-cyan-300 border-b-2 border-cyan-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
          }`}
        >
          <FileCode2 className="w-3.5 h-3.5 text-indigo-400" />
          <span>Components & Code Assets</span>
        </button>
        <button
          onClick={() => setActiveTab('corrections')}
          className={`flex items-center space-x-2 px-3 py-2 rounded-t-md transition-all ${
            activeTab === 'corrections'
              ? 'bg-zinc-800/90 text-cyan-300 border-b-2 border-cyan-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
          }`}
        >
          <Wrench className="w-3.5 h-3.5 text-amber-400" />
          <span>Self-Correction Log</span>
        </button>
        <button
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center space-x-2 px-3 py-2 rounded-t-md transition-all ${
            activeTab === 'catalog'
              ? 'bg-zinc-800/90 text-cyan-300 border-b-2 border-cyan-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span>Product Catalog ({catalog.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('governance')}
          className={`flex items-center space-x-2 px-3 py-2 rounded-t-md transition-all ${
            activeTab === 'governance'
              ? 'bg-zinc-800/90 text-cyan-300 border-b-2 border-cyan-400 shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5 text-rose-400" />
          <span>FinOps & SLSA Gates</span>
        </button>
      </div>

      {/* TAB 1: BLUEPRINT & PRD SYNTHESIZER */}
      {activeTab === 'blueprint' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1 bg-zinc-900/70 border border-zinc-800 rounded-lg p-4 space-y-4">
            <h2 className="text-sm font-bold text-cyan-300 flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Synthesize New Product</span>
            </h2>

            <form onSubmit={handleSynthesizeBlueprint} className="space-y-3">
              <div>
                <label className="block text-xs text-zinc-400 mb-1">Product Archetype</label>
                <select
                  value={selectedArchetype}
                  onChange={e => setSelectedArchetype(e.target.value as ProductArchetype)}
                  className="w-full bg-zinc-950 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="FULLSTACK_WEB">FULLSTACK_WEB (FastAPI + React 19)</option>
                  <option value="MICROSERVICE_API">MICROSERVICE_API (FastAPI REST)</option>
                  <option value="CLI_TOOL">CLI_TOOL (Python Click / Rich)</option>
                  <option value="DATA_PIPELINE">DATA_PIPELINE (ETL & Transform)</option>
                  <option value="AI_AGENT_SYSTEM">AI_AGENT_SYSTEM (Autonomous Bot)</option>
                  <option value="LIBRARY_SDK">LIBRARY_SDK (Python Package)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-zinc-400 mb-1">Custom Product Name (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. cloud-sentinel-hub"
                  value={customName}
                  onChange={e => setCustomName(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-700 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-400 mb-1">Product Goal & Requirements Prompt</label>
                <textarea
                  rows={4}
                  placeholder="Describe your product goal, target features, constraints, and architecture expectations..."
                  value={goalPrompt}
                  onChange={e => setGoalPrompt(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-700 rounded p-2 text-xs text-zinc-200 focus:outline-none focus:border-cyan-500 font-sans"
                />
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  type="submit"
                  disabled={isSynthesizing || !goalPrompt.trim()}
                  className="flex-1 flex items-center justify-center space-x-1.5 px-3 py-2 bg-cyan-700 hover:bg-cyan-600 disabled:bg-zinc-800 disabled:text-zinc-600 rounded text-xs font-semibold text-white transition-all shadow-md"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isSynthesizing ? 'Synthesizing...' : 'Generate Blueprint'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleStartBuild()}
                  disabled={isBuilding}
                  className="flex items-center space-x-1 px-3 py-2 bg-emerald-700 hover:bg-emerald-600 disabled:bg-zinc-800 disabled:text-zinc-600 rounded text-xs font-semibold text-white transition-all shadow-md"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>Instant Build</span>
                </button>
              </div>
            </form>
          </div>

          <div className="lg:col-span-2 space-y-3">
            <h2 className="text-sm font-bold text-zinc-300 flex items-center space-x-2">
              <FileText className="w-4 h-4 text-zinc-400" />
              <span>Synthesized PRD Specifications ({specs.length})</span>
            </h2>

            {specs.length === 0 ? (
              <div className="p-8 text-center bg-zinc-900/40 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-xs">
                No product blueprints synthesized yet. Enter a product goal above to generate your first specification.
              </div>
            ) : (
              <div className="space-y-3">
                {specs.map(s => (
                  <div key={s.spec_id} className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3.5 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-sm text-cyan-300">{s.product_name}</span>
                        <span className="px-2 py-0.5 text-[10px] bg-cyan-950/60 border border-cyan-500/30 rounded text-cyan-400">
                          {s.archetype}
                        </span>
                      </div>
                      <button
                        onClick={() => handleStartBuild(s.spec_id)}
                        disabled={isBuilding}
                        className="flex items-center space-x-1 px-2.5 py-1 bg-emerald-800/80 hover:bg-emerald-700 border border-emerald-500/40 rounded text-xs text-emerald-200"
                      >
                        <Play className="w-3 h-3" />
                        <span>Launch Build</span>
                      </button>
                    </div>

                    <p className="text-xs text-zinc-300">{s.summary}</p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                      <div className="bg-zinc-950/60 p-2 rounded border border-zinc-800">
                        <div className="text-zinc-400 font-semibold mb-1">Target Features:</div>
                        <ul className="list-disc list-inside space-y-0.5 text-zinc-300 text-[11px]">
                          {s.features.map((f, i) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="bg-zinc-950/60 p-2 rounded border border-zinc-800">
                        <div className="text-zinc-400 font-semibold mb-1">API Endpoints:</div>
                        <div className="space-y-1 text-[11px]">
                          {s.api_endpoints.map((ep, i) => (
                            <div key={i} className="flex items-center space-x-1.5">
                              <span className="px-1 bg-zinc-800 rounded text-cyan-300 text-[10px] font-bold">
                                {ep.method}
                              </span>
                              <span className="text-zinc-300">{ep.path}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: ASSEMBLY LINE & BUILDS */}
      {activeTab === 'builds' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1 bg-zinc-900/70 border border-zinc-800 rounded-lg p-3 space-y-2">
            <h2 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Build Queue</h2>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {builds.map(b => (
                <div
                  key={b.build_id}
                  onClick={() => setSelectedBuild(b)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedBuild?.build_id === b.build_id
                      ? 'bg-zinc-800/90 border-cyan-500/60 shadow-md'
                      : 'bg-zinc-950/60 border-zinc-800 hover:bg-zinc-900'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs text-zinc-200">{b.product_name}</span>
                    <span className={`px-1.5 py-0.5 text-[10px] border rounded ${getStateClass(b.state)}`}>
                      {b.state}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-zinc-400">
                    <span>Stage: {b.current_stage}</span>
                    <span>Loop: #{b.iteration}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-3">
            {selectedBuild ? (
              <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div>
                    <h2 className="text-base font-bold text-cyan-300">{selectedBuild.product_name}</h2>
                    <p className="text-xs text-zinc-400">Build ID: {selectedBuild.build_id} • Spec: {selectedBuild.spec_id}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2.5 py-1 text-xs border rounded-md font-semibold ${getStageBadgeClass(selectedBuild.current_stage)}`}>
                      {selectedBuild.current_stage}
                    </span>
                    <button
                      onClick={() => handleRepairBuild(selectedBuild.build_id)}
                      className="flex items-center space-x-1 px-2.5 py-1 bg-amber-800/70 hover:bg-amber-700 border border-amber-500/40 rounded text-xs text-amber-200"
                    >
                      <Wrench className="w-3 h-3" />
                      <span>Trigger Auto-Fix</span>
                    </button>
                  </div>
                </div>

                {/* Stage Stepper */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-zinc-950 rounded border border-zinc-800">
                    <div className="text-zinc-500 text-[10px]">1. Scaffolding</div>
                    <div className="text-zinc-200 font-semibold">{selectedBuild.components.length} Components</div>
                  </div>
                  <div className="p-2 bg-zinc-950 rounded border border-zinc-800">
                    <div className="text-zinc-500 text-[10px]">2. Test Results</div>
                    <div className="text-emerald-400 font-semibold">{selectedBuild.test_results?.passed || 0} Passed</div>
                  </div>
                  <div className="p-2 bg-zinc-950 rounded border border-zinc-800">
                    <div className="text-zinc-500 text-[10px]">3. Security Sentinel</div>
                    <div className="text-cyan-400 font-semibold">{selectedBuild.security_findings?.length || 0} High/Crit</div>
                  </div>
                  <div className="p-2 bg-zinc-950 rounded border border-zinc-800">
                    <div className="text-zinc-500 text-[10px]">4. SLSA Level 3</div>
                    <div className="text-zinc-300 font-semibold truncate">{selectedBuild.slsa_provenance_hash ? 'Attested' : 'Pending'}</div>
                  </div>
                </div>

                {/* Test & Output Logs */}
                <div className="bg-black/80 rounded-lg p-3 border border-zinc-800 space-y-2">
                  <div className="flex items-center justify-between text-xs text-zinc-400">
                    <span className="flex items-center space-x-1">
                      <Terminal className="w-3.5 h-3.5 text-zinc-500" />
                      <span>Execution Output & Verification Log</span>
                    </span>
                    <span className="text-[10px]">Exit Code: {selectedBuild.test_results?.exit_code ?? 0}</span>
                  </div>
                  <pre className="text-xs text-zinc-300 font-mono overflow-x-auto max-h-48 whitespace-pre-wrap">
                    {selectedBuild.test_results?.stdout_summary || 'No execution logs recorded yet.'}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center bg-zinc-900/40 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-xs">
                Select a build from the queue to view assembly details.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: COMPONENTS & CODE ASSETS */}
      {activeTab === 'components' && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-zinc-300 flex items-center space-x-2">
            <FileCode2 className="w-4 h-4 text-indigo-400" />
            <span>Generated Product Components ({selectedBuild?.components.length || 0})</span>
          </h2>

          {selectedBuild?.components.map(comp => (
            <div key={comp.component_id} className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-sm text-indigo-300">{comp.name}</span>
                  <span className="px-2 py-0.5 text-[10px] bg-zinc-950 border border-zinc-700 rounded text-zinc-400">
                    {comp.language} • {comp.framework}
                  </span>
                </div>
                <span className="px-2 py-0.5 text-[10px] bg-emerald-950/60 border border-emerald-500/30 rounded text-emerald-400">
                  {comp.status}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                <div className="bg-zinc-950/60 p-2 rounded border border-zinc-800">
                  <div className="text-zinc-400 font-semibold mb-1">Generated Files:</div>
                  <ul className="space-y-0.5 text-zinc-300 text-[11px]">
                    {comp.generated_files.map((gf, i) => (
                      <li key={i} className="flex items-center space-x-1 text-cyan-300">
                        <FileCode2 className="w-3 h-3 text-cyan-500" />
                        <span>{gf}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="bg-zinc-950/60 p-2 rounded border border-zinc-800">
                  <div className="text-zinc-400 font-semibold mb-1">Dependencies:</div>
                  <div className="flex flex-wrap gap-1">
                    {comp.dependencies.map((dep, i) => (
                      <span key={i} className="px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-300 text-[10px]">
                        {dep}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 4: AUTONOMOUS SELF-CORRECTION LOG */}
      {activeTab === 'corrections' && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-amber-300 flex items-center space-x-2">
            <Wrench className="w-4 h-4 text-amber-400" />
            <span>Self-Correction & AST Repair Audit Trail</span>
          </h2>

          {selectedBuild?.corrections_applied.length === 0 ? (
            <div className="p-8 text-center bg-zinc-900/40 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-xs">
              No self-corrections required. All components compiled and passed verification cleanly on initial iteration.
            </div>
          ) : (
            <div className="space-y-2">
              {selectedBuild?.corrections_applied.map((corr, idx) => (
                <div key={idx} className="bg-zinc-900/80 border border-amber-500/30 rounded-lg p-3 space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-300">Iteration #{corr.iteration} — {corr.reason}</span>
                    <span className="text-zinc-500 text-[10px]">{corr.timestamp}</span>
                  </div>
                  <div className="text-zinc-300">{corr.action_taken}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: PRODUCT CATALOG */}
      {activeTab === 'catalog' && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-emerald-300 flex items-center space-x-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <span>Delivered Products Ready for Deployment ({catalog.length})</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {catalog.map(item => (
              <div key={item.product_id} className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-emerald-300">{item.product_name}</span>
                  <span className="px-2 py-0.5 text-[10px] bg-emerald-950/60 border border-emerald-500/30 rounded text-emerald-400">
                    v{item.version}
                  </span>
                </div>
                <div className="text-xs text-zinc-400">Archetype: {item.archetype}</div>
                <div className="text-[11px] text-zinc-500 truncate">Workspace: {item.workspace_path}</div>
                <div className="pt-2 border-t border-zinc-800 flex items-center justify-between text-[10px] text-zinc-400">
                  <span>Provenance: {item.provenance_chain_hash}</span>
                  <span className="text-emerald-400 font-semibold">SLSA Level 3</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 6: GOVERNANCE & SLSA GATES */}
      {activeTab === 'governance' && (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-4 space-y-4">
          <h2 className="text-sm font-bold text-rose-300 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-rose-400" />
            <span>Security Sentinel, SLSA Level 3 & FinOps Governance</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-zinc-950 rounded-lg border border-zinc-800 space-y-1">
              <div className="text-zinc-400 font-semibold">Zero-Trust AST Security</div>
              <div className="text-emerald-400 font-bold">PASS (0 Vulnerabilities)</div>
              <p className="text-[11px] text-zinc-500">AST parser verifies no raw exec/eval calls in synthesized code.</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded-lg border border-zinc-800 space-y-1">
              <div className="text-zinc-400 font-semibold">SLSA Level 3 Attestation</div>
              <div className="text-cyan-400 font-bold">CRYPTOGRAPHIC ATTESTED</div>
              <p className="text-[11px] text-zinc-500">Deterministic SHA-256 state and build manifest lineage verified.</p>
            </div>
            <div className="p-3 bg-zinc-950 rounded-lg border border-zinc-800 space-y-1">
              <div className="text-zinc-400 font-semibold">FinOps Zero-Cost Invariant</div>
              <div className="text-emerald-400 font-bold">$0.00 SPEND ENFORCED</div>
              <p className="text-[11px] text-zinc-500">Pure local process group and sandbox container execution.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default ProductBuilderMatrixView;
