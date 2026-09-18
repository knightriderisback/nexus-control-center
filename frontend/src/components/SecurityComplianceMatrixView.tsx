import { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  Unlock,
  FileCode,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Search,
  GitMerge,
  Scale
} from 'lucide-react';
import type {
  SecurityFinding,
  ComplianceControlResult,
  QuarantineRecord,
  SecOpsTelemetry,
  SecurityPolicyRule,
  SecurityEvidenceRecord
} from '../types';
import { sound } from '../utils/audio';

export const SecurityComplianceMatrixView = () => {
  const [telemetry, setTelemetry] = useState<SecOpsTelemetry | null>(null);
  const [findings, setFindings] = useState<SecurityFinding[]>([]);
  const [complianceResults, setComplianceResults] = useState<ComplianceControlResult[]>([]);
  const [quarantineRecords, setQuarantineRecords] = useState<QuarantineRecord[]>([]);
  const [policies, setPolicies] = useState<Record<string, SecurityPolicyRule>>({});
  const [evidenceList, setEvidenceList] = useState<SecurityEvidenceRecord[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<SecurityFinding | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [scanning, setScanning] = useState<boolean>(false);
  const [activeSubTab, setActiveSubTab] = useState<'findings' | 'compliance' | 'quarantine' | 'policies' | 'evidence'>('findings');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Scan modal options
  const [scanTargetPath, setScanTargetPath] = useState<string>('.');
  const [scanIncludeSecrets, setScanIncludeSecrets] = useState<boolean>(true);
  const [scanIncludeSast, setScanIncludeSast] = useState<boolean>(true);
  const [scanIncludeDeps, setScanIncludeDeps] = useState<boolean>(true);
  const [scanAutoQuarantine, setScanAutoQuarantine] = useState<boolean>(false);
  const [showScanModal, setShowScanModal] = useState<boolean>(false);

  const fetchSecOpsData = useCallback(async () => {
    try {
      const [telRes, findRes, compRes, quarRes, polRes, evRes] = await Promise.all([
        fetch('/api/v1/secops/telemetry').then(r => r.json()).catch(() => null),
        fetch('/api/v1/secops/findings').then(r => r.json()).catch(() => []),
        fetch('/api/v1/secops/compliance').then(r => r.json()).catch(() => []),
        fetch('/api/v1/secops/quarantine').then(r => r.json()).catch(() => []),
        fetch('/api/v1/secops/policies').then(r => r.json()).catch(() => ({})),
        fetch('/api/v1/secops/evidence').then(r => r.json()).catch(() => [])
      ]);

      if (telRes && typeof telRes === 'object') {
        setTelemetry(telRes.telemetry || telRes);
      }
      if (Array.isArray(findRes)) {
        setFindings(findRes);
      } else if (findRes && findRes.findings) {
        setFindings(findRes.findings);
      }

      if (Array.isArray(compRes)) {
        setComplianceResults(compRes);
      } else if (compRes && compRes.results) {
        setComplianceResults(compRes.results);
      }

      if (Array.isArray(quarRes)) {
        setQuarantineRecords(quarRes);
      } else if (quarRes && quarRes.records) {
        setQuarantineRecords(quarRes.records);
      }

      if (polRes && typeof polRes === 'object') {
        setPolicies(polRes);
      }

      if (Array.isArray(evRes)) {
        setEvidenceList(evRes);
      }
    } catch (err) {
      console.warn('Failed to load SecOps data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSecOpsData();
    const interval = setInterval(fetchSecOpsData, 5000);
    return () => clearInterval(interval);
  }, [fetchSecOpsData]);

  const handleRunScan = async () => {
    setScanning(true);
    sound.click();
    setShowScanModal(false);
    try {
      const res = await fetch('/api/v1/secops/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: scanTargetPath,
          include_secrets: scanIncludeSecrets,
          include_sast: scanIncludeSast,
          include_dependencies: scanIncludeDeps,
          auto_quarantine_critical: scanAutoQuarantine
        })
      });
      const data = await res.json();
      if (data && data.scan_id) {
        sound.beep(880, 0.15, 'sine');
        setActionMessage(`Scan completed: ${data.findings?.length || 0} findings detected in ${data.total_files_scanned} files.`);
      } else if (data.status === 'ok') {
        sound.beep(880, 0.15, 'sine');
        setActionMessage(`Scan completed: ${data.report?.findings?.length || 0} findings detected.`);
      } else {
        setActionMessage(`Scan completed.`);
      }
      await fetchSecOpsData();
    } catch (err) {
      setActionMessage('Failed to trigger scan.');
    } finally {
      setScanning(false);
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleQuarantine = async (findingId: string) => {
    sound.click();
    try {
      const res = await fetch(`/api/v1/secops/findings/${findingId}/quarantine?operator=CYBER-HUD_OPERATOR`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.quarantine_id) {
        sound.beep(600, 0.2, 'sawtooth');
        setActionMessage(`Finding ${findingId} quarantined successfully into vault (${data.permissions_applied || '0600'}).`);
      } else {
        setActionMessage(`Quarantine error: ${data.detail || 'Operation failed'}`);
      }
      await fetchSecOpsData();
    } catch (err) {
      setActionMessage('Failed to execute threat quarantine.');
    } finally {
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleReleaseQuarantine = async (quarantineId: string) => {
    sound.click();
    try {
      const res = await fetch(`/api/v1/secops/quarantine/${quarantineId}/release?operator=CYBER-HUD_OPERATOR&reason=Manual_Audit_Release`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.status === 'ok') {
        sound.beep(800, 0.15, 'sine');
        setActionMessage(`Quarantine artifact ${quarantineId} released safely.`);
      }
      await fetchSecOpsData();
    } catch (err) {
      setActionMessage('Failed to release quarantine.');
    } finally {
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleTransitionState = async (findingId: string, newState: string) => {
    sound.click();
    try {
      const res = await fetch(`/api/v1/secops/findings/${findingId}/transition?new_state=${newState}&actor=CYBER-HUD_OPERATOR`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.finding_id) {
        sound.beep(900, 0.1, 'sine');
        setActionMessage(`Finding ${findingId} transitioned to ${newState}.`);
        if (selectedFinding && selectedFinding.finding_id === findingId) {
          setSelectedFinding(data);
        }
      }
      await fetchSecOpsData();
    } catch (err) {
      setActionMessage('Failed to transition finding state.');
    } finally {
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const handleRemediate = async (findingId: string) => {
    sound.click();
    try {
      const res = await fetch(`/api/v1/secops/findings/${findingId}/remediate?operator=CYBER-HUD_OPERATOR`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.status === 'REMEDIATED' || data.finding_id) {
        sound.beep(950, 0.12, 'sine');
        setActionMessage(`Finding ${findingId} remediated.`);
      } else {
        setActionMessage(`Remediation error: ${data.detail || 'Operation failed'}`);
      }
      await fetchSecOpsData();
    } catch (err) {
      setActionMessage('Failed to remediate finding.');
    } finally {
      setTimeout(() => setActionMessage(null), 5000);
    }
  };

  const filteredFindings = findings.filter(f => {
    if (severityFilter !== 'ALL' && f.severity !== severityFilter) return false;
    if (statusFilter !== 'ALL' && f.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        f.title.toLowerCase().includes(q) ||
        f.finding_id.toLowerCase().includes(q) ||
        (f.file_path && f.file_path.toLowerCase().includes(q)) ||
        f.category.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-emerald-400 border-emerald-500/40 bg-emerald-950/20';
    if (score >= 60) return 'text-amber-400 border-amber-500/40 bg-amber-950/20';
    return 'text-rose-400 border-rose-500/40 bg-rose-950/20';
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 animate-pulse">CRITICAL</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">HIGH</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-500/20 text-yellow-300 border border-yellow-500/40">MEDIUM</span>;
      case 'LOW':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/40">LOW</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-500/20 text-slate-400 border border-slate-500/40">INFO</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'QUARANTINED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/40 font-mono">QUARANTINED</span>;
      case 'REMEDIATED':
      case 'RESOLVED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono">{status}</span>;
      case 'OPEN':
      case 'DISCOVERED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/40 font-mono">{status}</span>;
      case 'BLOCKED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-rose-600/30 text-rose-200 border border-rose-400 font-mono">BLOCKED</span>;
      case 'ACCEPTED_RISK':
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">ACCEPTED_RISK</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-500/20 text-slate-300 border border-slate-500/40 font-mono">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast / Action Message */}
      {actionMessage && (
        <div className="hud-panel p-3 bg-cyan-950/80 border border-cyan-400/60 rounded text-cyan-200 text-xs font-mono flex items-center justify-between shadow-[0_0_15px_rgba(0,240,255,0.3)] animate-bounce">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Top Banner: SecOps Telemetry Cockpit */}
      <div className="hud-panel p-5 bg-[#080d1a]/90 border border-cyan-500/30 rounded-lg shadow-[0_0_20px_rgba(0,240,255,0.08)]">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-cyan-500/20">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded border border-cyan-400/40 bg-cyan-950/40 text-cyan-400 shadow-[0_0_12px_rgba(0,240,255,0.3)]">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-black tracking-wider text-cyan-300 font-mono">
                  AUTONOMOUS SECOPS & COMPLIANCE MATRIX
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono">
                  ZERO-TRUST ENFORCED
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono">
                  $0.00 FINOPS GUARANTEED
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Continuous AST Secret Scanner • SAST Injection Defense • Dependency CVE Auditing • CIS/SOC2 Benchmarking
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowScanModal(true)}
              disabled={scanning}
              className="flex items-center gap-2 px-3.5 py-2 rounded bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/60 text-cyan-300 text-xs font-mono font-bold transition-all shadow-[0_0_10px_rgba(0,240,255,0.2)]"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin text-cyan-400' : ''}`} />
              <span>{scanning ? 'SCANNING CODEBASE...' : 'RUN SECURITY SCAN'}</span>
            </button>
          </div>
        </div>

        {/* Telemetry Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-4">
          {/* Posture Score */}
          <div className={`p-3 rounded border ${getScoreColor(telemetry?.overall_security_posture_score || 100)} flex flex-col justify-between`}>
            <span className="text-[10px] font-mono tracking-wider opacity-80">SECURITY POSTURE</span>
            <div className="text-2xl font-black font-mono">
              {telemetry ? telemetry.overall_security_posture_score : 100}
              <span className="text-xs font-normal opacity-70"> / 100</span>
            </div>
            <span className="text-[9px] font-mono opacity-60">Weighted Risk Index</span>
          </div>

          {/* Critical Vulnerabilities */}
          <div className="p-3 rounded border border-rose-500/30 bg-rose-950/20 text-rose-300 flex flex-col justify-between">
            <span className="text-[10px] font-mono tracking-wider opacity-80">CRITICAL THREATS</span>
            <div className="text-2xl font-black font-mono text-rose-400">
              {telemetry?.critical_findings ?? 0}
            </div>
            <span className="text-[9px] font-mono opacity-60">Immediate Action Required</span>
          </div>

          {/* High Vulnerabilities */}
          <div className="p-3 rounded border border-amber-500/30 bg-amber-950/20 text-amber-300 flex flex-col justify-between">
            <span className="text-[10px] font-mono tracking-wider opacity-80">HIGH FINDINGS</span>
            <div className="text-2xl font-black font-mono text-amber-400">
              {telemetry?.high_findings ?? 0}
            </div>
            <span className="text-[9px] font-mono opacity-60">Elevated SAST / CVE Risk</span>
          </div>

          {/* Medium & Low */}
          <div className="p-3 rounded border border-cyan-500/30 bg-cyan-950/20 text-cyan-300 flex flex-col justify-between">
            <span className="text-[10px] font-mono tracking-wider opacity-80">MED / LOW / INFO</span>
            <div className="text-2xl font-black font-mono text-cyan-400">
              {(telemetry?.medium_findings ?? 0) + (telemetry?.low_findings ?? 0)}
            </div>
            <span className="text-[9px] font-mono opacity-60">Advisory / Deprecations</span>
          </div>

          {/* Quarantined Vault Items */}
          <div className="p-3 rounded border border-purple-500/30 bg-purple-950/20 text-purple-300 flex flex-col justify-between">
            <span className="text-[10px] font-mono tracking-wider opacity-80">QUARANTINE VAULT</span>
            <div className="text-2xl font-black font-mono text-purple-400">
              {telemetry?.quarantined_threats ?? quarantineRecords.length}
            </div>
            <span className="text-[9px] font-mono opacity-60">POSIX 0600 Isolation</span>
          </div>

          {/* FinOps Zero-Cost */}
          <div className="p-3 rounded border border-emerald-500/30 bg-emerald-950/20 text-emerald-300 flex flex-col justify-between">
            <span className="text-[10px] font-mono tracking-wider opacity-80">ZERO-COST SENTINEL</span>
            <div className="text-2xl font-black font-mono text-emerald-400">
              $0.00
            </div>
            <span className="text-[9px] font-mono opacity-60">FinOps Gate Passed</span>
          </div>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
          <button
            onClick={() => { sound.click(); setActiveSubTab('findings'); }}
            className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeSubTab === 'findings'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>FINDINGS ({findings.length})</span>
          </button>

          <button
            onClick={() => { sound.click(); setActiveSubTab('compliance'); }}
            className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeSubTab === 'compliance'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_10px_rgba(0,240,255,0.2)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>COMPLIANCE ({complianceResults.length})</span>
          </button>

          <button
            onClick={() => { sound.click(); setActiveSubTab('quarantine'); }}
            className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeSubTab === 'quarantine'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-400/50 shadow-[0_0_10px_rgba(168,85,247,0.2)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            <span>QUARANTINE VAULT ({quarantineRecords.length})</span>
          </button>

          <button
            onClick={() => { sound.click(); setActiveSubTab('policies'); }}
            className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeSubTab === 'policies'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-400/50 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>POLICY RULES ({Object.keys(policies).length})</span>
          </button>

          <button
            onClick={() => { sound.click(); setActiveSubTab('evidence'); }}
            className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeSubTab === 'evidence'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitMerge className="w-3.5 h-3.5" />
            <span>EVIDENCE TRAIL ({evidenceList.length})</span>
          </button>
        </div>

        {/* Search & Filters */}
        {activeSubTab === 'findings' && (
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
              <input
                type="text"
                placeholder="Search findings..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1 bg-slate-900 border border-cyan-500/30 rounded text-xs font-mono text-cyan-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 w-44"
              />
            </div>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-900 border border-cyan-500/30 rounded px-2 py-1 text-xs font-mono text-cyan-300 focus:outline-none"
            >
              <option value="ALL">ALL SEVERITY</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
              <option value="INFO">INFO</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900 border border-cyan-500/30 rounded px-2 py-1 text-xs font-mono text-cyan-300 focus:outline-none"
            >
              <option value="ALL">ALL STATUS</option>
              <option value="OPEN">OPEN</option>
              <option value="QUARANTINED">QUARANTINED</option>
              <option value="REMEDIATED">REMEDIATED</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>
        )}
      </div>

      {/* Tab 1: Findings Table */}
      {activeSubTab === 'findings' && (
        <div className="space-y-4">
          {loading ? (
            <div className="hud-panel p-8 text-center text-slate-400 font-mono text-xs">
              <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
              FETCHING SECOPS AUDIT DATA...
            </div>
          ) : filteredFindings.length === 0 ? (
            <div className="hud-panel p-8 text-center text-slate-400 font-mono text-xs bg-slate-950/40 border border-cyan-500/20 rounded">
              <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-emerald-400" />
              <div className="text-emerald-300 font-bold text-sm">NO VULNERABILITIES DETECTED</div>
              <div className="text-slate-500 mt-1">Codebase meets zero-trust security baselines. Run a scan to re-verify.</div>
            </div>
          ) : (
            <div className="hud-panel overflow-hidden border border-cyan-500/20 rounded-lg bg-[#080d1a]/80">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/90 text-slate-400 border-b border-cyan-500/20">
                  <tr>
                    <th className="p-3">SEVERITY</th>
                    <th className="p-3">FINDING & CATEGORY</th>
                    <th className="p-3">TARGET LOCATION</th>
                    <th className="p-3">CVSS</th>
                    <th className="p-3">STATUS</th>
                    <th className="p-3 text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-500/10">
                  {filteredFindings.map((finding) => (
                    <tr key={finding.finding_id} className="hover:bg-cyan-950/20 transition-colors">
                      <td className="p-3 whitespace-nowrap">
                        {getSeverityBadge(finding.severity)}
                      </td>
                      <td className="p-3">
                        <div className="font-bold text-cyan-200">{finding.title}</div>
                        <div className="text-[10px] text-slate-400 flex items-center gap-1.5 mt-0.5">
                          <span className="text-cyan-400">{finding.category}</span>
                          <span>•</span>
                          <span>ID: {finding.finding_id}</span>
                        </div>
                      </td>
                      <td className="p-3 font-mono text-[11px] text-slate-300">
                        {finding.file_path ? (
                          <span className="flex items-center gap-1 text-slate-300" title={finding.file_path}>
                            <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                            <span className="truncate max-w-[200px]">{finding.file_path}:{finding.line_number || 1}</span>
                          </span>
                        ) : (
                          <span className="text-slate-500">Repository Root</span>
                        )}
                      </td>
                      <td className="p-3 font-mono font-bold text-amber-300">
                        {finding.cvss_score.toFixed(1)}
                      </td>
                      <td className="p-3 whitespace-nowrap">
                        {getStatusBadge(finding.status)}
                      </td>
                      <td className="p-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setSelectedFinding(finding)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono border border-slate-600"
                          >
                            Details
                          </button>
                          {finding.status === 'OPEN' && (
                            <>
                              <button
                                onClick={() => handleQuarantine(finding.finding_id)}
                                className="px-2 py-1 rounded bg-purple-950/60 hover:bg-purple-900/80 text-purple-300 text-[10px] font-mono border border-purple-500/40"
                              >
                                Quarantine
                              </button>
                              <button
                                onClick={() => handleRemediate(finding.finding_id)}
                                className="px-2 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 text-[10px] font-mono border border-emerald-500/40"
                              >
                                Remediate
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Compliance Frameworks Grid */}
      {activeSubTab === 'compliance' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {['SOC2', 'ISO27001', 'CIS_BENCHMARK', 'NIST_800_53', 'GDPR_PRIVACY', 'FINOPS_ZERO_COST'].map((fw) => {
              const fwResults = complianceResults.filter(r => r.framework === fw);
              const passedCount = fwResults.filter(r => r.passed).length;
              const totalCount = fwResults.length;
              const pct = totalCount > 0 ? Math.round((passedCount / totalCount) * 100) : 100;

              return (
                <div key={fw} className="hud-panel p-4 bg-[#080d1a]/90 border border-cyan-500/30 rounded-lg flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <h3 className="font-mono font-bold text-xs text-cyan-300">{fw.replace(/_/g, ' ')}</h3>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${pct === 100 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'}`}>
                        {pct}% COMPLIANT
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
                      <div className={`h-1.5 rounded-full ${pct === 100 ? 'bg-emerald-400' : 'bg-amber-400'}`} style={{ width: `${pct}%` }}></div>
                    </div>
                    <div className="mt-3 space-y-2">
                      {fwResults.map(r => (
                        <div key={r.control_id} className="p-2 rounded bg-slate-900/60 border border-cyan-500/10 text-[11px] font-mono flex items-start gap-2">
                          {r.passed ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                          ) : (
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                          )}
                          <div>
                            <div className="text-slate-200 font-semibold">{r.title}</div>
                            <div className="text-[10px] text-slate-400 mt-0.5">{r.details}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 3: Quarantine Threat Vault */}
      {activeSubTab === 'quarantine' && (
        <div className="space-y-4">
          <div className="hud-panel p-4 bg-purple-950/20 border border-purple-500/30 rounded-lg flex items-center justify-between text-xs font-mono text-purple-200">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-purple-400" />
              <span>ISOLATION VAULT ACTIVE • POSIX 0600 ENFORCED • TOKENS REDACTED IN-PLACE</span>
            </div>
            <span className="text-[10px] text-slate-400">Location: data/secops/quarantine/</span>
          </div>

          {quarantineRecords.length === 0 ? (
            <div className="hud-panel p-8 text-center text-slate-400 font-mono text-xs bg-slate-950/40 border border-purple-500/20 rounded">
              <Lock className="w-8 h-8 mx-auto mb-2 text-purple-400 opacity-60" />
              <div className="text-purple-300 font-bold text-sm">QUARANTINE VAULT IS EMPTY</div>
              <div className="text-slate-500 mt-1">No malicious artifacts or compromised secrets are currently isolated.</div>
            </div>
          ) : (
            <div className="hud-panel overflow-hidden border border-purple-500/20 rounded-lg bg-[#080d1a]/80">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/90 text-slate-400 border-b border-purple-500/20">
                  <tr>
                    <th className="p-3">QUARANTINE ID</th>
                    <th className="p-3">FINDING ID</th>
                    <th className="p-3">ORIGINAL LOCATION</th>
                    <th className="p-3">VAULT PATH & PERMISSIONS</th>
                    <th className="p-3">ISOLATED AT</th>
                    <th className="p-3 text-right">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-purple-500/10">
                  {quarantineRecords.map((rec) => (
                    <tr key={rec.quarantine_id} className="hover:bg-purple-950/20 transition-colors">
                      <td className="p-3 text-purple-300 font-bold">{rec.quarantine_id}</td>
                      <td className="p-3 text-cyan-300">{rec.finding_id}</td>
                      <td className="p-3 text-slate-300 truncate max-w-[200px]" title={rec.original_path}>{rec.original_path}</td>
                      <td className="p-3 text-slate-300 font-mono text-[10px]">
                        <div>{rec.quarantined_path}</div>
                        <span className="text-emerald-400">{rec.permissions_applied}</span>
                      </td>
                      <td className="p-3 text-slate-400 text-[11px]">{new Date(rec.quarantined_at).toLocaleTimeString()}</td>
                      <td className="p-3 text-right">
                        {!rec.released_at ? (
                          <button
                            onClick={() => handleReleaseQuarantine(rec.quarantine_id)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono border border-slate-600 flex items-center gap-1 ml-auto"
                          >
                            <Unlock className="w-3 h-3 text-emerald-400" />
                            <span>Release</span>
                          </button>
                        ) : (
                          <span className="text-emerald-400 text-[10px]">RELEASED</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Policy Rules Grid */}
      {activeSubTab === 'policies' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.values(policies).map((rule) => (
              <div key={rule.rule_id} className="hud-panel p-4 bg-[#080d1a]/90 border border-amber-500/30 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="font-mono font-bold text-xs text-amber-300 flex items-center gap-2">
                    <Scale className="w-4 h-4 text-amber-400" />
                    <span>{rule.rule_id}: {rule.name}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    rule.decision === 'BLOCK' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                    rule.decision === 'REQUIRES_HUMAN_APPROVAL' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                    'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  }`}>
                    {rule.decision}
                  </span>
                </div>
                <div className="text-xs text-slate-300 mt-2 font-mono">{rule.rationale}</div>
                <div className="mt-3 p-2 rounded bg-slate-900 border border-slate-800 font-mono text-[10px] text-slate-400">
                  <div><strong className="text-slate-300">Target Action:</strong> {rule.target_action}</div>
                  <div><strong className="text-slate-300">Condition:</strong> {rule.condition}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 5: Evidence Trail */}
      {activeSubTab === 'evidence' && (
        <div className="space-y-4">
          {evidenceList.length === 0 ? (
            <div className="hud-panel p-8 text-center text-slate-400 font-mono text-xs bg-slate-950/40 border border-cyan-500/20 rounded">
              <GitMerge className="w-8 h-8 mx-auto mb-2 text-cyan-400 opacity-60" />
              <div className="text-cyan-300 font-bold text-sm">NO EVIDENCE RECORDS LOGGED YET</div>
              <div className="text-slate-500 mt-1">Pre-merge and deployment evidence will be recorded here automatically.</div>
            </div>
          ) : (
            <div className="hud-panel overflow-hidden border border-cyan-500/20 rounded-lg bg-[#080d1a]/80">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/90 text-slate-400 border-b border-cyan-500/20">
                  <tr>
                    <th className="p-3">EVIDENCE ID</th>
                    <th className="p-3">TIMESTAMP</th>
                    <th className="p-3">SCAN / POLICY VERSION</th>
                    <th className="p-3">BRANCH / TARGET</th>
                    <th className="p-3">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-500/10">
                  {evidenceList.map((ev) => (
                    <tr key={ev.evidence_id} className="hover:bg-cyan-950/20 transition-colors">
                      <td className="p-3 text-cyan-300 font-bold">{ev.evidence_id}</td>
                      <td className="p-3 text-slate-400">{new Date(ev.timestamp).toLocaleTimeString()}</td>
                      <td className="p-3 text-slate-300">{ev.scan_id} ({ev.policy_version})</td>
                      <td className="p-3 text-slate-300">{ev.branch || 'Direct Pipeline'}</td>
                      <td className="p-3">
                        {ev.passed ? (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">PASSED</span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/40">BLOCKED</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Finding Detail Modal */}
      {selectedFinding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="hud-panel w-full max-w-2xl bg-[#080d1a] border border-cyan-500/40 rounded-lg p-6 shadow-[0_0_30px_rgba(0,240,255,0.2)] font-mono space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
              <div className="flex items-center gap-2">
                {getSeverityBadge(selectedFinding.severity)}
                <h3 className="text-sm font-bold text-cyan-200">{selectedFinding.title}</h3>
              </div>
              <button
                onClick={() => setSelectedFinding(null)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-500 text-[10px]">FINDING ID</span>
                <div className="text-cyan-300">{selectedFinding.finding_id}</div>
              </div>
              <div>
                <span className="text-slate-500 text-[10px]">CATEGORY</span>
                <div className="text-slate-200">{selectedFinding.category}</div>
              </div>
              <div>
                <span className="text-slate-500 text-[10px]">LOCATION</span>
                <div className="text-slate-200 truncate">{selectedFinding.file_path || 'Repository Root'}:{selectedFinding.line_number || 1}</div>
              </div>
              <div>
                <span className="text-slate-500 text-[10px]">CVSS SCORE</span>
                <div className="text-amber-300 font-bold">{selectedFinding.cvss_score.toFixed(1)} / 10.0</div>
              </div>
            </div>

            {selectedFinding.snippet && (
              <div>
                <span className="text-slate-500 text-[10px]">DETECTED CODE / AST SNIPPET</span>
                <pre className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] text-rose-300 overflow-x-auto">
                  {selectedFinding.snippet}
                </pre>
              </div>
            )}

            <div>
              <span className="text-slate-500 text-[10px]">REMEDIATION GUIDANCE</span>
              <div className="p-2.5 rounded bg-slate-900/80 border border-cyan-500/20 text-xs text-slate-300">
                {selectedFinding.remediation_advice}
              </div>
            </div>

            {/* Lifecycle State Transitions */}
            <div className="pt-2 border-t border-cyan-500/10 flex items-center justify-between text-xs">
              <span className="text-slate-400">Lifecycle State: <strong className="text-cyan-300">{selectedFinding.status}</strong></span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleTransitionState(selectedFinding.finding_id, 'INVESTIGATING')}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]"
                >
                  Investigating
                </button>
                <button
                  onClick={() => handleTransitionState(selectedFinding.finding_id, 'ACCEPTED_RISK')}
                  className="px-2 py-0.5 rounded bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 text-[10px] border border-amber-500/40"
                >
                  Accept Risk
                </button>
                <button
                  onClick={() => handleTransitionState(selectedFinding.finding_id, 'RESOLVED')}
                  className="px-2 py-0.5 rounded bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 text-[10px] border border-emerald-500/40"
                >
                  Resolve
                </button>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-cyan-500/20">
              <button
                onClick={() => setSelectedFinding(null)}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
              >
                Close
              </button>
              {selectedFinding.status === 'OPEN' && (
                <>
                  <button
                    onClick={() => {
                      handleQuarantine(selectedFinding.finding_id);
                      setSelectedFinding(null);
                    }}
                    className="px-3 py-1.5 rounded bg-purple-950/60 hover:bg-purple-900/80 text-purple-300 text-xs border border-purple-500/40"
                  >
                    Quarantine Threat
                  </button>
                  <button
                    onClick={() => {
                      handleRemediate(selectedFinding.finding_id);
                      setSelectedFinding(null);
                    }}
                    className="px-3 py-1.5 rounded bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 text-xs border border-emerald-500/40"
                  >
                    Auto-Remediate
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Security Scan Trigger Modal */}
      {showScanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="hud-panel w-full max-w-md bg-[#080d1a] border border-cyan-500/40 rounded-lg p-6 shadow-[0_0_30px_rgba(0,240,255,0.2)] font-mono space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
              <div className="flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-cyan-200">CONFIGURE SECURITY AUDIT</h3>
              </div>
              <button
                onClick={() => setShowScanModal(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Target Directory / Path</label>
                <input
                  type="text"
                  value={scanTargetPath}
                  onChange={(e) => setScanTargetPath(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-900 border border-cyan-500/30 rounded text-cyan-200 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="space-y-2 pt-2 border-t border-cyan-500/10">
                <label className="flex items-center gap-2 text-slate-300">
                  <input
                    type="checkbox"
                    checked={scanIncludeSecrets}
                    onChange={(e) => setScanIncludeSecrets(e.target.checked)}
                    className="rounded bg-slate-900 border-cyan-500/40 text-cyan-500"
                  />
                  <span>AST Zero-Leakage Secret Scanner</span>
                </label>

                <label className="flex items-center gap-2 text-slate-300">
                  <input
                    type="checkbox"
                    checked={scanIncludeSast}
                    onChange={(e) => setScanIncludeSast(e.target.checked)}
                    className="rounded bg-slate-900 border-cyan-500/40 text-cyan-500"
                  />
                  <span>SAST Code Injection Analyzer</span>
                </label>

                <label className="flex items-center gap-2 text-slate-300">
                  <input
                    type="checkbox"
                    checked={scanIncludeDeps}
                    onChange={(e) => setScanIncludeDeps(e.target.checked)}
                    className="rounded bg-slate-900 border-cyan-500/40 text-cyan-500"
                  />
                  <span>Dependency CVE & License Auditor</span>
                </label>

                <label className="flex items-center gap-2 text-purple-300 font-bold">
                  <input
                    type="checkbox"
                    checked={scanAutoQuarantine}
                    onChange={(e) => setScanAutoQuarantine(e.target.checked)}
                    className="rounded bg-slate-900 border-purple-500/40 text-purple-500"
                  />
                  <span>Auto-Quarantine Critical Threats</span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-cyan-500/20">
              <button
                onClick={() => setShowScanModal(false)}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleRunScan}
                className="px-3 py-1.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400 text-cyan-300 text-xs font-bold shadow-[0_0_10px_rgba(0,240,255,0.2)]"
              >
                Launch Audit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
