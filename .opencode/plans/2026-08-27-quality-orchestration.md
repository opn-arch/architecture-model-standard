# Quality Orchestration + Diff-Aware Doc Updates

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire together quality modules into a single orchestration loop, add diff-aware SE doc regeneration, and produce per-subsystem update summaries.

**Architecture:** Quality orchestrator chains code_review → model_feedback → apply → diff → selective doc regen → dashboard. The SE generator gains a `regenerate_affected()` function that uses `ModelDiff.affected_artifacts()` to only regenerate impacted docs.

**Tech Stack:** Python dataclasses, existing quality/ and docs/se/ modules

---

### Task A: Quality Orchestrator

**Files:**
- Create: `src/architecture_model/quality/orchestrator.py`
- Create: `tests/test_quality_orchestrator.py`
- Modify: `src/architecture_model/quality/__init__.py` (add lazy import)

### Task B: Diff-Aware Doc Regeneration

**Files:**
- Modify: `src/architecture_model/docs/se/generator.py` (add `regenerate_affected()`)
- Create: `tests/test_diff_aware_docs.py`

### Task C: Update Summaries

**Files:**
- Create: `src/architecture_model/quality/update_summary.py`
- Create: `tests/test_update_summary.py`

---

## Execution: 3 tasks, TDD, frequent commits
