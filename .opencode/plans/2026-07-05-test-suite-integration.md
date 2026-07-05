# Test Suite Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate target repo test suites as ground truth (extraction context) + penalty signal (CoverageScorer dimension) — test structure defines expected components, runtime coverage validates relationships.

**Architecture:** TestRunner creates per-repo venvs and runs pytest --cov. TestStructureAnalyzer extracts implied components from test file names. TestCoverageAnalyzer parses coverage JSON for module importance and cross-module test evidence. Results feed into OracleContextBuilder (pre-extraction) and CoverageScorer (post-extraction 5th dimension).

**Tech Stack:** Python 3.14, pytest, pytest-cov, venv module, subprocess, JSON coverage reports.

---

## Task 1: TestRunner — venv creation + pytest execution

**Files:**
- Create: `src/architecture_model/training/test_runner.py`
- Test: `tests/test_training/test_test_runner.py`

Core class that:
- Creates venv at `/tmp/test-repos/<name>/.venv`
- Installs repo (`pip install -e .`) + pytest + pytest-cov
- Runs `pytest --cov=<pkg> --cov-report=json -q --tb=no -x --timeout=60`
- Parses results into TestRunResult dataclass
- Caches results to `/tmp/test-repos/<name>/.test_cache.json`
- Best-effort: returns partial results on failure

---

## Task 2: TestStructureAnalyzer — static test file analysis

**Files:**
- Create: `src/architecture_model/training/test_analyzer.py`
- Test: `tests/test_training/test_test_analyzer.py`

Extracts:
- Implied components from test filenames (`test_client.py` → "Client")
- Test counts per file
- Test import graph (which test files import which source modules)

---

## Task 3: TestCoverageAnalyzer — runtime coverage parsing

**Files:**
- Modify: `src/architecture_model/training/test_analyzer.py` (add to same module)
- Test: `tests/test_training/test_test_analyzer.py`

Parses coverage.json to derive:
- Module importance scores (line coverage % → importance 0-1)
- Cross-module test evidence (test_X covers A+B → relationship evidence)
- Pass/fail rate

---

## Task 4: Integration — context + scoring + pipeline

**Files:**
- Modify: `src/architecture_model/training/oracle_context.py` — add test structure to context
- Modify: `src/architecture_model/training/coverage_scorer.py` — add test_alignment dimension
- Modify: `scripts/test_multi_repo.py` — wire TestRunner into pipeline
- Modify: `src/architecture_model/training/__init__.py` — exports

---

## Task 5: Validation — run on 3 repos and assess viability

Run the updated pipeline on click, python-dotenv, httpcore.
Compare CoverageScorer results with/without test_alignment dimension.
Assess whether test-implied components improve extraction quality.

---

## Execution Order

Sequential: Task 1 → 2 → 3 → 4 → 5 (each builds on the previous)
