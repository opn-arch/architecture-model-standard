"""Tests for lifecycle.publication (transactional package publication)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from pathlib import Path, PurePosixPath

import pytest

from architecture_model.lifecycle import publication as pub
from architecture_model.lifecycle.journal import (
    PACKAGE_PUBLISH_ABORT,
    PACKAGE_PUBLISH_BEGIN,
    PACKAGE_PUBLISH_COMMIT,
    Journal,
)
from architecture_model.lifecycle.locks import FileLock
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.publication import (
    GENERATION_ZERO_PAD,
    PackageBundle,
    PublicationLockTimeout,
    PublicationResult,
    list_generations,
    publish,
    read_current_generation,
    recover,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "lifecycle"
SAMPLE = FIXTURES / "sample_package_tree"


def _stage_pkg(tmp_path: Path):
    """Copy sample package into tmp and return a loaded ArchitecturePackage."""
    root = tmp_path / "pkg"
    shutil.copytree(SAMPLE, root)
    return load_package(root)


def _bundle(model_body: bytes = b"meta:\n  project: demo\n",
            manifest_body: bytes = b"{}",
            extras=None) -> PackageBundle:
    return PackageBundle(
        model_bytes=model_body,
        manifest_bytes=manifest_body,
        extra_files=extras or {},
    )


def _read_journal(journal_path: Path) -> list[dict]:
    entries = []
    with journal_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# 1
def test_first_publish_creates_generation_and_current(tmp_path):
    pkg = _stage_pkg(tmp_path)
    result = publish(pkg, _bundle())
    assert result.generation == 1
    gen1 = pkg.root / "generations" / "0000001"
    assert gen1.is_dir()
    assert (gen1 / "model" / ".architecture-model.yaml").is_file()
    assert (gen1 / "manifest" / "manifest.json").is_file()
    current = pkg.root / "CURRENT"
    assert current.is_symlink()
    assert current.resolve() == gen1.resolve()


# 2
def test_second_publish_advances_generation(tmp_path):
    pkg = _stage_pkg(tmp_path)
    publish(pkg, _bundle(model_body=b"v1\n"))
    r2 = publish(pkg, _bundle(model_body=b"v2\n"))
    assert r2.generation == 2
    assert (pkg.root / "generations" / "0000001").is_dir()
    assert (pkg.root / "generations" / "0000002").is_dir()
    assert (pkg.root / "CURRENT").resolve() == (
        pkg.root / "generations" / "0000002"
    ).resolve()


# 3
def test_publish_writes_digest_json(tmp_path):
    pkg = _stage_pkg(tmp_path)
    result = publish(pkg, _bundle())
    dj = result.generation_dir / "digest.json"
    assert dj.is_file()
    data = json.loads(dj.read_text(encoding="utf-8"))
    assert data["algo"] == "sha256-v1"
    assert data["root_digest"].startswith("sha256-v1:")
    assert data["root_digest"] == result.root_digest
    assert "model/.architecture-model.yaml" in data["files"]
    assert "manifest/manifest.json" in data["files"]
    # per-file digest matches sha256 of raw bytes
    body = (result.generation_dir / "model" / ".architecture-model.yaml").read_bytes()
    expect = f"sha256-v1:{hashlib.sha256(body).hexdigest()}"
    assert data["files"]["model/.architecture-model.yaml"] == expect


# 4
def test_publish_records_begin_and_commit_journal_events(tmp_path):
    pkg = _stage_pkg(tmp_path)
    result = publish(pkg, _bundle())
    entries = _read_journal(pkg.root / ".architecture" / "journal.jsonl")
    events = [e["event"] for e in entries]
    assert events == [PACKAGE_PUBLISH_BEGIN, PACKAGE_PUBLISH_COMMIT]
    for e in entries:
        assert e["payload"]["generation"] == 1
        assert e["payload"]["root_digest"] == result.root_digest
        assert e["payload"]["architecture_id"] == pkg.architecture_id


# 5
def test_publish_extra_files_placed_correctly(tmp_path):
    pkg = _stage_pkg(tmp_path)
    extras = {
        PurePosixPath("slices/foo.yaml"): b"slice: foo\n",
        PurePosixPath("artifacts/bar.svg"): b"<svg/>",
        PurePosixPath("views/v1.yaml"): b"view: v1\n",
    }
    result = publish(pkg, _bundle(extras=extras))
    for rel, data in extras.items():
        p = result.generation_dir / str(rel)
        assert p.is_file()
        assert p.read_bytes() == data
        assert str(rel) in result.files


# 6
def test_publish_lock_prevents_concurrent_write(tmp_path):
    pkg = _stage_pkg(tmp_path)
    lock_path = pkg.root / ".locks" / "publication.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    holder = FileLock(lock_path, timeout=5.0)
    holder.__enter__()
    try:
        with pytest.raises(PublicationLockTimeout):
            publish(pkg, _bundle(), lock_timeout=0.5)
    finally:
        holder.__exit__(None, None, None)


# 7
def test_publish_aborts_on_switch_current_failure(tmp_path, monkeypatch):
    pkg = _stage_pkg(tmp_path)
    # First succeed
    publish(pkg, _bundle(model_body=b"v1\n"))
    current_before = os.readlink(pkg.root / "CURRENT")

    def boom(pointer, target):
        raise RuntimeError("switch failed")

    monkeypatch.setattr(pub, "switch_current", boom)
    with pytest.raises(RuntimeError, match="switch failed"):
        publish(pkg, _bundle(model_body=b"v2\n"))

    entries = _read_journal(pkg.root / ".architecture" / "journal.jsonl")
    aborts = [e for e in entries if e["event"] == PACKAGE_PUBLISH_ABORT]
    assert aborts
    assert aborts[-1]["payload"]["generation"] == 2
    # CURRENT unchanged
    assert os.readlink(pkg.root / "CURRENT") == current_before


# 8
def test_publish_aborts_on_write_failure(tmp_path, monkeypatch):
    pkg = _stage_pkg(tmp_path)

    def boom(root, files):
        raise RuntimeError("write failed")

    monkeypatch.setattr(pub, "write_tree_atomic", boom)
    with pytest.raises(RuntimeError, match="write failed"):
        publish(pkg, _bundle())

    entries = _read_journal(pkg.root / ".architecture" / "journal.jsonl")
    events = [e["event"] for e in entries]
    assert PACKAGE_PUBLISH_ABORT in events
    # No generation dir was created
    assert not (pkg.root / "generations" / "0000001").exists()
    assert not (pkg.root / "CURRENT").exists()


# 9
def test_recover_detects_interrupted_publish(tmp_path):
    pkg = _stage_pkg(tmp_path)
    jpath = pkg.root / ".architecture" / "journal.jsonl"
    j = Journal(jpath)
    j.record(PACKAGE_PUBLISH_BEGIN, {
        "architecture_id": pkg.architecture_id,
        "generation": 1,
        "root_digest": "sha256-v1:deadbeef",
    })
    recover(pkg)
    entries = _read_journal(jpath)
    events = [e["event"] for e in entries]
    assert events[0] == PACKAGE_PUBLISH_BEGIN
    assert PACKAGE_PUBLISH_ABORT in events
    abort = [e for e in entries if e["event"] == PACKAGE_PUBLISH_ABORT][-1]
    assert "recovered from crash" in abort["payload"].get("error", "")
    assert abort["payload"]["generation"] == 1


# 10
def test_recover_leaves_current_alone(tmp_path):
    pkg = _stage_pkg(tmp_path)
    publish(pkg, _bundle(model_body=b"v1\n"))
    current_before = os.readlink(pkg.root / "CURRENT")
    # simulate crash after begin of gen 2
    j = Journal(pkg.root / ".architecture" / "journal.jsonl")
    j.record(PACKAGE_PUBLISH_BEGIN, {
        "architecture_id": pkg.architecture_id,
        "generation": 2,
        "root_digest": "sha256-v1:cafebabe",
    })
    recover(pkg)
    assert os.readlink(pkg.root / "CURRENT") == current_before


# 11
def test_recover_removes_orphan_staging_dirs(tmp_path):
    pkg = _stage_pkg(tmp_path)
    # Create an orphan generations/0000005 dir with no journal begin
    orphan = pkg.root / "generations" / "0000005"
    orphan.mkdir(parents=True)
    (orphan / "sentinel").write_text("orphan")
    # Recover with no matching begin should just be a no-op for it.
    recover(pkg)
    # No begin → nothing to abort; but function should not crash.
    # Now: create a begin for gen 5 and re-run; recover should remove the orphan dir.
    j = Journal(pkg.root / ".architecture" / "journal.jsonl")
    j.record(PACKAGE_PUBLISH_BEGIN, {
        "architecture_id": pkg.architecture_id,
        "generation": 5,
        "root_digest": "sha256-v1:aaa",
    })
    recover(pkg)
    assert not orphan.exists()


# 12
def test_list_generations_returns_sorted(tmp_path):
    pkg = _stage_pkg(tmp_path)
    gens = pkg.root / "generations"
    gens.mkdir()
    (gens / "0000003").mkdir()
    (gens / "0000001").mkdir()
    (gens / "0000002").mkdir()
    (gens / "not-a-gen").mkdir()
    assert list_generations(pkg) == [1, 2, 3]


# 13
def test_read_current_generation_none_when_no_symlink(tmp_path):
    pkg = _stage_pkg(tmp_path)
    assert read_current_generation(pkg) is None


# 14
def test_read_current_generation_returns_number_after_publish(tmp_path):
    pkg = _stage_pkg(tmp_path)
    publish(pkg, _bundle())
    publish(pkg, _bundle(model_body=b"v2\n"))
    assert read_current_generation(pkg) == 2


# 15
def test_root_digest_deterministic_across_two_publishes_of_same_bytes(tmp_path):
    pkg1 = _stage_pkg(tmp_path / "a")
    pkg2 = _stage_pkg(tmp_path / "b")
    r1 = publish(pkg1, _bundle(model_body=b"same\n", manifest_body=b"{}"))
    time.sleep(0.01)
    r2 = publish(pkg2, _bundle(model_body=b"same\n", manifest_body=b"{}"))
    assert r1.root_digest == r2.root_digest


# 16
def test_publication_result_reports_all_files(tmp_path):
    pkg = _stage_pkg(tmp_path)
    extras = {PurePosixPath("slices/s.yaml"): b"x: 1\n"}
    r = publish(pkg, _bundle(extras=extras))
    assert "model/.architecture-model.yaml" in r.files
    assert "manifest/manifest.json" in r.files
    assert "slices/s.yaml" in r.files
    assert "digest.json" in r.files
    for d in r.files.values():
        assert d.startswith("sha256-v1:")


def test_generation_zero_pad_constant():
    assert GENERATION_ZERO_PAD == 7
