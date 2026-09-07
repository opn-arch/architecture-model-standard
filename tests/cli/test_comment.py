"""CLI test for `architecture-model comment`."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def _init_fixture(tmp_path: Path) -> Path:
    """Copy sample_package_tree and stamp a minimal published generation."""
    fixt_src = Path("tests/fixtures/lifecycle/sample_package_tree").resolve()
    repo = tmp_path / "repo"
    shutil.copytree(fixt_src, repo)
    gen = repo / ".architecture" / "lifecycle" / "package" / "generations" / "0000001"
    gen.mkdir(parents=True)
    (gen / "digest.json").write_text(json.dumps({"root_digest": "sha256:deadbeef"}))
    (repo / ".architecture" / "lifecycle" / "package" / "CURRENT").write_text("0000001")
    return repo


def test_comment_cli_writes_stub_and_journals(tmp_path, monkeypatch):
    repo = _init_fixture(tmp_path)
    monkeypatch.chdir(repo)

    r = subprocess.run(
        [sys.executable, "-m", "architecture_model", "comment",
         "art-1",
         "--view-id", "v-1", "--slice-id", "s-1",
         "--package-id", "p-1", "--revision", "0000001",
         "--body", "hello", "--author", "tester"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr: {r.stderr!r}"

    comment_id = r.stdout.strip()
    assert comment_id, "CLI must print the new comment_id to stdout"

    stub_file = repo / ".architecture" / "comments" / f"{comment_id}.yaml"
    assert stub_file.exists()
    data = yaml.safe_load(stub_file.read_text())
    assert data["body"] == "hello"
    assert data["author"] == "tester"
    assert data["revision"] == "0000001"
    assert data["view_id"] == "v-1"
    assert data["slice_id"] == "s-1"
    assert data["package_id"] == "p-1"
    assert data["artifact_id"] == "art-1"

    # Journal event recorded with the COMMENT_CAPTURE kind.
    journal = repo / ".architecture" / "lifecycle" / "journal.jsonl"
    assert journal.exists()
    events = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
    capture_events = [e for e in events if e["event"] == "comment.capture"]
    assert len(capture_events) == 1
    payload = capture_events[0]["payload"]
    assert payload["comment_id"] == comment_id
    assert payload["artifact_id"] == "art-1"
    assert payload["actor"] == "cli:comment"
