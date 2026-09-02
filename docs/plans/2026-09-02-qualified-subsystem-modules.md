# Qualified Subsystem Modules Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add collision-free subsystem module pages, navigation, history, and comments to the self-contained HTML viewer.

**Architecture:** Extend the safe submodel loader to return qualified modules and component-to-module links. Load manifests from bounded paths without per-system scans, filter records by model ownership, and synthesize stubs when records are unavailable.

**Tech Stack:** Python, pytest, embedded JSON, vanilla JavaScript, Node.js syntax/runtime checks.

---

### Task 1: Specify Qualified Module Data

**Files:**
- Modify: `tests/test_visualize.py`
- Modify: `tests/test_viewer_comments.py`

1. Add fixtures for a root model and two child models that own the same relative module path.
2. Add adjacent child manifests with distinct symbols and pipeline history using canonical paths.
3. Assert distinct qualified keys, records, component links, comments, and history.
4. Add missing-manifest stub and malicious path rejection tests.
5. Add hostile names, JSON parse, inline asset, and `node --check` assertions.
6. Run focused tests and verify the new assertions fail for the expected missing behavior.

### Task 2: Implement Hierarchy-Aware Module Loading

**Files:**
- Modify: `src/architecture_model/core/visualize.py`

1. Normalize model-owned relative file paths and safely resolve repository-contained paths.
2. Parse root and child manifests once from adjacent/canonical locations.
3. Convert owned manifest records to viewer module records and synthesize stubs for missing records.
4. Return qualified child module keys and explicit component-file link records from submodel loading.
5. Restrict root records to explicitly modeled root component files.
6. Run focused tests until green.

### Task 3: Route Qualified Pages and History

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `tests/test_viewer_comments.py`

1. Render component file links using their resolved module key.
2. Render module detail from the qualified record while matching history through its canonical path.
3. Keep comment storage/export/import keyed by the qualified module key.
4. Run all viewer tests and Node.js checks until green.

### Task 4: Verify and Commit

**Files:**
- Modify only files required above; preserve `.architecture/**` dirt.

1. Run `pytest tests/test_visualize.py tests/test_viewer_comments.py -v`.
2. Run `pytest tests/ -v --ignore=tests/test_config_loader.py` and compare failures with the six known baseline failures.
3. Run architecture validation/gate checks.
4. Inspect the diff and stage only implementation, tests, and plan documents.
5. Create one concise commit describing qualified subsystem module navigation.
