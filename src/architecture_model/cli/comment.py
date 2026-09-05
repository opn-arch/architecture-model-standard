"""architecture-model comment — capture a comment on a lifecycle artifact."""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from architecture_model.comments.models import CommentStub
from architecture_model.comments.store import write_stub
from architecture_model.lifecycle.journal import COMMENT_CAPTURE, Journal


def add_subparser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
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
    return p


def run(args: argparse.Namespace) -> int:
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
    Journal(journal_path).record(
        COMMENT_CAPTURE,
        {
            "comment_id": stub.comment_id,
            "artifact_id": stub.artifact_id,
            "view_id": stub.view_id,
            "slice_id": stub.slice_id,
            "revision": stub.revision,
            "author": stub.author,
            "actor": "cli:comment",
        },
    )

    sys.stdout.write(stub.comment_id + "\n")
    return 0
