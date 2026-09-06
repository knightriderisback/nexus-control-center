import { useState, useEffect } from 'react';
import { 
  FileText, 
  RefreshCw, 
  Search,
  CheckCircle2,
  XCircle,
  Clock
} from 'lucide-react';
import type { AuditEventItem } from '../types';

export function AuditTrailView() {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const fetchAuditEvents = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/audit?limit=100');
      const data = await res.json();
      setEvents(data);
    } catch (e) {
      console.error('Failed to load audit trail:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditEvents();
  }, []);

  const filteredEvents = events.filter(e => 
    e.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.project.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.actor.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e.result.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
        <span className="text-cyan-300 font-mono text-xs tracking-widest uppercase">
          Streaming Append-Only Audit Trail...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="hud-panel p-5 rounded-lg border border-cyan-500/30 bg-[#080e1a]/90 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-950/60 border border-cyan-400/40 flex items-center justify-center text-cyan-400">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-black tracking-wider text-slate-100 font-mono uppercase">
                Enterprise Audit Trail
              </h1>
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                {events.length} LOGGED EVENTS
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5">
              Append-only immutable record of all agent operations, human approvals, risk assessments, and system mutations.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
            <input 
              type="text"
              placeholder="Search audit trail..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-3 py-1.5 rounded bg-black/40 border border-slate-700 text-xs font-mono text-slate-200 focus:border-cyan-400 outline-none w-56"
            />
          </div>

          <button
            onClick={fetchAuditEvents}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-700 font-mono text-xs transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>SYNC LOG</span>
          </button>
        </div>
      </div>

      {/* Audit Events Table */}
      <div className="hud-panel rounded-lg border border-slate-800 overflow-hidden bg-[#080d16]/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-[#0c1220] border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Project</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Risk Tier</th>
                <th className="py-3 px-4">Result</th>
                <th className="py-3 px-4">Correlation ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No matching audit records found.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((e) => {
                  const isCritical = e.risk_level === 'CRITICAL';
                  const isHigh = e.risk_level === 'HIGH';
                  const riskBadge = isCritical 
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' 
                    : (isHigh ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800 text-slate-300 border-slate-700');

                  const isSuccess = e.result === 'SUCCESS' || e.result === 'EXECUTED' || e.result === 'CLEAN' || e.result === 'VERIFIED_SAFE';
                  const isPending = e.result === 'PENDING_APPROVAL';

                  return (
                    <tr key={e.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-2.5 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                        {e.timestamp.replace('T', ' ').split('.')[0]}
                      </td>
                      <td className="py-2.5 px-4 font-bold text-slate-200">
                        {e.action}
                      </td>
                      <td className="py-2.5 px-4 text-cyan-300">
                        {e.project}
                      </td>
                      <td className="py-2.5 px-4 text-slate-400">
                        {e.actor}
                      </td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 text-[10px] rounded border ${riskBadge}`}>
                          {e.risk_level}
                        </span>
                      </td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 text-[10px] rounded flex items-center gap-1 w-max ${
                          isSuccess 
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' 
                            : (isPending ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30')
                        }`}>
                          {isSuccess && <CheckCircle2 className="w-3 h-3" />}
                          {isPending && <Clock className="w-3 h-3" />}
                          {!isSuccess && !isPending && <XCircle className="w-3 h-3" />}
                          <span>{e.result}</span>
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-slate-500 text-[10px]">
                        {e.correlation_id}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
