# CAP-DF Part 11 — `promise_save` Walk Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Ship the `save_promise_note` meta-walk + `architect_promise_save` MCP tool. Reads a Part-10 promise note (CommentStub with `PromiseTarget`), constructs a `WorkOrder` with `intent="fill_promise:<entity>:<attr>"` and `parameters={kind: "fill_promise", entity_id, attribute, source_comment_id, note_body}`, submits it via the existing WorkOrder store + JobStore + Journal path. Zero LLM calls — Tier 1 build; the Job it enqueues is what Part 12 (`author`) later executes with an LLM. Closes `CAP-WK.save`.

**Architecture:** Additive. New pure-Python function `save_promise_note(repo_path, comment_id, requested_by, *, now=None) -> WorkOrder` in `walks/meta/save_promise_note.py`. Loads stub via `comments.store.load_stub`, refuses stubs without `target`, builds `WorkOrder.build(...)` with `slices=[]`, `accepts=[ProposalKind.MODEL_PATCH]`, T2 budget (`max_tokens=8000, max_wall_seconds=120`), returns the WorkOrder. Persistence + Job creation happen in the OCA MCP tool `architect_promise_save`, which reuses the exact primitives from `architect_workorder_submit_tool` inline (WorkOrder atomic write, `JobStore.create`, `Journal.append`). No cross-tool async dispatch — the two tools share primitives, not the FastMCP wrapper.

**Tech Stack:** Python 3.11+ (anaconda), pydantic v2, pytest. Two-repo: AMS (this repo) + OCA (`../opencode-arch/`).

**Coverage impact:** 10 covered → 11 covered. Remaining uncovered: `author`.

---

## Prerequisites

- Working directory: `/Users/baigm2/Documents/Projects/architecture-model-standard`
- Branch: `feat/phase-5-fanout-provenance-family5`
- Head commit: `eea4bf2 feat(model): Part 10 — CAP-WK.note ...`
- OCA repo at `../opencode-arch/` on branch `feat/phase-5-fanout-provenance-family5`, head `983220d feat(mcp): architect_promise_note tool ...`
- Environment has `architecture_model` installed editably; Part 10's `note_promise` is importable.

---

## Task 1 — Write the `save_promise_note` meta-walk

**Files:**
- Create: `src/architecture_model/walks/meta/save_promise_note.py`
- Test: `tests/walks/meta/test_save_promise_note.py`

### Step 1: Write the failing test

Create `tests/walks/meta/test_save_promise_note.py`:

```python
"""Tests for save_promise_note meta-walk. Realizes ``CAP-WK.save``."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from architecture_model.ai.work_order import ProposalKind, WorkOrder
from architecture_model.comments.models import CommentStub, PromiseTarget
from architecture_model.comments.store import write_stub
from architecture_model.walks.meta.promise_note import note_promise
from architecture_model.walks.meta.save_promise_note import (
    NotAPromiseNoteError,
    SavePromiseNoteError,
    save_promise_note,
)


def _model_with_entity(entity_id: str, attribute: str) -> dict:
    return {
        "meta": {"schema_version": "3.0"},
        "entities": {
            "capabilities": [
                {
                    "id": entity_id,
                    "name": "test-cap",
                    "promises": [
                        {
                            "id": f"PR-{entity_id}-{attribute}",
                            "attribute": attribute,
                            "content": [],
                            "owner_entity": entity_id,
                            "delivered_from": None,
                            "verified_by": [],
                            "status": "proposed",
                            "gap_type": "retrofit-pending",
                            "provenance": "test",
                        }
                    ],
                }
            ]
        },
    }


def _fixed_now() -> datetime:
    return datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)


def _seed_note(tmp_path: Path) -> CommentStub:
    return note_promise(
        repo_path=tmp_path,
        model=_model_with_entity("CAP-DF.3", "goals"),
        entity_id="CAP-DF.3",
        attribute="goals",
        text="need measurable outcome",
        author="tester",
        now=_fixed_now(),
    )


def test_save_returns_workorder(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert isinstance(wo, WorkOrder)
    assert wo.intent == "fill_promise:CAP-DF.3:goals"
    assert wo.requested_by == "tester"


def test_save_workorder_carries_promise_parameters(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    params = dict(wo.parameters)
    assert params["kind"] == "fill_promise"
    assert params["entity_id"] == "CAP-DF.3"
    assert params["attribute"] == "goals"
    assert params["source_comment_id"] == stub.comment_id
    assert params["note_body"] == "need measurable outcome"


def test_save_workorder_accepts_model_patch(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert list(wo.accepts) == [ProposalKind.MODEL_PATCH]


def test_save_workorder_t2_budget(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert wo.budget.max_tokens == 8000
    assert wo.budget.max_wall_seconds == 120


def test_save_workorder_empty_slices(tmp_path: Path):
    stub = _seed_note(tmp_path)
    wo = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert list(wo.slices) == []


def test_save_workorder_deterministic_id(tmp_path: Path):
    """Same (comment_id, requested_by, now) → same WorkOrder id."""
    stub = _seed_note(tmp_path)
    wo_a = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    wo_b = save_promise_note(
        repo_path=tmp_path,
        comment_id=stub.comment_id,
        requested_by="tester",
        now=_fixed_now(),
    )
    assert wo_a.id == wo_b.id


def test_save_rejects_non_promise_note(tmp_path: Path):
    """CommentStub without a `target` cannot be saved."""
    stub = CommentStub(
        comment_id="freeform-001",
        artifact_id="a-1",
        view_id="v-1",
        slice_id="s-1",
        package_id="p-1",
        revision="0000001",
        target_entity_id="COMP-X",
        body="freeform comment (no promise target)",
        author="tester",
        created_at=_fixed_now(),
    )
    write_stub(tmp_path, stub)
    with pytest.raises(NotAPromiseNoteError):
        save_promise_note(
            repo_path=tmp_path,
            comment_id="freeform-001",
            requested_by="tester",
            now=_fixed_now(),
        )


def test_save_missing_comment(tmp_path: Path):
    with pytest.raises(SavePromiseNoteError):
        save_promise_note(
            repo_path=tmp_path,
            comment_id="does-not-exist",
            requested_by="tester",
            now=_fixed_now(),
        )


def test_save_docstring_declares_cap_wk_save():
    """Meta-coverage discovery (Part 9 audit) requires this marker."""
    import architecture_model.walks.meta.save_promise_note as m

    assert m.__doc__ is not None
    assert "``CAP-WK.save``" in m.__doc__
```

### Step 2: Run test to verify it fails

```
python -m pytest tests/walks/meta/test_save_promise_note.py -v
```

Expected: `ModuleNotFoundError: architecture_model.walks.meta.save_promise_note`.

### Step 3: Implement the walk

Create `src/architecture_model/walks/meta/save_promise_note.py`:

```python
"""Save-promise-note walk.

Realizes ``CAP-WK.save``.

Reads a promise note produced by :func:`architecture_model.walks.meta.
promise_note.note_promise` and constructs an
:class:`~architecture_model.ai.work_order.WorkOrder` targeting the
noted ``(entity_id, attribute)`` promise slot. The WorkOrder is
returned; persistence + Job creation happen in the OCA MCP tool
``architect_promise_save`` which reuses the WorkOrder store + JobStore
+ Journal primitives.

Tier: T1 (no LLM). Part 11 of CAP-DF Parts 10–15.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from architecture_model.ai.work_order import ProposalKind, WorkOrder
from architecture_model.comments.store import StubMissingError, load_stub

# Tier T2 (LLM-review) default budget — matches CAP-DF Parts 10–15 design.
_MAX_TOKENS = 8000
_MAX_WALL_SECONDS = 120


class SavePromiseNoteError(RuntimeError):
    """Base error for save-promise-note operations."""


class NotAPromiseNoteError(SavePromiseNoteError):
    """Raised when the loaded stub has no ``target`` (not a promise note)."""


def save_promise_note(
    *,
    repo_path: Path,
    comment_id: str,
    requested_by: str,
    now: datetime | None = None,
    parameters: Mapping[str, Any] | None = None,
) -> WorkOrder:
    """Build a WorkOrder from a promise-note CommentStub.

    Parameters
    ----------
    repo_path
        Repository root; comment is loaded from
        ``.architecture/comments/<comment_id>.yaml``.
    comment_id
        Identifier of the promise note (produced by ``note_promise``).
    requested_by
        Free-form actor id recorded on the WorkOrder.
    now
        Optional injected timestamp for deterministic WorkOrder ids.
    parameters
        Optional extra parameters to merge with the auto-derived
        ``fill_promise`` payload. Reserved keys (``kind``, ``entity_id``,
        ``attribute``, ``source_comment_id``, ``note_body``) always win.

    Returns
    -------
    The constructed :class:`WorkOrder` (not yet persisted).

    Raises
    ------
    SavePromiseNoteError
        If the comment does not exist.
    NotAPromiseNoteError
        If the loaded stub has no ``target`` (freeform comment, not a
        promise note).
    """
    try:
        stub = load_stub(repo_path, comment_id)
    except StubMissingError as exc:
        raise SavePromiseNoteError(f"comment not found: {comment_id!r}") from exc

    if stub.target is None:
        raise NotAPromiseNoteError(
            f"comment {comment_id!r} has no promise target — "
            "cannot save as fill_promise WorkOrder"
        )

    ts = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    base_params: dict[str, Any] = dict(parameters or {})
    # Reserved keys — override any caller-provided value.
    base_params.update(
        {
            "kind": "fill_promise",
            "entity_id": stub.target.entity_id,
            "attribute": stub.target.attribute,
            "source_comment_id": stub.comment_id,
            "note_body": stub.body,
        }
    )

    intent = f"fill_promise:{stub.target.entity_id}:{stub.target.attribute}"

    return WorkOrder.build(
        intent=intent,
        slices=[],
        accepts=[ProposalKind.MODEL_PATCH],
        requested_by=requested_by,
        max_tokens=_MAX_TOKENS,
        max_wall_seconds=_MAX_WALL_SECONDS,
        parameters=base_params,
        created_at=ts,
    )


__all__ = [
    "NotAPromiseNoteError",
    "SavePromiseNoteError",
    "save_promise_note",
]
```

### Step 4: Run test to verify it passes

```
python -m pytest tests/walks/meta/test_save_promise_note.py -v
```

Expected: 9 pass.

### Step 5: Quick smoke — verify WorkOrder validates against schema

```
python -c "
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from architecture_model.walks.meta.promise_note import note_promise
from architecture_model.walks.meta.save_promise_note import save_promise_note
model = {'meta': {'schema_version': '3.0'}, 'entities': {'capabilities': [{'id': 'CAP-X', 'name': 't', 'promises': [{'id': 'P1', 'attribute': 'goals', 'content': [], 'owner_entity': 'CAP-X', 'delivered_from': None, 'verified_by': [], 'status': 'proposed', 'gap_type': 'retrofit-pending', 'provenance': 't'}]}]}}
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    stub = note_promise(repo_path=p, model=model, entity_id='CAP-X', attribute='goals', text='hello', author='a', now=datetime(2026,9,18,tzinfo=timezone.utc))
    wo = save_promise_note(repo_path=p, comment_id=stub.comment_id, requested_by='a', now=datetime(2026,9,18,tzinfo=timezone.utc))
    errs = wo.validate_schema()
    print('validate_schema errors:', errs)
    print('id:', wo.id)
    print('intent:', wo.intent)
"
```

Expected: `validate_schema errors: []`. If not, STOP — the WorkOrder shape needs adjustment before persistence in Task 3.

### Step 6: Do not commit yet — Task 2 folds into the same commit.

---

## Task 2 — Wire `CAP-WK.save` promise to verified

**File:** `.architecture/model/capabilities.v3.yaml`

### Step 1: Locate current block

```
python -c "
import yaml
data = yaml.safe_load(open('.architecture/model/capabilities.v3.yaml'))
def walk(d):
    if isinstance(d, dict):
        if d.get('id') == 'CAP-WK.save':
            for p in d.get('promises', []):
                print(p.get('id'), p.get('status'))
        for v in d.values(): walk(v)
    elif isinstance(d, list):
        for x in d: walk(x)
walk(data)
"
```

Expected: `PR-CAP-WK-save-intent proposed`.

### Step 2: Edit the promise block

Find (indentation and surrounding fields may vary; preserve them):

```yaml
    - id: PR-CAP-WK-save-intent
      attribute: intent
      content:
      - Note → walk-author closure trigger.
      owner_entity: CAP-WK.save
      delivered_from: null
      verified_by: []
      status: proposed
      gap_type: retrofit-pending
      provenance: <existing text>
```

Replace ONLY this promise's fields with:

```yaml
    - id: PR-CAP-WK-save-intent
      attribute: intent
      content:
      - Save-promise-note walk. Reads a promise note (CommentStub with PromiseTarget) and constructs a WorkOrder with intent="fill_promise:<entity>:<attr>" and parameters describing the promise slot to fill. Persistence + Job creation happen in the OCA MCP tool architect_promise_save which reuses the existing WorkOrder store + JobStore + Journal primitives. Tier T1 (no LLM); the enqueued Job is what Part 12's author walk later executes.
      owner_entity: CAP-WK.save
      delivered_from: null
      verified_by:
      - src/architecture_model/walks/meta/save_promise_note.py
      - tests/walks/meta/test_save_promise_note.py
      status: verified
      gap_type: null
      provenance: Part 11 (2026-09-18) — CAP-DF ceremony ships save as Python meta-walk over comments/store + ai/work_order.
```

Preserve YAML indentation exactly.

### Step 3: Verify meta-coverage bumps to 11/1/2

```
python -c "
from pathlib import Path
import yaml
from architecture_model.walks.meta import audit_walk_coverage
from collections import Counter
model = yaml.safe_load(open('.architecture/model/capabilities.v3.yaml'))
r = audit_walk_coverage(Path('.architecture/model/walks'), model)
print(Counter(c.verdict for c in r.cards))
"
```

Expected: `Counter({'covered': 11, 'uncovered': 1, 'duplicate-walk': 2})`.

If still 10/2/2, verify the docstring `Realizes ``CAP-WK.save``` marker in `save_promise_note.py` matches Part 9's regex.

---

## Task 3 — OCA MCP tool `architect_promise_save`

**Files (OCA repo `../opencode-arch/`):**
- Create: `src/opencode_arch/mcp/tools/promise_save.py`
- Modify: `src/opencode_arch/mcp/server.py` (register new tool)
- Test: `tests/mcp/test_promise_save_tool.py`

### Step 1: Study existing pattern

Read `../opencode-arch/src/opencode_arch/mcp/tools/ai/workorder_submit.py` to understand the exact persistence + Job-creation + Journal sequence. The new tool reuses these primitives inline (do NOT call the other tool's async wrapper).

Also read `../opencode-arch/src/opencode_arch/mcp/tools/promise_note.py` (Part 10) as the local envelope + tool-registration reference.

### Step 2: Write failing MCP test

Create `../opencode-arch/tests/mcp/test_promise_save_tool.py`:

```python
"""Tests for architect_promise_save MCP tool. Wraps save_promise_note walk."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from opencode_arch.mcp.tools.promise_save import architect_promise_save
from opencode_arch.mcp.tools.promise_note import architect_promise_note


def _write_model(repo: Path) -> None:
    (repo / ".architecture" / "model").mkdir(parents=True, exist_ok=True)
    (repo / ".architecture" / "model" / "capabilities.v3.yaml").write_text(
        yaml.safe_dump(
            {
                "meta": {"schema_version": "3.0"},
                "entities": {
                    "capabilities": [
                        {
                            "id": "CAP-DF.3",
                            "name": "cap",
                            "promises": [
                                {
                                    "id": "PR-CAP-DF.3-goals",
                                    "attribute": "goals",
                                    "content": [],
                                    "owner_entity": "CAP-DF.3",
                                    "delivered_from": None,
                                    "verified_by": [],
                                    "status": "proposed",
                                    "gap_type": "retrofit-pending",
                                    "provenance": "test",
                                }
                            ],
                        }
                    ]
                },
            }
        )
    )


def _seed_note(repo: Path) -> str:
    _write_model(repo)
    env = architect_promise_note(
        repo_path=str(repo),
        entity_id="CAP-DF.3",
        attribute="goals",
        text="need measurable outcome",
        author="tester",
    )
    assert env["ok"] is True
    return env["comment_id"]


def test_happy_path(tmp_path: Path):
    cid = _seed_note(tmp_path)
    env = architect_promise_save(
        repo_path=str(tmp_path),
        comment_id=cid,
        requested_by="tester",
    )
    assert env["ok"] is True, env
    assert "work_order_id" in env
    assert "job_id" in env
    # Persistence: WorkOrder + Job files exist under .architecture/ai/
    wo_dir = tmp_path / ".architecture" / "ai" / "workorders"
    jobs_dir = tmp_path / ".architecture" / "ai" / "jobs"
    assert wo_dir.exists()
    assert jobs_dir.exists()
    assert (wo_dir / f"{env['work_order_id']}.yaml").exists()


def test_missing_repo(tmp_path: Path):
    env = architect_promise_save(
        repo_path=str(tmp_path / "does-not-exist"),
        comment_id="cid",
        requested_by="t",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


def test_missing_comment(tmp_path: Path):
    _write_model(tmp_path)
    env = architect_promise_save(
        repo_path=str(tmp_path),
        comment_id="does-not-exist",
        requested_by="t",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["reason"] == "comment_missing"


def test_freeform_comment_rejected(tmp_path: Path):
    """A CommentStub without a target (freeform, not a promise note) is rejected."""
    from architecture_model.comments.models import CommentStub
    from architecture_model.comments.store import write_stub

    stub = CommentStub(
        comment_id="freeform-001",
        artifact_id="a-1",
        view_id="v-1",
        slice_id="s-1",
        package_id="p-1",
        revision="0000001",
        target_entity_id="COMP-X",
        body="freeform",
        author="t",
        created_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
    )
    write_stub(tmp_path, stub)

    env = architect_promise_save(
        repo_path=str(tmp_path),
        comment_id="freeform-001",
        requested_by="t",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["reason"] == "not_a_promise_note"


def test_invalid_argument_empty_requested_by(tmp_path: Path):
    cid = _seed_note(tmp_path)
    env = architect_promise_save(
        repo_path=str(tmp_path),
        comment_id=cid,
        requested_by="",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
```

### Step 3: Run test to verify it fails

```
python -m pytest tests/mcp/test_promise_save_tool.py -v
```

Expected: `ModuleNotFoundError`.

### Step 4: Implement the MCP tool

Create `../opencode-arch/src/opencode_arch/mcp/tools/promise_save.py`:

```python
"""``architect_promise_save`` MCP tool.

Wraps :func:`architecture_model.walks.meta.save_promise_note.save_promise_note`,
persists the resulting WorkOrder, creates a tracking Job, and journals
the submission — mirroring the primitives used by
``architect_workorder_submit``. Part of CAP-DF Part 11 ceremony.

Contract:
    Input:  repo_path, comment_id, requested_by (all str).
    Output: {ok: True, work_order_id: str, job_id: str} on success.
            {ok: False, error: {code, message, details?}} on failure.

Error codes:
    INVALID_ARGUMENT     — empty required field.
    NOT_FOUND            — repo_path missing.
    PRECONDITION_FAILED  — comment_missing | not_a_promise_note |
                           already_exists.
    SCHEMA_VIOLATION     — WorkOrder validate_schema returned errors.
    INTERNAL             — unexpected error.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from architecture_model.walks.meta.save_promise_note import (
    NotAPromiseNoteError,
    SavePromiseNoteError,
    save_promise_note,
)


def _err(code: str, message: str, **details: Any) -> dict:
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


def architect_promise_save(
    *,
    repo_path: str,
    comment_id: str,
    requested_by: str,
) -> dict:
    if not isinstance(comment_id, str) or not comment_id:
        return _err("INVALID_ARGUMENT", "comment_id must be a non-empty string")
    if not isinstance(requested_by, str) or not requested_by:
        return _err("INVALID_ARGUMENT", "requested_by must be a non-empty string")

    repo = Path(repo_path)
    if not repo.exists():
        return _err(
            "NOT_FOUND",
            f"repo_path does not exist: {repo_path}",
            reason="repo_missing",
        )

    # Build WorkOrder.
    try:
        wo = save_promise_note(
            repo_path=repo, comment_id=comment_id, requested_by=requested_by
        )
    except NotAPromiseNoteError as exc:
        return _err(
            "PRECONDITION_FAILED",
            str(exc),
            reason="not_a_promise_note",
            comment_id=comment_id,
        )
    except SavePromiseNoteError as exc:
        return _err(
            "PRECONDITION_FAILED",
            str(exc),
            reason="comment_missing",
            comment_id=comment_id,
        )
    except Exception as exc:  # pragma: no cover
        return _err("INTERNAL", f"walk error: {exc}")

    # Validate schema (mirrors architect_workorder_submit).
    schema_errors = wo.validate_schema()
    if schema_errors:
        return _err(
            "SCHEMA_VIOLATION",
            "WorkOrder failed schema validation",
            errors=[str(e) for e in schema_errors],
        )

    # Persist WorkOrder + create Job + journal — mirror
    # architect_workorder_submit_tool primitives inline.
    from architecture_model.ai.jobs import JobStore
    from architecture_model.lifecycle.atomic_store import write_atomic
    from architecture_model.lifecycle.journal import Journal

    try:
        wo_dir = repo / ".architecture" / "ai" / "workorders"
        wo_dir.mkdir(parents=True, exist_ok=True)
        wo_path = wo_dir / f"{wo.id}.yaml"
        if wo_path.exists():
            return _err(
                "PRECONDITION_FAILED",
                f"WorkOrder already exists: {wo.id}",
                reason="already_exists",
                work_order_id=wo.id,
            )

        import yaml as _yaml

        payload = _yaml.safe_dump(wo.to_dict(), sort_keys=True).encode("utf-8")
        write_atomic(wo_path, payload)

        store = JobStore(repo)
        job = store.create(work_order_id=wo.id)

        Journal(repo).append(
            {
                "event": "workorder_submitted",
                "work_order_id": wo.id,
                "job_id": job.job_id,
                "source": "architect_promise_save",
            }
        )
    except Exception as exc:  # pragma: no cover
        return _err("INTERNAL", f"persistence error: {exc}")

    return {"ok": True, "work_order_id": wo.id, "job_id": job.job_id}


__all__ = ["architect_promise_save"]
```

**Note on primitives:** the exact `JobStore.create` / `Journal.append` signatures may differ slightly from what's above — copy the exact calls from `../opencode-arch/src/opencode_arch/mcp/tools/ai/workorder_submit.py`'s inline persistence block. If any call fails at runtime, mirror it verbatim from that file rather than inventing.

### Step 5: Register in server.py

Read `../opencode-arch/src/opencode_arch/mcp/server.py`, find where `architect_promise_note` was registered (Part 10, adjacent to `architect_require`), and add a parallel `@mcp.tool()` async wrapper for `architect_promise_save`. Match the surrounding style EXACTLY.

Typical (verify against actual):

```python
from opencode_arch.mcp.tools.promise_save import architect_promise_save as _promise_save_impl

# ... near architect_promise_note wrapper ...

@mcp.tool()
async def architect_promise_save(
    repo_path: str,
    comment_id: str,
    requested_by: str,
) -> dict:
    """Save a promise note as a WorkOrder + Job (CAP-DF Part 11)."""
    return _promise_save_impl(
        repo_path=repo_path,
        comment_id=comment_id,
        requested_by=requested_by,
    )
```

### Step 6: Run tests to verify pass

```
python -m pytest tests/mcp/test_promise_save_tool.py -v
```

Expected: 5 pass.

### Step 7: OCA MCP subtree regression check

```
python -m pytest tests/mcp/ -q -p no:cacheprovider
```

Expected: no regressions.

---

## Task 4 — Update CONTEXT.md

**File:** `CONTEXT.md`

Find the "Part 10 additions" block (added by Part 10, ends with `**2 uncovered** (``save``, ``author`` — Parts 11–12).`). Immediately AFTER that paragraph, add:

```markdown
**Part 11 additions** (2026-09-18):

- `src/architecture_model/walks/meta/save_promise_note.py` (new Python
  meta-walk, ``Realizes ``CAP-WK.save```): ``save_promise_note(
  repo_path, comment_id, requested_by, now=None, parameters=None)
  -> WorkOrder``. Loads a promise note via
  ``comments.store.load_stub``, refuses stubs without ``target``, builds
  a WorkOrder with ``intent="fill_promise:<entity>:<attr>"``,
  ``accepts=[ProposalKind.MODEL_PATCH]``, T2 budget (max_tokens=8000,
  max_wall_seconds=120), ``slices=[]``, and parameters
  ``{kind: "fill_promise", entity_id, attribute, source_comment_id,
  note_body}``. Tier T1 (no LLM); the enqueued Job is what Part 12's
  author walk later executes.
- `.architecture/model/capabilities.v3.yaml`: ``PR-CAP-WK-save-intent``
  flipped ``proposed`` → ``verified`` with verified_by wires.
- `../opencode-arch/src/opencode_arch/mcp/tools/promise_save.py` (new
  MCP tool): ``architect_promise_save`` envelope wrapper. Persists the
  WorkOrder, creates a tracking Job, and journals the submission —
  reuses the same primitives as ``architect_workorder_submit``. Error
  codes: INVALID_ARGUMENT | NOT_FOUND (repo_missing) |
  PRECONDITION_FAILED (comment_missing | not_a_promise_note |
  already_exists) | SCHEMA_VIOLATION | INTERNAL.

Coverage after Part 11 (2026-09-18): **11 covered**, 2 duplicate-walk,
**1 uncovered** (``author`` — Part 12).
```

---

## Task 5 — Verification before commit

### Step 1: AMS walks + comments

```
python -m pytest tests/walks/ tests/comments/ -q -p no:cacheprovider
```

Expected: all pass (previous 186 + 9 new = 195).

### Step 2: Full AMS suite

```
python -m pytest tests/ -q --ignore=tests/test_config_loader.py -p no:cacheprovider
```

Expected: 4287 + 9 ≈ 4296 passed, 105 skipped, 0 failures.

### Step 3: OCA MCP subtree

```
python -m pytest ../opencode-arch/tests/mcp/ -q -p no:cacheprovider
```

Expected: 334 + 5 ≈ 339 passed, no regressions.

### Step 4: Coverage counter

```
python -c "
from pathlib import Path
import yaml
from architecture_model.walks.meta import audit_walk_coverage
from collections import Counter
model = yaml.safe_load(open('.architecture/model/capabilities.v3.yaml'))
r = audit_walk_coverage(Path('.architecture/model/walks'), model)
print(Counter(c.verdict for c in r.cards))
"
```

Expected: `Counter({'covered': 11, 'uncovered': 1, 'duplicate-walk': 2})`.

STOP if any step regresses.

---

## Task 6 — Commit

### Step 1: Stage AMS files explicitly

```
git add src/architecture_model/walks/meta/save_promise_note.py \
        tests/walks/meta/test_save_promise_note.py \
        .architecture/model/capabilities.v3.yaml \
        CONTEXT.md
```

### Step 2: Verify staged tree

```
git status --short | grep -E "^[MA] "
```

Expected: only the 4 files above.

### Step 3: Commit AMS

```
git commit -m "feat(model): Part 11 — CAP-WK.save (promise-note → WorkOrder walk)

- walks/meta/save_promise_note.py: Python meta-walk realizing CAP-WK.save.
  Loads a promise note (CommentStub with PromiseTarget), builds a WorkOrder
  with intent=fill_promise:<entity>:<attr>, accepts=[MODEL_PATCH], T2 budget,
  slices=[], and parameters carrying the promise slot + note body.
  Tier T1 (no LLM); the enqueued Job is what Part 12 later executes.
- capabilities.v3.yaml: PR-CAP-WK-save-intent -> verified with wires.
- Tests: 9 walk tests, all pass.

Coverage: 10 -> 11 covered on capabilities.v3.yaml. Part 12 (author) remaining."
```

### Step 4: Commit OCA (separate repo)

```
cd ../opencode-arch
git add src/opencode_arch/mcp/tools/promise_save.py \
        src/opencode_arch/mcp/server.py \
        tests/mcp/test_promise_save_tool.py
git status --short | grep -E "^[MA] "
git commit -m "feat(mcp): architect_promise_save tool (CAP-DF Part 11)

Envelope wrapper around architecture_model.walks.meta.save_promise_note.
Persists the WorkOrder, creates a tracking Job, and journals the
submission — reuses the same primitives as architect_workorder_submit.

Error codes: INVALID_ARGUMENT | NOT_FOUND (repo_missing) |
PRECONDITION_FAILED (comment_missing / not_a_promise_note /
already_exists) | SCHEMA_VIOLATION | INTERNAL.

Realizes the OCA side of CAP-WK.save. 5 tests, all pass."
cd -
```

### Step 5: Confirm

```
git log -1 --oneline && cd ../opencode-arch && git log -1 --oneline && cd -
```

---

## Success criteria

- [x] `save_promise_note` walk exists with `Realizes ``CAP-WK.save``` docstring marker.
- [x] Walk returns a valid `WorkOrder` (validate_schema errors == []).
- [x] Walk refuses freeform comments (no `target`) with `NotAPromiseNoteError`.
- [x] Deterministic WorkOrder id under fixed `now` + inputs.
- [x] `PR-CAP-WK-save-intent` status = `verified`, verified_by wires present.
- [x] `architect_promise_save` MCP tool persists WorkOrder + Job atomically, returns `{ok, work_order_id, job_id}`.
- [x] Full AMS suite green: ≈4296 passed, 105 skipped, 0 failures.
- [x] OCA MCP tests green: 5 new pass, no regressions.
- [x] Meta-coverage: `11 covered / 1 uncovered / 2 duplicate-walk`.
- [x] Two atomic commits (one per repo), explicit `git add` paths.

---

## Notes for Part 12 (`author`)

- The Jobs enqueued by Part 11 sit in `.architecture/ai/jobs/` in `queued` state.
- Part 12's `author` walk (or the OCA `architect_promise_author` tool) will:
  - Dequeue a Job whose WorkOrder has `parameters.kind == "fill_promise"`.
  - Dispatch a new `PromisePatchLLM` write-back projector variant against a slice scoped to the promise's owning entity.
  - Emit a `model-patch` proposal that fills the promise `content` list.
  - Set the WorkOrder's Job state to `completed` with `result_ref` pointing at the proposal.
- Part 12 is the first Part that actually calls an LLM (Tier T3 — authoring).
