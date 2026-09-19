import React, { useState, useEffect } from 'react';
import { 
  Server, 
  Key, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Globe, 
  Cpu, 
  ShieldCheck, 
  X,
  Wifi,
  Sparkles
} from 'lucide-react';
import { 
  getApiBaseUrl, 
  setApiBaseUrl, 
  getNexusApiKey, 
  setNexusApiKey, 
  testBridgeHealth, 
  type BridgeHealthCheckResult 
} from '../utils/api';
import { sound } from '../utils/audio';

interface BridgeSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBridgeUpdated?: () => void;
}

export const BridgeSettingsModal: React.FC<BridgeSettingsModalProps> = ({
  isOpen,
  onClose,
  onBridgeUpdated
}) => {
  const [bridgeUrl, setBridgeUrlInput] = useState<string>('');
  const [apiKey, setApiKeyInput] = useState<string>('');
  const [testing, setTesting] = useState<boolean>(false);
  const [healthResult, setHealthResult] = useState<BridgeHealthCheckResult | null>(null);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      setBridgeUrlInput(getApiBaseUrl());
      setApiKeyInput(getNexusApiKey());
      setSavedSuccess(false);
      // Run quick auto-ping
      runHealthCheck(getApiBaseUrl(), getNexusApiKey());
    }
  }, [isOpen]);

  const runHealthCheck = async (url: string, key: string) => {
    setTesting(true);
    try {
      const result = await testBridgeHealth(url, key);
      setHealthResult(result);
    } catch (e: any) {
      setHealthResult({
        ok: false,
        status: 'ERROR',
        latencyMs: 0,
        error: e.message || 'Unknown network exception'
      });
    } finally {
      setTesting(false);
    }
  };

  const handleAutoDetect = async () => {
    sound.click();
    setTesting(true);
    const candidates = [
      '', // relative origin
      'http://127.0.0.1:8000',
      'http://localhost:8000',
    ];

    for (const candidate of candidates) {
      const res = await testBridgeHealth(candidate, apiKey);
      if (res.ok) {
        setBridgeUrlInput(candidate);
        setHealthResult(res);
        setTesting(false);
        sound.beep(880, 0.1, 'sine');
        return;
      }
    }
    setTesting(false);
    // If none worked, test current input
    await runHealthCheck(bridgeUrl, apiKey);
  };

  const handleSave = () => {
    sound.beep(1000, 0.1, 'sine');
    setApiBaseUrl(bridgeUrl);
    setNexusApiKey(apiKey);
    setSavedSuccess(true);
    if (onBridgeUpdated) {
      onBridgeUpdated();
    }
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 600);
  };

  const handleClear = () => {
    sound.click();
    setBridgeUrlInput('');
    setApiKeyInput('');
    setApiBaseUrl('');
    setNexusApiKey('');
    setHealthResult(null);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md font-mono">
      <div 
        className="w-full max-w-xl bg-[#090f1d] border-2 border-cyan-500/80 rounded-xl shadow-[0_0_40px_rgba(0,240,255,0.25)] overflow-hidden animate-in fade-in zoom-in duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/30 bg-[#060a14]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wider flex items-center gap-2">
                NEXUS LOCAL BRIDGE & TUNNEL
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  SECURE CONTROL PLANE
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Connect Vercel Cyber-HUD or Mobile Web to your local Termux/Ubuntu backend daemon.
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

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Bridge URL Field */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-cyan-300 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-cyan-400" />
                BACKEND BRIDGE URL
              </span>
              <span className="text-[10px] text-slate-400 font-normal">
                Leave empty for default local origin
              </span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={bridgeUrl}
                onChange={(e) => setBridgeUrlInput(e.target.value)}
                placeholder="e.g. http://192.168.1.15:8000 or https://tunnel.domain.com"
                className="flex-1 bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
              />
              <button
                onClick={handleAutoDetect}
                disabled={testing}
                className="px-3 py-2 bg-cyan-950/60 hover:bg-cyan-900 border border-cyan-500/40 rounded-lg text-xs font-semibold text-cyan-300 flex items-center gap-1.5 transition-all disabled:opacity-50"
                title="Scan standard localhost endpoints"
              >
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                Auto-Detect
              </button>
            </div>
          </div>

          {/* API Key Field */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-cyan-300 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-cyan-400" />
                OPERATOR API KEY / TOKEN (X-NEXUS-KEY)
              </span>
              <span className="text-[10px] text-slate-400 font-normal">
                Stored in client localStorage only
              </span>
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="e.g. nexus-dev-operator-key-2026 or custom bearer token"
              className="w-full bg-slate-950/80 border border-slate-700 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-xs text-cyan-100 placeholder-slate-600 focus:outline-none transition-colors"
            />
          </div>

          {/* Live Status Card */}
          <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="text-slate-300">BRIDGE CONNECTIVITY STATUS:</span>
                {testing ? (
                  <span className="text-amber-400 flex items-center gap-1">
                    <RefreshCw className="w-3 h-3 animate-spin" /> PROBING...
                  </span>
                ) : healthResult?.ok ? (
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> ONLINE ({healthResult.latencyMs}ms)
                  </span>
                ) : (
                  <span className="text-rose-400 font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> {healthResult?.status || 'DISCONNECTED'}
                  </span>
                )}
              </div>
              <button
                onClick={() => runHealthCheck(bridgeUrl, apiKey)}
                disabled={testing}
                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-cyan-300 transition-colors text-xs flex items-center gap-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
                Test Ping
              </button>
            </div>

            {healthResult && (
              <div className="grid grid-cols-2 gap-2 text-[11px] pt-2 border-t border-slate-800/80">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Host Environment:</span>
                  <span className="text-cyan-200 font-semibold">{healthResult.osEnvironment || 'Unknown'}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Termux Mode:</span>
                  <span className="text-cyan-200 font-semibold">{healthResult.isTermux ? 'ACTIVE' : 'STANDARD'}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
                  <span>Registered Projects:</span>
                  <span className="text-cyan-200 font-semibold">{healthResult.projectsCount ?? 0}</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400">
                  <span>Latency:</span>
                  <span className={`font-semibold ${healthResult.latencyMs < 100 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {healthResult.latencyMs} ms
                  </span>
                </div>
              </div>
            )}

            {healthResult && !healthResult.ok && healthResult.error && (
              <p className="text-[11px] text-rose-400/90 bg-rose-950/30 border border-rose-900/50 p-2 rounded">
                {healthResult.error}
              </p>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-cyan-500/20 bg-[#060a14] flex items-center justify-between">
          <button
            onClick={handleClear}
            className="text-xs text-slate-500 hover:text-rose-400 transition-colors"
          >
            Clear / Reset to Default
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className={`px-5 py-2 rounded-lg text-xs font-bold transition-all shadow-lg flex items-center gap-1.5 ${
                savedSuccess
                  ? 'bg-emerald-600 text-white'
                  : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-cyan-500/20'
              }`}
            >
              {savedSuccess ? (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Saved & Connected!
                </>
              ) : (
                'Save & Apply Bridge'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
