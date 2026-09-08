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
