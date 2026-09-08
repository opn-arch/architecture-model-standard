"""Task 6 (Phase 2 schema-and-semantic-content): ``architecture-model migrate`` CLI.

Adapted from plan spec: plan uses Click's ``CliRunner``; the actual CLI is
argparse-based (``main(argv)``), so we invoke ``main`` directly and
capture stdout via pytest ``capsys``. Behaviour and exit codes match the
plan.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.cli.main import main


TWO_ZERO = "meta:\n  schema_version: '2.0'\n  project: demo\nentities: {}\n"


def _write(tmp_path: Path, contents: str) -> Path:
    src = tmp_path / ".architecture-model.yaml"
    src.write_text(contents, encoding="utf-8")
    return src


def test_dry_run_reports_planned_changes_and_does_not_write(tmp_path, capsys) -> None:
    src = _write(tmp_path, TWO_ZERO)
    exit_code = main(["migrate", str(src), "--to", "2.1", "--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "would set schema_version to 2.1" in captured.out
    # File unchanged, byte-for-byte
    assert src.read_text(encoding="utf-8") == TWO_ZERO


def test_apply_writes_2_1_version(tmp_path, capsys) -> None:
    src = _write(tmp_path, TWO_ZERO)
    exit_code = main(["migrate", str(src), "--to", "2.1"])
    captured = capsys.readouterr()
    assert exit_code == 0
    result = src.read_text(encoding="utf-8")
    assert "schema_version: '2.1'" in result
    assert "schema_version: '2.0'" not in result
    # Non-meta content preserved byte-for-byte
    assert "project: demo\nentities: {}\n" in result
    assert "migrated" in captured.out


def test_refuses_when_already_at_target(tmp_path, capsys) -> None:
    src = _write(tmp_path, TWO_ZERO.replace("'2.0'", "'2.1'"))
    exit_code = main(["migrate", str(src), "--to", "2.1"])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "already at 2.1" in captured.err


def test_errors_when_no_schema_version_line(tmp_path, capsys) -> None:
    src = _write(tmp_path, "meta:\n  project: demo\nentities: {}\n")
    exit_code = main(["migrate", str(src), "--to", "2.1"])
    captured = capsys.readouterr()
    assert exit_code == 3
    assert "no meta.schema_version line found" in captured.err


def test_errors_when_model_missing(tmp_path, capsys) -> None:
    src = tmp_path / "nonexistent.yaml"
    exit_code = main(["migrate", str(src), "--to", "2.1"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "not found" in captured.err


def test_unquoted_schema_version_is_still_matched(tmp_path, capsys) -> None:
    """Some hand-authored models have unquoted versions; regex must match."""
    src = _write(tmp_path, "meta:\n  schema_version: 2.0\n  project: demo\nentities: {}\n")
    exit_code = main(["migrate", str(src), "--to", "2.1"])
    assert exit_code == 0
    assert "schema_version: '2.1'" in src.read_text(encoding="utf-8")


def test_only_first_schema_version_line_is_replaced(tmp_path) -> None:
    """Guard against runaway substitution — regex uses ``count=1``."""
    src = _write(
        tmp_path,
        (
            "meta:\n"
            "  schema_version: '2.0'\n"
            "  project: demo\n"
            "entities: {}\n"
            "# a stray reference: schema_version: '2.0' in a comment\n"
        ),
    )
    main(["migrate", str(src), "--to", "2.1"])
    contents = src.read_text(encoding="utf-8")
    # First (real) occurrence bumped
    assert "  schema_version: '2.1'\n" in contents
    # Comment line untouched (starts with '#', not matched by the regex)
    assert "schema_version: '2.0' in a comment" in contents
