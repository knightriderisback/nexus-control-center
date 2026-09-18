import React, { useState, useEffect, useCallback } from 'react';
import {
  GitPullRequest,
  GitMerge,
  Layers,
  RefreshCw,
  Trash2
} from 'lucide-react';
import type { DeliveryRecord, MergeCandidate, WorktreeInfo } from '../types';
import { sound } from '../utils/audio';

export const DeliveryMatrixView: React.FC = () => {
  const [deliveries, setDeliveries] = useState<DeliveryRecord[]>([]);
  const [candidates, setCandidates] = useState<MergeCandidate[]>([]);
  const [worktrees, setWorktrees] = useState<WorktreeInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const fetchDeliveryData = useCallback(async () => {
    try {
      const [delivRes, candRes, wtRes] = await Promise.all([
        fetch('/api/v1/github/delivery/deliveries?limit=25').then(r => r.json()),
        fetch('/api/v1/agents/merge/candidates?limit=25').then(r => r.json()),
        fetch('/api/v1/agents/worktrees').then(r => r.json())
      ]);

      setDeliveries(Array.isArray(delivRes) ? delivRes : []);
      setCandidates(Array.isArray(candRes) ? candRes : []);
      setWorktrees(Array.isArray(wtRes) ? wtRes : []);
    } catch (err) {
      console.warn('Delivery fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDeliveryData();
    const interval = setInterval(fetchDeliveryData, 4000);
    return () => clearInterval(interval);
  }, [fetchDeliveryData]);

  const handleReviewDelivery = async (deliveryId: string) => {
    sound.click();
    try {
      const res = await fetch(`/api/v1/github/delivery/review/${deliveryId}`, { method: 'POST' });
      const data = await res.json();
      setStatusMsg(`Review complete for ${deliveryId}: State is ${data.state}`);
      fetchDeliveryData();
    } catch (err) {
      setStatusMsg(`Review failed: ${err}`);
    }
  };

  const handleMergeDelivery = async (deliveryId: string) => {
    sound.click();
    try {
      const res = await fetch('/api/v1/github/delivery/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delivery_id: deliveryId })
      });
      const data = await res.json();
      setStatusMsg(`Governed merge executed for ${deliveryId}: ${data.state}`);
      sound.beep(880, 0.1, 'sine');
      fetchDeliveryData();
    } catch (err) {
      setStatusMsg(`Merge execution failed: ${err}`);
    }
  };

  const handleAnalyzeCandidate = async (candidateId: string) => {
    sound.click();
    try {
      await fetch(`/api/v1/agents/merge/candidates/${candidateId}/analyze`, { method: 'POST' });
      setStatusMsg(`3-Way analysis complete for candidate ${candidateId}`);
      fetchDeliveryData();
    } catch (err) {
      setStatusMsg(`Analysis failed: ${err}`);
    }
  };

  const handleIntegrateCandidate = async (candidateId: string) => {
    sound.click();
    try {
      await fetch(`/api/v1/agents/merge/candidates/${candidateId}/integrate`, { method: 'POST' });
      setStatusMsg(`Candidate ${candidateId} integrated cleanly`);
      sound.beep(880, 0.1, 'sine');
      fetchDeliveryData();
    } catch (err) {
      setStatusMsg(`Integration failed: ${err}`);
    }
  };

  const handleRollbackCandidate = async (candidateId: string) => {
    sound.click();
    try {
      await fetch(`/api/v1/agents/merge/candidates/${candidateId}/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Operator manual rollback via Cyber-HUD' })
      });
      setStatusMsg(`Candidate ${candidateId} rolled back cleanly`);
      fetchDeliveryData();
    } catch (err) {
      setStatusMsg(`Rollback failed: ${err}`);
    }
  };

  const handleTeardownWorktree = async (sessionId: string) => {
    sound.click();
    try {
      await fetch(`/api/v1/agents/worktrees/${sessionId}/teardown`, { method: 'POST' });
      setStatusMsg(`Worktree ${sessionId} safely unmounted`);
      fetchDeliveryData();
    } catch (err) {
      setStatusMsg(`Worktree teardown failed: ${err}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="hud-panel p-4 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-cyan-500/30">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-400">
            <GitPullRequest className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold font-mono text-cyan-300 tracking-wider">
              GITHUB DELIVERY & MERGE GOVERNANCE
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Phases 8, 9 & 11: Worktree Sandboxes, 3-Way Conflict Arbitration, and PR Governance
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              sound.click();
              fetchDeliveryData();
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

      {/* SECTION 1: Governed GitHub Deliveries */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/20">
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              GOVERNED GITHUB DELIVERIES ({deliveries.length})
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300">
            IDEMPOTENT MERGE PIPELINE
          </span>
        </div>

        {deliveries.length === 0 ? (
          <div className="py-6 text-center font-mono text-xs text-slate-500">
            No active GitHub delivery pipelines found. Create merge candidates to initiate delivery.
          </div>
        ) : (
          <div className="space-y-3">
            {deliveries.map(deliv => {
              const isPassed = deliv.state === 'COMPLETED' || deliv.state === 'VERIFIED';
              const isBlocked = deliv.state === 'SECURITY_BLOCKED' || deliv.state === 'FAILED';
              const canMerge = deliv.state === 'VERIFIED' || deliv.state === 'APPROVED';

              return (
                <div
                  key={deliv.delivery_id}
                  className="p-3.5 rounded border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all font-mono text-xs space-y-2.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-cyan-300">{deliv.delivery_id}</span>
                      <span className="text-slate-500">•</span>
                      <span className="text-slate-300">{deliv.source_branch}</span>
                      {deliv.pr_number && (
                        <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-bold">
                          PR #{deliv.pr_number}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isPassed
                          ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-400'
                          : isBlocked
                          ? 'bg-rose-950/80 border border-rose-500/50 text-rose-400'
                          : 'bg-amber-950/80 border border-amber-500/50 text-amber-400'
                      }`}>
                        {deliv.state}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">
                        RISK: {deliv.risk_level.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Verification Checks */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-[11px] pt-1">
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                      <span className="text-slate-400">Pytest Suite:</span>
                      <span className={deliv.checks_results.some(c => c.check === 'pytest-suite' && c.conclusion === 'clean') ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                        {deliv.checks_results.some(c => c.check === 'pytest-suite' && c.conclusion === 'clean') ? 'PASSED' : 'PENDING'}
                      </span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                      <span className="text-slate-400">AST Sentinel:</span>
                      <span className={deliv.checks_results.some(c => c.check === 'ast-security-sentinel' && c.conclusion === 'clean') ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                        {deliv.checks_results.some(c => c.check === 'ast-security-sentinel' && c.conclusion === 'clean') ? 'CLEAN' : 'PENDING'}
                      </span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                      <span className="text-slate-400">Reviews:</span>
                      <span className="text-slate-200">{deliv.reviews.length} Completed</span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                      <span className="text-slate-400">Target Branch:</span>
                      <span className="text-slate-200">{deliv.target_branch}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80 justify-end">
                    <button
                      onClick={() => handleReviewDelivery(deliv.delivery_id)}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-mono transition-all"
                    >
                      Run Agent Swarm Review
                    </button>
                    {canMerge && (
                      <button
                        onClick={() => handleMergeDelivery(deliv.delivery_id)}
                        className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-[11px] font-mono transition-all shadow-[0_0_8px_rgba(0,240,255,0.3)]"
                      >
                        Execute Governed Merge
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: Merge Candidates & 3-Way Conflict Arbitration */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/20">
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <GitMerge className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              MERGE CANDIDATES & 3-WAY ARBITRATION ({candidates.length})
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/40 text-cyan-300">
            PHASE 9 ENGINE
          </span>
        </div>

        {candidates.length === 0 ? (
          <div className="py-6 text-center font-mono text-xs text-slate-500">
            No active merge candidates awaiting arbitration.
          </div>
        ) : (
          <div className="space-y-3">
            {candidates.map(cand => {
              const isMerged = cand.state === 'MERGED';
              const isConflict = cand.state === 'CONFLICT' || cand.state === 'BLOCKED';

              return (
                <div
                  key={cand.candidate_id}
                  className="p-3.5 rounded border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all font-mono text-xs space-y-2.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-cyan-300">{cand.candidate_id}</span>
                      <span className="text-slate-500">•</span>
                      <span className="text-slate-300">{cand.source_branch}</span>
                      <span className="text-slate-500">→</span>
                      <span className="text-slate-300">{cand.target_branch}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        isMerged
                          ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-400'
                          : isConflict
                          ? 'bg-rose-950/80 border border-rose-500/50 text-rose-400'
                          : 'bg-amber-950/80 border border-amber-500/50 text-amber-400'
                      }`}>
                        {cand.state}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">
                        {cand.strategy.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] pt-1">
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800 flex justify-between">
                      <span className="text-slate-400">Conflict Classification:</span>
                      <span className="text-slate-200 font-bold">{cand.conflict_type}</span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800 flex justify-between">
                      <span className="text-slate-400">Risk Level:</span>
                      <span className="text-amber-400">{cand.risk_level.toUpperCase()}</span>
                    </div>
                    <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800 flex justify-between">
                      <span className="text-slate-400">Source SHA:</span>
                      <span className="text-slate-400 truncate max-w-[100px]">{cand.source_sha || 'local_head'}</span>
                    </div>
                  </div>

                  {/* Candidate Actions */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80 justify-end">
                    <button
                      onClick={() => handleAnalyzeCandidate(cand.candidate_id)}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-mono transition-all"
                    >
                      3-Way Diff Analysis
                    </button>
                    {cand.state !== 'MERGED' && (
                      <button
                        onClick={() => handleIntegrateCandidate(cand.candidate_id)}
                        className="px-2.5 py-1 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-[11px] font-mono transition-all"
                      >
                        Integrate Branch
                      </button>
                    )}
                    {cand.state === 'MERGED' && (
                      <button
                        onClick={() => handleRollbackCandidate(cand.candidate_id)}
                        className="px-2.5 py-1 rounded bg-rose-950/80 border border-rose-600/60 text-rose-300 hover:bg-rose-900/80 text-[11px] font-mono transition-all"
                      >
                        Rollback Merge
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 3: Isolated Worktree Sandboxes */}
      <div className="hud-panel p-5 rounded-lg space-y-4 border-cyan-500/20">
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="font-mono text-sm font-bold text-slate-200 tracking-wider">
              ISOLATED WORKTREE SANDBOXES ({worktrees.length})
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950/60 border border-purple-500/40 text-purple-300">
            PHASE 8 ZERO-MUTATION RUNTIME
          </span>
        </div>

        {worktrees.length === 0 ? (
          <div className="py-6 text-center font-mono text-xs text-slate-500">
            No active worktrees running. Environment is 100% clean and pristine.
          </div>
        ) : (
          <div className="space-y-3">
            {worktrees.map(wt => (
              <div
                key={wt.session_id}
                className="p-3 rounded border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-300 font-bold">{wt.branch_name}</span>
                    <span className="text-slate-500">•</span>
                    <span className="text-slate-400">ID: {wt.session_id}</span>
                  </div>
                  <div className="text-[11px] text-slate-500 truncate max-w-md">
                    {wt.worktree_path}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] ${
                    wt.is_dirty ? 'bg-amber-950/80 text-amber-400 border border-amber-500/40' : 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                  }`}>
                    {wt.is_dirty ? 'DIRTY' : 'CLEAN'}
                  </span>
                  <button
                    onClick={() => handleTeardownWorktree(wt.session_id)}
                    className="p-1.5 rounded bg-rose-950/60 border border-rose-600/50 text-rose-400 hover:bg-rose-900/60 transition-all"
                    title="Teardown isolated worktree"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
