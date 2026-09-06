#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo -e "\033[36m"
cat << "BANNER"
  ███╗   ██╗███████╗██╗   ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗ ██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚████╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝    ╚██╔╝  ██║   ██║╚════██║
  ██║ ╚████║███████╗   ██║   ╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝
  >> PERSONAL ENGINEERING CONTROL CENTER // v1.0.4 <<
BANNER
echo -e "\033[0m"

if [ "$1" == "--dev" ]; then
    echo -e "\033[33m[!] Starting in Full Hot-Reload Development Mode...\033[0m"
    python3 backend/server.py &
    BACKEND_PID=$!
    cd frontend && npm run dev -- --host 0.0.0.0 --port 5173 &
    FRONTEND_PID=$!
    echo -e "\033[32m[+] Cyber-HUD Live Dev Server: http://localhost:5173\033[0m"
    echo -e "\033[32m[+] NEXUS Core FastAPI Engine: http://localhost:8000\033[0m"
    echo -e "\033[35m[+] Interactive API Docs:     http://localhost:8000/docs\033[0m"
    trap "kill $BACKEND_PID $FRONTEND_PID" SIGINT SIGTERM EXIT
    wait
else
    echo -e "\033[32m[+] Starting Unified Production Engine...\033[0m"
    echo -e "\033[32m[+] Cyber-HUD Cockpit:     http://localhost:8000\033[0m"
    echo -e "\033[35m[+] Interactive API Docs:  http://localhost:8000/docs\033[0m"
    echo -e "\033[36m[+] Live WebSocket Stream: ws://localhost:8000/ws\033[0m"
    python3 backend/server.py
fi
