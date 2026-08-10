# Regen Readiness Metric Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Predictive score (0-100) per system/component/function that estimates regeneration success from enriched model data, with spot-check confirmation via LLM regen.

**Architecture:** Static metric in arch-std reads enriched .architecture-model.yaml, computes per-function/component/system scores. Spot-check + self-healing loop in opencode-arch uses LLM to regenerate targeted components and feeds failures back through learning loop.

**Tech Stack:** Python dataclasses, argparse CLI, existing model parser, opencode-arch LLM integration

---

## Phase 1: Static Metric (arch-std)

### Task 1: RegenReadiness types

**Files:**
- Create: `src/architecture_model/core/regen_readiness.py`
- Test: `tests/test_regen_readiness.py`

Types to define:
- `FunctionReadiness(name, score, has_body_hint, body_hint_quality, called_in_tests, blockers)`
- `ComponentReadiness(id, name, score, functions, body_hint_coverage, body_hint_trivial_ratio, test_contract_count, constant_coverage, signature_coverage, dep_stub_coverage, blockers)`
- `RegenReadiness(overall, grade, components, blockers, recommendation)`

### Task 2: Per-function scoring

Compute per-function readiness:
- body_hint present → base 50
- body_hint quality: trivial=+40, short=+25, complex=+10
- called_in_tests: +10 per test (cap at +30 from >=3 tests)
- Blocker: called in >=3 tests + no body_hint → "critical_no_hint"

### Task 3: Per-component scoring

Weighted formula:
- body_hint_coverage (sigs_with_hint / total_sigs): weight 25
- body_hint_trivial_ratio (trivial / total_hints): weight 15
- test_contract_density (min(1.0, contracts/10)): weight 20
- constant_coverage (defined / referenced_in_tests): weight 15
- signature_coverage (defined_sigs / called_in_tests): weight 15
- dep_stub_coverage (interfaces_defined / cross_deps): weight 10

### Task 4: System-level aggregation + grading

- overall = weighted avg of component scores (by file count)
- Grade: A(90+), B(70-89), C(50-69), D(30-49), F(<30)
- Blockers: components scoring <50
- Recommendation: actionable next step

### Task 5: CLI command `regen-score`

```
architecture-model regen-score [path] [--component ID] [--verbose]
```

### Task 6: Pipeline stage (optional, runs after validate)

Add `RegenScoreStage` to the pipeline that computes readiness if enriched model exists.

---

## Phase 2: Spot-Check (opencode-arch)

### Task 7: Spot-check component regen

`src/opencode_arch/regen/spot_check.py`:
- Accept component ID or subsystem name
- Format model data as regen prompt
- Call LLM, capture output
- Diff against actual source (structural)
- Return pass/fail + diagnostics

### Task 8: Self-healing loop

`src/opencode_arch/regen/self_heal.py`:
- On failure: classify pattern (MISSING_IMPL, WRONG_CONSTANT, etc.)
- Apply adaptive fix (enrich missing data, expand context)
- Retry (max 3 iterations)
- Record outcome in learning store

### Task 9: MCP tools

- `architect_regen_score` → static metric
- `architect_spot_check` → component/subsystem regen probe

---

## Testing Strategy

- Unit tests for scoring math with known inputs
- Integration test: load real enriched model, compute score, verify >=70
- Spot-check tests: mock LLM response, verify diff logic
