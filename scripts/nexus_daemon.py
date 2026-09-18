#!/usr/bin/env python3
"""
NEXUS Local Production Daemon & Process Supervisor.
Manages the lifecycle of the NEXUS Control Plane API service:
- Clean daemonization with PID file tracking and session detachment
- Health probing on startup
- Graceful SIGTERM shutdown with SIGKILL escalation
- Status, health, and structured log tailing
"""

import os
import sys
import time
import signal
import psutil
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

WORKSPACE_ROOT = Path("/root/control-center")
BACKEND_DIR = WORKSPACE_ROOT / "backend"
DATA_DIR = WORKSPACE_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"
PID_FILE = DATA_DIR / "nexus.pid"
LOG_FILE = LOGS_DIR / "nexus.log"

DEFAULT_HOST = os.getenv("NEXUS_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("NEXUS_PORT", "8000"))
HEALTH_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/api/health"
TELEMETRY_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/api/telemetry"

def ensure_directories():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

def read_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        if psutil.pid_exists(pid):
            # Verify process command line contains uvicorn or server
            try:
                proc = psutil.Process(pid)
                cmdline = " ".join(proc.cmdline())
                if "server" in cmdline or "uvicorn" in cmdline or "python" in cmdline:
                    return pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        # Stale PID file
        PID_FILE.unlink(missing_ok=True)
        return None
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        return None

def probe_health(timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    import json
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "nexus-daemon/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode())
    except Exception:
        return None
    return None

def cmd_status() -> int:
    pid = read_pid()
    health = probe_health(timeout=1.5)
    
    print("==================================================")
    print("      NEXUS LOCAL DAEMON SERVICE STATUS           ")
    print("==================================================")
    if pid and health:
        proc = psutil.Process(pid)
        mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
        print(f"  Status:       \033[92mONLINE (RUNNING)\033[0m")
        print(f"  PID:          {pid}")
        print(f"  Endpoint:     http://{DEFAULT_HOST}:{DEFAULT_PORT}")
        print(f"  Memory (RSS): {mem_mb} MB")
        print(f"  System:       {health.get('system', 'Personal Engineering OS')}")
        print(f"  Version:      {health.get('version', '1.0.0')}")
        print(f"  Log File:     {LOG_FILE}")
        return 0
    elif pid and not health:
        print(f"  Status:       \033[93mDEGRADED (PID {pid} active, API non-responsive)\033[0m")
        print(f"  Log File:     {LOG_FILE}")
        return 1
    else:
        print("  Status:       \033[91mSTOPPED (INACTIVE)\033[0m")
        print(f"  Host/Port:    {DEFAULT_HOST}:{DEFAULT_PORT}")
        print(f"  PID File:     {PID_FILE}")
        return 3

def cmd_start() -> int:
    ensure_directories()
    existing_pid = read_pid()
    if existing_pid:
        print(f"[NEXUS DAEMON] Already running with PID {existing_pid}.")
        return 0

    print(f"[NEXUS DAEMON] Launching NEXUS Control API on {DEFAULT_HOST}:{DEFAULT_PORT}...")
    with open(LOG_FILE, "a") as log_out:
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "server:app",
                "--host", DEFAULT_HOST,
                "--port", str(DEFAULT_PORT),
                "--no-access-log"
            ],
            cwd=str(BACKEND_DIR),
            stdout=log_out,
            stderr=log_out,
            start_new_session=True
        )

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    # Health probe verification loop (up to 10 seconds)
    print(f"[NEXUS DAEMON] Process spawned (PID {proc.pid}). Probing health check...", end="", flush=True)
    healthy = False
    for _ in range(20):
        time.sleep(0.5)
        if probe_health(timeout=1.0):
            healthy = True
            break
        print(".", end="", flush=True)

    if healthy:
        print(f"\n\033[92m✓ NEXUS Control Plane ONLINE at http://{DEFAULT_HOST}:{DEFAULT_PORT} (PID {proc.pid})\033[0m")
        return 0
    else:
        print(f"\n\033[91m✗ Daemon spawned but failed health probe within 10s. Check logs at {LOG_FILE}\033[0m")
        return 1

def cmd_stop() -> int:
    pid = read_pid()
    if not pid:
        print("[NEXUS DAEMON] Service is not running.")
        PID_FILE.unlink(missing_ok=True)
        return 0

    print(f"[NEXUS DAEMON] Stopping NEXUS Control Plane (PID {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        print("[NEXUS DAEMON] Process already exited.")
        return 0

    # Wait up to 5 seconds for graceful shutdown
    graceful = False
    for _ in range(10):
        time.sleep(0.5)
        if not psutil.pid_exists(pid):
            graceful = True
            break

    if not graceful:
        print(f"[NEXUS DAEMON] PID {pid} did not exit cleanly. Sending SIGKILL...")
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    PID_FILE.unlink(missing_ok=True)
    print("\033[92m✓ NEXUS Control Plane stopped cleanly.\033[0m")
    return 0

def cmd_restart() -> int:
    cmd_stop()
    time.sleep(1.0)
    return cmd_start()

def cmd_logs(lines: int = 30) -> int:
    if not LOG_FILE.exists():
        print(f"[NEXUS DAEMON] No log file found at {LOG_FILE}")
        return 1
    print(f"--- Showing last {lines} lines of {LOG_FILE} ---")
    try:
        res = subprocess.run(["tail", "-n", str(lines), str(LOG_FILE)], capture_output=True, text=True)
        print(res.stdout)
        return 0
    except Exception as e:
        print(f"Failed to read logs: {e}")
        return 1

def main():
    if len(sys.argv) < 2:
        sys.exit(cmd_status())

    action = sys.argv[1].lower()
    if action == "start":
        sys.exit(cmd_start())
    elif action == "stop":
        sys.exit(cmd_stop())
    elif action == "restart":
        sys.exit(cmd_restart())
    elif action == "status":
        sys.exit(cmd_status())
    elif action == "logs":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        sys.exit(cmd_logs(lines))
    elif action in ["help", "--help", "-h"]:
        print("Usage: python3 scripts/nexus_daemon.py [start|stop|restart|status|logs [N]]")
        sys.exit(0)
    else:
        print(f"Unknown action '{action}'. Valid actions: start, stop, restart, status, logs")
        sys.exit(1)

if __name__ == "__main__":
    main()
