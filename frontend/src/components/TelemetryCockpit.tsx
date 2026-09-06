import React from 'react';
import { 
  Cpu, 
  HardDrive, 
  Server, 
  Network, 
  Clock, 
  Activity, 
  Radio, 
  ListOrdered, 
  ShieldCheck, 
  Layers 
} from 'lucide-react';
import type { Telemetry } from '../types';

interface TelemetryCockpitProps {
  telemetry: Telemetry | null;
}

export const TelemetryCockpit: React.FC<TelemetryCockpitProps> = ({ telemetry }) => {
  if (!telemetry) {
    return (
      <div className="hud-panel p-12 text-center text-cyan-400 font-mono text-sm animate-pulse">
        CONNECTING TO NEXUS HARDWARE TELEMETRY SENSORS...
      </div>
    );
  }

  const { cpu, memory, disk, network, uptime, processes, open_ports, agent_summary } = telemetry;

  return (
    <div className="space-y-6 font-mono">
      {/* Top HUD Telemetry Stats Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* CPU */}
        <div className="hud-panel p-4 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-cyan-400" /> CPU LOAD
            </span>
            <span className="text-[10px] text-cyan-400">{cpu.core_count} CORES</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-cyan-300 text-glow-cyan">
              {cpu.overall.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-3 border border-slate-800">
            <div
              className="h-full bg-cyan-400 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(5, cpu.overall))}%` }}
            ></div>
          </div>
        </div>

        {/* Memory */}
        <div className="hud-panel p-4 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs flex items-center gap-1.5">
              <Server className="w-4 h-4 text-emerald-400" /> SYSTEM RAM
            </span>
            <span className="text-[10px] text-emerald-400">{memory.percent}%</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-emerald-300 text-glow-emerald">
              {memory.used_gb}
            </span>
            <span className="text-xs text-slate-400">/ {memory.total_gb} GB</span>
          </div>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-3 border border-slate-800">
            <div
              className="h-full bg-emerald-400 transition-all duration-300"
              style={{ width: `${memory.percent}%` }}
            ></div>
          </div>
        </div>

        {/* Disk NVMe */}
        <div className="hud-panel p-4 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs flex items-center gap-1.5">
              <HardDrive className="w-4 h-4 text-amber-400" /> STORAGE
            </span>
            <span className="text-[10px] text-amber-400">{disk.percent}%</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-amber-300 text-glow-amber">
              {disk.used_gb}
            </span>
            <span className="text-xs text-slate-400">/ {disk.total_gb} GB</span>
          </div>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-3 border border-slate-800">
            <div
              className="h-full bg-amber-400 transition-all duration-300"
              style={{ width: `${disk.percent}%` }}
            ></div>
          </div>
        </div>

        {/* Network & Uptime */}
        <div className="hud-panel p-4 rounded-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs flex items-center gap-1.5">
              <Network className="w-4 h-4 text-purple-400" /> NETWORK I/O
            </span>
            <span className="text-[10px] text-purple-400">UP: {uptime.split(' ')[0]}</span>
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-xs text-slate-400">TX / RX</div>
              <div className="text-sm font-bold text-purple-300">
                {network.bytes_sent_mb} / {network.bytes_recv_mb} MB
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-400">PACKETS</div>
              <div className="text-xs text-slate-200">{network.packets_recv.toLocaleString()}</div>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-slate-400 mt-2">
            <Clock className="w-3 h-3 text-cyan-400" /> Uptime: {uptime}
          </div>
        </div>
      </div>

      {/* Core Breakdown & Hardware Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Multicore CPU Breakdown (6 cols) */}
        <div className="lg:col-span-6 hud-panel p-5 rounded-lg space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold text-cyan-300 tracking-wider">
                MULTICORE PROCESSOR ARRAY ({cpu.core_count} LOGICAL CORES)
              </span>
            </div>
            <span className="text-[10px] text-emerald-400 animate-pulse flex items-center gap-1">
              <Radio className="w-3 h-3" /> LIVE SAMPLING
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {cpu.cores.map((coreLoad, idx) => (
              <div key={idx} className="p-2.5 rounded bg-[#070b14] border border-cyan-500/20 space-y-1.5">
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>CORE #{idx}</span>
                  <span className="text-cyan-300 font-bold">{coreLoad.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-cyan-400 transition-all duration-300"
                    style={{ width: `${Math.min(100, Math.max(3, coreLoad))}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>

          {/* Agent Fleet Overview pill */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-300">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-400" /> AGENT ALLOCATION
            </span>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="text-emerald-400">{agent_summary.active} Active</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-400">{agent_summary.idle} Standby</span>
              <span className="text-slate-500">•</span>
              <span className="text-purple-400">{agent_summary.monitoring} Daemon</span>
            </div>
          </div>
        </div>

        {/* Right: Active Open Ports & Network Listeners (6 cols) */}
        <div className="lg:col-span-6 hud-panel p-5 rounded-lg space-y-4">
          <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-emerald-300 tracking-wider">
                NETWORK INTERFACES & LISTENING SERVICES
              </span>
            </div>
            <span className="text-[10px] text-slate-400">
              {open_ports.length} ACTIVE SOCKETS
            </span>
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto">
            {open_ports.map((p, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 rounded bg-[#070b14] border border-slate-800 text-xs hover:border-cyan-500/30 transition-all"
              >
                <div className="flex items-center gap-3">
                  <span className="px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 font-bold border border-cyan-500/30 text-[11px]">
                    :{p.port}
                  </span>
                  <div>
                    <div className="text-slate-200 font-bold">{p.service || 'Service Endpoint'}</div>
                    <div className="text-[10px] text-slate-500">{p.ip}</div>
                  </div>
                </div>

                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
                  {p.state || 'LISTENING'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Real Top System Processes */}
      <div className="hud-panel p-5 rounded-lg space-y-3">
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
          <div className="flex items-center gap-2">
            <ListOrdered className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold text-cyan-300 tracking-wider">
              REAL-TIME HOST PROCESS MONITOR (TOP MEMORY / CPU CONSUMERS)
            </span>
          </div>
          <span className="text-[10px] text-slate-400">PSUTIL LIVE SNAPSHOT</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-800 pb-2 text-[10px]">
                <th className="py-2">PID</th>
                <th className="py-2">PROCESS NAME</th>
                <th className="py-2">CPU %</th>
                <th className="py-2">MEMORY %</th>
                <th className="py-2 text-right">SECURITY STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {processes.map((proc) => (
                <tr key={proc.pid} className="hover:bg-slate-900/40 text-slate-300">
                  <td className="py-2 font-mono text-cyan-400">{proc.pid}</td>
                  <td className="py-2 font-bold text-slate-200">{proc.name}</td>
                  <td className="py-2">
                    <span className="text-cyan-300">{proc.cpu.toFixed(1)}%</span>
                  </td>
                  <td className="py-2">
                    <span className="text-emerald-300">{proc.memory.toFixed(1)}%</span>
                  </td>
                  <td className="py-2 text-right">
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      VERIFIED
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
