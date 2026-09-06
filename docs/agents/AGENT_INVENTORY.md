# 🤖 NEXUS AI AGENT SWARM INVENTORY
**Swarm Size**: 13 Specialized Agents  
**Provider Adapters**: Google Gemini Pro/Flash, OpenAI GPT-4o, Deterministic Local Mock  
**Execution Tiers**: Autonomous (Read-only/Heuristic), Guardrailed (State modification), Step-by-Step (Production/Infra)  

---

## Complete Agent Roster

### 1. `agent-research` (SCOUT-CORE)
* **Role**: Codebase Discovery & Deep Research
* **Category**: Research
* **Autonomy Tier**: Autonomous
* **Risk Level**: `LOW`
* **Model**: Gemini 2.0 Pro Experimental
* **Avatar / Color**: 🔍 `#00ffcc`
* **Allowed Tools**: `codebase_search`, `read_file`, `web_search`, `ast_grep`
* **Capabilities**: AST symbol navigation, Architecture reverse-engineering, External documentation lookup
* **Execution Policy**: Fully autonomous read-only operation. Zero file modification permitted.

### 2. `agent-dev` (ARCH-DEV)
* **Role**: Full-Stack Architect & Core Implementation
* **Category**: Development
* **Autonomy Tier**: Guardrailed
* **Risk Level**: `MEDIUM`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 💻 `#3b82f6`
* **Allowed Tools**: `write_file`, `replace_file`, `run_tests`, `refactor_engine`
* **Capabilities**: Feature implementation, Code refactoring, Architectural alignment
* **Execution Policy**: Guardrailed file modification. Runs unit tests post-edit. Large deletions require operator clearance.

### 3. `agent-security` (SENTINEL-SEC)
* **Role**: Secret Leak Auditor & AST Vulnerability Scanner
* **Category**: Security
* **Autonomy Tier**: Autonomous
* **Risk Level**: `HIGH`
* **Model**: Gemini 2.0 Flash Security
* **Avatar / Color**: 🛡️ `#ff3366`
* **Allowed Tools**: `regex_audit`, `cve_lookup`, `secret_detector`, `iam_inspector`
* **Capabilities**: Key leak detection, Dependency CVE audit, Zero-trust verification
* **Execution Policy**: Autonomous scanning. Quarantine and permission alterations require human clearance.

### 4. `agent-qa` (VERIFY-QA)
* **Role**: Automated Test Synthesizer & Quality Engine
* **Category**: QA
* **Autonomy Tier**: Autonomous
* **Risk Level**: `LOW`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 🧪 `#10b981`
* **Allowed Tools**: `pytest_runner`, `jest_runner`, `coverage_evaluator`, `test_generator`
* **Capabilities**: Test suite synthesis, Boundary fuzzing, Regression verification
* **Execution Policy**: Autonomous test execution and report generation.

### 5. `agent-docs` (CHRONICLER)
* **Role**: Architecture Scribe & Knowledge Base Custodian
* **Category**: Documentation
* **Autonomy Tier**: Autonomous
* **Risk Level**: `LOW`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 📚 `#8b5cf6`
* **Allowed Tools**: `markdown_builder`, `diagram_generator`, `docstring_extractor`
* **Capabilities**: Architectural Decision Records (ADRs), API spec synchronization, Runbook compilation
* **Execution Policy**: Autonomous document authoring within `/docs` directory.

### 6. `agent-devops` (PIPELINE-OPS)
* **Role**: CI/CD Pipeline & GitHub Actions Automation
* **Category**: DevOps
* **Autonomy Tier**: Guardrailed
* **Risk Level**: `HIGH`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 🚀 `#f59e0b`
* **Allowed Tools**: `workflow_linter`, `action_dispatcher`, `secret_validator`
* **Capabilities**: GitHub Actions configuration, OIDC WIF verification, Release staging
* **Execution Policy**: Workflow generation permitted. Live pipeline triggers requiring deployment role require human gate.

### 7. `agent-infra` (TERRA-FORM)
* **Role**: Cloud Run & Keyless GCP Provisioning
* **Category**: Infrastructure
* **Autonomy Tier**: Guardrailed
* **Risk Level**: `HIGH`
* **Model**: Gemini 2.0 Pro
* **Avatar / Color**: 🏗️ `#06b6d4`
* **Allowed Tools**: `gcloud_cli`, `cloudbuild_submit`, `wif_inspector`
* **Capabilities**: Keyless WIF verification, Service Account configuration, Cloud Run manifest staging
* **Execution Policy**: Strict read and plan mode autonomous. Live provisioning requires operator clearance.

### 8. `agent-data` (SYNAPSE-DB)
* **Role**: Schema Migration & Read-Replica Analyst
* **Category**: Data
* **Autonomy Tier**: Guardrailed
* **Risk Level**: `HIGH`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 🗄️ `#ec4899`
* **Allowed Tools**: `schema_diff`, `migration_generator`, `query_optimizer`
* **Capabilities**: Backward-compatible schema migrations, Index optimization, Read-replica performance
* **Execution Policy**: Schema migration generation autonomous. Execution against production databases requires human gate.

### 9. `agent-ux` (INTERFACE-UX)
* **Role**: HUD Cyberpunk Component Architect
* **Category**: Frontend
* **Autonomy Tier**: Autonomous
* **Risk Level**: `LOW`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 🎨 `#a855f7`
* **Allowed Tools**: `component_builder`, `css_compiler`, `asset_optimizer`
* **Capabilities**: React 19 UI widgets, Cyberpunk HUD themes, Audio-visual telemetry feedback
* **Execution Policy**: Autonomous frontend component refinement within `frontend/src`.

### 10. `agent-seo` (RADAR-METRICS)
* **Role**: Performance, Vitals & Search Indexer
* **Category**: Analytics
* **Autonomy Tier**: Autonomous
* **Risk Level**: `LOW`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 📡 `#14b8a6`
* **Allowed Tools**: `lighthouse_eval`, `meta_auditor`, `sitemap_builder`
* **Capabilities**: Web vitals optimization, Structured metadata verification, Search engine preview
* **Execution Policy**: Autonomous inspection and report generation.

### 11. `agent-cost` (PRUDENCE-COST)
* **Role**: Zero-Spend Guard & Quota Maximizer
* **Category**: FinOps
* **Autonomy Tier**: Autonomous
* **Risk Level**: `LOW`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 💰 `#eab308`
* **Allowed Tools**: `billing_auditor`, `quota_checker`, `pricing_calculator`
* **Capabilities**: Free-tier limit enforcement, Spend trajectory modeling, Unlinked billing validation
* **Execution Policy**: Autonomous quota auditing. Zero spending allowance strictly enforced.

### 12. `agent-mon` (TELEM-BEACON)
* **Role**: Real-Time Health & Log Correlation Probe
* **Category**: Monitoring
* **Autonomy Tier**: Autonomous
* **Risk Level**: `LOW`
* **Model**: Gemini 2.0 Flash
* **Avatar / Color**: 🚨 `#ef4444`
* **Allowed Tools**: `trace_collector`, `metric_aggregator`, `anomaly_detector`
* **Capabilities**: OpenTelemetry span ingestion, Anomaly detection, Error rate calculation
* **Execution Policy**: Continuous background telemetry monitoring.

### 13. `agent-recovery` (PHOENIX-REC)
* **Role**: Incident Auto-Remediation & Rollback Dispatcher
* **Category**: SRE
* **Autonomy Tier**: Guardrailed
* **Risk Level**: `CRITICAL`
* **Model**: Gemini 2.0 Pro
* **Avatar / Color**: 🔥 `#f97316`
* **Allowed Tools**: `rollback_executor`, `service_restart`, `panic_interceptor`
* **Capabilities**: Traffic redirection, Revision rollback, Emergency quarantine
* **Execution Policy**: Emergency recovery protocols require operator confirmation except under active Panic Protocol.
