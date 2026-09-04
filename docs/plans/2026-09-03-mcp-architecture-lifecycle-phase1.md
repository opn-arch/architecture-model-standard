# MCP Architecture Lifecycle — Phase 1 Foundations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task in this session with fresh implementer + spec review + code quality review per task. Use superpowers:test-driven-development inside each implementer dispatch.

**Goal:** Establish the standard-library foundations (recursive `ArchitecturePackage`, canonical identity/serialization, atomic derived-object store, complete semantic diff, dependency/stale graph, recursive gates, ModelSlice, ViewSpec-over-DiagramSpec, ArtifactSpec+DAG, AI work orders) so that `opencode-arch` Phase 2 can register thin MCP endpoints against a stable, well-tested contract.

**Architecture:**
- New package `src/architecture_model/lifecycle/` owns identity, serialization, atomic store, packages, revisions, diff, stale graph, gates.
- New package `src/architecture_model/ai/` owns work orders, proposals, jobs, result validators (pure standard-lib logic; execution transport stays in `opencode-arch`).
- Existing `DiagramSpec` stays as renderer-neutral content; a new `ViewSpec` wraps selectors/curation/projector-config and references DiagramSpec as its content payload.
- `ArtifactSpec` moves from `opencode_arch/artifacts/selector.py` to the standard library; MCP layer imports it.
- All new schemas live under `src/architecture_model/spec/` as `*.schema.json` and are versioned via a single `SchemaVersions` registry.

**Tech Stack:** Python 3.11, pydantic v2 (already in use), pytest, PyYAML, jsonschema, fcntl for POSIX locks (with a portability shim), hashlib for digests.

**Baseline test command (unchanged):**
```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py
```
Baseline: 2394 passed, 109 skipped, 9 pre-existing failures. Do NOT introduce new failures. Pre-existing failures must remain in the same 9 test IDs.

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/curated-se-views` on branch `feat/curated-se-views` (HEAD 7d93742). Do NOT stage `.architecture/*.jsonl|yaml` telemetry files.

**Global conventions for every task:**
- TDD: write failing test, run to see it fail, minimum implementation, run to see it pass, refactor, commit.
- Do not weaken or delete existing tests. Do not modify existing public APIs (`core.parser`, `core.validator`, `core.slicer`, `manifest.generator`, `integrations.llm_context`) — additive only. Legacy behavior stays intact as compatibility.
- One logical unit per commit. Conventional Commit messages: `feat(lifecycle): ...`, `feat(ai): ...`, `test(lifecycle): ...`, `refactor(diagram): ...`.
- No new runtime dependencies without explicit approval.
- Every new module gets a docstring stating: purpose, invariants, thread-safety assumptions, error taxonomy.

---

## Phase 1 Task Index

| # | Task | Depends on | Est. commits |
|---|------|-----------|--------------|
| T1 | Terminology + version policy | — | 1 |
| T2 | Canonical serialization + digest | T1 | 1 |
| T3 | Atomic store primitives (write/lock/journal) | T2 | 2 |
| T4 | ArchitecturePackage descriptor + loader (recursive) | T2 | 2 |
| T5 | Root package index (`.architecture/package-index.yaml`) | T3, T4 | 1 |
| T6 | Model↔manifest revision pairing enforcement | T4 | 1 |
| T7 | Canonical package ownership + shared-file declarations | T4 | 1 |
| T8 | Transactional package publication (generation dirs + CURRENT switch + journal + recovery) | T3, T5, T6 | 2 |
| T9 | Schema migration framework | T1, T2 | 1 |
| T10 | Complete semantic diff | T2, T4 | 2 |
| T11 | Dependency/stale graph with semantic-intersection invalidation | T4, T10 | 1 |
| T12 | Recursive lifecycle gates | T4, T10 | 1 |
| T13 | ModelSlice types + JSON Schema | T2, T4 | 1 |
| T14 | ModelSlice materializer (local/descendants/federated, closure modes, shared_refs modes) | T13 | 2 |
| T15 | ViewSpec types + JSON Schema (wraps DiagramSpec) | T2 | 1 |
| T16 | ViewSpec projector (consumes ModelSlice only) | T14, T15 | 1 |
| T17 | ArtifactSpec migration to standard + JSON Schema | T2, T15 | 1 |
| T18 | ArtifactSpec renderers (SVG, Markdown, HTML, AI-context, ZIP bundle) | T17 | 2 |
| T19 | ArtifactSpec DAG resolution + rebuild plan | T11, T17 | 1 |
| T20 | AI WorkOrder + Proposal types + JSON Schema | T2, T13 | 1 |
| T21 | AI job manager state machine (draft→…→completed|failed|cancelled) | T20 | 1 |
| T22 | AI result validators + typed proposal appliers (validate only, do not mutate) | T20, T21 | 1 |

Total: 22 tasks, ~28 commits. Phase 2 (MCP endpoints in `opencode-arch`) is a separate plan.

---

## Task detail

Below, T1–T3 are written in full bite-sized step form as the reference template. Every subsequent task follows the same TDD pattern (failing test → run → implement → run → refactor → commit) even where prose spec is shown for brevity. Implementer subagents MUST expand each task into concrete TDD steps before writing code and MUST NOT proceed without a failing test.

---

### Task 1: Terminology + version policy

**Purpose:** Single source of truth for schema/package/manifest/slice/view/artifact/workorder versions and for the vocabulary used across the lifecycle package. Eliminates the current drift (parser default 1.1 vs schema 2.1.0 vs README 1.4 vs docs 2.0).

**Files:**
- Create: `src/architecture_model/lifecycle/__init__.py`
- Create: `src/architecture_model/lifecycle/versions.py`
- Create: `src/architecture_model/lifecycle/terminology.md`
- Create: `tests/lifecycle/__init__.py`
- Create: `tests/lifecycle/test_versions.py`

**Step 1 — Failing test:**

```python
# tests/lifecycle/test_versions.py
from architecture_model.lifecycle.versions import SchemaVersions, ContractKind

def test_schema_versions_expose_all_contracts():
    assert SchemaVersions.MODEL == "2.1.0"
    assert SchemaVersions.PACKAGE == "1.0.0"
    assert SchemaVersions.MANIFEST == "1.0.0"
    assert SchemaVersions.MODEL_SLICE == "1.0.0"
    assert SchemaVersions.VIEW_SPEC == "1.0.0"
    assert SchemaVersions.ARTIFACT_SPEC == "1.0.0"
    assert SchemaVersions.AI_WORK_ORDER == "1.0.0"
    assert SchemaVersions.DIGEST_ALGO == "sha256-v1"

def test_contract_kind_covers_every_persisted_artifact():
    kinds = {k.value for k in ContractKind}
    assert kinds == {
        "model", "package", "manifest", "model-slice",
        "view-spec", "artifact-spec", "ai-work-order",
    }

def test_version_for_kind_lookup():
    assert SchemaVersions.for_kind(ContractKind.MODEL) == "2.1.0"
    assert SchemaVersions.for_kind(ContractKind.VIEW_SPEC) == "1.0.0"
```

**Step 2 — Run:** `pytest tests/lifecycle/test_versions.py -q` → FAIL (module not found).

**Step 3 — Implement:**

```python
# src/architecture_model/lifecycle/versions.py
"""Single source of truth for lifecycle contract versions.

Any persisted artifact under .architecture/ or a package directory MUST
carry a `contract_version` string produced by SchemaVersions.for_kind().
Bumping any version here requires a matching migration registered in
architecture_model.lifecycle.migrations.
"""
from __future__ import annotations
from enum import Enum
from typing import Final

class ContractKind(str, Enum):
    MODEL = "model"
    PACKAGE = "package"
    MANIFEST = "manifest"
    MODEL_SLICE = "model-slice"
    VIEW_SPEC = "view-spec"
    ARTIFACT_SPEC = "artifact-spec"
    AI_WORK_ORDER = "ai-work-order"

class SchemaVersions:
    MODEL: Final = "2.1.0"
    PACKAGE: Final = "1.0.0"
    MANIFEST: Final = "1.0.0"
    MODEL_SLICE: Final = "1.0.0"
    VIEW_SPEC: Final = "1.0.0"
    ARTIFACT_SPEC: Final = "1.0.0"
    AI_WORK_ORDER: Final = "1.0.0"
    DIGEST_ALGO: Final = "sha256-v1"

    _BY_KIND = {
        ContractKind.MODEL: MODEL,
        ContractKind.PACKAGE: PACKAGE,
        ContractKind.MANIFEST: MANIFEST,
        ContractKind.MODEL_SLICE: MODEL_SLICE,
        ContractKind.VIEW_SPEC: VIEW_SPEC,
        ContractKind.ARTIFACT_SPEC: ARTIFACT_SPEC,
        ContractKind.AI_WORK_ORDER: AI_WORK_ORDER,
    }

    @classmethod
    def for_kind(cls, kind: ContractKind) -> str:
        return cls._BY_KIND[kind]
```

Also create `src/architecture_model/lifecycle/__init__.py` re-exporting `SchemaVersions`, `ContractKind`.

**Step 4 — Write terminology.md** defining the exact meaning of: ArchitecturePackage (root and child use same contract), ModelSlice, ViewSpec (wraps DiagramSpec), DiagramSpec (renderer-neutral content), ArtifactSpec (materialized output), Revision (immutable content-addressed model version — NOT `base/final` from pipeline history), Generation (numbered publication of a package), CURRENT (atomically-switched pointer), digest (`sha256-v1(canonical_json(...))`), qualified id `(architecture_id, model_revision, local_id)`.

**Step 5 — Run:** `pytest tests/lifecycle/test_versions.py -q` → PASS.

**Step 6 — Full-suite guard:** run the baseline test command. Confirm still 2394 passed / 9 same pre-existing failures.

**Step 7 — Commit:**

```
git add src/architecture_model/lifecycle/ tests/lifecycle/
git commit -m "feat(lifecycle): freeze contract versions and terminology"
```

---

### Task 2: Canonical serialization + digest

**Purpose:** Deterministic serialization required for revision identity, semantic diff, and signature slots. Fixes the current implicit ordering that makes revisions non-reproducible.

**Files:**
- Create: `src/architecture_model/lifecycle/serialization.py`
- Create: `tests/lifecycle/test_serialization.py`

**Spec (implementer expands to TDD steps):**
- `canonical_json(obj: Any) -> bytes` — UTF-8 encoded, NFC-normalized strings, sorted object keys, no insignificant whitespace, `ensure_ascii=False`, floats forbidden (raise `TypeError`), integers only, tuples serialized as lists, `None` allowed only at declared-optional fields (caller responsibility — module treats None as null).
- `digest(obj: Any) -> str` — returns `"sha256-v1:<hex>"`. Algorithm tag comes from `SchemaVersions.DIGEST_ALGO`.
- `canonical_yaml_load(text: str) -> Any` — thin wrapper around `yaml.safe_load` that rejects duplicate keys and non-string mapping keys.
- Exclude a caller-declared list of volatile field paths (`exclude_paths: Sequence[tuple[str, ...]]`) so callers can hash "content" while excluding e.g. `generated_at`, `signatures`.

**Tests (must include):**
- Same input in two dict-key orders yields byte-identical output.
- NFC normalization: `"e\u0301"` and `"\u00e9"` produce identical bytes.
- Float raises TypeError with clear message.
- Duplicate YAML key raises.
- Digest is deterministic and stable across processes (spawn subprocess check).
- `exclude_paths=[("generated_at",), ("signatures",)]` yields same digest regardless of those field values.

**Commit:** `feat(lifecycle): add canonical json/yaml serialization and digest`

---

### Task 3: Atomic store primitives

**Purpose:** All derived-object writes under `.architecture/` and package generation directories must be crash-safe. Current `pipeline/emit.py` writes files sequentially — a mid-write crash leaves the store in an inconsistent state.

**Files:**
- Create: `src/architecture_model/lifecycle/atomic_store.py`
- Create: `src/architecture_model/lifecycle/locks.py`
- Create: `src/architecture_model/lifecycle/journal.py`
- Create: `tests/lifecycle/test_atomic_store.py`
- Create: `tests/lifecycle/test_locks.py`
- Create: `tests/lifecycle/test_journal.py`

**Spec:**

`atomic_store.py`:
- `write_atomic(path: Path, data: bytes, *, fsync: bool = True) -> None` — write to `path.with_suffix(path.suffix + ".tmp-<uuid>")`, fsync file, `os.replace` onto final, fsync parent directory.
- `write_tree_atomic(root: Path, files: dict[Path, bytes]) -> None` — write all files into a staging directory `root.with_suffix(".staging-<uuid>")`, fsync each, then `os.replace(staging, root)` if `root` does not exist, else rely on `switch_current` (below).
- `switch_current(pointer: Path, target_dir: Path) -> None` — atomic symlink swap (create tmp symlink, `os.replace` over the pointer).

`locks.py`:
- `class FileLock(path: Path, *, timeout: float | None = None, stale_after: float = 600)` — POSIX `fcntl.flock` with timeout via non-blocking retry loop + jitter; stale-lock reclaim if lock-holder PID no longer exists (check `/proc` on Linux, `os.kill(pid, 0)` on POSIX). Windows shim raises `NotImplementedError` (out of scope for Phase 1; document in module docstring).
- Context-manager interface. Raises `LockTimeout`, `StaleLockReclaimed` (warning, not error).

`journal.py`:
- Append-only JSONL journal per store root: `.architecture/journal.jsonl`.
- `record(event: str, payload: Mapping[str, Any]) -> str` — returns event id; fsync after each write.
- `replay(root: Path, *, since: str | None = None) -> Iterable[JournalEntry]`.
- Standard event kinds: `package.publish.begin`, `package.publish.commit`, `package.publish.abort`, `store.write.begin`, `store.write.commit`.

**Tests (must include):**
- Atomic write: kill mid-write (simulated via monkeypatched `os.replace` raising after fsync) leaves original file intact.
- Two processes contend for the same lock: one acquires, other times out cleanly.
- Stale lock: create lock, exit process, next acquire succeeds with `StaleLockReclaimed` warning.
- Journal replay yields events in write order; entries after `since` filter correctly.
- write_tree_atomic never leaves half-populated directory visible under `root`.

**Commits:**
1. `feat(lifecycle): add crash-safe atomic write and tree publish`
2. `feat(lifecycle): add file lock with timeout and journal`

---

### Task 4: ArchitecturePackage descriptor + loader (recursive)

**Purpose:** Codify the recursive package contract. Root package and child packages use identical schema. No special-casing of the top.

**Files:**
- Create: `src/architecture_model/lifecycle/package.py`
- Create: `src/architecture_model/spec/package.schema.json`
- Create: `tests/lifecycle/test_package.py`
- Create: `tests/fixtures/lifecycle/sample_package_tree/` (nested valid packages for tests)

**Spec:**
- `package.yaml` fields: `architecture_id` (stable UUID or slug), `name`, `slug`, `contract_version` (must equal `SchemaVersions.PACKAGE`), `model_ref` (relative path to `.architecture-model.yaml`), `manifest_ref` (relative path to `manifest.json`), `children` (list of relative child package roots), `owned_paths` (glob list — files this package canonically owns), `shared_paths` (list of `{path, owners: [...]}` — files intentionally shared), `refs` (list of external architecture_id references), `revisions_dir` (default `revisions/`), optional `metadata: {description, tags}`.
- `class ArchitecturePackage` pydantic model.
- `load_package(path: Path) -> ArchitecturePackage` — accepts either the `package.yaml` file or the directory containing it.
- `iter_descendants(pkg) -> Iterable[ArchitecturePackage]` — depth-first, cycle-detecting.
- `resolve(pkg, architecture_id) -> ArchitecturePackage | None` — search this tree.
- Reject: unknown fields, `contract_version` mismatch, path escapes package root, duplicate `architecture_id` in descendants, children pointing outside root (unless declared as `federated_ref`).

**Tests:** load valid tree; reject cycle; reject duplicate id; reject path traversal; `iter_descendants` yields deterministic order.

**Commits:**
1. `feat(lifecycle): add ArchitecturePackage schema and pydantic model`
2. `feat(lifecycle): add recursive package loader with cycle detection`

---

### Task 5: Root package index

**Purpose:** Enable discovery from any subtree entry point. Cache of `(architecture_id, slug, root_path, current_generation)` for the whole federation known to this repo.

**Files:**
- Create: `src/architecture_model/lifecycle/package_index.py`
- Create: `tests/lifecycle/test_package_index.py`

**Spec:**
- Path: `<repo>/.architecture/package-index.yaml`.
- Regenerated by `rebuild_index(repo_root)` — walks package tree from a configured root; uses `atomic_store.write_atomic`.
- Lookup APIs: `find_by_id`, `find_by_slug`, `find_containing(source_path)` (walks upward from a source file to the owning package).
- Emits `journal.record("index.rebuild.commit", ...)`.

**Commit:** `feat(lifecycle): add root package index with atomic rebuild`

---

### Task 6: Model↔manifest revision pairing

**Purpose:** A `.architecture-model.yaml` and its `manifest.json` must be immutably paired. Prevents drift where the model claims a manifest revision that no longer exists.

**Files:**
- Modify: `src/architecture_model/lifecycle/package.py` (add `assert_pairing(pkg)`)
- Create: `src/architecture_model/lifecycle/pairing.py`
- Create: `tests/lifecycle/test_pairing.py`

**Spec:**
- Manifest carries `pairing.model_digest` (digest of the paired model bytes, excluding `signatures` and `generated_at`).
- Model carries `meta.manifest_digest` mirror.
- `verify_pairing(pkg)` recomputes both digests via `serialization.digest(..., exclude_paths=[("signatures",), ("generated_at",)])` and raises `PairingMismatch` on any drift.
- Root manifest owns cross-system evidence: `cross_system_files: [...]` — files not owned by any single child.
- Additive to existing manifest generator: emit `pairing` block; keep backward compat (if absent, log warning, do not fail existing tests).

**Commit:** `feat(lifecycle): enforce model/manifest revision pairing`

---

### Task 7: Canonical package ownership + shared-file declarations

**Files:**
- Modify: `src/architecture_model/lifecycle/package.py`
- Create: `src/architecture_model/lifecycle/ownership.py`
- Create: `tests/lifecycle/test_ownership.py`

**Spec:**
- Every source file has exactly one owner package unless declared in `shared_paths` (with a list of owners).
- `compute_ownership(root_pkg) -> OwnershipMap` — enumerates all packages, resolves globs, detects conflicts (same file claimed by two packages without a `shared_paths` entry → error).
- Persist ID/slug remaps as provenance in `.architecture/remaps.yaml` when a slug changes (append-only). Loader honors remaps.
- `OwnershipConflict`, `UnownedFile` typed errors.

**Commit:** `feat(lifecycle): enforce single-owner + declared-shared ownership`

---

### Task 8: Transactional package publication

**Purpose:** Publish all derived artifacts of a package as one atomic generation. Replaces `pipeline/emit.py`'s sequential file promotion for lifecycle-managed outputs (legacy `emit.py` behavior stays for backward compat callers).

**Files:**
- Create: `src/architecture_model/lifecycle/publication.py`
- Create: `tests/lifecycle/test_publication.py`

**Spec:**
- Layout: `<package>/generations/<N>/{model, manifest, slices/, views/, artifacts/, digest.json}` and pointer `<package>/CURRENT -> generations/<N>`.
- `publish(pkg, bundle: PackageBundle) -> PublicationResult` — algorithm:
  1. Determine `N = max(existing) + 1`.
  2. `atomic_store.write_tree_atomic(gen_dir, bundle.files)`.
  3. Write `digest.json` = `{contract_version, files: {rel_path: digest}, root_digest}`.
  4. `journal.record("package.publish.begin", ...)`.
  5. `atomic_store.switch_current(pkg.root / "CURRENT", gen_dir)`.
  6. `journal.record("package.publish.commit", {generation: N, root_digest})`.
- On any exception between begin and commit: `journal.record("package.publish.abort", ...)`, staging dir removed.
- `recover(pkg)` — inspects journal; if last event is `begin` without matching `commit`, deletes staging, keeps prior CURRENT intact.

**Tests:** crash injection between begin and switch; concurrent publish blocked by package-level lock (from T3); `CURRENT` never dangles.

**Commits:**
1. `feat(lifecycle): add generation-based transactional publication`
2. `feat(lifecycle): add crash recovery for aborted publications`

---

### Task 9: Schema migration framework

**Files:**
- Create: `src/architecture_model/lifecycle/migrations.py`
- Create: `tests/lifecycle/test_migrations.py`

**Spec:**
- Register migrations as `(ContractKind, from_version, to_version, callable)`. Callable is pure `(dict) -> dict`.
- `migrate(kind, payload) -> (migrated_payload, chain: list[str])` — resolves deterministic path from `payload["contract_version"]` to `SchemaVersions.for_kind(kind)`. Fails if no path.
- Migration provenance recorded on the object under `meta.migration_chain: [...]` (never overwritten; append).
- Zero migrations for Phase 1 (all versions are 1.0.0 / 2.1.0). Registry exists and is tested with a synthetic pair `("model-slice", "1.0.0", "1.1.0", ...)` under `tests/`.

**Commit:** `feat(lifecycle): add schema migration framework`

---

### Task 10: Complete semantic diff

**Purpose:** Current `core/differ.py` diffs 7 legacy entity types and the MCP diff tool reads `source/target` where the model uses `from/to` (documented bug). Replace with a complete semantic diff over all entity types, all relationship attributes, manifest files/symbols, and child revision changes.

**Files:**
- Create: `src/architecture_model/lifecycle/diff.py`
- Modify: `src/architecture_model/core/differ.py` (delegate to new module; keep old signature)
- Create: `tests/lifecycle/test_diff.py`

**Spec:**
- `semantic_diff(a: ArchitectureModel, b: ArchitectureModel, *, manifest_a=None, manifest_b=None, child_revisions_a=None, child_revisions_b=None) -> SemanticDiff` returning:
  - `entities: {kind: {added, removed, changed: [{id, field, old, new}]}}`
  - `relationships: {added, removed, changed: [...]}` — normalized on `(from, to, type)` triple; compares all optional attributes.
  - `manifest: {files_added, files_removed, symbols_added, symbols_removed, symbols_signature_changed}`
  - `children: {added, removed, revision_changed: [{architecture_id, from, to}]}`
  - `git: {commit_a, commit_b}` when both models carry `meta.provenance.git_commit`.
- Deterministic ordering (sorted). Digest-stable via canonical serialization.
- MCP `diff.py` bug (`source/target`) fixed as a side effect: update the delegator to normalize keys.

**Tests:** parametric coverage over every entity kind, every relationship type in `core.types.RelationshipType`; manifest add/remove/rename detection; child revision change; empty diff produces empty structure not None.

**Commits:**
1. `feat(lifecycle): implement complete semantic diff`
2. `refactor(core): delegate differ to lifecycle.diff and fix from/to keys`

---

### Task 11: Dependency/stale graph

**Files:**
- Create: `src/architecture_model/lifecycle/stale.py`
- Create: `tests/lifecycle/test_stale.py`

**Spec:**
- Build DAG over: package → model → manifest → slice → view → artifact.
- `mark_stale(root_pkg, changed: set[Path]) -> StaleSet` — invalidate nodes whose semantic input intersects `changed`. Semantic intersection: for a slice with `owned_paths` selector, changing a file outside those globs does NOT invalidate the slice.
- `stale_report(root_pkg) -> list[StaleNode]` — read from `.architecture/stale.yaml` cache; regenerate if underlying digests changed.
- No execution — this is planning-only. Rebuild execution is Phase 2.

**Commit:** `feat(lifecycle): add semantic-intersection stale graph`

---

### Task 12: Recursive lifecycle gates

**Files:**
- Create: `src/architecture_model/lifecycle/gates.py`
- Create: `tests/lifecycle/test_gates.py`

**Spec:**
- Gate kinds: `PackageGate`, `SliceGate`, `ViewGate`, `ArtifactGate`, `EvolutionGate`.
- Each gate: `evaluate(pkg) -> GateResult{passed, findings, blocking}`.
- Recursion: `evaluate_tree(root_pkg)` runs gates for every descendant; child failures propagate upward with breadcrumbs.
- Wire the existing gate concept in `opencode_arch/mcp/tools/gate.py` to consume this later (Phase 2). Do NOT change opencode-arch this task.

**Commit:** `feat(lifecycle): add recursive lifecycle gates`

---

### Task 13: ModelSlice types + JSON Schema

**Files:**
- Create: `src/architecture_model/lifecycle/model_slice.py`
- Create: `src/architecture_model/spec/model-slice.schema.json`
- Create: `tests/lifecycle/test_model_slice.py`

**Spec fields:**
- `id`, `contract_version`, `architecture_id`, `model_revision`, `scope: local|descendants|federated`, `closure: strict|boundary-stubs|transitive`, `shared_refs: none|explicit|transitive`, `selectors: {entity_kinds?, entity_ids?, layers?, fblocks?, tags?, paths?}`, `curation: {include?, exclude?, redactions?}`, `parameters: dict`.
- Digest field auto-computed via `serialization.digest` excluding `generated_at`, `signatures`.

**Commit:** `feat(lifecycle): add ModelSlice contract`

---

### Task 14: ModelSlice materializer

**Files:**
- Create: `src/architecture_model/lifecycle/model_slice_materializer.py`
- Create: `tests/lifecycle/test_model_slice_materializer.py`

**Spec:**
- `materialize(slice: ModelSlice, pkg: ArchitecturePackage) -> MaterializedSlice{model_fragment, provenance, warnings}`.
- Selector application deterministic and idempotent.
- Closure modes:
  - `strict`: remove any relationship whose endpoint is not in the fragment.
  - `boundary-stubs`: keep dangling endpoints as stub entities with `stub=True` and `origin_ref` back-pointer.
  - `transitive`: expand fragment to include reachable neighbors up to `parameters.transitive_depth` (default 1, max 3).
- `shared_refs`:
  - `none`: never include referenced-package entities.
  - `explicit`: include only entities listed in `selectors.entity_ids` from other packages.
  - `transitive`: include reachable entities from other packages up to depth 1.
- Federated scope requires a `refs` resolver (accept a callable at materialize time).

**Tests:** materializer produces same output for the same slice+revision pair (property test with hypothesis-lite fixture cases); each closure/shared_refs mode has explicit assertions; dangling-relationship bug from existing slicer verified NOT to occur here.

**Commits:**
1. `feat(lifecycle): implement ModelSlice materializer selectors and closures`
2. `feat(lifecycle): add federated shared_refs resolution`

---

### Task 15: ViewSpec types + JSON Schema

**Files:**
- Create: `src/architecture_model/lifecycle/view_spec.py`
- Create: `src/architecture_model/spec/view-spec.schema.json`
- Create: `tests/lifecycle/test_view_spec.py`

**Spec fields:**
- `id`, `contract_version`, `slice_ref: {slice_id, model_revision}`, `projector: str` (registry name), `projector_config: dict`, `curation: {include?, exclude?, redactions?, drill_downs?}`, `parameters: dict`, `output_content_kind: "diagram" | "prose" | "table"`.
- `slice_ref.model_revision` is REQUIRED — ViewSpec is bound to an immutable slice revision.
- Does NOT itself carry rendered content. Rendered `DiagramSpec` is produced by T16's projector call.

**Commit:** `feat(lifecycle): add ViewSpec contract wrapping DiagramSpec`

---

### Task 16: ViewSpec projector

**Files:**
- Create: `src/architecture_model/lifecycle/view_projection.py`
- Create: `tests/lifecycle/test_view_projection.py`

**Spec:**
- `project(view: ViewSpec, materialized_slice: MaterializedSlice) -> ProjectedView{diagram_spec, provenance, warnings}`.
- Projector registry: map projector name → callable. Seed with adapters that wrap existing `se_view_projectors.py` functions (ConOps, Functional, Logical, Use Cases) — DO NOT rewrite the projectors, just adapt.
- Projector callable signature: `(slice_fragment: ArchitectureModel, config: dict) -> DiagramSpec`.
- Projector MUST NOT read the file system or any model outside the provided fragment.

**Commit:** `feat(lifecycle): add ViewSpec projector registry over materialized slices`

---

### Task 17: ArtifactSpec migration + JSON Schema

**Purpose:** Move ownership of `ArtifactSpec` from `opencode_arch/artifacts/selector.py` to standard library. Keep opencode-arch import shim for one release.

**Files:**
- Create: `src/architecture_model/lifecycle/artifact_spec.py`
- Create: `src/architecture_model/spec/artifact-spec.schema.json`
- Create: `tests/lifecycle/test_artifact_spec.py`
- Modify (opencode-arch will happen in Phase 2, NOT this task): leave a note in module docstring that `opencode_arch/artifacts/selector.py` needs to become an import shim.

**Spec fields:**
- `id`, `contract_version`, `renderer: "svg"|"markdown"|"html"|"ai-context"|"zip"`, `view_ref: {view_id, model_revision}` OR `bundle_refs: [artifact_spec_id, ...]` (for ZIP), `parameters: dict`, `signature_slots: [SignatureSlot]`.
- Digest excludes `signatures` slot.

**Commit:** `feat(lifecycle): move ArtifactSpec into standard library`

---

### Task 18: ArtifactSpec renderers

**Files:**
- Create: `src/architecture_model/lifecycle/renderers/__init__.py`
- Create: `src/architecture_model/lifecycle/renderers/svg.py`
- Create: `src/architecture_model/lifecycle/renderers/markdown.py`
- Create: `src/architecture_model/lifecycle/renderers/html.py`
- Create: `src/architecture_model/lifecycle/renderers/ai_context.py`
- Create: `src/architecture_model/lifecycle/renderers/zip.py`
- Create: `tests/lifecycle/test_renderers_*.py` (one per renderer)

**Spec:**
- Adapt existing `core/diagram_renderer.py` (SVG), `core/visualize.py` (HTML), `integrations/llm_context.py` (AI context) as underlying implementations.
- Each renderer signature: `render(view: ProjectedView | list[ProjectedView], artifact: ArtifactSpec) -> bytes`.
- ZIP renderer takes `bundle_refs` and packages resolved artifact bytes with a `manifest.json` inside the zip listing digests.
- Renderers MUST be pure (no I/O side effects); caller writes bytes via `atomic_store.write_atomic`.

**Commits:**
1. `feat(lifecycle): add SVG/Markdown/HTML artifact renderers`
2. `feat(lifecycle): add AI-context and ZIP bundle renderers`

---

### Task 19: ArtifactSpec DAG resolution + rebuild plan

**Files:**
- Create: `src/architecture_model/lifecycle/artifact_dag.py`
- Create: `tests/lifecycle/test_artifact_dag.py`

**Spec:**
- Build DAG over ArtifactSpec dependencies (a ZIP artifact depends on its `bundle_refs`; any renderer depends on `view_ref` which depends on slice which depends on model).
- `rebuild_plan(root_pkg, stale: StaleSet) -> list[BuildStep]` — topologically ordered list, each step declares `{artifact_id, kind, inputs, output_path}`.
- No execution — this is planning-only. Execution moves to Phase 2 MCP endpoints (`architect_rebuild`).

**Commit:** `feat(lifecycle): add ArtifactSpec DAG and rebuild plan generator`

---

### Task 20: AI WorkOrder + Proposal types

**Files:**
- Create: `src/architecture_model/ai/__init__.py`
- Create: `src/architecture_model/ai/work_order.py`
- Create: `src/architecture_model/ai/proposals.py`
- Create: `src/architecture_model/spec/ai-work-order.schema.json`
- Create: `tests/ai/__init__.py`
- Create: `tests/ai/test_work_order.py`
- Create: `tests/ai/test_proposals.py`

**Spec:**
- `WorkOrder` fields: `id`, `contract_version`, `intent` (string), `input_slice_refs: [{slice_id, model_revision}]`, `expected_proposal_kinds: [ProposalKind]`, `parameters: dict`, `budget: {max_tokens, max_wall_seconds}`, `requested_by`, `created_at`.
- `ProposalKind` enum: `model-patch`, `decomposition-proposal`, `slice-proposal`, `view-curation-proposal`, `artifact-candidate`, `impact-assessment`.
- One typed dataclass per proposal kind, each with mandatory `provenance: {work_order_id, model_version, prompt_digest}`.
- Bounded-input rule: WorkOrder MUST reference at least one slice; unbounded model reads not allowed.

**Commit:** `feat(ai): add WorkOrder and typed Proposal contracts`

---

### Task 21: AI job manager

**Files:**
- Create: `src/architecture_model/ai/jobs.py`
- Create: `tests/ai/test_jobs.py`

**Spec:**
- States: `draft → approved → queued → running → validating → completed | failed | cancelled`. Only these transitions:
  - draft → approved, cancelled
  - approved → queued, cancelled
  - queued → running, cancelled
  - running → validating, failed, cancelled
  - validating → completed, failed
- `JobStore` persists jobs as `.architecture/ai/jobs/<job_id>.yaml`, atomic writes.
- `transition(job_id, new_state, *, reason=None)` — validates transition, writes journal event.
- Execution is NOT implemented here (opencode-arch owns the worker in Phase 2). This task only implements the state machine and persistence.

**Commit:** `feat(ai): add work-order job state machine`

---

### Task 22: AI result validators

**Files:**
- Create: `src/architecture_model/ai/validators.py`
- Create: `tests/ai/test_validators.py`

**Spec:**
- For each `ProposalKind`, a validator that checks:
  - Proposal targets the declared work-order slices.
  - No cross-revision drift: proposal's referenced `model_revision` matches the input slice's `model_revision`.
  - Structural validity via JSON Schema.
  - Semantic validity: e.g. `ModelPatch` operations only touch entities present in the input slice fragment; `SliceProposal` produces a schema-valid `ModelSlice`.
- `validate(proposal) -> ValidationReport{passed, findings}`.
- Validators do NOT apply the proposal — application is Phase 2 (`architect_ai_result_apply`).

**Commit:** `feat(ai): add typed proposal validators`

---

## Phase 1 exit criteria (verify before starting Phase 2)

1. Full suite: 2394+ passed (new tests additive), same 9 pre-existing failures, no new failures.
2. `python -c "from architecture_model.lifecycle import SchemaVersions; ..."` imports every new module cleanly.
3. `docs/plans/2026-09-03-mcp-architecture-lifecycle-phase1.md` (this file) checked off task-by-task in a follow-up "phase1 completion report" appended at the bottom.
4. `opencode-arch` untouched — Phase 2 is a separate plan.
5. No changes to `core/parser.py`, `core/validator.py`, `manifest/generator.py` public signatures.
6. All new persisted artifacts carry a `contract_version` and a `digest`.
7. `journal.jsonl` populated by any test that publishes a package.

## Out of scope for Phase 1 (explicitly)

- Cryptographic signing (signature slots present + verified, but no key management).
- Three-way auto-merge (Phase 1 detects conflicts only).
- Federated registries beyond in-repo path resolution.
- Rebuild execution (only rebuild_plan).
- MCP endpoints (all Phase 2).
- CLI wiring for new commands (Phase 2 with MCP).

## Notes for implementer subagents

- Do not read `.architecture/*.jsonl` telemetry files. Do not commit them.
- Do not touch `logs_db` at all.
- Do not modify existing E2E test fixtures.
- If a task requires touching a file listed under "Do not modify existing public APIs", stop and ask.
- Follow superpowers:test-driven-development inside every task.
- Each task ends with the baseline test command passing.

## Phase 1 completion report

- **Date:** 2026-09-03
- **Branch:** `feat/curated-se-views`
- **HEAD SHA:** `22012a8`

### Task → commit map

| Task | Description | Commit(s) |
|-----:|-------------|-----------|
| T1  | Terminology + version policy | `6712fc9` |
| T2  | Canonical serialization + digest | `8572bac` |
| T3  | Atomic store + locks + journal | `b4bef36`, `55dee9c` |
| T4  | ArchitecturePackage descriptor + loader | `71d51ea` |
| T5  | Root package index | `e0d20ec` |
| T6  | Model/manifest revision pairing | `0ba6222` |
| T7  | Canonical package ownership | `da48761` |
| T8  | Transactional package publication | `ec03cbe` |
| T9  | Schema migration framework | `77aba3d` |
| T10 | Complete semantic diff + differ delegator | `9622ad7`, `a3222d4` |
| T11 | Semantic-intersection stale graph | `64b3286` |
| T12 | Recursive lifecycle gates | `36bac2b` |
| T13 | ModelSlice + JSON Schema | `5b3b30d` |
| T14 | ModelSlice materializer + federated shared_refs | `65a6f1d`, `054118f` |
| T15 | ViewSpec + JSON Schema | `72b5a4b` |
| T16 | ViewSpec projector registry (SE adapters) | `17bf1fc` |
| T17 | ArtifactSpec migration + JSON Schema | `b339f7d` |
| T18 | SVG/Markdown/HTML + AI-context/ZIP renderers | `ae8db76`, `c7b2e64` |
| T19 | ArtifactSpec DAG + rebuild plan | `d4a64c7` |
| T20 | WorkOrder + typed Proposal contracts | `88581c8` |
| T21 | Work-order job state machine | `237272a` |
| T22 | Typed proposal validators | `22012a8` |

### Final test totals

- Full suite (excluding pre-existing-ignore `tests/test_config_loader.py`): **2885 passed**, **6 failed** (unchanged pre-existing), 102 skipped.
- Pre-existing failures (baseline, unchanged across Phase 1):
  - `tests/test_docs_gen.py::TestHealthReport::test_includes_confidence`
  - `tests/test_docs_gen.py::TestHealthReport::test_includes_components`
  - `tests/test_manifest.py::TestFunctionalBlocks::test_has_f1_through_f6`
  - `tests/test_manifest.py::TestGenerateManifest::test_has_functional_blocks`
  - `tests/test_multi_scanner.py::TestScanAllLanguages::test_real_logs_db`
  - `tests/test_pipeline_decompose.py::TestStageMetadata::test_name_version_requires`
- New passing tests added across Phase 1 tasks (additive): net **+491** over the pre-Phase-1 baseline of 2394.

### Exit-criteria checklist (from plan lines 620–628)

- ✅ Full suite: 2885 passed (well above the 2394+ threshold), same 6 pre-existing failures, no new failures.
- ✅ Every new lifecycle/AI module imports cleanly (`SchemaVersions`, `atomic_store`, `journal`, `package`, `package_index`, `pairing`, `ownership`, `publication`, `migrations`, `diff`, `stale`, `gates`, `model_slice`, `model_slice_materializer`, `view_spec`, `view_projection`, `artifact_spec`, `renderers`, `artifact_dag`, `ai.work_order`, `ai.proposals`, `ai.jobs`, `ai.validators`).
- ✅ This "Phase 1 completion report" is appended to `docs/plans/2026-09-03-mcp-architecture-lifecycle-phase1.md`.
- ✅ `opencode-arch` untouched — Phase 2 remains a separate plan.
- ✅ No changes to `core/parser.py`, `core/validator.py`, `manifest/generator.py`, `pipeline/emit.py` public signatures.
- ✅ All new persisted artifacts (`ArchitecturePackage`, `ModelSlice`, `ViewSpec`, `ArtifactSpec`, `WorkOrder`, `Proposal`) carry `contract_version` and expose deterministic `digest()`.
- ✅ `journal.jsonl` is populated by publication tests (see `tests/lifecycle/test_publication.py` and downstream tasks that exercise atomic package writes).

Phase 1 is complete. Ready for Phase 2 (MCP endpoints, CLI wiring, cryptographic signing).
