# Session Report: Copilot-Relay PoC Experiment

**Date:** 2026-07-06
**Session type:** Test-guided code generation with frontier model comparison
**Package version:** 0.3.0-dev
**Schema version:** 1.0

---

## Executive Summary

This session completed a 10-task test-guided code generation plan (Tasks 1--10) and then re-ran the PoC using a copilot-relay frontier model in place of the local qwen2.5:7b baseline. The frontier model achieved a **3x improvement** on python-dotenv (11.1% to 33.3%) but exposed new failure modes: single-shot truncation, rate limiting, and import-structure mismatches that prevent larger repos from passing any tests. Infrastructure built during the session (per-component generation, preamble stripping, retry guards) partially addresses these issues but significant work remains on import resolution and architecture-model filtering.

---

## 1. Objectives

1. Execute the full 10-task plan for test-guided code generation.
2. Swap the Ollama/qwen2.5:7b surrogate for a copilot-relay frontier model and measure the difference.
3. Identify root causes for any regressions or new failure modes.
4. Catalog improvement areas for prioritized follow-up.

---

## 2. PoC Results

### 2.1 Baseline (qwen2.5:7b via Ollama)

| Repo | Pass Rate | Iterations | Time | Target |
|------|-----------|------------|------|--------|
| python-dotenv | 11.1% | 3 (converged) | 210s | >50% |
| colorama | 0% | 3 (converged) | 90s | >40% |
| arrow | 0% | 3 (converged) | 125s | >30% |
| click | 0% | 3 (converged) | 198s | >15% |

All four repos converged within 3 iterations but none met their target pass rate. qwen2.5:7b produced structurally plausible code but lacked the precision to satisfy real test suites.

### 2.2 Copilot-Relay (Frontier Model)

| Repo | Pass Rate | Iterations | Time | Notes |
|------|-----------|------------|------|-------|
| python-dotenv | 33.3% | 3 (converged) | 201s | 3x improvement, all 6 components generated |
| colorama | DNF | -- | >900s | 15 components (9 demo files), rate limited |
| arrow | 0% | 3 (converged) | 477s | 11 components, 60K chars generated, import errors |
| click | DNF | -- | >900s | 38 components, too many for sequential generation |

**Key observations:**

- **python-dotenv** saw a genuine quality leap: the frontier model produced correct implementations for 3 of 9 test files, compared to 1 of 9 with qwen2.5:7b.
- **colorama** and **click** did not finish (DNF) due to component count and rate limiting. The architecture model for colorama includes 9 demo files that should not be generated; click has 38 components which overwhelm sequential generation.
- **arrow** generated ~60K characters of code across 11 components but scored 0% because inter-module imports use absolute paths (`from arrow.factory import ...`) instead of the relative paths the test harness expects.

---

## 3. Infrastructure Built During Session

### 3.1 CopilotRelaySurrogate

**Location:** `scripts/test_guided_round_trip.py`

Adapter that calls copilot-relay's SSE endpoint instead of Ollama's `/api/generate`.

- **Request format:** `{"content": "<user prompt>", "system": "<system prompt>"}`
- **Endpoint:** `POST http://localhost:8400/chat`
- **Response:** SSE stream with `data: {"type": "chunk", "content": "..."}` events, terminated by `data: {"type": "done"}`
- **Error handling:** Detects `{"type": "error"}` events and raises immediately
- **Timeout:** 180s per request (up from default)
- **Preamble stripping:** Removes non-code text (markdown explanations, mermaid diagrams) that the frontier model prepends to responses

### 3.2 PerComponentGenerator

**Location:** `scripts/test_guided_round_trip.py` (subclass of `TestGuidedGenerator`)

Generates each component individually instead of requesting all modules in a single prompt.

- Overrides `_initial_generation()` to loop through components one at a time
- Overrides `_targeted_retry()` to retry only the specific failing components
- Uses focused natural-language prompts instead of heavy YAML system prompts
- Adds regression guard: only retries components that are known from the architecture model (prevents phantom module generation)
- 1-second delay between requests to avoid rate limiting

### 3.3 Supporting Changes

- `_strip_preamble()` -- removes markdown fences, mermaid blocks, and explanatory text before code extraction
- `_fix_relative_imports()` in `CodeWriter` -- rewrites absolute imports to relative (partial fix)
- Retry logic with exponential backoff for transient SSE failures

---

## 4. Root Causes Identified

### RC-1: Single-shot truncation

Asking the frontier model to generate all modules at once produces truncated or off-topic output. The model emits mermaid diagrams, architectural commentary, and incomplete modules instead of the requested code. **Mitigated** by per-component generation.

### RC-2: Import structure mismatch

Generated code uses absolute imports (`from arrow.factory import ArrowFactory`) instead of relative imports (`from .factory import ArrowFactory`). Each module may be correct in isolation, but inter-module imports break at test time because the test harness installs code under a temporary package root. **Partially fixed** by `CodeWriter._fix_relative_imports()`, but edge cases remain.

### RC-3: Rate limiting

copilot-relay returns `{"type": "error"}` events after multiple large requests in succession. Some requests hang indefinitely with no response. **Mitigated** by inter-request delays, 180s timeouts, and retry logic, but repos with many components (colorama, click) still exceed limits.

### RC-4: Architecture model quality

The architecture model includes irrelevant files -- demo scripts (`demos/`), test fixtures, `__main__.py` stubs -- that inflate the component count and waste generation budget. colorama's 15-component model includes 9 demo files that are not exercised by any test. **Not addressed.**

### RC-5: Retry regression

The retry mechanism regenerated "phantom" modules not present in the architecture model, which overwrote working code. For example, a retry for `arrow` generated a `utils.py` module that was not in the component list, clobbering the existing generated code. **Fixed** by filtering retry targets against `generated_components`.

### RC-6: Duplicate modules from splicing

`_splice_component()` appends code instead of replacing it when the module header (comment marker) doesn't exactly match the existing header. This produces files with duplicate class definitions. **Not addressed.**

---

## 5. Comprehensive Improvement Areas (28 Items)

### A. Test-Guided Generation (Items 1--10)

| # | Issue | Status |
|---|-------|--------|
| 1 | Single-shot generation truncation | FIXED (per-component generation) |
| 2 | Non-code preamble in responses | FIXED (`_strip_preamble`) |
| 3 | Retry regenerates phantom modules | FIXED (filter against `generated_components`) |
| 4 | Retry regression (no guard) | PARTIALLY FIXED (retries limited to known components) |
| 5 | Heavy YAML prompts fail with copilot-relay | FIXED (focused NL prompts) |
| 6 | copilot-relay rate limiting | MITIGATED (delays, timeouts, retry) |
| 7 | Import structure (absolute vs relative) | PARTIALLY FIXED (`CodeWriter._fix_relative_imports`) |
| 8 | Convergence threshold too aggressive | NOT ADDRESSED |
| 9 | Architecture model includes irrelevant files | NOT ADDRESSED |
| 10 | Duplicate modules from retry splicing | NOT ADDRESSED |

### B. Pipeline Architecture (Items 11--20)

| # | Issue |
|---|-------|
| 11 | Entity ID collisions in extraction |
| 12 | Prompt precision for oracle/surrogate |
| 13 | Reconstruction fidelity in round-trip |
| 14 | Facade-pattern test mapping confuses contract miner |
| 15 | Manifest coverage gaps |
| 16 | Large-repo handling (50+ components overwhelm context) |
| 17 | Multi-model benchmarking needed |
| 18 | Schema v1.1 universality extensions |
| 19 | Interface enforcement from manifest |
| 20 | Enhanced multi-pass extraction |

### C. Documentation & Hygiene (Items 21--28)

| # | Issue |
|---|-------|
| 21 | README severely underdeveloped (16 lines) |
| 22 | No LICENSE file |
| 23 | No CONTRIBUTING guide |
| 24 | No documentation of copilot-relay integration |
| 25 | No PoC results analysis |
| 26 | Significant uncommitted work (3 modified, 17 untracked) |
| 27 | Plans scattered (`docs/plans/` vs `.opencode/plans/`) |
| 28 | Changelog in wrong location (`docs/` not root) |

---

## 6. Behavioral Assessment

### 6.1 Test Suite Health

- **904+ tests passing** (619 in training module alone)
- **Test-to-source ratio:** 1.13:1 (lines) -- excellent coverage density
- **0 TODO/FIXME/HACK comments** in source
- **1 pre-existing failure** in `test_config_loader.py` (unrelated to this session)

### 6.2 Code Quality Metrics

| Metric | Value |
|--------|-------|
| Training module files | 39 |
| Training module lines | 10,662 |
| Training test files | 42 |
| Training test lines | 12,048 |
| Docstring coverage | 100% (every module) |
| Type system | Clean dataclass-based |

### 6.3 Generation Quality Trajectory

| Version | Capability |
|---------|-----------|
| v0.2.0 | MPC training loop infrastructure only |
| v0.3.0 | Test-guided generation achieves 33.3% on python-dotenv |
| Next | Import resolution + model filtering could push to 50%+ |

---

## 7. What Would Help Next (Prioritized)

### Priority 1: Import resolution post-processing

Fix inter-module imports based on what was actually generated. Currently the single biggest blocker across both backends -- arrow generated correct module bodies but 0% of tests passed because imports could not resolve. A post-generation pass that rewrites `from package.module import X` to `from .module import X` based on the known generated file set would have immediate impact.

### Priority 2: Architecture model filtering

Exclude demo scripts, test fixtures, `__main__.py` stubs, and other non-functional files from the component list before generation. This directly reduces colorama from 15 to 6 components and click from 38 to ~20, making both viable for sequential generation within rate limits.

### Priority 3: Full regression guard

Track the best pass rate achieved so far and revert to the best-known code when a retry worsens the pass rate. Currently retries can degrade working code with no recovery mechanism.

### Priority 4: Parallel generation for Ollama

Generate components concurrently when using the local Ollama backend (no rate limit applies). This would cut generation time by 3--5x for repos with many components.

### Priority 5: Retry splicing fix

Replace existing module code instead of appending when a component is regenerated. Requires matching on module path rather than header comment text.

---

## 8. Appendix

### 8.1 Result Files

| File | Description |
|------|-------------|
| `results/test-guided/test_guided_python-dotenv_2026-07-06_044619.json` | Best dotenv result (33.3%, copilot-relay) |
| `results/test-guided/test_guided_python-dotenv_2026-07-06_034054.json` | Best dotenv result (11.1%, qwen2.5:7b) |
| `results/test-guided/test_guided_arrow_2026-07-06_051014.json` | Arrow result (0%, copilot-relay) |

### 8.2 Copilot-Relay API Reference

| Property | Value |
|----------|-------|
| Chat endpoint | `POST http://localhost:8400/chat` |
| Health endpoint | `GET http://localhost:8400/health` |
| Health response | `{"status": "ok", "pending": 0}` |
| Request body | `{"content": "<user prompt>", "system": "<system prompt>"}` |
| Response format | SSE stream |
| Chunk event | `data: {"type": "chunk", "content": "..."}` |
| Done event | `data: {"type": "done"}` |
| Error event | `data: {"type": "error", ...}` |

### 8.3 Key Source Files

| File | Role |
|------|------|
| `scripts/test_guided_round_trip.py` | PoC script with `CopilotRelaySurrogate` + `PerComponentGenerator` |
| `src/architecture_model/training/test_guided_generator.py` | Core generator with retry loop and convergence detection |
| `src/architecture_model/training/surrogate.py` | Ollama adapter (`OllamaSurrogate`) |

### 8.4 Session Timeline

| Time (approx.) | Event |
|----------------|-------|
| 03:00 | Session start, plan review |
| 03:15 | Tasks 1--5 executed (core generation infrastructure) |
| 03:40 | Tasks 6--10 executed (retry, convergence, CLI) |
| 04:00 | Baseline runs complete (qwen2.5:7b, all 4 repos) |
| 04:30 | CopilotRelaySurrogate built and tested |
| 04:46 | python-dotenv achieves 33.3% with copilot-relay |
| 05:00 | PerComponentGenerator built to address truncation |
| 05:10 | arrow run completes (0%, import errors identified) |
| 05:30 | colorama and click DNF (rate limiting, component count) |
| 06:00 | Root cause analysis and improvement catalog |
| 06:30 | Session wrap-up |
