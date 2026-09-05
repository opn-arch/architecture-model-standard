# Phase 1 Escalations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Fix 9 nits (N50, N52, N53, N64, N73, N74, N81, N100, N105) surfaced during Phase 2 opencode-arch work, without breaking the Phase 1 test baseline or the Phase 2 downstream consumer.

**Architecture:** Additive-first API changes wherever possible: subclass rather than replace existing exceptions (N50), add helper functions rather than restructure (N53), add property alias rather than rename (N81), add factory alongside constructor (N100). Two rippling changes (N64 `proposal_id`, N105 `fragment` serializer) are also additive: `proposal_id` auto-computes when omitted; the new `MaterializedSlice.to_dict()` is a new method with no removal of existing behavior.

**Tech Stack:** Python 3.12, pytest, PyYAML, dataclasses (frozen), Pydantic v2 (`ArchitecturePackage`), Python-idiomatic hashlib.

**Environment:**
- Worktree: `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/phase1-escalations`
- Branch: `feat/phase1-escalations` (based on `feat/curated-se-views` HEAD `7f0c7dc`)
- Python: `/opt/anaconda3/bin/python`
- PYTHONPATH for ALL commands: `PYTHONPATH="$PWD/src"`
- Default test cmd: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
- **Baseline: 2885 passed, 6 pre-existing failures** — never fix, never regress:
  - `tests/test_manifest.py::TestFunctionalBlocks::test_has_f1_through_f6`
  - `tests/test_manifest.py::TestGenerateManifest::test_has_functional_blocks`
  - `tests/test_multi_scanner.py::TestScanAllLanguages::test_real_logs_db`
  - `tests/test_pipeline_decompose.py::TestStageMetadata::test_name_version_requires`
  - (2 more collection-time; capture from the baseline run)

**Constraints:**
- NEVER `git add -A` — add only changed files explicitly.
- NEVER touch `.architecture*` telemetry directories.
- NEVER `pip install -e` (not needed; use PYTHONPATH).
- One commit per task, Conventional Commit style: `fix(<area>): <summary> (N##)`.
- Amend only if the paired reviewer subagent flags a critical bug (`git commit --amend --no-edit`).
- All new files must include the same license header pattern as sibling files (check one first).

**Ordering (dependency-driven):** N73 → N81 → N50 → N74 → N53 → N64 → N100 → N52 → N105 → verification report.

---

### Task 1: N73 — remove clock injection from `_parse_meta`

**Files:**
- Modify: `src/architecture_model/core/parser.py:166`
- Test: `tests/core/test_parser.py` (add one test)

**Step 1: Failing test.** Add near existing `_parse_meta` tests:

```python
def test_parse_meta_leaves_generated_at_empty_when_absent():
    from architecture_model.core.parser import _parse_meta
    meta = _parse_meta({"project": "p", "schema_version": "1.3"})
    assert meta.generated_at == ""
```

**Step 2: Run — expect FAIL** with a non-empty `isoformat()` string:
`PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_parser.py::test_parse_meta_leaves_generated_at_empty_when_absent -v`

**Step 3: Fix.** In `parser.py:166`, change:
```python
generated_at=d.get("generated_at", datetime.now(timezone.utc).isoformat()),
```
to:
```python
generated_at=d.get("generated_at", ""),
```

**Step 4: Verify** — full suite: expect **2886 passed, 6 pre-existing failures**. No new failures.

**Step 5: Commit**
```bash
git add src/architecture_model/core/parser.py tests/core/test_parser.py
git commit -m "fix(core): remove clock injection from _parse_meta (N73)"
```

---

### Task 2: N81 — add `.id` alias on `ArchitecturePackage`

**Files:**
- Modify: `src/architecture_model/lifecycle/package.py:81-105` (add property)
- Test: `tests/lifecycle/test_package.py` (add one test)

**Step 1: Failing test.**

```python
def test_architecture_package_id_alias():
    from architecture_model.lifecycle.package import ArchitecturePackage
    pkg = ArchitecturePackage(architecture_id="arch-x", root="/tmp/arch-x")
    assert pkg.id == "arch-x"
    assert pkg.id == pkg.architecture_id
```

(Adjust constructor kwargs to match actual signature — reviewer to confirm from file.)

**Step 2: Run — expect FAIL** (`AttributeError: id`).

**Step 3: Fix.** In `ArchitecturePackage`, add:

```python
@property
def id(self) -> str:
    """Alias for architecture_id; consistent with entity ID convention."""
    return self.architecture_id
```

**Step 4: Verify** — full suite: **2887 passed, 6 pre-existing**.

**Step 5: Commit**
```bash
git add src/architecture_model/lifecycle/package.py tests/lifecycle/test_package.py
git commit -m "feat(lifecycle): add .id alias on ArchitecturePackage (N81)"
```

---

### Task 3: N50 — canonical `ParseError`

**Files:**
- Create: `src/architecture_model/core/errors.py`
- Modify: `src/architecture_model/core/parser.py:102` (raise `ParseError`)
- Modify: `src/architecture_model/lifecycle/serialization.py:171,182` (raise `ParseError`)
- Modify: `src/architecture_model/lifecycle/package.py:34` (`PackageLoadError(ParseError)`)
- Modify: `src/architecture_model/ai/proposals.py:232` (raise `ParseError`)
- Modify: `src/architecture_model/core/__init__.py` (re-export)
- Modify: `src/architecture_model/__init__.py` (re-export)
- Test: `tests/core/test_errors.py` (new)

**Step 1: Create `core/errors.py`.**

```python
"""Canonical parse-error type for architecture_model.

All modules that produce parse-time failures (YAML, JSON, schema shape) should
raise ParseError or a subclass. Subclass of ValueError for back-compat with
`except ValueError` sites.
"""
from __future__ import annotations

__all__ = ["ParseError"]


class ParseError(ValueError):
    """Canonical parse error for architecture models, packages, and proposals."""
```

**Step 2: Failing test.** `tests/core/test_errors.py`:

```python
import pytest
from architecture_model.core.errors import ParseError

def test_parse_error_is_value_error():
    assert issubclass(ParseError, ValueError)

def test_parser_raises_parse_error_on_empty_file(tmp_path):
    from architecture_model.core.parser import load_model
    p = tmp_path / "empty.yaml"
    p.write_text("")
    with pytest.raises(ParseError):
        load_model(p)

def test_package_load_error_is_parse_error():
    from architecture_model.lifecycle.package import PackageLoadError
    assert issubclass(PackageLoadError, ParseError)

def test_proposals_unknown_kind_raises_parse_error():
    from architecture_model.ai.proposals import proposal_from_dict
    with pytest.raises(ParseError):
        proposal_from_dict({"kind": "nonexistent-proposal"})
```

(Second test uses the actual proposal loader entry — reviewer/implementer must locate `proposal_from_dict` or the closest equivalent that hits line 232.)

**Step 3: Run tests — expect FAIL.**

**Step 4: Wire up.**
- `parser.py:102`: `raise ParseError(f"Empty model file: {path}")` — remove or keep `except ValueError` at line 388 (still works since `ParseError` IS-A `ValueError`).
- `serialization.py:171`: replace `yaml.constructor.ConstructorError` with `ParseError` (verify no test asserts the yaml-specific type; if so, keep the yaml error but chain: `raise ParseError(...) from err`).
- `serialization.py:182`: `raise ParseError(f"duplicate key {key!r} in YAML mapping")`.
- `package.py:34`: `class PackageLoadError(ParseError)` (was `ValueError`).
- `proposals.py:232`: `raise ParseError(f"unknown proposal kind {kind!r}")`.
- Re-export `ParseError` from `core/__init__.py` and top-level `__init__.py`.

**Step 5: Verify** — full suite: **2891 passed, 6 pre-existing**. If any test that specifically caught `yaml.YAMLError` or `ValueError` breaks, reviewer will flag; fix additively (keep chained exception).

**Step 6: Commit**
```bash
git add src/architecture_model/core/errors.py \
        src/architecture_model/core/parser.py \
        src/architecture_model/core/__init__.py \
        src/architecture_model/__init__.py \
        src/architecture_model/lifecycle/serialization.py \
        src/architecture_model/lifecycle/package.py \
        src/architecture_model/ai/proposals.py \
        tests/core/test_errors.py
git commit -m "feat(core): introduce canonical ParseError (N50)"
```

---

### Task 4: N74 — publicize `generation_dir`

**Files:**
- Modify: `src/architecture_model/lifecycle/publication.py` (rename `_generation_dir` → `generation_dir`, keep alias, update internal callsites at 187, 318)
- Modify: `src/architecture_model/lifecycle/__init__.py` (export)
- Test: `tests/lifecycle/test_publication.py` (add one test)

**Step 1: Failing test.**

```python
def test_generation_dir_is_public():
    from architecture_model.lifecycle.publication import generation_dir
    assert callable(generation_dir)
```

**Step 2: Run — expect FAIL** (`ImportError`).

**Step 3: Fix.**
- Rename the function definition at `publication.py:124` from `_generation_dir` to `generation_dir`.
- Immediately after the definition add `_generation_dir = generation_dir` alias for one release (deprecation-friendly).
- Internal callsites at 187, 318: change to `generation_dir(...)`.
- Add to `lifecycle/__init__.py` `__all__` and import.

**Step 4: Verify** — full suite: **2892 passed, 6 pre-existing**.

**Step 5: Commit**
```bash
git add src/architecture_model/lifecycle/publication.py \
        src/architecture_model/lifecycle/__init__.py \
        tests/lifecycle/test_publication.py
git commit -m "refactor(lifecycle): publicize generation_dir (N74)"
```

---

### Task 5: N53 — `current_root_digest` helper

**Files:**
- Modify: `src/architecture_model/lifecycle/publication.py` (add function)
- Modify: `src/architecture_model/lifecycle/__init__.py` (export)
- Test: `tests/lifecycle/test_publication.py` (add two tests)

**Step 1: Failing tests.**

```python
def test_current_root_digest_returns_none_when_no_publications(tmp_path):
    from architecture_model.lifecycle.publication import current_root_digest
    from architecture_model.lifecycle.package import ArchitecturePackage
    pkg = ArchitecturePackage(architecture_id="a", root=tmp_path)
    assert current_root_digest(pkg) is None

def test_current_root_digest_matches_publish_result(tmp_path):
    # Uses existing publish() helper to create a publication;
    # asserts current_root_digest(pkg) == result.root_digest
    ...
```

(Second test uses whatever fixture pattern the file already uses to publish a bundle — implementer follows existing test conventions.)

**Step 2: Run — expect FAIL** (`ImportError` then value mismatch).

**Step 3: Add function** in `publication.py` (near `read_current_generation`):

```python
def current_root_digest(pkg: ArchitecturePackage) -> str | None:
    """Return the root_digest of the current generation, or None if none exists."""
    n = read_current_generation(pkg)
    if n is None:
        return None
    dj = generation_dir(pkg, n) / "digest.json"
    if not dj.is_file():
        return None
    return json.loads(dj.read_text())["root_digest"]
```

**Step 4: Verify** — full suite: **2894 passed, 6 pre-existing**.

**Step 5: Commit**
```bash
git add src/architecture_model/lifecycle/publication.py \
        src/architecture_model/lifecycle/__init__.py \
        tests/lifecycle/test_publication.py
git commit -m "feat(lifecycle): add current_root_digest helper (N53)"
```

---

### Task 6: N64 — stable `proposal_id` in Provenance

**Files:**
- Modify: `src/architecture_model/ai/proposals.py` (Provenance dataclass + factory)
- Modify: `spec/ai-proposals.schema.json` if it exists (else skip)
- Test: `tests/ai/test_proposals.py` (add three tests)

**Step 1: Failing tests.**

```python
def test_provenance_auto_derives_proposal_id_when_omitted():
    from architecture_model.ai.proposals import Provenance
    p = Provenance(work_order_id="wo-1", model_version="m-1", prompt_digest="sha256-v1:abc")
    assert p.proposal_id.startswith("sha256-v1:")

def test_provenance_proposal_id_is_deterministic():
    from architecture_model.ai.proposals import Provenance
    p1 = Provenance(work_order_id="wo-1", model_version="m-1", prompt_digest="sha256-v1:abc")
    p2 = Provenance(work_order_id="wo-1", model_version="m-1", prompt_digest="sha256-v1:abc")
    assert p1.proposal_id == p2.proposal_id

def test_provenance_accepts_supplied_proposal_id():
    from architecture_model.ai.proposals import Provenance
    p = Provenance(work_order_id="wo-1", model_version="m-1", prompt_digest="sha256-v1:abc",
                   proposal_id="sha256-v1:deadbeef")
    assert p.proposal_id == "sha256-v1:deadbeef"
```

**Step 2: Run — expect FAIL.**

**Step 3: Fix.** Change Provenance to:

```python
@dataclass(frozen=True)
class Provenance:
    work_order_id: str
    model_version: str
    prompt_digest: str
    proposal_id: str = ""  # auto-derived when empty via __post_init__

    def __post_init__(self) -> None:
        if not self.proposal_id:
            payload = f"{self.work_order_id}|{self.model_version}|{self.prompt_digest}".encode()
            digest = hashlib.sha256(payload).hexdigest()
            object.__setattr__(self, "proposal_id", f"sha256-v1:{digest}")
```

Add `import hashlib` if not already imported.

Update `to_dict`/`from_dict` if present in file to include `proposal_id`.

**Step 4: Verify** — full suite. Any test that constructs `Provenance(...)` positionally without `proposal_id` still works (default). Expect **2897 passed, 6 pre-existing**.

**Step 5: Commit**
```bash
git add src/architecture_model/ai/proposals.py tests/ai/test_proposals.py
git commit -m "feat(ai): add stable proposal_id to Provenance (N64)"
```

---

### Task 7: N100 — `WorkOrder.build(...)` factory

**Files:**
- Modify: `src/architecture_model/ai/work_order.py:97-137`
- Test: `tests/ai/test_work_order.py` (add tests)

**Step 1: Failing tests.**

```python
def test_workorder_build_minimal():
    from architecture_model.ai.work_order import WorkOrder
    wo = WorkOrder.build(
        intent="patch model",
        slices=[("slice-a", "rev-1")],
        accepts=["model-patch"],
        requested_by="test",
        max_tokens=1000,
        max_wall_seconds=30,
    )
    assert wo.intent == "patch model"
    assert wo.id  # auto-derived
    assert wo.created_at  # auto-set

def test_workorder_build_accepts_datetime_created_at():
    from datetime import datetime, timezone
    from architecture_model.ai.work_order import WorkOrder
    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo = WorkOrder.build(
        intent="x", slices=[("s","r")], accepts=["model-patch"],
        requested_by="t", max_tokens=1, max_wall_seconds=1,
        created_at=dt,
    )
    assert wo.created_at == dt.isoformat()

def test_workorder_build_deterministic_id_when_omitted():
    from architecture_model.ai.work_order import WorkOrder
    kwargs = dict(intent="x", slices=[("s","r")], accepts=["model-patch"],
                  requested_by="t", max_tokens=1, max_wall_seconds=1,
                  created_at="2026-01-01T00:00:00+00:00")
    w1 = WorkOrder.build(**kwargs)
    w2 = WorkOrder.build(**kwargs)
    assert w1.id == w2.id
```

**Step 2: Run — expect FAIL** (no `build`).

**Step 3: Fix.** Add `@classmethod build(...)` on `WorkOrder`:
- Normalize `slices`: accept `SliceRef | tuple[str,str] | Mapping[str,str]`, convert each to `SliceRef(...)`.
- Normalize `accepts`: accept `ProposalKind | str`, convert strings via `ProposalKind(v)`.
- Build `Budget(max_tokens=..., max_wall_seconds=...)`.
- Normalize `created_at`: accept `str | datetime | None`. If `datetime`, `.isoformat()`. If `None`, `datetime.now(timezone.utc).isoformat()`.
- Derive `id` if `None`: `sha256-v1:<hex>` over canonical JSON of intent + slice tuples + accepts strings + budget tuple + requested_by + created_at.
- Return `cls(...)` — no changes to existing constructor.

**Step 4: Verify** — full suite: **2900 passed, 6 pre-existing**.

**Step 5: Commit**
```bash
git add src/architecture_model/ai/work_order.py tests/ai/test_work_order.py
git commit -m "feat(ai): add WorkOrder.build factory (N100)"
```

---

### Task 8: N52 — `apply_model_patch`

**Files:**
- Create: `src/architecture_model/ai/patch.py`
- Modify: `src/architecture_model/ai/__init__.py` (export)
- Test: `tests/ai/test_patch.py` (new file)

**Step 1: Read** `src/architecture_model/ai/validators.py` top for `_VALID_OPS` — implementer must confirm the operation set (`add`, `remove`, `replace`) and target-id semantics BEFORE writing tests.

**Step 2: Failing tests.** Cover the three ops + unknown-op error path:

```python
import copy, pytest
from architecture_model.ai.proposals import ModelPatch
from architecture_model.ai.patch import apply_model_patch
from architecture_model.core.errors import ParseError
from architecture_model.core.parser import _parse_raw

def _base_model():
    return _parse_raw({
        "meta": {"project": "p", "schema_version": "1.3"},
        "entities": {"components": [{"id": "COMP-1", "name": "C1", "status": "ACTIVE"}]},
        "relationships": [],
    })

def test_apply_add_component():
    m = _base_model()
    patch = ModelPatch(operations=[
        {"op": "add", "target_kind": "components",
         "value": {"id": "COMP-2", "name": "C2", "status": "ACTIVE"}}
    ])
    m2 = apply_model_patch(m, patch)
    ids = {c.id for c in m2.entities.components}
    assert ids == {"COMP-1", "COMP-2"}

def test_apply_remove_component():
    m = _base_model()
    patch = ModelPatch(operations=[{"op": "remove", "target_id": "COMP-1"}])
    m2 = apply_model_patch(m, patch)
    assert m2.entities.components == []

def test_apply_replace_component_field():
    m = _base_model()
    patch = ModelPatch(operations=[
        {"op": "replace", "target_id": "COMP-1", "field": "name", "value": "renamed"}
    ])
    m2 = apply_model_patch(m, patch)
    assert m2.entities.components[0].name == "renamed"

def test_apply_unknown_op_raises_parse_error():
    m = _base_model()
    patch = ModelPatch(operations=[{"op": "nuke", "target_id": "COMP-1"}])
    with pytest.raises(ParseError):
        apply_model_patch(m, patch)

def test_apply_does_not_mutate_input():
    m = _base_model()
    before = copy.deepcopy(m)
    apply_model_patch(m, ModelPatch(operations=[{"op": "remove", "target_id": "COMP-1"}]))
    assert m.entities.components == before.entities.components
```

(Implementer must adjust op payload keys to match whatever `_VALID_OPS` semantics exist in validators.py. If the op schema differs, tests get rewritten to match reality — NOT to match this plan's guess.)

**Step 3: Run — expect FAIL** (no `patch` module).

**Step 4: Implement.** `ai/patch.py`:

```python
"""Apply ModelPatch proposals to ArchitectureModel."""
from __future__ import annotations

import copy
from typing import Any

from architecture_model.ai.proposals import ModelPatch
from architecture_model.core.errors import ParseError
from architecture_model.core.types import ArchitectureModel

__all__ = ["apply_model_patch"]

_VALID_OPS = {"add", "remove", "replace"}  # keep in sync with ai.validators


def apply_model_patch(model: ArchitectureModel, patch: ModelPatch) -> ArchitectureModel:
    """Return a new ArchitectureModel with patch.operations applied.

    Raises ParseError on unknown op or malformed operation.
    Does not mutate input model.
    """
    result = copy.deepcopy(model)
    for op in patch.operations:
        kind = op.get("op")
        if kind not in _VALID_OPS:
            raise ParseError(f"unknown patch op: {kind!r}")
        if kind == "add":
            _apply_add(result, op)
        elif kind == "remove":
            _apply_remove(result, op)
        elif kind == "replace":
            _apply_replace(result, op)
    return result


def _apply_add(model: ArchitectureModel, op: dict[str, Any]) -> None: ...
def _apply_remove(model: ArchitectureModel, op: dict[str, Any]) -> None: ...
def _apply_replace(model: ArchitectureModel, op: dict[str, Any]) -> None: ...
```

Implementer fills in the three helpers based on the actual `ArchitectureModel.entities` shape.

**Step 5: Verify** — full suite: **2905 passed, 6 pre-existing**.

**Step 6: Commit**
```bash
git add src/architecture_model/ai/patch.py src/architecture_model/ai/__init__.py tests/ai/test_patch.py
git commit -m "feat(ai): add apply_model_patch executor (N52)"
```

---

### Task 9: N105 — `MaterializedSlice.to_dict()` emits `fragment`

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py` (MaterializedSlice dataclass at line 124)
- Test: `tests/lifecycle/test_model_slice_materializer.py` (add tests)

**Step 1: Failing tests.**

```python
def test_materialized_slice_to_dict_has_fragment_key():
    # Build MaterializedSlice via materialize() with a small model+slicespec
    mslice = _materialize_helper(...)
    d = mslice.to_dict()
    assert "fragment" in d
    assert "entities" in d["fragment"]

def test_materialized_slice_to_dict_round_trip_through_validators():
    from architecture_model.ai.validators import _collect_slice_entity_ids
    mslice = _materialize_helper(...)
    slice_dict = mslice.to_dict()
    ids = _collect_slice_entity_ids({slice_dict["slice_id"]: slice_dict})
    assert ids  # non-empty, meaning validators see entities via fragment key
```

(Implementer copies `_materialize_helper` shape from existing tests in the file.)

**Step 2: Run — expect FAIL** (no `to_dict`).

**Step 3: Fix.** Add to `MaterializedSlice`:

```python
def to_dict(self) -> dict:
    """Serialize to the shape expected by ai.validators (fragment key)."""
    from dataclasses import asdict
    return {
        "slice_id": self.slice_id,
        "architecture_id": self.architecture_id,
        "model_revision": self.model_revision,
        "fragment": self.model_fragment.to_dict(),
        "stub_entity_ids": list(self.stub_entity_ids),
        "provenance": self.provenance,
        "warnings": [asdict(w) for w in self.warnings],
    }
```

**Step 4: Verify** — full suite: **2907 passed, 6 pre-existing**.

**Step 5: Commit**
```bash
git add src/architecture_model/lifecycle/model_slice_materializer.py \
        tests/lifecycle/test_model_slice_materializer.py
git commit -m "feat(lifecycle): MaterializedSlice.to_dict emits fragment key (N105)"
```

---

### Task 10: Verification report + CONTEXT update

**Files:**
- Append: `docs/plans/2026-09-05-phase1-escalations.md` (`## Completion report`)
- Update: `CONTEXT.md` at repo root (mention new APIs: `ParseError`, `generation_dir`, `current_root_digest`, `WorkOrder.build`, `apply_model_patch`, `MaterializedSlice.to_dict`)

**Step 1:** Run full suite and record exact numbers. Expected: **2907 passed, 6 pre-existing failures.** Zero new failures.

**Step 2:** Append `## Completion report` to this plan with:
- Task-by-task result
- Test delta (2885 → 2907)
- Downstream impact note: opencode-arch may adopt new APIs in follow-up branch
- Nit-ledger status: N50, N52, N53, N64, N73, N74, N81, N100, N105 all closed

**Step 3:** Update `CONTEXT.md`:
- In the API sections, mention new symbols added.
- Update "Test suite" line to new count.

**Step 4: Commit**
```bash
git add docs/plans/2026-09-05-phase1-escalations.md CONTEXT.md
git commit -m "docs(phase1): completion report for 9 escalations (N50/52/53/64/73/74/81/100/105)"
```

---

## Completion report

**Date completed:** 2026-09-05
**Branch:** `feat/phase1-escalations` (based on `feat/curated-se-views` @ `7f0c7dc`)
**Worktree:** `.worktrees/phase1-escalations`

### Test suite delta

| Metric | Baseline | Final | Delta |
|--------|:--------:|:-----:|:-----:|
| Passed | 2885 | **2918** | **+33** |
| Pre-existing failures | 6 | 6 | 0 |
| New failures / regressions | — | **0** | — |

Command: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Result: `6 failed, 2918 passed, 102 skipped` in 68.35s. All 6 failures match the documented baseline (`test_has_f1_through_f6`, `test_has_functional_blocks`, `test_real_logs_db`, `test_name_version_requires`, `test_includes_confidence`, `test_includes_components`).

### Task-by-task result

| # | Nit | Commit | Summary | Reviewer verdict | Tests added |
|:-:|:---:|:------:|:--------|:-----------------|:-----------:|
| Plan | — | `918fb15` | Plan committed | — | — |
| T1 | N73 | `24d6751` | Removed clock injection from `_parse_meta` | APPROVED | +1 |
| T2 | N81 | `1583efe` | Added `.id` alias on `ArchitecturePackage` | APPROVED | +1 |
| T3 | N50 | `3feff3b` | Canonical `ParseError` (new `core/errors.py`; 4 raise sites; re-exports) | APPROVED | +7 |
| T4 | N74 | `787dd20` | Publicized `generation_dir` (kept `_generation_dir` alias) | APPROVED | +3 |
| T5 | N53 | `78d1f82` | Added `current_root_digest(pkg)` helper + `json` import | APPROVED | +2 |
| T6 | N64 | `69c2160` | Added `Provenance.proposal_id` (auto-derived SHA-256) | APPROVED | +4 |
| T7 | N100 | `67f9b72` | Added `WorkOrder.build(...)` factory | APPROVED | +6 |
| T8 | N52 | `78c743e` | New `ai/patch.py::apply_model_patch` (add/remove/replace; `move` → ParseError) | APPROVED | +6 |
| T9 | N105 | `915a33a` | Added `MaterializedSlice.to_dict()` emitting `fragment` key | APPROVED | +3 |

**Total new tests:** +33 (matches suite delta).

### Nit-ledger status

All 9 escalations closed:

- **N50** — canonical `ParseError` ✅
- **N52** — `apply_model_patch` executor ✅
- **N53** — `current_root_digest()` helper ✅
- **N64** — `Provenance.proposal_id` auto-derived ✅
- **N73** — clock injection removed from `_parse_meta` ✅
- **N74** — `generation_dir` publicized ✅
- **N81** — `ArchitecturePackage.id` alias ✅
- **N100** — `WorkOrder.build()` factory ✅
- **N105** — `MaterializedSlice.to_dict()` fragment shape ✅

### Downstream impact

The `opencode-arch` package (Phase 2 consumer, currently on main `531b845`) can now adopt the new APIs in a **follow-up branch**:

- Import `ParseError` for consistent parse-error handling.
- Consume `MaterializedSlice.to_dict()` directly instead of hand-rolling the `fragment` shape.
- Use `WorkOrder.build(...)` factory in tests and MCP handlers.
- Use `apply_model_patch(...)` for proposal application in `architect_extract`.
- Use `current_root_digest(pkg)` instead of reading `digest.json` directly.
- Use `.id` property on `ArchitecturePackage` where downstream code expected it.
- Rely on `Provenance.proposal_id` auto-derivation.
- Replace private `_generation_dir` calls with public `generation_dir`.

None of the changes are breaking: all Phase 1 API additions are additive, and the pre-existing symbols (`_generation_dir`, bare `ValueError` raises) are preserved as aliases / subclasses.

### Follow-up nit ledger (deferred; NOT in scope)

Recorded for a future maintenance pass; each is non-blocking:

1. **N73-followup** — `types.py:780` writes `generated_at` unconditionally on emit; add emit-side guard for true byte-identical round-trip.
2. **N50-ripple** — `ai/proposals.py:30/32/34` `Provenance.__post_init__` raises bare `ValueError`; migrate to `ParseError`. `serialization.py:171` loses yaml `node.start_mark` (line/col) info — restore in a follow-up.
3. **N53-nit** — malformed `digest.json` still raises raw `json.JSONDecodeError`/`KeyError`; wrap in `ParseError`.
4. **N64-nit** — `proposal_id` payload uses unescaped `|` delimiter — collision-prone if fields ever accept free-form text.
5. **N100-nits** — `id` shadows builtin (consider `work_order_id`); slice tuple `(id, rev)` is positional in the hash schema.
6. **N52-nits** — `move` op deferred as `ParseError` (validators allow it); `_apply_add` depends on private `_parse_raw`; silent no-op on missing `target_id` for `remove`/`replace` (undocumented policy).
