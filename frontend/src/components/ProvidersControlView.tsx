import React, { useState, useEffect, useCallback } from 'react';
import {
  Zap,
  Lock,
  RefreshCw,
  RotateCcw
} from 'lucide-react';
import type { ProviderInfo, FinOpsSummary } from '../types';
import { sound } from '../utils/audio';

export const ProvidersControlView: React.FC = () => {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [activePreference, setActivePreference] = useState<string>('local_mock');
  const [finops, setFinops] = useState<FinOpsSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const fetchProviderData = useCallback(async () => {
    try {
      const [provRes, finopsRes] = await Promise.all([
        fetch('/api/v1/providers').then(r => r.json()),
        fetch('/api/v1/cost/summary').then(r => r.json())
      ]);

      if (Array.isArray(provRes)) {
        setProviders(provRes);
      }
      setFinops(finopsRes);

      const healthRes = await fetch('/api/v1/providers/health').then(r => r.json());
      if (healthRes.default_preference) {
        setActivePreference(healthRes.default_preference);
      }
    } catch (err) {
      console.warn('Provider control fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviderData();
    const interval = setInterval(fetchProviderData, 4000);
    return () => clearInterval(interval);
  }, [fetchProviderData]);

  const handleSwitchProvider = async (providerName: string) => {
    sound.click();
    try {
      const res = await fetch('/api/v1/providers/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_name: providerName })
      });
      const data = await res.json();
      setActivePreference(data.active_provider);
      setStatusMsg(`Primary AI provider switched to: ${data.active_provider}`);
      sound.beep(750, 0.1, 'sine');
      fetchProviderData();
    } catch (err) {
      setStatusMsg(`Switch failed: ${err}`);
    }
  };

  const handleResetCircuit = async (providerName?: string) => {
    sound.click();
    try {
      await fetch('/api/v1/providers/reset-circuit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_name: providerName })
      });
      setStatusMsg(`Circuit breaker reset for ${providerName || 'all providers'}`);
      sound.beep(850, 0.1, 'sine');
      fetchProviderData();
    } catch (err) {
      setStatusMsg(`Circuit reset failed: ${err}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="hud-panel p-4 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-cyan-500/30">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-amber-950/60 border border-amber-500/40 text-amber-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold font-mono text-cyan-300 tracking-wider">
              AI PROVIDERS CLUSTER & FINOPS LEDGER
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Phase 10 Model Switching, Resilient Circuit Breakers & Phase 7 Zero-Cost Enforcement
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              sound.click();
              fetchProviderData();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-300 hover:text-cyan-300 font-mono text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>REFRESH</span>
          </button>
        </div>
      </div>

      {statusMsg && (
        <div className="hud-panel p-3 rounded border-cyan-500/40 bg-cyan-950/50 text-cyan-200 font-mono text-xs flex items-center justify-between">
          <span>{statusMsg}</span>
          <button onClick={() => setStatusMsg(null)} className="text-slate-400 hover:text-slate-200">×</button>
        </div>
      )}

      {/* FinOps Zero-Cost Ceiling Card */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-emerald-500/30 bg-[#061214]/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-emerald-500/20 pb-3">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-emerald-400" />
            <h3 className="font-mono text-sm font-bold text-emerald-300 tracking-wider">
              FINOPS ZERO-COST CEILING LEDGER
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 font-bold">
            GCP BILLING UNLINKED (100% AIR-GAPPED)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-1 font-mono text-xs">
          <div className="p-3 rounded bg-slate-900/80 border border-emerald-500/30 space-y-1">
            <div className="text-[10px] text-slate-400 uppercase">Current Month Spend</div>
            <div className="text-xl font-bold text-emerald-400">
              ${(finops?.current_spend_usd ?? 0.0).toFixed(2)} USD
            </div>
            <div className="text-[10px] text-slate-500">Live backend ledger</div>
          </div>

          <div className="p-3 rounded bg-slate-900/80 border border-emerald-500/30 space-y-1">
            <div className="text-[10px] text-slate-400 uppercase">Hard Spend Limit</div>
            <div className="text-xl font-bold text-emerald-400">
              ${(finops?.hard_spend_limit_usd ?? 0.0).toFixed(2)} USD
            </div>
            <div className="text-[10px] text-slate-500">Strict zero-cost barrier</div>
          </div>

          <div className="p-3 rounded bg-slate-900/80 border border-emerald-500/30 space-y-1">
            <div className="text-[10px] text-slate-400 uppercase">Billing Status</div>
            <div className="text-xl font-bold text-emerald-400">
              {finops?.billing_linked ? 'LINKED (WARNING)' : 'UNLINKED / SAFE'}
            </div>
            <div className="text-[10px] text-slate-500">Zero cloud billing liability</div>
          </div>

          <div className="p-3 rounded bg-slate-900/80 border border-emerald-500/30 space-y-1">
            <div className="text-[10px] text-slate-400 uppercase">Cost Guardrail</div>
            <div className="text-xl font-bold text-emerald-400">
              {finops?.zero_cost_guardrail_active ? 'ENFORCING' : 'DISABLED'}
            </div>
            <div className="text-[10px] text-slate-500">Pre-execution circuit trip</div>
          </div>
        </div>
      </div>

      {/* Registered AI Providers Cluster */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              REGISTERED AI PROVIDERS & CIRCUIT BREAKERS ({providers.length})
            </h3>
          </div>
          <button
            onClick={() => handleResetCircuit()}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs transition-all"
          >
            <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
            <span>RESET ALL CIRCUITS</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers.map(prov => {
            const isPreferred = prov.name.toLowerCase() === activePreference.toLowerCase();
            const isCircuitOpen = prov.health.circuit_state === 'OPEN';
            const isCircuitHalf = prov.health.circuit_state === 'HALF_OPEN';

            return (
              <div
                key={prov.name}
                className={`p-4 rounded-lg border transition-all font-mono text-xs space-y-3 ${
                  isPreferred
                    ? 'bg-cyan-950/40 border-cyan-400/80 shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                    : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-100 uppercase">{prov.name}</span>
                    {isPreferred && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-400/60 font-bold">
                        ACTIVE PRIMARY
                      </span>
                    )}
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                    isCircuitOpen
                      ? 'bg-rose-950 text-rose-400 border border-rose-600/50'
                      : isCircuitHalf
                      ? 'bg-amber-950 text-amber-400 border border-amber-600/50'
                      : 'bg-emerald-950 text-emerald-400 border border-emerald-600/50'
                  }`}>
                    CIRCUIT: {prov.health.circuit_state}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                  <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 flex justify-between">
                    <span>Type:</span>
                    <span className="text-slate-200">{prov.provider_type}</span>
                  </div>
                  <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 flex justify-between">
                    <span>Latency:</span>
                    <span className="text-slate-200">{prov.health.latency_ms} ms</span>
                  </div>
                  <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 flex justify-between">
                    <span>Status:</span>
                    <span className="text-emerald-400 font-bold">{prov.health.status}</span>
                  </div>
                  <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 flex justify-between">
                    <span>Failures:</span>
                    <span className={prov.health.failure_count > 0 ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                      {prov.health.failure_count}
                    </span>
                  </div>
                </div>

                {prov.health.last_error && (
                  <div className="text-[10px] text-rose-400 bg-rose-950/40 p-2 rounded border border-rose-800/50 line-clamp-2">
                    {prov.health.last_error}
                  </div>
                )}

                <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80 justify-end">
                  {isCircuitOpen && (
                    <button
                      onClick={() => handleResetCircuit(prov.name)}
                      className="px-2.5 py-1 rounded bg-rose-950 hover:bg-rose-900 border border-rose-600/60 text-rose-300 text-[10px] font-bold"
                    >
                      Reset Circuit
                    </button>
                  )}
                  {!isPreferred && (
                    <button
                      onClick={() => handleSwitchProvider(prov.name)}
                      className="px-2.5 py-1 rounded bg-cyan-950 hover:bg-cyan-900 border border-cyan-500/40 text-cyan-300 text-[10px] font-bold transition-all"
                    >
                      Set As Primary
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
