"""Tests for typed discover_config returning (ProjectConfig, DiscoveryReport)."""

from pathlib import Path


def test_discover_config_returns_report(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""My package."""\n')
    sub = pkg / "core"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "engine.py").write_text("x = 1\n")

    from architecture_model.config.loader import discover_config
    config, report = discover_config(tmp_path)
    assert config.name == tmp_path.name
    assert report.layout_detected in ("src-layout", "flat-layout", "lib-layout", "fallback")
    assert report.blocks_discovered >= 1
    assert len(report.candidates) > 0


def test_discover_config_includes_underscore_dirs(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    internal = pkg / "_internal"
    internal.mkdir()
    (internal / "__init__.py").write_text("")
    (internal / "helpers.py").write_text("x = 1\n")

    from architecture_model.config.loader import discover_config
    config, report = discover_config(tmp_path)
    block_dirs = [d for b in config.functional_blocks for d in b.dirs]
    assert any("_internal" in d for d in block_dirs)


def test_sub_blocks_have_files(tmp_path):
    pkg = tmp_path / "src" / "mypkg"
    sub = pkg / "feature"
    sub.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (sub / "__init__.py").write_text("")
    (sub / "handler.py").write_text("x = 1\n")

    from architecture_model.config.loader import discover_config
    config, report = discover_config(tmp_path)
    for block in config.functional_blocks:
        for sb in block.sub_blocks:
            if sb.dirs:
                assert len(sb.files) > 0, f"Sub-block {sb.id} has dirs but no files"
