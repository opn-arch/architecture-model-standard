# Risk Assessment Document

## 1. Risk Register

| Risk ID | Description | Likelihood | Impact | Mitigation |
|---------|-------------|------------|--------|------------|
| R-01 | No defined inter-component dependencies; implicit coupling untracked | High | High | Define explicit `uses`/`depends_on` relationships; enforce via linting |
| R-02 | 10-stage pipeline failure cascades (COMP-2) | Medium | High | Add stage-level circuit breakers, retry logic, partial-result checkpointing |
| R-03 | COMP-1.4 Model Operations overly broad (7+ modules) | Medium | Medium | Decompose into focused sub-components with clear interfaces |
| R-04 | No test inventory or coverage data available | High | High | Establish coverage baselines; prioritize tests for COMP-1.2 and COMP-2.1 |
| R-05 | Single CLI entry point (COMP-8) as only interface | Medium | Medium | Add programmatic API surface; decouple CLI from orchestration |
| R-06 | Multi-language scanners (Py/TS/Kt) with no shared test harness | Medium | Medium | Create cross-language scanner conformance tests |
| R-07 | SE Document Suite (COMP-4.2) has 21+ files — high complexity | Medium | Low | Introduce template abstraction to reduce duplication |
| R-08 | YAML round-trip parsing data loss | Low | High | Property-based fuzz tests on parser/serializer round-trips |
| R-09 | Global learning store (COMP-11) state corruption | Low | High | Add schema versioning and integrity checks on learning store |
| R-10 | No security model for CLI input handling | Medium | Medium | Input sanitization on file paths, YAML deserialization (safe_load) |

## 2. Architectural Risks

### Implicit Coupling
The architecture defines **zero** explicit `uses` or `depends_on` relationships. This means coupling is invisible — COMP-5 (Orchestration) almost certainly depends on COMP-2 (Pipeline), COMP-3 (Manifest), and COMP-1 (Core), but nothing enforces layering constraints. Violations will go undetected.

### Single Points of Failure
- **COMP-2.1 (Pipeline Coordinator)** — all 10 stages flow through a single orchestrator. A bug here halts the entire extraction pipeline.
- **COMP-1.2 (Validation)** — every model must pass through this; a false-positive rejection blocks all downstream work.

### Scalability Limits
- The pipeline is sequential (10 stages). Large codebases will hit wall-clock time limits with no parallelization path evident.
- COMP-3.1 scanners do AST parsing in-process; large monorepos will pressure memory.

## 3. Technical Debt

| Area | Concern |
|------|---------|
| COMP-1.4 | 7 modules with overlapping concerns (slicer, differ, coverage, cluster, source_block_assign, source_block_quality, representativeness) — unclear boundaries |
| COMP-4.2 | 21+ files for SE docs suggests copy-paste patterns rather than shared abstractions |
| COMP-2.x | Each stage has a paired `*_types.py` — 10 type modules may diverge from actual runtime contracts |
| COMP-5.1/5.2 | Enrichment and Decomposition both exist in Orchestration AND Pipeline (COMP-2.5) — duplication of responsibility |
| Missing tests | Zero test coverage data; no evidence of integration tests across pipeline stages |

## 4. Dependency Risks

| Dependency | Risk |
|------------|------|
| PyYAML / ruamel.yaml | YAML deserialization vulnerabilities (CVE history); round-trip fidelity |
| Python 3.11+ | Narrow runtime support; limits deployment environments |
| GitHub Actions (CI) | Single CI vendor lock-in; no local reproducibility guarantee |
| AST module (stdlib) | Python version-specific grammar changes can break scanners |
| No declared external deps | Likely undocumented dependencies in scanner/pipeline code |

## 5. Security Risks

- **YAML deserialization**: If `yaml.safe_load` is not consistently used, arbitrary code execution is possible via crafted model files.
- **Path traversal**: CLI accepts file paths; no evidence of sandboxing or canonicalization.
- **Learning store (COMP-11)**: Persisted heuristics could be poisoned if the store is writable by untrusted processes.
- **No authentication model**: CLI assumes trusted local user; if exposed as a service, no access control exists.

## 6. Operational Risks

| Risk | Description |
|------|-------------|
| Silent data loss | Parser/merger (COMP-1.3) may silently drop unknown YAML fields during round-trip |
| Pipeline hangs | No timeout evidence on pipeline stages; an LLM-backed stage could hang indefinitely |
| Cache staleness | COMP-2.1 cache and COMP-3.1 scan_cache may serve stale results after code changes |
| No observability | Monitoring (COMP-12) exists but no evidence of structured logging, metrics export, or alerting |
| Partial pipeline output | If a mid-stage fails, unclear whether partial artifacts are cleaned up or left in inconsistent state |

---

**Overall Risk Posture: MEDIUM-HIGH** — The system has significant architectural complexity (100+ files, 12 top-level components) with no explicit dependency governance, no visible test coverage, and duplicated responsibilities across layers.