# ⚡ ECO CLI Operator Manual

The `eco` command-line utility is installed at `/usr/local/bin/eco` and linked to the NEXUS Control API.

### Usage Synopsis
```bash
eco status                   # Live system load, cloud project, fleet counts
eco projects                 # Registry matrix with health scores & providers
eco agents                   # Swarm agent registry with risk tiers & status
eco audit <project_id>       # Run multi-factor audit
eco test <project_id>        # Run automated tests
eco security <project_id>    # AST and secret leak scan
eco deploy <project_id>      # Deploy project (enforces human approval gate)
eco approvals list           # List pending gates
eco approvals approve <id>   # Approve high-risk action
eco approvals reject <id>    # Reject high-risk action
eco brief                    # Instant Morning Engineering Brief
eco cost                     # Zero-cost guardrail & free tier status
eco secrets                  # Safe secret metadata inspection
eco automations              # View scheduled routines
eco automations run <id>     # Run scheduled routine
eco traces                   # Inspect real-time distributed traces
eco "<natural prompt>"       # AI directive routing
```

### Examples
- `eco "portfolio ka audit karo"`: Dispatches research agent autonomously.
- `eco "production deploy kardo"`: Intercepted by Policy Rule `pol-004`, generates approval token.
