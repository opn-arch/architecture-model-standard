# Comment→View→Issue→MCP-Dev Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship an end-to-end ticket lifecycle where a comment on a lifecycle-rendered view becomes a logs-db Issue, gets picked up by MCP, and results in a validated model+code change committed with provenance trailers, then closes the Issue.

**Architecture:** Local comment stubs stored under `.architecture/comments/*.yaml` (authoritative for content + coordinate); logs-db owns Issue state via a REST API. A new `architect_work_issue` MCP tool orchestrates fetch → resolve → WorkOrder → Job → validate (two-stage) → apply → publish → rebuild → commit → close, reusing every existing Phase-1 API (`ai/`, `lifecycle/`). Commits carry standard git trailers linking commit → issue → comment → session → model diff.

**Tech Stack:** Python 3.11+, Pydantic v2, existing AMS package + opencode-arch package. Networking: `httpx` (already a project dep). Test HTTP: `respx`. E2E: `pytest` + `FakeLogsDB` in-process HTTP fixture.

**Design doc:** `docs/plans/2026-09-05-comment-view-loop-design.md`
**Shared interfaces:** `docs/plans/2026-09-05-comment-view-shared-interfaces-design.md`

---

## Preflight — Verify branch, dependencies, and baseline tests

**Files:** none (verification only)

**Step P.1: Confirm branch**

```bash
git rev-parse --abbrev-ref HEAD
```

Expected: `feat/comment-view-loop`

**Step P.2: Confirm the two design docs exist**

```bash
ls -la docs/plans/2026-09-05-comment-view-*-design.md
```

Expected: two files.

**Step P.3: Confirm Phase-1 API imports resolve**

```bash
python -c "from architecture_model.ai.work_order import WorkOrder; from architecture_model.lifecycle.publication import read_current_generation; from architecture_model.lifecycle.model_slice_materializer import materialize; print('ok')"
```

Expected: `ok`

**Step P.4: Baseline tests green**

Run: `pytest tests/ -x --ignore=tests/test_config_loader.py -q 2>&1 | tail -20`
Expected: all green (6 pre-existing failures allowed only if in the documented list from CONTEXT.md).

**Step P.5: If any dep missing, install**

```bash
pip install respx pytest-httpx 2>/dev/null || true
python -c "import respx" && echo "respx ok"
```

---

## Phase A1 — Comment stub + capture CLI (2 days)

Goal: writing a comment locally produces a well-formed YAML stub, appends a journal event, and the stub round-trips through the store.

### Task A1.1 — SI package skeleton (comments module)

**Files:**
- Create: `src/architecture_model/comments/__init__.py`
- Create: `src/architecture_model/comments/models.py`
- Test: `tests/comments/__init__.py`, `tests/comments/test_models.py`

**Step 1: Write the failing test for the stub model**

```python
# tests/comments/test_models.py
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from architecture_model.comments.models import CommentStub, IssueRef

def _base_kwargs():
    return dict(
        comment_id="c-0001",
        artifact_id="art-1",
        view_id="view-1",
        slice_id="slice-1",
        package_id="pkg-1",
        revision="0000042",
        body="something is off",
        author="user@example.com",
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

def test_stub_minimal_valid():
    stub = CommentStub(**_base_kwargs())
    assert stub.issue_ref is None
    assert stub.target_entity_id is None

def test_stub_revision_must_be_seven_digits():
    with pytest.raises(ValidationError):
        CommentStub(**{**_base_kwargs(), "revision": "42"})

def test_stub_body_size_cap():
    with pytest.raises(ValidationError):
        CommentStub(**{**_base_kwargs(), "body": "x" * 8193})

def test_issue_ref_backfill():
    ref = IssueRef(system="logs-db", issue_id=123, synced_at=datetime.now(timezone.utc))
    stub = CommentStub(**_base_kwargs(), issue_ref=ref)
    assert stub.issue_ref.issue_id == 123
```

**Step 2: Verify tests fail**

Run: `pytest tests/comments/test_models.py -v`
Expected: `ModuleNotFoundError: No module named 'architecture_model.comments'`

**Step 3: Implement**

```python
# src/architecture_model/comments/__init__.py
"""Comment stubs for lifecycle-rendered views (Plan A)."""

from architecture_model.comments.models import CommentStub, IssueRef

__all__ = ["CommentStub", "IssueRef"]
```

```python
# src/architecture_model/comments/models.py
"""Pydantic schemas for comment stubs. See
docs/plans/2026-09-05-comment-view-shared-interfaces-design.md §2."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

_REVISION_RE = r"^\d{7}$"
_MAX_BODY_BYTES = 8192


class IssueRef(BaseModel):
    system: Literal["logs-db"] = "logs-db"
    issue_id: Optional[int | str] = None
    synced_at: Optional[datetime] = None


class CommentStub(BaseModel):
    comment_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    view_id: str = Field(..., min_length=1)
    slice_id: str = Field(..., min_length=1)
    package_id: str = Field(..., min_length=1)
    revision: str = Field(..., pattern=_REVISION_RE)
    target_entity_id: Optional[str] = None
    body: str
    author: str
    created_at: datetime
    issue_ref: Optional[IssueRef] = None

    @field_validator("body")
    @classmethod
    def _body_size(cls, v: str) -> str:
        if len(v.encode("utf-8")) > _MAX_BODY_BYTES:
            raise ValueError(f"body exceeds {_MAX_BODY_BYTES} bytes")
        return v
```

**Step 4: Run tests, expect pass**

Run: `pytest tests/comments/test_models.py -v`
Expected: 4 passed.

**Step 5: Commit**

```bash
git add src/architecture_model/comments/ tests/comments/
git commit -m "feat(comments): add CommentStub + IssueRef pydantic models"
```

### Task A1.2 — Comment stub store (atomic write, load, list)

**Files:**
- Create: `src/architecture_model/comments/store.py`
- Test: `tests/comments/test_store.py`

**Step 1: Failing test**

```python
# tests/comments/test_store.py
from datetime import datetime, timezone
from pathlib import Path
import pytest
from architecture_model.comments.models import CommentStub, IssueRef
from architecture_model.comments.store import (
    write_stub, load_stub, list_stubs, StubExistsError,
)

def _stub(cid="c-0001", rev="0000042"):
    return CommentStub(
        comment_id=cid, artifact_id="art-1", view_id="v-1",
        slice_id="s-1", package_id="p-1", revision=rev,
        body="x", author="a", created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

def test_write_and_load(tmp_path):
    write_stub(tmp_path, _stub())
    loaded = load_stub(tmp_path, "c-0001")
    assert loaded.comment_id == "c-0001"

def test_duplicate_id_rejected(tmp_path):
    write_stub(tmp_path, _stub())
    with pytest.raises(StubExistsError):
        write_stub(tmp_path, _stub())

def test_list_stubs_all_and_by_revision(tmp_path):
    write_stub(tmp_path, _stub("c-1", "0000001"))
    write_stub(tmp_path, _stub("c-2", "0000002"))
    write_stub(tmp_path, _stub("c-3", "0000002"))
    assert {s.comment_id for s in list_stubs(tmp_path)} == {"c-1", "c-2", "c-3"}
    assert {s.comment_id for s in list_stubs(tmp_path, revision="0000002")} == {"c-2", "c-3"}

def test_backfill_issue_ref(tmp_path):
    write_stub(tmp_path, _stub())
    ref = IssueRef(issue_id=42, synced_at=datetime.now(timezone.utc))
    from architecture_model.comments.store import set_issue_ref
    set_issue_ref(tmp_path, "c-0001", ref)
    assert load_stub(tmp_path, "c-0001").issue_ref.issue_id == 42
```

**Step 2: Verify fail**

Run: `pytest tests/comments/test_store.py -v`
Expected: import error.

**Step 3: Implement**

```python
# src/architecture_model/comments/store.py
"""On-disk store for comment stubs (.architecture/comments/*.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional

import yaml

from architecture_model.comments.models import CommentStub, IssueRef
from architecture_model.lifecycle.atomic_store import write_atomic

_DIR = Path(".architecture") / "comments"


class StubExistsError(RuntimeError):
    pass


class StubMissingError(RuntimeError):
    pass


def _dir(repo_path: Path) -> Path:
    d = repo_path / _DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(repo_path: Path, comment_id: str) -> Path:
    return _dir(repo_path) / f"{comment_id}.yaml"


def write_stub(repo_path: Path, stub: CommentStub) -> Path:
    p = _path(repo_path, stub.comment_id)
    if p.exists():
        raise StubExistsError(str(p))
    payload = yaml.safe_dump(
        stub.model_dump(mode="json"), sort_keys=True, default_flow_style=False
    ).encode("utf-8")
    write_atomic(p, payload)
    return p


def load_stub(repo_path: Path, comment_id: str) -> CommentStub:
    p = _path(repo_path, comment_id)
    if not p.exists():
        raise StubMissingError(str(p))
    return CommentStub.model_validate(yaml.safe_load(p.read_text()))


def list_stubs(repo_path: Path, revision: Optional[str] = None) -> Iterator[CommentStub]:
    for p in sorted(_dir(repo_path).glob("*.yaml")):
        stub = CommentStub.model_validate(yaml.safe_load(p.read_text()))
        if revision is None or stub.revision == revision:
            yield stub


def set_issue_ref(repo_path: Path, comment_id: str, ref: IssueRef) -> None:
    stub = load_stub(repo_path, comment_id)
    updated = stub.model_copy(update={"issue_ref": ref})
    p = _path(repo_path, comment_id)
    payload = yaml.safe_dump(
        updated.model_dump(mode="json"), sort_keys=True, default_flow_style=False
    ).encode("utf-8")
    write_atomic(p, payload)
```

**Step 4: Verify pass**

Run: `pytest tests/comments/test_store.py -v`
Expected: 4 passed.

**Step 5: Commit**

```bash
git add src/architecture_model/comments/store.py tests/comments/test_store.py
git commit -m "feat(comments): add store with atomic write, load, list, issue_ref back-fill"
```

### Task A1.3 — Journal event kinds

**Files:**
- Modify: `src/architecture_model/lifecycle/journal.py` (extend the `kind` Literal)
- Test: `tests/lifecycle/test_journal.py` (add cases)

**Step 1: Read current journal kind literal**

```bash
grep -n "kind" src/architecture_model/lifecycle/journal.py | head -20
```

Identify the `Literal[...]` union declaring valid `kind` values.

**Step 2: Failing test**

Add to `tests/lifecycle/test_journal.py`:

```python
def test_comment_and_issue_event_kinds_are_valid(tmp_path):
    from architecture_model.lifecycle.journal import Journal
    j = Journal(tmp_path / "journal.jsonl")
    for kind in [
        "comment.capture", "comment.sync", "issue.pull",
        "workorder.from_issue", "issue.close",
    ]:
        j.append(kind=kind, payload={"note": kind}, actor="test")
    entries = list(j.read())
    assert [e["kind"] for e in entries[-5:]] == [
        "comment.capture", "comment.sync", "issue.pull",
        "workorder.from_issue", "issue.close",
    ]
```

**Step 3: Run — expect fail (invalid kind)**

Run: `pytest tests/lifecycle/test_journal.py::test_comment_and_issue_event_kinds_are_valid -v`
Expected: validation error on unknown kind.

**Step 4: Extend the Literal**

Edit `src/architecture_model/lifecycle/journal.py` and add the five new kinds to the `Literal[...]` union used by `JournalEntry.kind`. Preserve existing entries.

**Step 5: Verify pass + full journal suite green**

Run: `pytest tests/lifecycle/test_journal.py -v`
Expected: all green.

**Step 6: Commit**

```bash
git add src/architecture_model/lifecycle/journal.py tests/lifecycle/test_journal.py
git commit -m "feat(journal): add comment/issue/workorder event kinds"
```

### Task A1.4 — `architecture-model comment` CLI

**Files:**
- Create: `src/architecture_model/cli/comment.py`
- Modify: `src/architecture_model/cli/main.py` (register subcommand)
- Test: `tests/cli/test_comment.py`

**Step 1: Failing CLI test**

```python
# tests/cli/test_comment.py
import subprocess, sys, yaml, os
from pathlib import Path

def _init_fixture(tmp_path: Path) -> Path:
    """Set up a minimal .architecture/lifecycle with one published generation."""
    # Copy the sample_package_tree fixture and publish generation 0000001
    fixt_src = Path("tests/fixtures/lifecycle/sample_package_tree")
    import shutil
    shutil.copytree(fixt_src, tmp_path / "repo")
    # Create a minimal generation dir
    gen = tmp_path / "repo" / ".architecture" / "lifecycle" / "package" / "generations" / "0000001"
    gen.mkdir(parents=True)
    (gen / "digest.json").write_text('{"root_digest": "sha256:deadbeef"}')
    (tmp_path / "repo" / ".architecture" / "lifecycle" / "package" / "CURRENT").write_text("0000001")
    return tmp_path / "repo"

def test_comment_cli_writes_stub(tmp_path, monkeypatch):
    repo = _init_fixture(tmp_path)
    monkeypatch.chdir(repo)
    r = subprocess.run(
        [sys.executable, "-m", "architecture_model", "comment",
         "art-1", "--view-id", "v-1", "--slice-id", "s-1",
         "--package-id", "p-1", "--revision", "0000001",
         "--body", "hello", "--author", "tester"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    comment_id = r.stdout.strip()
    stub_file = repo / ".architecture" / "comments" / f"{comment_id}.yaml"
    assert stub_file.exists()
    data = yaml.safe_load(stub_file.read_text())
    assert data["body"] == "hello"
    assert data["author"] == "tester"
    assert data["revision"] == "0000001"
```

**Step 2: Run — expect fail**

Run: `pytest tests/cli/test_comment.py -v`
Expected: subcommand `comment` not registered.

**Step 3: Implement CLI**

```python
# src/architecture_model/cli/comment.py
"""architecture-model comment - capture a comment on a lifecycle artifact."""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import write_stub
from architecture_model.lifecycle.journal import Journal


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("comment", help="Capture a comment on a rendered artifact")
    p.add_argument("artifact_id")
    p.add_argument("--view-id", required=True)
    p.add_argument("--slice-id", required=True)
    p.add_argument("--package-id", required=True)
    p.add_argument("--revision", required=True)
    p.add_argument("--target-entity", default=None)
    p.add_argument("--body", required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--repo", default=".", help="Repo root (default: cwd)")
    p.set_defaults(func=_run)


def _run(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    stub = CommentStub(
        comment_id=str(uuid.uuid4()),
        artifact_id=args.artifact_id,
        view_id=args.view_id,
        slice_id=args.slice_id,
        package_id=args.package_id,
        revision=args.revision,
        target_entity_id=args.target_entity,
        body=args.body,
        author=args.author,
        created_at=datetime.now(timezone.utc),
    )
    write_stub(repo, stub)
    journal_path = repo / ".architecture" / "lifecycle" / "journal.jsonl"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    Journal(journal_path).append(
        kind="comment.capture",
        payload={
            "comment_id": stub.comment_id,
            "artifact_id": stub.artifact_id,
            "view_id": stub.view_id,
            "slice_id": stub.slice_id,
            "revision": stub.revision,
            "author": stub.author,
        },
        actor="cli:comment",
    )
    sys.stdout.write(stub.comment_id + "\n")
    return 0
```

**Step 4: Register in main CLI**

Edit `src/architecture_model/cli/main.py`: locate the `subparsers = parser.add_subparsers(...)` block, add:

```python
from architecture_model.cli import comment as _comment_cli
_comment_cli.add_subparser(subparsers)
```

**Step 5: Verify pass**

Run: `pytest tests/cli/test_comment.py -v`
Expected: passes.

Run: `python -m architecture_model comment --help` — expected: help text.

**Step 6: Commit**

```bash
git add src/architecture_model/cli/comment.py src/architecture_model/cli/main.py tests/cli/test_comment.py
git commit -m "feat(cli): add architecture-model comment subcommand"
```

---

## Phase A2 — logs-db client + sync push (2 days)

Goal: unsynced stubs are pushed as logs-db Issues; `issue_ref` is back-filled; `comment.sync` journaled.

### Task A2.1 — Extract `LogsDBClient` from existing sync

**Files:**
- Create: `src/opencode_arch/logs_db/__init__.py`
- Create: `src/opencode_arch/logs_db/client.py`
- Test: `tests/logs_db/test_client.py`

> This task lives in the opencode-arch sibling repo. Switch worktrees:
> `pushd ../opencode-arch && git checkout -b feat/comment-view-loop && popd`
> All A2 and A3+ tasks live there. Use `git worktree add` if you prefer.

**Step 1: Failing test (in opencode-arch)**

```python
# tests/logs_db/test_client.py
import respx, httpx, pytest
from opencode_arch.logs_db.client import LogsDBClient, LogsDBUnreachable

@respx.mock
def test_create_issue_ok():
    route = respx.post("http://logs.local/issues").mock(
        return_value=httpx.Response(200, json={"issue_id": 42, "url": "http://x/42", "created_at": "2026-09-05T00:00:00Z"})
    )
    c = LogsDBClient("http://logs.local")
    r = c.create_issue(external_key="c-1", title="t", body="b", tags=["x"], meta={"k": "v"})
    assert r["issue_id"] == 42
    assert route.called

@respx.mock
def test_create_issue_conflict_returns_existing():
    respx.post("http://logs.local/issues").mock(
        return_value=httpx.Response(409, json={"issue_id": 42, "reason": "duplicate_external_key"})
    )
    r = LogsDBClient("http://logs.local").create_issue(
        external_key="c-1", title="t", body="b", tags=[], meta={}
    )
    assert r["issue_id"] == 42

@respx.mock
def test_unreachable_raises():
    respx.post("http://logs.local/issues").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(LogsDBUnreachable):
        LogsDBClient("http://logs.local", retries=1).create_issue(
            external_key="c", title="t", body="b", tags=[], meta={}
        )
```

**Step 2: Verify fail**

Run: `pytest tests/logs_db/test_client.py -v` → import error.

**Step 3: Implement**

```python
# src/opencode_arch/logs_db/__init__.py
from opencode_arch.logs_db.client import (
    LogsDBClient, LogsDBUnreachable, LogsDBConflict, LogsDBForbidden,
)

__all__ = ["LogsDBClient", "LogsDBUnreachable", "LogsDBConflict", "LogsDBForbidden"]
```

```python
# src/opencode_arch/logs_db/client.py
"""HTTP client for logs-db (Plan A consumed surface)."""

from __future__ import annotations

import time
from typing import Any, Mapping, Sequence

import httpx


class LogsDBError(RuntimeError):
    pass


class LogsDBUnreachable(LogsDBError):
    pass


class LogsDBConflict(LogsDBError):
    pass


class LogsDBForbidden(LogsDBError):
    pass


class LogsDBClient:
    def __init__(
        self,
        base_url: str,
        *,
        auth_token: str | None = None,
        timeout: float = 10.0,
        retries: int = 3,
        backoff: Sequence[float] = (0.5, 2.0, 8.0),
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        self._client = httpx.Client(timeout=timeout, headers=self._headers)
        self._retries = retries
        self._backoff = backoff

    def _request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None) -> httpx.Response:
        url = f"{self._base}{path}"
        last_exc: Exception | None = None
        for attempt in range(self._retries):
            try:
                r = self._client.request(method, url, json=json)
            except httpx.ConnectError as e:
                last_exc = e
                if attempt < self._retries - 1:
                    time.sleep(self._backoff[min(attempt, len(self._backoff) - 1)])
                    continue
                raise LogsDBUnreachable(str(e)) from e
            if r.status_code < 500:
                return r
            last_exc = LogsDBError(f"{r.status_code}: {r.text[:200]}")
            if attempt < self._retries - 1:
                time.sleep(self._backoff[min(attempt, len(self._backoff) - 1)])
        assert last_exc is not None
        raise last_exc

    def create_issue(
        self, *, external_key: str, title: str, body: str,
        tags: Sequence[str], meta: Mapping[str, Any],
    ) -> dict:
        r = self._request("POST", "/issues", json={
            "external_key": external_key, "title": title,
            "body": body, "tags": list(tags), "meta": dict(meta),
        })
        if r.status_code == 409:
            data = r.json()
            if "issue_id" in data:
                return data
            raise LogsDBConflict(r.text)
        if r.status_code == 403:
            raise LogsDBForbidden(r.text)
        r.raise_for_status()
        return r.json()

    def get_issue(self, issue_id: int | str) -> dict:
        r = self._request("GET", f"/issues/{issue_id}")
        r.raise_for_status()
        return r.json()

    def post_comment(self, issue_id: int | str, *, author: str, body: str) -> dict:
        r = self._request("POST", f"/issues/{issue_id}/comments",
                          json={"author": author, "body": body})
        r.raise_for_status()
        return r.json()

    def close_issue(
        self, issue_id: int | str, *, commit_sha: str, model_diff_digest: str, note: str,
    ) -> dict:
        r = self._request("POST", f"/issues/{issue_id}/close", json={
            "commit_sha": commit_sha, "model_diff_digest": model_diff_digest, "note": note,
        })
        r.raise_for_status()
        return r.json()
```

**Step 4: Verify pass**

Run: `pytest tests/logs_db/test_client.py -v` → 3 passed.

**Step 5: Commit**

```bash
git add src/opencode_arch/logs_db/ tests/logs_db/
git commit -m "feat(logs_db): add LogsDBClient with retries and typed errors"
```

### Task A2.2 — `FakeLogsDB` fixture

**Files:**
- Create: `tests/fixtures/fake_logs_db.py`
- Test: `tests/logs_db/test_fake_logs_db.py`

**Step 1: Failing test**

```python
# tests/logs_db/test_fake_logs_db.py
from tests.fixtures.fake_logs_db import FakeLogsDB

def test_fake_create_get_close():
    with FakeLogsDB() as fake:
        c = fake.client
        r = c.create_issue(external_key="c-1", title="t", body="b", tags=[], meta={})
        iid = r["issue_id"]
        assert c.get_issue(iid)["state"] == "open"
        c.close_issue(iid, commit_sha="deadbeef", model_diff_digest="sha256:00", note="ok")
        assert c.get_issue(iid)["state"] == "closed"

def test_fake_duplicate_returns_existing():
    with FakeLogsDB() as fake:
        c = fake.client
        r1 = c.create_issue(external_key="c-x", title="a", body="b", tags=[], meta={})
        r2 = c.create_issue(external_key="c-x", title="a", body="b", tags=[], meta={})
        assert r1["issue_id"] == r2["issue_id"]
```

**Step 2: Verify fail**

Run: `pytest tests/logs_db/test_fake_logs_db.py -v`
Expected: import error.

**Step 3: Implement**

```python
# tests/fixtures/fake_logs_db.py
"""In-process FakeLogsDB served over Werkzeug for contract tests."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from wsgiref.simple_server import make_server, WSGIRequestHandler

from flask import Flask, jsonify, request

from opencode_arch.logs_db.client import LogsDBClient


class _SilentHandler(WSGIRequestHandler):
    def log_message(self, format, *args):  # noqa: D401
        return


class FakeLogsDB:
    def __init__(self, port: int = 0):
        self._port = port
        self._app = Flask(__name__)
        self._issues: dict[int, dict] = {}
        self._by_key: dict[str, int] = {}
        self._next_id = 1
        self._register_routes()

    def _register_routes(self):
        app = self._app

        @app.post("/issues")
        def create():
            data = request.get_json(force=True)
            key = data["external_key"]
            if key in self._by_key:
                iid = self._by_key[key]
                return jsonify(self._issues[iid]), 409
            iid = self._next_id
            self._next_id += 1
            issue = {
                "issue_id": iid,
                "external_key": key,
                "title": data["title"],
                "body": data["body"],
                "tags": data.get("tags", []),
                "meta": data.get("meta", {}),
                "state": "open",
                "comments": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "url": f"http://fake/issues/{iid}",
            }
            self._issues[iid] = issue
            self._by_key[key] = iid
            return jsonify(issue), 200

        @app.get("/issues/<int:iid>")
        def get(iid):
            return jsonify(self._issues[iid])

        @app.post("/issues/<int:iid>/comments")
        def comment(iid):
            data = request.get_json(force=True)
            entry = {
                "comment_id": len(self._issues[iid]["comments"]) + 1,
                "author": data["author"], "body": data["body"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._issues[iid]["comments"].append(entry)
            return jsonify(entry)

        @app.post("/issues/<int:iid>/close")
        def close(iid):
            data = request.get_json(force=True)
            self._issues[iid]["state"] = "closed"
            self._issues[iid]["close_meta"] = data
            return jsonify({"issue_id": iid, "state": "closed"})

    def __enter__(self):
        self._server = make_server("127.0.0.1", self._port, self._app, handler_class=_SilentHandler)
        self._port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.client = LogsDBClient(f"http://127.0.0.1:{self._port}", retries=1)
        return self

    def __exit__(self, *a):
        self._server.shutdown()
        self._server.server_close()

    @property
    def issues(self) -> dict[int, dict]:
        return self._issues
```

**Step 4: Verify pass**

Run: `pytest tests/logs_db/test_fake_logs_db.py -v`
Expected: 2 passed. (If `flask` not installed: `pip install flask`.)

**Step 5: Commit**

```bash
git add tests/fixtures/fake_logs_db.py tests/logs_db/test_fake_logs_db.py
git commit -m "test(logs_db): add in-process FakeLogsDB HTTP fixture"
```

### Task A2.3 — Extend `architect_sync` with issue-push branch

**Files:**
- Modify: `src/opencode_arch/mcp/tools/sync.py`
- Test: `tests/mcp/tools/test_sync_issues.py`

**Step 1: Failing test**

```python
# tests/mcp/tools/test_sync_issues.py
from pathlib import Path
from datetime import datetime, timezone
import yaml
from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import write_stub, load_stub
from opencode_arch.mcp.tools.sync import _push_comments  # extracted helper
from tests.fixtures.fake_logs_db import FakeLogsDB

def _stub(cid="c-1"):
    return CommentStub(
        comment_id=cid, artifact_id="a", view_id="v", slice_id="s",
        package_id="p", revision="0000001",
        body="hi", author="me",
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

def test_push_backfills_issue_ref(tmp_path):
    write_stub(tmp_path, _stub())
    with FakeLogsDB() as fake:
        results = _push_comments(tmp_path, fake.client)
    assert len(results) == 1
    assert results[0]["issue_id"] == 1
    reloaded = load_stub(tmp_path, "c-1")
    assert reloaded.issue_ref.issue_id == 1

def test_push_is_idempotent(tmp_path):
    write_stub(tmp_path, _stub())
    with FakeLogsDB() as fake:
        _push_comments(tmp_path, fake.client)
        results2 = _push_comments(tmp_path, fake.client)
    assert results2 == []  # nothing to push second time
```

**Step 2: Verify fail**

Run: `pytest tests/mcp/tools/test_sync_issues.py -v`
Expected: `ImportError: cannot import name '_push_comments'`.

**Step 3: Implement**

Add to `src/opencode_arch/mcp/tools/sync.py`:

```python
# Anchor at end of file, before the MCP tool wrapper.
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from architecture_model.comments.store import list_stubs, set_issue_ref
from architecture_model.comments.models import IssueRef
from architecture_model.lifecycle.journal import Journal
from opencode_arch.logs_db.client import LogsDBClient


def _push_comments(repo_path: Path, client: LogsDBClient) -> list[dict]:
    """Push unsynced comment stubs to logs-db, back-fill issue_ref, journal event."""
    journal = Journal(repo_path / ".architecture" / "lifecycle" / "journal.jsonl")
    results: list[dict] = []
    for stub in list_stubs(repo_path):
        if stub.issue_ref and stub.issue_ref.issue_id is not None:
            continue
        title = f"{stub.artifact_id}@{stub.revision}"
        meta = {
            "artifact_id": stub.artifact_id, "view_id": stub.view_id,
            "slice_id": stub.slice_id, "package_id": stub.package_id,
            "revision": stub.revision, "target_entity_id": stub.target_entity_id,
        }
        r = client.create_issue(
            external_key=stub.comment_id, title=title, body=stub.body,
            tags=["mcp-comment"], meta=meta,
        )
        ref = IssueRef(system="logs-db", issue_id=r["issue_id"], synced_at=datetime.now(timezone.utc))
        set_issue_ref(repo_path, stub.comment_id, ref)
        journal.append(kind="comment.sync", payload={
            "comment_id": stub.comment_id, "issue_ref": ref.model_dump(mode="json"),
            "direction": "push",
        }, actor="architect_sync")
        results.append({"comment_id": stub.comment_id, "issue_id": r["issue_id"]})
    return results
```

Then update the MCP tool entrypoint at the top of `sync.py` (existing `sync_tool`) to invoke `_push_comments(repo_path, client)` before its existing findings push. Preserve current behavior — appending the new branch.

**Step 4: Verify pass**

Run: `pytest tests/mcp/tools/test_sync_issues.py -v` → 2 passed.

Run the full `sync` suite: `pytest tests/mcp/tools/test_sync.py -v` — expected still green.

**Step 5: Commit**

```bash
git add src/opencode_arch/mcp/tools/sync.py tests/mcp/tools/test_sync_issues.py
git commit -m "feat(sync): push unsynced comment stubs to logs-db and back-fill issue_ref"
```

---

## Phase A3 — `architect_work_issue` (4 days)

Goal: given an `issue_id`, execute the full 13-step flow up through Apply (steps 1–9); steps 10–13 land in phase A4.

### Task A3.1 — Commit trailer serializer

**Files:**
- Create: `src/opencode_arch/lifecycle_exec/commit.py`
- Test: `tests/lifecycle_exec/test_commit.py`

**Step 1: Failing test**

```python
# tests/lifecycle_exec/test_commit.py
import subprocess
from opencode_arch.lifecycle_exec.commit import build_trailers

def test_trailers_parseable_by_git():
    block = build_trailers(
        issue_id=42, comment_id="c-1", session_id="s-1",
        revision_from="0000042", revision_to="0000043",
        model_diff_digest="sha256:abc", provider="frontier/claude-4.7",
    )
    r = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        input=f"subject\n\n{block}\n", capture_output=True, text=True,
    )
    assert r.returncode == 0
    lines = r.stdout.strip().splitlines()
    assert "Issue: logs-db#42" in lines
    assert "Comment: c-1" in lines
    assert "Session: s-1" in lines
    assert "Model-Revision-From: 0000042" in lines
    assert "Model-Revision-To: 0000043" in lines
    assert "Model-Diff-Digest: sha256:abc" in lines
    assert "Provider: frontier/claude-4.7" in lines

def test_optional_provider_absent():
    block = build_trailers(
        issue_id=1, comment_id="c", session_id="s",
        revision_from="0000001", revision_to="0000002",
        model_diff_digest="sha256:0",
    )
    assert "Provider:" not in block
```

**Step 2: Verify fail**

Run: `pytest tests/lifecycle_exec/test_commit.py -v` → import error.

**Step 3: Implement**

```python
# src/opencode_arch/lifecycle_exec/commit.py
"""Git commit-trailer serializer for MCP-produced commits.

See docs/plans/2026-09-05-comment-view-shared-interfaces-design.md §6."""

from __future__ import annotations

import subprocess
from pathlib import Path


def build_trailers(
    *,
    issue_id: int | str,
    comment_id: str,
    session_id: str,
    revision_from: str,
    revision_to: str,
    model_diff_digest: str,
    provider: str | None = None,
) -> str:
    lines = [
        f"Issue: logs-db#{issue_id}",
        f"Comment: {comment_id}",
        f"Session: {session_id}",
        f"Model-Revision-From: {revision_from}",
        f"Model-Revision-To: {revision_to}",
        f"Model-Diff-Digest: {model_diff_digest}",
    ]
    if provider is not None:
        lines.append(f"Provider: {provider}")
    return "\n".join(lines)


def commit_with_trailers(
    repo_path: Path, *, subject: str, body: str, trailers: str,
) -> str:
    """Runs git add -A + git commit -m; returns resulting SHA."""
    message = subject
    if body:
        message += "\n\n" + body
    message += "\n\n" + trailers + "\n"
    subprocess.run(["git", "-C", str(repo_path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", message],
        check=True,
    )
    sha = subprocess.check_output(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"], text=True,
    ).strip()
    return sha
```

**Step 4: Verify pass**

Run: `pytest tests/lifecycle_exec/test_commit.py -v` → 2 passed.

**Step 5: Commit**

```bash
git add src/opencode_arch/lifecycle_exec/commit.py tests/lifecycle_exec/test_commit.py
git commit -m "feat(lifecycle_exec): git commit trailer builder + committer"
```

### Task A3.2 — Session-id helper

**Files:**
- Create: `src/opencode_arch/session.py`
- Test: `tests/test_session.py`

**Step 1: Failing test**

```python
# tests/test_session.py
import os
from opencode_arch.session import resolve_session_id

def test_resolves_from_env(monkeypatch):
    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_abc")
    assert resolve_session_id() == "ses_abc"

def test_synthesises_when_absent(monkeypatch):
    monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
    v = resolve_session_id()
    assert v.startswith("session:") and v.endswith("-cli")
```

**Step 2: Fail → Implement → Pass**

```python
# src/opencode_arch/session.py
import os
import uuid


def resolve_session_id() -> str:
    v = os.environ.get("OPENCODE_SESSION_ID")
    if v:
        return v
    return f"session:{uuid.uuid4()}-cli"
```

Run: `pytest tests/test_session.py -v` → 2 passed.

**Step 3: Commit**

```bash
git add src/opencode_arch/session.py tests/test_session.py
git commit -m "feat: add resolve_session_id helper"
```

### Task A3.3 — `_load_and_resolve` (steps 1–3 of work_issue)

**Files:**
- Create: `src/opencode_arch/mcp/tools/work_issue.py` (scaffolding only in this task)
- Test: `tests/mcp/tools/test_work_issue.py`

**Step 1: Failing test — resolve coordinate from issue**

```python
# tests/mcp/tools/test_work_issue.py
from pathlib import Path
from datetime import datetime, timezone
from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import write_stub, set_issue_ref
from architecture_model.comments.models import IssueRef
from tests.fixtures.fake_logs_db import FakeLogsDB
from opencode_arch.mcp.tools.work_issue import _load_and_resolve, WorkIssueError


def _stub(cid="c-1"):
    return CommentStub(
        comment_id=cid, artifact_id="a", view_id="v", slice_id="s",
        package_id="p", revision="0000001",
        body="body", author="me",
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )


def test_load_and_resolve_happy(tmp_path, monkeypatch):
    write_stub(tmp_path, _stub())
    with FakeLogsDB() as fake:
        r = fake.client.create_issue(
            external_key="c-1", title="t", body="b", tags=[], meta={},
        )
        set_issue_ref(tmp_path, "c-1", IssueRef(issue_id=r["issue_id"]))
        ctx = _load_and_resolve(tmp_path, fake.client, r["issue_id"])
    assert ctx.stub.comment_id == "c-1"
    assert ctx.issue["state"] == "open"


def test_load_and_resolve_missing_stub_raises(tmp_path):
    with FakeLogsDB() as fake:
        r = fake.client.create_issue(
            external_key="unknown-id", title="t", body="b", tags=[], meta={},
        )
        try:
            _load_and_resolve(tmp_path, fake.client, r["issue_id"])
        except WorkIssueError as e:
            assert "stub" in str(e).lower()
        else:
            raise AssertionError("expected WorkIssueError")
```

**Step 2: Verify fail**

Run: `pytest tests/mcp/tools/test_work_issue.py -v` → import error.

**Step 3: Implement scaffolding**

```python
# src/opencode_arch/mcp/tools/work_issue.py
"""architect_work_issue MCP tool — comment→issue→dev loop entrypoint."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import load_stub, StubMissingError
from architecture_model.lifecycle.journal import Journal
from opencode_arch.logs_db.client import LogsDBClient


class WorkIssueError(RuntimeError):
    pass


@dataclass
class _WorkContext:
    repo_path: Path
    issue: dict
    stub: CommentStub


def _load_and_resolve(repo_path: Path, client: LogsDBClient, issue_id: int | str) -> _WorkContext:
    issue = client.get_issue(issue_id)
    comment_id = issue.get("external_key")
    if not comment_id:
        raise WorkIssueError(f"issue {issue_id} has no external_key")
    try:
        stub = load_stub(repo_path, comment_id)
    except StubMissingError as e:
        raise WorkIssueError(f"stub missing for comment_id={comment_id}: {e}") from e
    journal = Journal(repo_path / ".architecture" / "lifecycle" / "journal.jsonl")
    journal.append(kind="issue.pull", payload={
        "issue_id": issue_id, "comment_id": comment_id,
        "package_revision": stub.revision,
    }, actor="architect_work_issue")
    return _WorkContext(repo_path=repo_path, issue=issue, stub=stub)
```

**Step 4: Verify pass**

Run: `pytest tests/mcp/tools/test_work_issue.py::test_load_and_resolve_happy tests/mcp/tools/test_work_issue.py::test_load_and_resolve_missing_stub_raises -v` → 2 passed.

**Step 5: Commit**

```bash
git add src/opencode_arch/mcp/tools/work_issue.py tests/mcp/tools/test_work_issue.py
git commit -m "feat(work_issue): steps 1-3 - load stub, resolve coordinate, journal issue.pull"
```

### Task A3.4 — WorkOrder factory (step 5)

**Files:**
- Modify: `src/opencode_arch/mcp/tools/work_issue.py`
- Test: `tests/mcp/tools/test_work_issue.py` (extend)

**Step 1: Failing test**

Append:

```python
def test_workorder_from_stub_populates_provenance(tmp_path, monkeypatch):
    from opencode_arch.mcp.tools.work_issue import _workorder_from_stub
    monkeypatch.setenv("OPENCODE_SESSION_ID", "ses_xyz")
    stub = _stub()
    wo = _workorder_from_stub(stub=stub, issue_id=42, issue_url="http://x/42")
    assert wo.requested_by == "logs-db#42"
    assert wo.provenance["issue_id"] == 42
    assert wo.provenance["comment_id"] == "c-1"
    assert wo.provenance["session_id"] == "ses_xyz"
    assert wo.input_slice_refs and wo.input_slice_refs[0].slice_id == "s"
```

**Step 2: Verify fail**

Run: `pytest tests/mcp/tools/test_work_issue.py::test_workorder_from_stub_populates_provenance -v`.

**Step 3: Implement**

Add to `work_issue.py`:

```python
from architecture_model.ai.work_order import WorkOrder, SliceRef, Budget
from opencode_arch.session import resolve_session_id


def _workorder_from_stub(*, stub: CommentStub, issue_id: int | str, issue_url: str) -> WorkOrder:
    intent = (stub.body[:200] + ("..." if len(stub.body) > 200 else "")) \
        + f"\n\nSource: {issue_url}"
    return WorkOrder.build(
        intent=intent,
        input_slice_refs=[SliceRef(slice_id=stub.slice_id, model_revision=stub.revision)],
        expected_proposal_kinds=["model_patch", "file_spec"],
        budget=Budget(max_tokens=200_000, max_usd=5.0),
        requested_by=f"logs-db#{issue_id}",
        provenance={
            "issue_id": issue_id, "comment_id": stub.comment_id,
            "session_id": resolve_session_id(),
            "artifact_id": stub.artifact_id, "view_id": stub.view_id,
            "package_id": stub.package_id, "revision": stub.revision,
        },
    )
```

**Step 4: Verify pass**

Run: `pytest tests/mcp/tools/test_work_issue.py -v` → all green.

**Step 5: Commit**

```bash
git add src/opencode_arch/mcp/tools/work_issue.py tests/mcp/tools/test_work_issue.py
git commit -m "feat(work_issue): step 5 - WorkOrder factory from stub"
```

### Task A3.5 — Idempotency check (step 4)

**Files:**
- Modify: `src/opencode_arch/mcp/tools/work_issue.py`
- Test: extend `tests/mcp/tools/test_work_issue.py`

**Step 1: Failing test**

```python
def test_existing_completed_job_short_circuits(tmp_path):
    from architecture_model.ai.jobs import Job, JobStore, JobState, JobEvent
    from datetime import datetime, timezone
    from opencode_arch.mcp.tools.work_issue import _existing_completed_job
    js = JobStore(tmp_path)
    j = Job(id="j-1", work_order_id="wo-1", state=JobState.completed,
            provenance={"comment_id": "c-1"}, result_ref="prop-1", events=[])
    js.save(j)
    found = _existing_completed_job(tmp_path, comment_id="c-1")
    assert found is not None
    assert found.id == "j-1"
```

**Step 2: Fail → Implement → Pass**

Add:

```python
def _existing_completed_job(repo_path: Path, *, comment_id: str):
    from architecture_model.ai.jobs import JobStore, JobState
    js = JobStore(repo_path)
    for j in js.iter_jobs():
        if j.state == JobState.completed and \
           j.provenance.get("comment_id") == comment_id:
            return j
    return None
```

If `JobStore.iter_jobs` does not exist yet, add it as a small helper in the AMS `ai/jobs.py` (walk the `job_dir()`, deserialize each YAML). This is a one-line change adjacent to the existing `save` / `load`; write a test in `tests/ai/test_jobs.py::test_iter_jobs` first.

Run: `pytest tests/mcp/tools/test_work_issue.py::test_existing_completed_job_short_circuits -v`

**Step 3: Commit**

```bash
git add src/opencode_arch/mcp/tools/work_issue.py tests/mcp/tools/test_work_issue.py src/architecture_model/ai/jobs.py tests/ai/test_jobs.py
git commit -m "feat(work_issue): step 4 idempotency - short-circuit on completed Job for same comment"
```

### Task A3.6 — Hard-gate validate + apply (steps 6-9)

**Files:**
- Modify: `src/opencode_arch/mcp/tools/work_issue.py`
- Test: extend `tests/mcp/tools/test_work_issue.py`

Follow the same red→green→commit rhythm.

**Steps to write, in order:**

1. Test: given a resolved context + a fake proposer that returns an invalid proposal, the tool returns `ok=False, error="proposal_invalid"`, posts a progress comment to the FakeLogsDB issue, does not publish a new generation.
2. Test: given a valid proposal, tool publishes a new generation, records `ai.proposal.apply` journal event, returns `commit_sha=None` (commit lands in A4), `package_revision_to` is set.
3. Implement `_submit_run_validate_apply(ctx, work_order, dry_run)` calling in order:
   - `architect_workorder_submit` (via existing OCA MCP tool internal function, not the MCP wrapper — import from `opencode_arch.mcp.tools.ai.workorder_submit`)
   - `architect_job_run`
   - `architect_proposal_validate` — if `passed=False`, POST progress comment, return failure.
   - `architect_proposal_apply(dry_run=dry_run)` — capture new revision + digest from returned `ApplyReport`.
4. Every step emits `workorder.from_issue` after submit; other events are auto-written by the underlying tools.

**Commit rhythm:** one commit per test/impl slice: `feat(work_issue): step 8 hard-gate validate rejects invalid proposal`, `feat(work_issue): steps 6-7 submit and run job`, `feat(work_issue): step 9 apply proposal and capture new revision`.

### Task A3.7 — MCP tool registration + envelope

**Files:**
- Modify: `src/opencode_arch/mcp/server.py`
- Add: MCP tool wrapper at the bottom of `work_issue.py` returning the envelope
- Test: extend `tests/mcp/tools/test_work_issue.py`

**Step 1: Test envelope shape**

```python
def test_work_issue_dry_run_envelope(tmp_path, monkeypatch):
    from opencode_arch.mcp.tools.work_issue import architect_work_issue
    # ... build fixture repo + stub + FakeLogsDB issue ...
    env = architect_work_issue(str(repo), issue_id=iid, dry_run=True)
    assert env["ok"] is True
    assert "work_order_id" in env
    assert "package_revision_to" in env  # dry-run reports would-be revision
    assert env.get("commit_sha") is None  # dry-run does not commit
```

**Step 2: Implement wrapper**

```python
def architect_work_issue(
    repo_path: str, *, issue_id: int | str, dry_run: bool = False, force: bool = False,
) -> dict:
    from opencode_arch.logs_db.client import LogsDBClient
    from opencode_arch.mcp.tools.sync import _default_logs_db_url  # existing helper
    repo = Path(repo_path).resolve()
    client = LogsDBClient(_default_logs_db_url(repo))
    ctx = _load_and_resolve(repo, client, issue_id)
    # idempotency
    if not force:
        prior = _existing_completed_job(repo, comment_id=ctx.stub.comment_id)
        if prior is not None:
            return {"ok": True, "work_order_id": prior.work_order_id,
                    "commit_sha": prior.provenance.get("commit_sha"),
                    "reused": True}
    wo = _workorder_from_stub(stub=ctx.stub, issue_id=issue_id,
                              issue_url=ctx.issue.get("url", ""))
    return _submit_run_validate_apply(ctx, wo, client=client, dry_run=dry_run)
```

**Step 3: Register in `mcp/server.py`**

Follow the pattern of existing tools: add a `@app.tool()` (or the registration idiom used in this repo) wrapping `architect_work_issue`.

**Step 4: Commit**

```bash
git add src/opencode_arch/mcp/tools/work_issue.py src/opencode_arch/mcp/server.py tests/mcp/tools/test_work_issue.py
git commit -m "feat(mcp): register architect_work_issue tool"
```

---

## Phase A4 — Soft-gate, rebuild, commit, close, E2E (2 days)

Goal: complete steps 10–13, then verify the entire pipeline in one integration test.

### Task A4.1 — Soft-gate progress comment (step 11)

**Step 1: Test** — after a successful `apply`, `_soft_gate(...)` calls
`architect_check` + `architect_gate` on the new revision; posts a
`/issues/{id}/comments` with author `"mcp"` whose body contains both scores
(or the `passed=True` line if both pass); leaves issue open, returns
non-blocking.

**Step 2: Implement `_soft_gate(ctx, client, new_revision)` in `work_issue.py`.**

**Step 3: Verify + commit.**

### Task A4.2 — Artifact rebuild (step 10)

**Step 1: Test** — after `apply`, call `architect_package_stale(...)` with
the model diff's changed paths, then `architect_artifact_rebuild(...)` for
each stale artifact; skip in `dry_run`.

**Step 2: Implement `_rebuild_affected(ctx, apply_report)`**, then
`_run_full(...)` wires steps 10 → 11 → 12 → 13 together.

**Step 3: Commit.**

### Task A4.3 — Commit with trailers (step 12)

**Step 1: Test** — after `apply` + `rebuild`, `commit_with_trailers` is
invoked; the returned SHA appears in the envelope; a `git log -1 --format=%B`
on the working tree contains every required trailer per the shared-interfaces
spec §6.

**Step 2: Implement `_commit_step(ctx, apply_report)`.**

Compute `model_diff_digest` from the `ApplyReport.digest`. `provider` trailer
included only if `apply_report.model.meta.provider` is set (defer this
integration to Plan B; for A4, emit `Provider` only when the field exists).

**Step 3: Commit.**

### Task A4.4 — Close issue (step 13)

**Step 1: Test** — after successful commit, `close_issue(...)` is called with
the SHA and digest; the FakeLogsDB records `state="closed"`; the journal has
`issue.close` with the correct payload.

**Step 2: Implement `_close_issue(ctx, client, commit_sha, model_diff_digest)`.**

**Step 3: Commit.**

### Task A4.5 — End-to-end integration test

**Files:**
- Create: `tests/e2e/test_comment_view_loop.py`

**Step 1: Write the test**

```python
# tests/e2e/test_comment_view_loop.py
"""E2E: capture -> sync -> work_issue -> commit -> close."""

import subprocess
from pathlib import Path
from tests.fixtures.fake_logs_db import FakeLogsDB
from tests.fixtures.repo_fixture import fresh_repo_with_published_generation


def test_full_loop(tmp_path):
    repo = fresh_repo_with_published_generation(tmp_path)

    # 1) Capture
    r = subprocess.run(
        ["architecture-model", "comment", "art-1",
         "--view-id", "v-1", "--slice-id", "s-1",
         "--package-id", "p-1", "--revision", "0000001",
         "--body", "COMP-2.5 missing constraint",
         "--author", "tester"],
        capture_output=True, text=True, cwd=repo,
    )
    assert r.returncode == 0, r.stderr
    comment_id = r.stdout.strip()

    # 2) Sync (push to fake logs-db)
    with FakeLogsDB() as fake:
        # Point sync at the fake by env or config override
        subprocess.run(
            ["python", "-c",
             f"from opencode_arch.mcp.tools.sync import _push_comments;"
             f"from opencode_arch.logs_db.client import LogsDBClient;"
             f"import pathlib; _push_comments(pathlib.Path(r'{repo}'), "
             f"LogsDBClient('http://127.0.0.1:{fake._port}'))"],
            check=True,
        )
        # Look up the issue
        issues = list(fake.issues.values())
        assert len(issues) == 1
        iid = issues[0]["issue_id"]

        # 3) Work issue
        from opencode_arch.mcp.tools.work_issue import architect_work_issue
        env = architect_work_issue(str(repo), issue_id=iid, dry_run=False)
        assert env["ok"] is True
        assert env["commit_sha"]

        # 4) Commit trailers present
        msg = subprocess.check_output(
            ["git", "-C", str(repo), "log", "-1", "--format=%B"], text=True,
        )
        for line in [
            f"Issue: logs-db#{iid}",
            f"Comment: {comment_id}",
            "Session:",
            "Model-Revision-From: 0000001",
            "Model-Revision-To: 0000002",
            "Model-Diff-Digest: sha256:",
        ]:
            assert line in msg, f"missing trailer line: {line}\n---\n{msg}"

        # 5) Issue closed
        assert fake.issues[iid]["state"] == "closed"
        assert fake.issues[iid]["close_meta"]["commit_sha"] == env["commit_sha"]

    # 6) Journal has all 6 event kinds in order
    import json
    journal = (repo / ".architecture" / "lifecycle" / "journal.jsonl").read_text().splitlines()
    kinds = [json.loads(l)["kind"] for l in journal]
    for k in ["comment.capture", "comment.sync", "issue.pull",
              "workorder.from_issue", "ai.proposal.apply", "issue.close"]:
        assert k in kinds, f"missing journal event {k}"
```

**Step 2: Create `tests/fixtures/repo_fixture.py`** with a small helper that
copies `tests/fixtures/lifecycle/sample_package_tree` into `tmp_path`, initializes
git, publishes generation `0000001`, and returns the repo path.

**Step 3: Wire the proposer for E2E**

For deterministic E2E, wire the proposer config to a **stub proposer** that
returns a hard-coded `ModelPatch` proposal that passes schema validation.
Add: `tests/fixtures/stub_proposer.py` and a
`.architecture/ai/proposer_config.yaml` in the fixture repo pointing at it.

**Step 4: Run**

Run: `pytest tests/e2e/test_comment_view_loop.py -v`
Expected: passes end-to-end (may need to tune fixture proposer to produce a
patch that passes the current AMS schema validator).

**Step 5: Commit**

```bash
git add tests/e2e/ tests/fixtures/repo_fixture.py tests/fixtures/stub_proposer.py
git commit -m "test(e2e): full comment->issue->commit->close loop"
```

### Task A4.6 — CONTEXT.md + docs

**Files:**
- Modify: `CONTEXT.md` (opencode-arch repo)

**Step 1: Add a short section**

Under a new heading `## Comment→Issue→Dev Loop (Plan A)`, describe the CLI
capture, `architect_sync` extension, and `architect_work_issue` tool with a
minimal usage snippet.

**Step 2: Commit**

```bash
git add CONTEXT.md
git commit -m "docs: describe comment->issue->dev loop"
```

### Task A4.7 — Full test-suite green

**Step 1: Run everything**

In `architecture-model-standard`:
Run: `pytest tests/ -x --ignore=tests/test_config_loader.py 2>&1 | tail`
Expected: no new failures.

In `opencode-arch`:
Run: `pytest tests/ -x 2>&1 | tail`
Expected: no new failures.

**Step 2: If any pre-existing green test regresses, fix or roll back and
re-open the offending task.**

### Task A4.8 — Definition-of-done checklist commit

Manually verify the checklist from the design doc §10, then:

```bash
git commit --allow-empty -m "chore: Plan A DoD verified

- E2E green
- All 6 new journal events emitted in order
- Commit has all required trailers
- CONTEXT.md updated"
```

---

## Handoff notes

- Every task is red → green → commit. Never batch multiple tasks in one commit.
- Verify with `git interpret-trailers --parse` after any trailer format change.
- If a Phase-1 API changes shape mid-plan, update the *shared-interfaces doc first*, then align this plan.
- Once A2 lands, Plan B.1 (LLMProvider) can start in the sibling worktree without any coordination.
- Plan B.3 (dashboard) reads `.architecture/comments/*.yaml`. Do not rename or reshape stub files without updating that dependency.
