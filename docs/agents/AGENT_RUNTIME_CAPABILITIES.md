# Agent Runtime Capabilities Matrix

## 1. Classification Methodology
In accordance with implementation truth standards, every agent persona capability is strictly classified into one of four empirical states:
- **REAL**: Backed by actual local code execution, verified with automated tests.
- **PARTIAL**: Basic local tool execution exists, but higher-order automation or external integration is incomplete.
- **SIMULATED**: Deterministic offline mock response returned without external provider or live system side-effects.
- **NOT_IMPLEMENTED**: Capability is absent or explicitly blocked pending future cloud architecture phases.

## 2. Capability Audit Matrix

| Agent ID | Name | Local Execution | Code Modification | Test Execution | Security Audits | GitHub PR/Write | Cloud Ops | Status Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `agent-research` | RESEARCH-01 | REAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-dev` | DEVELOPER-02 | REAL | REAL (Fixture repo) | REAL (Fixture repo) | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-security` | SENTINEL-SEC | REAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL (Regex secrets) | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-qa` | QA-VERIFIER | REAL | NOT_IMPLEMENTED | REAL (Pytest discovery) | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-docs` | DOC-CHRONICLER | REAL | REAL (ADRs & Docs) | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-data` | DATA-CATALYST | REAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-cost` | COST-OPTIMIZER | REAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-mon` | METRICS-PROBER | REAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-recovery` | RECOVERY-GUARDIAN | REAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | REAL |
| `agent-devops` | DEVOPS-RUNNER | PARTIAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | PARTIAL |
| `agent-infra` | INFRA-ENGINEER | PARTIAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | PARTIAL |
| `agent-ux` | UX-TACTICIAN | PARTIAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | PARTIAL |
| `agent-seo` | SEO-AMPLIFIER | PARTIAL | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | NOT_IMPLEMENTED | PARTIAL |

## 3. Detailed Persona Execution Verification

### Developer Agent (`agent-dev`): REAL
- Executes in isolated testbed: `/root/control-center/data/fixtures/developer_test_repo`.
- Completes 7-phase sequence:
  1. Inspect repository state (`git.status`).
  2. Synthesize feature plan.
  3. Read target code file (`calculator.py`).
  4. Apply modifications (`multiply` feature).
  5. Run test runner (`pytest`) verifying test pass.
  6. Extract git diff (`git.diff`).
  7. Revert cleanly upon failure flag (`git checkout .`).

### QA Agent (`agent-qa`): REAL
- Automatically detects test framework (`pytest`).
- Executes test suite with recursion prevention flags (`--ignore=tests/test_agent_runtime.py`, etc.).
- Parses real stdout to extract assertions passed, failed, and run duration.

### Security Agent (`agent-security`): REAL
- Scans directory tree for exposed PEM keys, JWTs, and GCP service account keys.
- Categorizes findings into `REAL_FINDING` (actionable leak), `INFORMATIONAL` (safe config), and `UNAVAILABLE_CHECK` (uninstalled tools).

### Documentation Agent (`agent-docs`): REAL
- Path-restricted writer allowing creation only inside `docs/` and `data/memory_vault.json`.
- Authors structured Architecture Decision Records (ADRs) with UUIDs and timestamp tracking.

### AI Router & Provider Subsystem: REAL (MockEngine Active)
- Abstract interface `AIProvider` supports `generate()`, `stream()`, `health()`, and `metadata()`.
- Real cloud providers (`VertexAIProvider`, `GeminiAPIProvider`, `AnthropicProvider`) return status `NOT_CONFIGURED` when API keys are absent.
- `MockEngine` active as deterministic fallback with $0.00 cost.
