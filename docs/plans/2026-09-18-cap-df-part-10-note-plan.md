# CAP-DF Part 10 — `promise_note` Walk Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship the `promise_note` meta-walk + `architect_promise_note` MCP tool, extending the `Comment` model with an optional promise target so users/agents can attach notes to specific (entity_id, attribute) promise slots. Closes `CAP-WK.note` sub-cap.

**Architecture:** Additive extension of existing `comments/` substrate. New `PromiseTarget` pydantic model + optional `target` field on `CommentStub`. New Python meta-walk (`walks/meta/promise_note.py`) that validates entity+attribute against a v3 model, constructs a `CommentStub` with sentinel view-scope fields, and delegates to `comments.store.write_stub`. New OCA MCP tool `architect_promise_note` that wraps the walk with envelope-shaped error handling. Zero LLM calls — Tier 1.

**Tech Stack:** Python 3.11+ (anaconda), pydantic v2, PyYAML, pytest. Two-repo: AMS (this repo) + OCA (`../opencode-arch/`).

**Coverage impact:** 9 covered → 10 covered on `capabilities.v3.yaml`.

---

## Prerequisites

- Working directory: `/Users/baigm2/Documents/Projects/architecture-model-standard`
- Branch: `feat/phase-5-fanout-provenance-family5` (current)
- Verify clean start: `git log -1 --oneline` should show `ca8b3c0 docs: CAP-DF Parts 10–15 design...`
- OCA repo at `../opencode-arch/` on any branch

---

## Task 1 — Extend `CommentStub` with optional promise target

**Files:**
- Modify: `src/architecture_model/comments/models.py`
- Test: `tests/comments/test_promise_target.py`

**Step 1: Write the failing test**

Create `tests/comments/test_promise_target.py`:

```python
"""Tests for PromiseTarget on CommentStub. Realizes CAP-WK.note (Part 10 Task 1)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from architecture_model.comments.models import CommentStub, PromiseTarget


def _base_stub_kwargs() -> dict:
    return dict(
        comment_id="c-001",
        artifact_id="a-001",
        view_id="v-001",
        slice_id="s-001",
        package_id="p-001",
        revision="0000001",
        body="hello",
        author="tester",
        created_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
    )


def test_promise_target_construction():
    t = PromiseTarget(entity_id="CAP-DF.3", attribute="goals")
    assert t.entity_id == "CAP-DF.3"
    assert t.attribute == "goals"


def test_promise_target_forbids_extra_fields():
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="CAP-DF.3", attribute="goals", extra="nope")


def test_promise_target_requires_entity_id():
    with pytest.raises(ValidationError):
        PromiseTarget(attribute="goals")


def test_promise_target_requires_attribute():
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="CAP-DF.3")


def test_promise_target_rejects_empty_strings():
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="", attribute="goals")
    with pytest.raises(ValidationError):
        PromiseTarget(entity_id="CAP-DF.3", attribute="")


def test_comment_stub_target_defaults_none():
    stub = CommentStub(**_base_stub_kwargs())
    assert stub.target is None


def test_comment_stub_accepts_target():
    stub = CommentStub(
        **_base_stub_kwargs(),
        target=PromiseTarget(entity_id="CAP-DF.3", attribute="goals"),
    )
    assert stub.target is not None
    assert stub.target.entity_id == "CAP-DF.3"
    assert stub.target.attribute == "goals"


def test_comment_stub_serializes_with_target():
    stub = CommentStub(
        **_base_stub_kwargs(),
        target=PromiseTarget(entity_id="CAP-DF.3", attribute="goals"),
    )
    dumped = stub.model_dump(mode="json")
    assert dumped["target"] == {"entity_id": "CAP-DF.3", "attribute": "goals"}


def test_comment_stub_backward_compat_no_target():
    # Existing stubs without a `target` field parse unchanged.
    payload = _base_stub_kwargs()
    payload["created_at"] = payload["created_at"].isoformat()
    stub = CommentStub.model_validate(payload)
    assert stub.target is None
```

**Step 2: Run test to verify it fails**

```
python -m pytest tests/comments/test_promise_target.py -v
```

Expected: FAIL with `ImportError: cannot import name 'PromiseTarget' from 'architecture_model.comments.models'`.

**Step 3: Implement `PromiseTarget` + extend `CommentStub`**

Edit `src/architecture_model/comments/models.py`. Add after the `IssueRef` class and before `CommentStub`:

```python
class PromiseTarget(BaseModel):
    """Pointer to a specific promise slot on a v3 entity.

    Used by CAP-WK.note (Part 10) to attach comments to (entity_id,
    attribute) tuples rather than freeform bodies. Additive: existing
    stubs without a `target` field continue to parse unchanged.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_id: str = Field(..., min_length=1)
    attribute: str = Field(..., min_length=1)
```

Then extend `CommentStub` with the new optional field. In `CommentStub`, add after `issue_ref`:

```python
    target: Optional[PromiseTarget] = None
```

**Step 4: Run test to verify it passes**

```
python -m pytest tests/comments/test_promise_target.py -v
```

Expected: PASS (9 tests).

**Step 5: Verify no regressions in comment tests**

```
python -m pytest tests/comments/ -v
```

Expected: all existing tests still pass.

**Step 6: Do not commit yet — Task 2 (walk) lands in the same commit.**

---

## Task 2 — Write the `promise_note` meta-walk

**Files:**
- Create: `src/architecture_model/walks/meta/promise_note.py`
- Test: `tests/walks/meta/test_promise_note.py`
- Create dir if needed: `tests/walks/meta/`

**Step 1: Write the failing test**

Ensure `tests/walks/meta/__init__.py` exists (if not, create empty).

Create `tests/walks/meta/test_promise_note.py`:

```python
"""Tests for promise_note meta-walk. Realizes ``CAP-WK.note``."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import list_stubs
from architecture_model.walks.meta.promise_note import (
    PromiseNoteError,
    UnknownAttributeError,
    UnknownEntityError,
    note_promise,
)


def _model_with_entity(entity_id: str, attribute: str) -> dict:
    """Minimal v3-shape model dict carrying one entity with one promise slot."""
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


def test_note_promise_appends_stub(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    stub = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="Goal missing — must specify measurable outcome.",
        author="tester",
        now=_fixed_now(),
    )
    assert isinstance(stub, CommentStub)
    assert stub.target is not None
    assert stub.target.entity_id == "CAP-DF.3"
    assert stub.target.attribute == "goals"
    assert stub.body == "Goal missing — must specify measurable outcome."
    # Persisted on disk under .architecture/comments/
    saved = list(list_stubs(tmp_path))
    assert len(saved) == 1
    assert saved[0].comment_id == stub.comment_id


def test_note_promise_unknown_entity(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    with pytest.raises(UnknownEntityError):
        note_promise(
            repo_path=tmp_path,
            model=model,
            entity_id="CAP-DOES-NOT-EXIST",
            attribute="goals",
            text="body",
            author="t",
            now=_fixed_now(),
        )


def test_note_promise_unknown_attribute(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    with pytest.raises(UnknownAttributeError):
        note_promise(
            repo_path=tmp_path,
            model=model,
            entity_id="CAP-DF.3",
            attribute="does-not-exist",
            text="body",
            author="t",
            now=_fixed_now(),
        )


def test_note_promise_multiple_notes_per_promise(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    s1 = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="first",
        author="a",
        now=_fixed_now(),
    )
    s2 = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="second",
        author="b",
        now=_fixed_now(),
    )
    assert s1.comment_id != s2.comment_id
    saved = list(list_stubs(tmp_path))
    assert {s1.comment_id, s2.comment_id} == {s.comment_id for s in saved}


def test_note_promise_deterministic_comment_id(tmp_path: Path):
    """Same (entity, attribute, body, author, timestamp) → same comment_id."""
    from architecture_model.walks.meta.promise_note import _derive_comment_id

    cid_a = _derive_comment_id("CAP-DF.3", "goals", "body", "a", _fixed_now())
    cid_b = _derive_comment_id("CAP-DF.3", "goals", "body", "a", _fixed_now())
    assert cid_a == cid_b
    cid_c = _derive_comment_id("CAP-DF.3", "goals", "body", "b", _fixed_now())
    assert cid_a != cid_c


def test_note_promise_empty_body_rejected(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    with pytest.raises(PromiseNoteError):
        note_promise(
            repo_path=tmp_path,
            model=model,
            entity_id="CAP-DF.3",
            attribute="goals",
            text="",
            author="t",
            now=_fixed_now(),
        )


def test_note_promise_target_roundtrips_on_disk(tmp_path: Path):
    model = _model_with_entity("CAP-DF.3", "goals")
    stub = note_promise(
        repo_path=tmp_path,
        model=model,
        entity_id="CAP-DF.3",
        attribute="goals",
        text="roundtrip",
        author="t",
        now=_fixed_now(),
    )
    (loaded,) = list(list_stubs(tmp_path))
    assert loaded.target is not None
    assert loaded.target.entity_id == "CAP-DF.3"
    assert loaded.target.attribute == "goals"
    assert loaded.body == "roundtrip"


def test_note_promise_docstring_declares_cap_wk_note():
    """Meta-coverage discovery (Part 9 audit) requires this marker."""
    import architecture_model.walks.meta.promise_note as m

    assert m.__doc__ is not None
    assert "``CAP-WK.note``" in m.__doc__
```

**Step 2: Run test to verify it fails**

```
python -m pytest tests/walks/meta/test_promise_note.py -v
```

Expected: FAIL with `ModuleNotFoundError: architecture_model.walks.meta.promise_note`.

**Step 3: Implement the walk**

Create `src/architecture_model/walks/meta/promise_note.py`:

```python
"""Promise-scoped note walk.

Realizes ``CAP-WK.note``.

Attaches a comment to a specific ``(entity_id, attribute)`` promise slot
on a v3 architecture model. Validates the target against the model's
entity graph, constructs a :class:`~architecture_model.comments.models.CommentStub`
with a :class:`~architecture_model.comments.models.PromiseTarget`, and
persists it via :func:`architecture_model.comments.store.write_stub`.

Tier: T1 (no LLM). Part 10 of CAP-DF Parts 10–15.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from architecture_model.comments.models import CommentStub, PromiseTarget
from architecture_model.comments.store import write_stub

# Sentinel values for view-scope fields when a note originates outside a
# rendered artifact (e.g., from a CLI or MCP call rather than a viewer).
# The comment-store schema requires all view-scope fields; promise-scoped
# notes MAY carry real artifact context later, but Part 10 only enforces
# a non-empty placeholder to keep pydantic happy.
_SENTINEL_VIEW_ID = "promise-note"
_SENTINEL_SLICE_ID = "promise-note"
_SENTINEL_PACKAGE_ID = "promise-note"
_SENTINEL_REVISION = "0000000"


class PromiseNoteError(RuntimeError):
    """Base error for promise-scoped note operations."""


class UnknownEntityError(PromiseNoteError):
    """Raised when ``entity_id`` is not present in the model."""


class UnknownAttributeError(PromiseNoteError):
    """Raised when the target entity carries no promise for ``attribute``."""


def _iter_entities(model: Mapping[str, Any]):
    """Yield every entity dict across all v3 entity kinds."""
    entities = model.get("entities") or {}
    for kind_list in entities.values():
        if not isinstance(kind_list, list):
            continue
        for ent in kind_list:
            if isinstance(ent, Mapping):
                yield ent


def _find_entity(model: Mapping[str, Any], entity_id: str) -> Mapping[str, Any] | None:
    for ent in _iter_entities(model):
        if ent.get("id") == entity_id:
            return ent
    return None


def _entity_has_attribute(entity: Mapping[str, Any], attribute: str) -> bool:
    promises = entity.get("promises") or []
    for p in promises:
        if isinstance(p, Mapping) and p.get("attribute") == attribute:
            return True
    return False


def _derive_comment_id(
    entity_id: str, attribute: str, body: str, author: str, now: datetime
) -> str:
    """Deterministic comment id: sha1 over (entity, attr, body, author, iso-time)[:12]."""
    payload = "|".join(
        [entity_id, attribute, body, author, now.astimezone(timezone.utc).isoformat()]
    ).encode("utf-8")
    return "pn-" + hashlib.sha1(payload).hexdigest()[:12]


def note_promise(
    *,
    repo_path: Path,
    model: Mapping[str, Any],
    entity_id: str,
    attribute: str,
    text: str,
    author: str,
    now: datetime | None = None,
) -> CommentStub:
    """Attach a note to ``(entity_id, attribute)`` and persist it.

    Parameters
    ----------
    repo_path
        Repository root; comments are written under
        ``.architecture/comments/<comment_id>.yaml``.
    model
        v3-shape model dict (as loaded from ``capabilities.v3.yaml``).
    entity_id
        Target entity id (must exist in ``model.entities.*``).
    attribute
        Promise attribute to target (must exist on ``entity_id``'s
        ``promises`` list).
    text
        Note body (non-empty, max 8 KiB per ``CommentStub`` constraint).
    author
        Free-form author string.
    now
        Optional injected timestamp for deterministic tests. Defaults to
        ``datetime.now(timezone.utc)``.

    Returns
    -------
    The written :class:`CommentStub`.

    Raises
    ------
    UnknownEntityError
        If ``entity_id`` is not present in ``model``.
    UnknownAttributeError
        If the entity carries no promise for ``attribute``.
    PromiseNoteError
        If ``text`` is empty or whitespace-only.
    """
    if not text or not text.strip():
        raise PromiseNoteError("note text must be non-empty")

    entity = _find_entity(model, entity_id)
    if entity is None:
        raise UnknownEntityError(f"entity_id not in model: {entity_id!r}")
    if not _entity_has_attribute(entity, attribute):
        raise UnknownAttributeError(
            f"entity {entity_id!r} has no promise for attribute {attribute!r}"
        )

    ts = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    comment_id = _derive_comment_id(entity_id, attribute, text, author, ts)

    stub = CommentStub(
        comment_id=comment_id,
        artifact_id=f"promise-note:{entity_id}:{attribute}",
        view_id=_SENTINEL_VIEW_ID,
        slice_id=_SENTINEL_SLICE_ID,
        package_id=_SENTINEL_PACKAGE_ID,
        revision=_SENTINEL_REVISION,
        target_entity_id=entity_id,
        body=text,
        author=author,
        created_at=ts,
        target=PromiseTarget(entity_id=entity_id, attribute=attribute),
    )
    write_stub(repo_path, stub)
    return stub


__all__ = [
    "PromiseNoteError",
    "UnknownEntityError",
    "UnknownAttributeError",
    "note_promise",
]
```

**Step 4: Run test to verify it passes**

```
python -m pytest tests/walks/meta/test_promise_note.py -v
```

Expected: PASS (8 tests).

**Step 5: Verify meta-coverage sees the new walk**

```
python -c "
from pathlib import Path
import yaml
from architecture_model.walks.meta import audit_walk_coverage
from collections import Counter
model = yaml.safe_load(open('.architecture/model/capabilities.v3.yaml'))
r = audit_walk_coverage(Path('.architecture/model/walks'), model)
counts = Counter(c.verdict for c in r.cards)
print(counts)
covered = [c.subject_id for c in r.cards if c.verdict == 'covered']
print('CAP-WK.note covered:', 'CAP-WK.note' in covered)
"
```

Expected: `CAP-WK.note covered: True` AND the counts show one more `covered` than before (10 vs. 9). Note: the model wire in Task 4 is what actually flips this — until then, coverage stays at 9 but the walk file exists and is discoverable.

Actually the audit couples model sub-caps to walks via `verified_by` OR docstring `Realizes` marker. Since the docstring carries `Realizes ``CAP-WK.note```, Python meta-walk discovery should already list `META-promise_note` as a walk that audits `CAP-WK.note`. Expected output NOW: `CAP-WK.note` shows up as `covered`. If not, proceed to Task 4 which explicitly wires `verified_by` — Task 4 is the belt-and-braces path.

---

## Task 3 — Verify full test suite still green

**Step 1: Run walks tests**

```
python -m pytest tests/walks/ -q -p no:cacheprovider
```

Expected: all pass (previous 161 + 17 new).

**Step 2: Run full suite**

```
python -m pytest tests/ -q --ignore=tests/test_config_loader.py -p no:cacheprovider
```

Expected: 4270+ passed, 105 skipped, 0 failures.

Do NOT proceed if any regression appears. Investigate before continuing.

---

## Task 4 — Wire `CAP-WK.note` promise to verified

**Files:**
- Modify: `.architecture/model/capabilities.v3.yaml`

**Step 1: Locate `PR-CAP-WK-note-intent`**

```
python -c "
import yaml
with open('.architecture/model/capabilities.v3.yaml') as f:
    data = yaml.safe_load(f)
for ent in data.get('capabilities', []):
    if ent.get('id') == 'CAP-WK.note':
        for p in ent.get('promises', []):
            print(p['id'], p['status'], p.get('verified_by'))
"
```

Expected output shows `PR-CAP-WK-note-intent proposed []` (or similar).

**Step 2: Edit `capabilities.v3.yaml`**

Find the block:

```yaml
  - id: CAP-WK.note
    name: walk_note
    promises:
    - id: PR-CAP-WK-note-intent
      attribute: intent
      content:
      - Viewer-annotation walk producing note payloads.
      owner_entity: CAP-WK.note
      delivered_from: null
      verified_by: []
      status: proposed
      gap_type: retrofit-pending
      provenance: Part 4 step 5 (deferred to follow-up commit).
```

Replace with:

```yaml
  - id: CAP-WK.note
    name: walk_note
    promises:
    - id: PR-CAP-WK-note-intent
      attribute: intent
      content:
      - Promise-scoped note walk. Attaches a comment to a specific (entity_id, attribute) promise slot on a v3 architecture model, persisting it via the existing comments/store substrate. Tier T1 (no LLM). Enables the L13 loop's `note` step at promise granularity.
      owner_entity: CAP-WK.note
      delivered_from: null
      verified_by:
      - src/architecture_model/walks/meta/promise_note.py
      - src/architecture_model/comments/models.py
      - tests/walks/meta/test_promise_note.py
      - tests/comments/test_promise_target.py
      status: verified
      gap_type: null
      provenance: Part 10 (2026-09-18) — CAP-DF ceremony ships note as Python meta-walk over comments/store.
```

**Step 3: Run meta-coverage audit**

```
python -c "
from pathlib import Path
import yaml
from architecture_model.walks.meta import audit_walk_coverage
from collections import Counter
model = yaml.safe_load(open('.architecture/model/capabilities.v3.yaml'))
r = audit_walk_coverage(Path('.architecture/model/walks'), model)
counts = Counter(c.verdict for c in r.cards)
print(counts)
"
```

Expected: `Counter({'covered': 10, 'uncovered': 2, 'duplicate-walk': 2})`.

If the count is still `9 covered / 3 uncovered`, verify the docstring `Realizes ``CAP-WK.note``` marker matches Part 9's regex (allows `\s+` including newline between `Realizes` and backticks).

---

## Task 5 — OCA MCP tool `architect_promise_note`

**Files:**
- Create: `../opencode-arch/src/opencode_arch/mcp/tools/promise_note.py`
- Modify: `../opencode-arch/src/opencode_arch/mcp/server.py` (register new tool)
- Test: `../opencode-arch/tests/mcp/test_promise_note_tool.py`

**Step 1: Check existing MCP tool pattern**

Read one existing tool for reference:

```
python -c "
with open('../opencode-arch/src/opencode_arch/mcp/tools/require.py') as f:
    print(f.read())
" | head -80
```

Note the envelope convention (`{ok: bool, ...}` + `INVALID_ARGUMENT`/`NOT_FOUND`/`PRECONDITION_FAILED` error codes).

**Step 2: Write failing MCP test**

Create `../opencode-arch/tests/mcp/test_promise_note_tool.py`:

```python
"""Tests for architect_promise_note MCP tool. Wraps promise_note walk."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


def test_happy_path(tmp_path: Path):
    _write_model(tmp_path)
    env = architect_promise_note(
        repo_path=str(tmp_path),
        entity_id="CAP-DF.3",
        attribute="goals",
        text="need measurable outcome",
        author="tester",
    )
    assert env["ok"] is True
    assert "comment_id" in env
    # Persisted on disk
    assert (tmp_path / ".architecture" / "comments").exists()


def test_missing_repo(tmp_path: Path):
    env = architect_promise_note(
        repo_path=str(tmp_path / "does-not-exist"),
        entity_id="CAP-DF.3",
        attribute="goals",
        text="body",
        author="t",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"


def test_missing_model(tmp_path: Path):
    env = architect_promise_note(
        repo_path=str(tmp_path),
        entity_id="CAP-DF.3",
        attribute="goals",
        text="body",
        author="t",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "NOT_FOUND"
    assert env["error"]["details"]["reason"] == "model_missing"


def test_unknown_entity(tmp_path: Path):
    _write_model(tmp_path)
    env = architect_promise_note(
        repo_path=str(tmp_path),
        entity_id="CAP-DOES-NOT-EXIST",
        attribute="goals",
        text="body",
        author="t",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "PRECONDITION_FAILED"
    assert env["error"]["details"]["reason"] == "unknown_entity"


def test_empty_text_rejected(tmp_path: Path):
    _write_model(tmp_path)
    env = architect_promise_note(
        repo_path=str(tmp_path),
        entity_id="CAP-DF.3",
        attribute="goals",
        text="",
        author="t",
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "INVALID_ARGUMENT"
```

**Step 3: Run test to verify it fails**

```
python -m pytest ../opencode-arch/tests/mcp/test_promise_note_tool.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

**Step 4: Implement the MCP tool**

Create `../opencode-arch/src/opencode_arch/mcp/tools/promise_note.py`:

```python
"""``architect_promise_note`` MCP tool.

Wraps :func:`architecture_model.walks.meta.promise_note.note_promise`
with envelope-shaped error handling. Part of CAP-DF Part 10 ceremony.

Contract:
    Input:  repo_path, entity_id, attribute, text, author (all str).
    Output: {ok: True, comment_id: str} on success.
            {ok: False, error: {code, message, details?}} on failure.

Error codes:
    INVALID_ARGUMENT   — empty text or missing required field.
    NOT_FOUND          — repo_path or capabilities.v3.yaml missing.
    PRECONDITION_FAILED — unknown_entity / unknown_attribute.
    INTERNAL           — unexpected walk error.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from architecture_model.walks.meta.promise_note import (
    PromiseNoteError,
    UnknownAttributeError,
    UnknownEntityError,
    note_promise,
)


def _err(code: str, message: str, **details: Any) -> dict:
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return payload


def architect_promise_note(
    *,
    repo_path: str,
    entity_id: str,
    attribute: str,
    text: str,
    author: str,
) -> dict:
    if not isinstance(text, str) or not text.strip():
        return _err("INVALID_ARGUMENT", "text must be a non-empty string")
    if not isinstance(entity_id, str) or not entity_id:
        return _err("INVALID_ARGUMENT", "entity_id must be a non-empty string")
    if not isinstance(attribute, str) or not attribute:
        return _err("INVALID_ARGUMENT", "attribute must be a non-empty string")
    if not isinstance(author, str) or not author:
        return _err("INVALID_ARGUMENT", "author must be a non-empty string")

    repo = Path(repo_path)
    if not repo.exists():
        return _err("NOT_FOUND", f"repo_path does not exist: {repo_path}", reason="repo_missing")

    model_path = repo / ".architecture" / "model" / "capabilities.v3.yaml"
    if not model_path.exists():
        return _err(
            "NOT_FOUND",
            f"capabilities.v3.yaml missing under {repo_path}",
            reason="model_missing",
        )

    try:
        model = yaml.safe_load(model_path.read_text()) or {}
    except yaml.YAMLError as exc:
        return _err("INTERNAL", f"model YAML parse failed: {exc}")

    try:
        stub = note_promise(
            repo_path=repo,
            model=model,
            entity_id=entity_id,
            attribute=attribute,
            text=text,
            author=author,
        )
    except UnknownEntityError as exc:
        return _err(
            "PRECONDITION_FAILED",
            str(exc),
            reason="unknown_entity",
            entity_id=entity_id,
        )
    except UnknownAttributeError as exc:
        return _err(
            "PRECONDITION_FAILED",
            str(exc),
            reason="unknown_attribute",
            entity_id=entity_id,
            attribute=attribute,
        )
    except PromiseNoteError as exc:
        return _err("INVALID_ARGUMENT", str(exc))
    except Exception as exc:  # pragma: no cover
        return _err("INTERNAL", f"unexpected error: {exc}")

    return {"ok": True, "comment_id": stub.comment_id}


__all__ = ["architect_promise_note"]
```

**Step 5: Register in MCP server**

Read `../opencode-arch/src/opencode_arch/mcp/server.py`, find where existing tools like `architect_require` or `architect_note` (if any) are registered, and add a parallel registration for `architect_promise_note`. The exact registration pattern depends on the server framework (FastMCP). Sub-task: match the surrounding style — do NOT invent a new pattern.

Typical pattern (verify against actual file):

```python
from opencode_arch.mcp.tools.promise_note import architect_promise_note

# ... in tool registration section ...
mcp.tool()(architect_promise_note)
```

**Step 6: Run MCP test to verify it passes**

```
python -m pytest ../opencode-arch/tests/mcp/test_promise_note_tool.py -v
```

Expected: PASS (5 tests).

**Step 7: Run OCA full test suite (or at least mcp/ subtree)**

```
python -m pytest ../opencode-arch/tests/mcp/ -q -p no:cacheprovider
```

Expected: no regressions.

---

## Task 6 — Update CONTEXT.md

**Files:**
- Modify: `CONTEXT.md`

**Step 1: Add Part 10 section**

Find the "Part 9 additions (2026-09-18)" section in `CONTEXT.md` (the walk-substrate area). Immediately AFTER the "Coverage after Part 9" paragraph, add:

```markdown
**Part 10 additions** (2026-09-18):

- `src/architecture_model/comments/models.py`: added `PromiseTarget`
  pydantic model (frozen, ``extra="forbid"``, entity_id + attribute) and
  optional ``target: PromiseTarget | None`` field on ``CommentStub``.
  Additive — existing stubs without ``target`` continue to parse.
- `src/architecture_model/walks/meta/promise_note.py` (new Python
  meta-walk, ``Realizes ``CAP-WK.note```): ``note_promise(repo_path,
  model, entity_id, attribute, text, author, now=None) -> CommentStub``.
  Validates target against v3 model, derives deterministic
  ``comment_id`` (sha1 of entity|attr|body|author|iso-time), persists
  via ``comments.store.write_stub`` with sentinel view-scope fields
  (``artifact_id="promise-note:<entity>:<attr>"``, other view fields
  fixed sentinel). Tier T1 (no LLM).
- `.architecture/model/capabilities.v3.yaml`: ``PR-CAP-WK-note-intent``
  flipped ``proposed`` → ``verified`` with verified_by wires.
- `../opencode-arch/src/opencode_arch/mcp/tools/promise_note.py` (new
  MCP tool): ``architect_promise_note`` envelope wrapper. Error codes:
  INVALID_ARGUMENT | NOT_FOUND (repo_missing | model_missing) |
  PRECONDITION_FAILED (unknown_entity | unknown_attribute) | INTERNAL.

Coverage after Part 10 (2026-09-18): **10 covered**, 2 duplicate-walk,
**2 uncovered** (``save``, ``author`` — Parts 11–12).
```

---

## Task 7 — Verification before commit

**Step 1: Run walks tests**

```
python -m pytest tests/walks/ tests/comments/ -q -p no:cacheprovider
```

Expected: PASS.

**Step 2: Run full AMS suite**

```
python -m pytest tests/ -q --ignore=tests/test_config_loader.py -p no:cacheprovider
```

Expected: 4270 + 17 (comments) + 8 (walks/meta) ≈ 4295 passed, 105 skipped.

**Step 3: Run OCA mcp tests**

```
python -m pytest ../opencode-arch/tests/mcp/ -q -p no:cacheprovider
```

Expected: no regressions, 5 new tests pass.

**Step 4: Verify coverage bump**

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

Expected: `Counter({'covered': 10, 'uncovered': 2, 'duplicate-walk': 2})`.

If any step fails, STOP. Do not commit until all four verifications green.

---

## Task 8 — Commit

**Step 1: Stage explicit paths (AMS)**

```
git add src/architecture_model/comments/models.py \
        src/architecture_model/walks/meta/promise_note.py \
        tests/comments/test_promise_target.py \
        tests/walks/meta/test_promise_note.py \
        tests/walks/meta/__init__.py \
        .architecture/model/capabilities.v3.yaml \
        CONTEXT.md
```

If `tests/walks/meta/__init__.py` was pre-existing, it will be no-op.

**Step 2: Verify staged tree**

```
git status --short | grep -E "^[MA]"
```

Expected: only the 6–7 files above; no unintended captures.

**Step 3: Commit AMS**

```
git commit -m "feat(model): Part 10 — CAP-WK.note (promise-scoped note walk + PromiseTarget)

- comments/models.py: new PromiseTarget (entity_id + attribute, frozen);
  optional target field on CommentStub. Additive; existing stubs parse unchanged.
- walks/meta/promise_note.py: Python meta-walk realizing CAP-WK.note.
  Validates (entity, attribute) against v3 model, derives deterministic
  comment_id, persists via comments.store.write_stub with sentinel view fields.
  Tier T1 (no LLM).
- capabilities.v3.yaml: PR-CAP-WK-note-intent → verified with wires.
- Tests: 8 walk tests + 9 pydantic tests, all pass.

Coverage: 9 → 10 covered on capabilities.v3.yaml. Parts 11 (save) and
12 (author) still open."
```

**Step 4: Commit OCA (separate repo)**

```
cd ../opencode-arch
git add src/opencode_arch/mcp/tools/promise_note.py \
        src/opencode_arch/mcp/server.py \
        tests/mcp/test_promise_note_tool.py
git status --short | grep -E "^[MA]"
git commit -m "feat(mcp): architect_promise_note tool (CAP-DF Part 10)

Envelope wrapper around architecture_model.walks.meta.promise_note.
Error codes: INVALID_ARGUMENT | NOT_FOUND (repo_missing/model_missing) |
PRECONDITION_FAILED (unknown_entity/unknown_attribute) | INTERNAL.

Realizes the OCA side of CAP-WK.note. 5 tests, all pass."
cd -
```

**Step 5: Confirm success**

```
git log -1 --oneline
```

Expected: shows the Part 10 AMS commit.

```
cd ../opencode-arch && git log -1 --oneline && cd -
```

Expected: shows the Part 10 OCA commit.

---

## Success criteria

- [x] `PromiseTarget` pydantic model exists with frozen `extra="forbid"`.
- [x] `CommentStub.target` optional field added, backward-compatible.
- [x] `promise_note.py` walk implements `note_promise(...)` + docstring `Realizes ``CAP-WK.note```.
- [x] Deterministic `_derive_comment_id` (sha1-based) for idempotency and testability.
- [x] `.architecture/model/capabilities.v3.yaml` — `PR-CAP-WK-note-intent` status = `verified`, `verified_by` wires include the 4 new files.
- [x] `architect_promise_note` MCP tool with envelope error handling.
- [x] Full AMS suite green: 4270+ passed, 105 skipped, 0 failures.
- [x] OCA MCP tests green: 5 new pass, no regressions.
- [x] Meta-coverage audit reports `10 covered / 2 uncovered / 2 duplicate-walk`.
- [x] Two atomic commits (one per repo) with explicit `git add` paths.

---

## Notes for future parts

- Part 11 (`save`) will build on `PromiseTarget` — reading a comment's target to construct a `WorkOrder.intent = {kind: "fill_promise", entity_id, attribute, source_comment_id}`.
- Part 12 (`author`) will read the WorkOrder's provenance, dispatch `PromisePatchLLM`, and emit a proposal patching `entities.<kind>[?id==entity_id].promises[?attribute==attribute].content`.
- The sentinel view-scope fields (`view_id="promise-note"` etc.) are intentional — a future Part could add "viewer-originated" promise notes that carry real artifact context. Additive path preserved.
