import React, { useState, useEffect, useCallback } from 'react';
import {
  RotateCcw,
  RefreshCw,
  Search,
  FileText,
  Zap
} from 'lucide-react';
import type { RecoveryStatus, AuditEventItem } from '../types';
import { sound } from '../utils/audio';

export const RecoveryControlView: React.FC = () => {
  const [recovery, setRecovery] = useState<RecoveryStatus | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const fetchRecoveryData = useCallback(async () => {
    try {
      const [recRes, audRes] = await Promise.all([
        fetch('/api/system/recovery').then(r => r.json()),
        fetch('/api/v1/audit?limit=60').then(r => r.json())
      ]);

      setRecovery(recRes);
      setAuditEvents(Array.isArray(audRes) ? audRes : []);
    } catch (err) {
      console.warn('Recovery data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecoveryData();
    const interval = setInterval(fetchRecoveryData, 4000);
    return () => clearInterval(interval);
  }, [fetchRecoveryData]);

  const handleRemediateMission = async (missionId: string) => {
    sound.click();
    try {
      const res = await fetch(`/api/v1/missions/${missionId}/remediate`, { method: 'POST' });
      const data = await res.json();
      setStatusMsg(`Remediation triggered for mission ${missionId}: State is ${data.state}`);
      sound.beep(800, 0.1, 'sine');
      fetchRecoveryData();
    } catch (err) {
      setStatusMsg(`Remediation failed: ${err}`);
    }
  };

  const handleResetCircuit = async (provider: string) => {
    sound.click();
    try {
      await fetch('/api/v1/providers/reset-circuit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_name: provider })
      });
      setStatusMsg(`Circuit reset for ${provider}`);
      fetchRecoveryData();
    } catch (err) {
      setStatusMsg(`Circuit reset failed: ${err}`);
    }
  };

  const filteredAudits = auditEvents.filter(a => {
    if (severityFilter !== 'all' && a.risk_level.toLowerCase() !== severityFilter.toLowerCase()) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        a.action.toLowerCase().includes(q) ||
        a.target.toLowerCase().includes(q) ||
        a.actor.toLowerCase().includes(q) ||
        a.reason.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="hud-panel p-4 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-cyan-500/30">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-400">
            <RotateCcw className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold font-mono text-cyan-300 tracking-wider">
              RECOVERY CENTER & AUDIT TRAIL EXPLORER
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Resumable Checkpoints, Closed-Loop Remediation, Circuit Resets & Immutable Audit
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              sound.click();
              fetchRecoveryData();
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

      {/* SECTION 1: Recovery Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 font-mono text-xs">
        {/* Recoverable Missions */}
        <div className="hud-panel p-5 rounded-lg space-y-3 border-cyan-500/20">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2.5">
            <span className="font-bold text-slate-200 flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-cyan-400" />
              CHECKPOINTED / FAILED MISSIONS ({recovery?.recoverable_missions.length || 0})
            </span>
          </div>

          {!recovery?.recoverable_missions.length ? (
            <div className="py-6 text-center text-slate-500">
              No failed or checkpointed missions. Clean execution state.
            </div>
          ) : (
            <div className="space-y-2.5">
              {recovery.recoverable_missions.map(m => (
                <div
                  key={m.mission_id}
                  className="p-3 rounded border border-slate-800 bg-slate-900/60 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-300 font-bold">{m.mission_id}</span>
                    <span className="px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/40 text-[10px]">
                      {m.state}
                    </span>
                  </div>
                  <div className="text-slate-300 text-[11px] truncate">{m.goal}</div>
                  {m.error && (
                    <div className="text-rose-400 bg-rose-950/40 p-2 rounded text-[10px]">
                      {m.error}
                    </div>
                  )}
                  <div className="flex items-center justify-between pt-1 border-t border-slate-800/60">
                    <span className="text-slate-500 text-[10px]">
                      Remediation Rounds: {m.remediation_attempts}
                    </span>
                    {m.can_remediate && (
                      <button
                        onClick={() => handleRemediateMission(m.mission_id)}
                        className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-[10px] transition-all"
                      >
                        Auto-Remediate
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Tripped Circuits & Disputed Merges */}
        <div className="hud-panel p-5 rounded-lg space-y-3 border-cyan-500/20">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2.5">
            <span className="font-bold text-slate-200 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              CIRCUITS & DISPUTED CANDIDATES
            </span>
          </div>

          <div className="space-y-3">
            {recovery?.open_circuits.length === 0 && recovery?.disputed_candidates.length === 0 ? (
              <div className="py-6 text-center text-slate-500">
                All AI circuits closed. Zero merge disputes active.
              </div>
            ) : (
              <>
                {recovery?.open_circuits.map(c => (
                  <div
                    key={c.provider}
                    className="p-3 rounded border border-rose-800/60 bg-rose-950/30 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-rose-300 font-bold uppercase">{c.provider} CIRCUIT OPEN</div>
                      <div className="text-[10px] text-rose-400">Failures: {c.failure_count}</div>
                    </div>
                    <button
                      onClick={() => handleResetCircuit(c.provider)}
                      className="px-2.5 py-1 rounded bg-rose-900/80 hover:bg-rose-800 text-rose-200 text-[10px] font-bold"
                    >
                      Reset Circuit
                    </button>
                  </div>
                ))}

                {recovery?.disputed_candidates.map(d => (
                  <div
                    key={d.candidate_id}
                    className="p-3 rounded border border-amber-800/60 bg-amber-950/30 space-y-1"
                  >
                    <div className="flex justify-between">
                      <span className="text-amber-300 font-bold">{d.candidate_id}</span>
                      <span className="text-rose-400">{d.conflict_type}</span>
                    </div>
                    <div className="text-slate-400 text-[10px]">
                      {d.source_branch} → {d.target_branch}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>

      {/* SECTION 2: Immutable Audit Trail Explorer */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              AUDIT TRAIL EXPLORER (APPEND-ONLY)
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
            <div className="flex items-center gap-1.5 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search audit actions..."
                className="bg-transparent text-slate-200 placeholder-slate-500 focus:outline-none text-[11px] w-36 sm:w-48"
              />
            </div>

            <select
              value={severityFilter}
              onChange={e => setSeverityFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-300 px-2 py-1 rounded text-[11px] focus:outline-none"
            >
              <option value="all">All Risk Levels</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                <th className="pb-2">TIMESTAMP</th>
                <th className="pb-2">ACTION</th>
                <th className="pb-2">RISK</th>
                <th className="pb-2">ACTOR</th>
                <th className="pb-2">TARGET</th>
                <th className="pb-2">RESULT</th>
                <th className="pb-2">REASON</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40 text-[11px]">
              {filteredAudits.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No matching audit records found.
                  </td>
                </tr>
              ) : (
                filteredAudits.slice(0, 30).map(aud => (
                  <tr key={aud.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2 text-slate-400 whitespace-nowrap">
                      {aud.timestamp ? new Date(aud.timestamp).toLocaleTimeString('en-US', { hour12: false }) : '--:--:--'}
                    </td>
                    <td className="py-2 text-slate-200 font-bold">{aud.action}</td>
                    <td className="py-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        aud.risk_level.toLowerCase() === 'critical'
                          ? 'bg-rose-950 text-rose-400 border border-rose-600/50'
                          : aud.risk_level.toLowerCase() === 'high'
                          ? 'bg-amber-950 text-amber-400 border border-amber-600/50'
                          : 'bg-slate-800 text-slate-300'
                      }`}>
                        {aud.risk_level.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2 text-slate-300">{aud.agent || aud.actor}</td>
                    <td className="py-2 text-slate-400 truncate max-w-[120px]">{aud.target}</td>
                    <td className="py-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        aud.result === 'CLEAN' || aud.result === 'APPROVED'
                          ? 'text-emerald-400'
                          : aud.result === 'BLOCKED' || aud.result === 'REJECTED'
                          ? 'text-rose-400'
                          : 'text-slate-300'
                      }`}>
                        {aud.result}
                      </span>
                    </td>
                    <td className="py-2 text-slate-400 truncate max-w-xs" title={aud.reason}>
                      {aud.reason}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
