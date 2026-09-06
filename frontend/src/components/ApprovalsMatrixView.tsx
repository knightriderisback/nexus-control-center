import { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  RefreshCw,
  Terminal
} from 'lucide-react';
import { sound } from '../utils/audio';

interface ApprovalItem {
  id: string;
  task_id?: string;
  action: string;
  target_project: string;
  risk_level: string;
  command?: string;
  actor: string;
  reason: string;
  timestamp: string;
  status: string;
  approved_by?: string;
  decided_at?: string;
}

export function ApprovalsMatrixView() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/approvals');
      const data = await res.json();
      setApprovals(data);
    } catch (e) {
      console.error('Failed to load approvals:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleDecision = async (id: string, decision: 'APPROVED' | 'REJECTED') => {
    sound.click();
    setProcessingId(id);
    try {
      await fetch(`/api/v1/approvals/${id}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, user: 'hud_operator' })
      });
      sound.beep(decision === 'APPROVED' ? 880 : 400, 0.12, 'sine');
      fetchApprovals();
    } catch (e) {
      alert('Decision dispatch failed.');
    } finally {
      setProcessingId(null);
    }
  };

  const pendingCount = approvals.filter(a => a.status === 'PENDING').length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
        <span className="text-cyan-300 font-mono text-xs tracking-widest uppercase">
          Querying Policy Engine Approval Vault...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="hud-panel p-5 rounded-lg border border-amber-500/30 bg-[#0c101a]/90 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
            <ShieldAlert className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-black tracking-wider text-slate-100 font-mono uppercase">
                Human Approval Gates
              </h1>
              {pendingCount > 0 ? (
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold animate-pulse">
                  {pendingCount} PENDING ACTION
                </span>
              ) : (
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  ALL CLEAR
                </span>
              )}
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5">
              High and Critical risk operations intercepted by the Policy Engine. Operator clearance required before execution.
            </p>
          </div>
        </div>

        <button
          onClick={fetchApprovals}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-700 font-mono text-xs transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>SYNC GATES</span>
        </button>
      </div>

      {/* Approvals Table / Cards */}
      <div className="space-y-3">
        {approvals.length === 0 ? (
          <div className="hud-panel p-12 text-center rounded-lg border border-slate-800 text-slate-500 font-mono text-xs">
            Zero approval requests recorded. Autonomous execution operating within low-risk guardrails.
          </div>
        ) : (
          approvals.map((a) => {
            const isPending = a.status === 'PENDING';
            const riskBg = a.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' : 'bg-amber-500/20 text-amber-300 border-amber-500/40';

            return (
              <div 
                key={a.id}
                className={`hud-panel p-4 rounded-lg border transition-all ${
                  isPending ? 'border-amber-500/40 bg-[#121624]' : 'border-slate-800/80 bg-[#080d16]/70'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-300 font-mono font-bold text-xs">{a.id}</span>
                      <span className={`px-2 py-0.5 text-[10px] font-mono rounded border ${riskBg}`}>
                        {a.risk_level}
                      </span>
                      <span className="text-slate-400 font-mono text-xs">• Project: <strong className="text-slate-200">{a.target_project}</strong></span>
                      <span className="text-slate-500 font-mono text-[11px]">• {a.timestamp.replace('T', ' ').split('.')[0]}</span>
                    </div>

                    <h2 className="text-sm font-bold text-slate-200 font-mono">{a.action}</h2>
                    <p className="text-xs text-slate-400 font-mono">{a.reason}</p>

                    {a.command && (
                      <div className="mt-2 p-2 rounded bg-black/50 border border-slate-800 font-mono text-[11px] text-cyan-300 flex items-center gap-2">
                        <Terminal className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                        <code className="truncate">{a.command}</code>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {isPending ? (
                      <>
                        <button
                          onClick={() => handleDecision(a.id, 'REJECTED')}
                          disabled={processingId === a.id}
                          className="flex items-center gap-1 px-3 py-1.5 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-500/40 font-mono text-xs transition-all disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>REJECT</span>
                        </button>
                        <button
                          onClick={() => handleDecision(a.id, 'APPROVED')}
                          disabled={processingId === a.id}
                          className="flex items-center gap-1 px-3 py-1.5 rounded bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-500/40 font-mono text-xs transition-all shadow-[0_0_10px_rgba(16,185,129,0.25)] disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>APPROVE & EXECUTE</span>
                        </button>
                      </>
                    ) : (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800/80 border border-slate-700 font-mono text-xs">
                        {a.status === 'APPROVED' || a.status === 'EXECUTED' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-rose-400" />
                        )}
                        <span className={a.status === 'APPROVED' || a.status === 'EXECUTED' ? 'text-emerald-300' : 'text-rose-300'}>
                          {a.status}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
