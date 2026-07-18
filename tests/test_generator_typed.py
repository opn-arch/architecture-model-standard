"""Tests for typed Manifest return from generate_manifest."""

from pathlib import Path

from architecture_model.manifest.types import Manifest, ScanReport


def test_generate_manifest_returns_manifest(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""My package."""\n')
    (pkg / "core.py").write_text('"""Core module."""\ndef hello(): pass\n')

    from architecture_model.manifest.generator import generate_manifest

    result = generate_manifest(tmp_path)
    assert isinstance(result, Manifest)
    assert isinstance(result.scan_report, ScanReport)
    assert result.scan_report.files_attempted > 0


def test_generate_manifest_to_dict_backward_compat(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("x = 1\n")

    from architecture_model.manifest.generator import generate_manifest

    manifest = generate_manifest(tmp_path)
    d = manifest.to_dict()
    assert "generated_at" in d
    assert "metrics" in d
    assert isinstance(d["metrics"], dict)
    assert "modules" in d
    assert isinstance(d["modules"], list)


def test_scan_report_tracks_counts(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("def foo(): pass\nclass Bar: pass\n")
    (pkg / "b.py").write_text("X = 42\n")

    from architecture_model.manifest.generator import generate_manifest

    manifest = generate_manifest(tmp_path)
    report = manifest.scan_report
    assert report.files_succeeded == report.files_attempted
    assert report.files_failed == 0
    assert report.functions_extracted >= 1
    assert report.classes_extracted >= 1


def test_load_or_generate_returns_dict(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")

    from architecture_model.manifest.generator import load_or_generate_manifest

    result = load_or_generate_manifest(tmp_path, output_dir=tmp_path)
    assert isinstance(result, dict)
    assert "modules" in result
