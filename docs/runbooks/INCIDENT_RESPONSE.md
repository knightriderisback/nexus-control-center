# 🚨 Incident Response & Panic Protocol Runbook

## Emergency Master Panic Protocol
In case of anomalous agent behavior, rogue execution, or security alert:
- Via Dashboard: Click the **PANIC PROTOCOL** button in HUD Header.
- Via API: `curl -X POST http://localhost:8000/api/panic`
- Effect:
  - Immediately aborts all running agent tasks.
  - Flushes in-flight dispatch queues.
  - Records CRITICAL audit event in `audit_trail.jsonl`.
  - Sets system status to `HALTED`.

## Service Rollback Procedure
If a production deployment causes regressions:
1. Run: `bash /root/control-center/scripts/rollback.sh`
2. Or use CLI: `eco deploy rollback`
