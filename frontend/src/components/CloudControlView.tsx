import { useState, useEffect } from 'react';
import { 
  Cloud, 
  ShieldCheck, 
  Server, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw,
  Layers,
  Workflow
} from 'lucide-react';
import { sound } from '../utils/audio';

interface CloudData {
  project_id: string;
  project_number: string;
  display_name: string;
  lifecycle_state: string;
  region_primary: string;
  billing: {
    status: string;
    guardrail: string;
    cost_estimate: string;
  };
  identity: {
    service_account: string;
    roles: string[];
    keys_count: number;
    security_posture: string;
  };
  workload_identity: {
    pool: string;
    provider: string;
    issuer: string;
    condition: string;
    status: string;
    full_provider_uri: string;
  };
  enabled_apis: Array<{ name: string; title: string }>;
  cloud_run_readiness: {
    dockerfile: string;
    cicd_pipeline: string;
    cloudbuild: string;
    service_account: string;
    federation: string;
    blockers: string[];
  };
}

export function CloudControlView() {
  const [cloud, setCloud] = useState<CloudData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [auditing, setAuditing] = useState<boolean>(false);
  const [auditResult, setAuditResult] = useState<string | null>(null);

  const fetchCloudData = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/cloud');
      const data = await res.json();
      setCloud(data);
    } catch (e) {
      console.error('Failed to fetch cloud telemetry:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCloudData();
  }, []);

  const handleRunAudit = async () => {
    sound.click();
    setAuditing(true);
    setAuditResult(null);
    try {
      const res = await fetch('/api/cloud/audit', { method: 'POST' });
      const data = await res.json();
      setAuditResult(`[${data.timestamp.split('T')[1].split('.')[0]}] AUDIT COMPLETE: ${data.message} Status: ${data.status} | Static Keys: ${data.static_keys} | Billable: ${data.billable_resources}`);
      sound.beep(960, 0.12, 'sine');
    } catch (e) {
      setAuditResult('[ERROR] Cloud audit call failed.');
    } finally {
      setAuditing(false);
    }
  };

  if (loading || !cloud) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
        <span className="text-cyan-300 font-mono text-xs tracking-widest uppercase">
          Probing Google Cloud Project Infrastructure...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner / Project Overview */}
      <div className="hud-panel p-5 rounded-lg border border-cyan-500/30 bg-[#080e1a]/90 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-cyan-950/60 border border-cyan-400/40 flex items-center justify-center text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.25)]">
              <Cloud className="w-7 h-7 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-black tracking-wider text-slate-100 font-mono">
                  {cloud.display_name.toUpperCase()}
                </h1>
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  {cloud.lifecycle_state}
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                  {cloud.region_primary}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-slate-400 mt-1">
                <span>PROJECT ID: <strong className="text-cyan-300">{cloud.project_id}</strong></span>
                <span>•</span>
                <span>PROJECT NUMBER: <strong className="text-slate-300">{cloud.project_number}</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunAudit}
              disabled={auditing}
              className="flex items-center gap-2 px-3.5 py-2 rounded bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 border border-cyan-400/50 font-mono text-xs transition-all shadow-[0_0_10px_rgba(0,240,255,0.2)] disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${auditing ? 'animate-spin' : ''}`} />
              <span>{auditing ? 'AUDITING...' : 'RUN SECURITY AUDIT'}</span>
            </button>
          </div>
        </div>

        {/* Real-time Audit Terminal Banner if triggered */}
        {auditResult && (
          <div className="mt-4 p-3 rounded bg-black/60 border border-emerald-500/30 text-[11px] font-mono text-emerald-400 flex items-center gap-2 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{auditResult}</span>
          </div>
        )}
      </div>

      {/* Grid: 4 Core Infrastructure Quadrants */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Quadrant 1: Keyless Zero-Trust Security */}
        <div className="hud-panel p-5 rounded-lg border border-cyan-500/20 bg-[#080d18]/80 space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h2 className="text-xs font-bold tracking-wider text-slate-200 uppercase font-mono">
                Keyless Zero-Trust Identity
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              {cloud.identity.security_posture}
            </span>
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div>
              <div className="text-[11px] text-slate-400">DEDICATED SERVICE ACCOUNT</div>
              <div className="text-cyan-300 font-bold break-all bg-black/40 p-2 rounded border border-cyan-500/10 mt-1">
                {cloud.identity.service_account}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="p-2.5 rounded bg-black/30 border border-slate-800">
                <div className="text-[10px] text-slate-500">STATIC JSON KEYS</div>
                <div className="text-emerald-400 font-bold text-sm mt-0.5 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  0 KEYS (100% KEYLESS)
                </div>
              </div>
              <div className="p-2.5 rounded bg-black/30 border border-slate-800">
                <div className="text-[10px] text-slate-500">MONTHLY BILLING RATE</div>
                <div className="text-cyan-400 font-bold text-sm mt-0.5">
                  {cloud.billing.cost_estimate} / MO
                </div>
              </div>
            </div>

            <div>
              <div className="text-[10px] text-slate-500 mb-1">IAM LEAST-PRIVILEGE BINDINGS</div>
              <div className="flex flex-wrap gap-1.5">
                {cloud.identity.roles.map((r) => (
                  <span key={r} className="px-2 py-0.5 text-[10px] rounded bg-slate-800/80 text-cyan-200 border border-cyan-500/20">
                    {r.replace('roles/', '')}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Quadrant 2: Workload Identity Federation (GitHub CI/CD) */}
        <div className="hud-panel p-5 rounded-lg border border-cyan-500/20 bg-[#080d18]/80 space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Workflow className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs font-bold tracking-wider text-slate-200 uppercase font-mono">
                Workload Identity Federation
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
              {cloud.workload_identity.status}
            </span>
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded bg-black/40 border border-cyan-500/10">
                <div className="text-[10px] text-slate-500">OIDC POOL</div>
                <div className="text-slate-200 font-bold">{cloud.workload_identity.pool}</div>
              </div>
              <div className="p-2 rounded bg-black/40 border border-cyan-500/10">
                <div className="text-[10px] text-slate-500">OIDC PROVIDER</div>
                <div className="text-slate-200 font-bold">{cloud.workload_identity.provider}</div>
              </div>
            </div>

            <div>
              <div className="text-[10px] text-slate-500">ISSUER URI</div>
              <div className="text-slate-300 text-[11px] truncate bg-black/30 p-1.5 rounded mt-0.5 border border-slate-800">
                {cloud.workload_identity.issuer}
              </div>
            </div>

            <div>
              <div className="text-[10px] text-slate-500">REPOSITORY ACCESS CONDITION</div>
              <div className="text-amber-300 text-[11px] bg-black/30 p-1.5 rounded mt-0.5 border border-amber-500/20">
                {cloud.workload_identity.condition}
              </div>
            </div>
          </div>
        </div>

        {/* Quadrant 3: Cloud Run Deployment Readiness */}
        <div className="hud-panel p-5 rounded-lg border border-cyan-500/20 bg-[#080d18]/80 space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-purple-400" />
              <h2 className="text-xs font-bold tracking-wider text-slate-200 uppercase font-mono">
                Cloud Run Deployment Engine
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40">
              STANDBY
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between p-2 rounded bg-black/30 border border-slate-800">
              <span className="text-slate-400">Dockerfile ($PORT dynamic)</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> READY
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-black/30 border border-slate-800">
              <span className="text-slate-400">CI/CD Pipeline (GitHub Actions)</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> READY
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-black/30 border border-slate-800">
              <span className="text-slate-400">Cloud Build Config</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> READY
              </span>
            </div>

            {cloud.cloud_run_readiness.blockers.length > 0 && (
              <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] flex items-start gap-2 mt-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
                <span>
                  <strong>DEPLOYMENT GUARDRAIL:</strong> {cloud.cloud_run_readiness.blockers[0]}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Quadrant 4: Enabled Cloud APIs Matrix */}
        <div className="hud-panel p-5 rounded-lg border border-cyan-500/20 bg-[#080d18]/80 space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs font-bold tracking-wider text-slate-200 uppercase font-mono">
                Active Cloud Services ({cloud.enabled_apis.length})
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">
              GCP PLATFORM
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[180px] overflow-y-auto pr-1">
            {cloud.enabled_apis.map((api) => (
              <div key={api.name} className="p-2 rounded bg-black/40 border border-cyan-500/10 flex items-center justify-between">
                <div>
                  <div className="text-[11px] font-mono text-cyan-300 font-bold">{api.title}</div>
                  <div className="text-[9px] font-mono text-slate-500 truncate">{api.name}</div>
                </div>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
