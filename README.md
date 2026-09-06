# NEXUS // Futuristic Personal Engineering Control Center

A high-performance, AI-native Personal Engineering Control Center designed with a **Cyber-HUD / Sci-Fi Tactical** aesthetic (obsidian black, neon cyan/amber/emerald glows, monospace live telemetry, glassmorphic panels, and zero-dependency Web Audio synthesizer).

---

## ⚡ Key Capabilities & Modules

### 1. Autonomous Agent Swarm Matrix (`/api/agents`)
- **Fleet Management**: Monitor multi-agent status (`ARCHITECT-01`, `SENTINEL-X`, `REVIEWER-PR`, `NEURAL-CODER`, `OPS-DEPLOYER`).
- **Autonomy Protocols**:
  - `Autonomous`: Full agent discretion.
  - `Guardrailed`: Sensitive operations require operator clearance.
  - `Step-by-Step`: Interactive step-by-step verification.
- **Mission Dispatcher**: Transmit technical directives to any specialized agent with real-time reasoning traces and token velocity counters.
- **Operator Guardrails**: Approve or reject sensitive shell/git actions before execution.
- **Emergency Panic Protocol**: 1-click master killswitch to abort all active neural threads immediately.

### 2. Live Host Telemetry Cockpit (`/api/telemetry` & `/ws`)
- **Real-Time Sampling**: Live WebSocket stream delivering 1000ms metrics.
- **Multicore CPU Array**: Overall usage + per-core load breakdown (8 logical cores).
- **RAM & Swap Footprint**: Used, available, and percentage gauges.
- **Disk Storage**: NVMe partition usage and capacity.
- **Real Host Process Monitor**: Live inspection of top memory/CPU-intensive host processes via `psutil`.
- **Socket & Port Scanner**: Detection of active listening sockets (`:8000`, `:5173`, etc.).

### 3. Workspace Mission Control & Tactical Macros (`/api/workspace`, `/api/macros`)
- **Repository Telemetry**: Live status of local repos (e.g. `/root/portfolio`), active git branches, commit logs, and modified file deltas.
- **Tactical Macros**:
  - `git:status`: Audit modified files and commit tree.
  - `system:diagnostics`: Multicore balance and memory verification.
  - `network:scan-ports`: Probe listening TCP sockets.
  - `memory:purge-cache`: Trigger Python cyclic garbage collector.
- **Integrated Tactical Console**: Live stream output directly in the HUD.

### 4. Neural Memory Matrix (`/api/memories`)
- Persistent architectural context vault.
- Store ADRs (Architecture Decision Records), agent directives, and prompt templates.
- Filter by category (`Architecture`, `Governance`, `API Contract`, `Directive`) or tag.
- Pin high-priority vectors to the top.

### 5. Cyber-HUD Cockpit Features
- **Omnibar Command Palette (`Ctrl+K` / `Cmd+K`)**: Keyboard-driven launcher for all views, macros, agent dispatches, and emergency protocols.
- **Web Audio API Synthesizer**: Built-in sci-fi mechanical clicks, warning alerts, success chimes, and panic alarms without external audio files.
- **CRT Scanlines Overlay**: Toggleable retro-futuristic scanlines shader.
- **Chronometer & Clock**: UTC + Local live mission timestamps.

---

## 🚀 Quick Start

### 1. Launch the Unified Production Cockpit
FastAPI serves both the backend API and the built Cyber-HUD frontend on port `8000`:

```bash
cd /root/control-center
./start.sh
```

Open:
- **Cockpit HUD**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live WebSocket Stream**: `ws://localhost:8000/ws`

### 2. Development Mode with Hot Reload
To run with live frontend Vite hot module reloading:

```bash
cd /root/control-center
./start.sh --dev
```
- **Vite Dev Server**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Engine**: [http://localhost:8000](http://localhost:8000)

---

## ⌨️ Hotkeys
- `Ctrl + K` or `Cmd + K`: Open Omnibar Command Palette
- `1`: Switch to Agent Swarm Matrix
- `2`: Switch to Telemetry Cockpit
- `3`: Switch to Workspace Mission Control
- `4`: Switch to Neural Memory Matrix
- `Esc`: Close modals
