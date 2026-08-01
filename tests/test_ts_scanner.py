"""Tests for TypeScript fallback scanner."""
from pathlib import Path
import pytest
from architecture_model.manifest.ts_scanner import scan_typescript_fallback


@pytest.fixture
def ts_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.ts").write_text(
        "import { helper } from './utils';\n"
        "export function main(): void { helper(); }\n"
    )
    (src / "utils.ts").write_text(
        "export function helper(): string { return 'hi'; }\n"
        "export class Config { value: number = 0; }\n"
    )
    (tmp_path / "tsconfig.json").write_text("{}")
    return tmp_path


def test_fallback_produces_source_graph(ts_project):
    result = scan_typescript_fallback(ts_project)
    assert "units" in result
    assert "edges" in result
    assert len(result["units"]) >= 2


def test_fallback_extracts_exports(ts_project):
    result = scan_typescript_fallback(ts_project)
    utils = next(u for u in result["units"] if "utils" in u["file"])
    export_names = [e["name"] for e in utils["exports"]]
    assert "helper" in export_names
    assert "Config" in export_names


def test_fallback_extracts_imports_as_edges(ts_project):
    result = scan_typescript_fallback(ts_project)
    assert len(result["edges"]) >= 1
    edge = result["edges"][0]
    assert "main" in edge["source"]
    assert "utils" in edge["target"]
