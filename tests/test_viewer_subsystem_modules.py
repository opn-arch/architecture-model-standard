"""Acceptance tests for hierarchy-qualified subsystem module pages."""

from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import generate_html_viewer


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.current = {"attrs": dict(attrs), "text": ""}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.items.append(self.current)
            self.current = None


def _parts(html: str) -> tuple[dict, str, list[dict]]:
    parser = _Scripts()
    parser.feed(html)
    data = json.loads(next(item["text"] for item in parser.items if item["attrs"].get("type") == "application/json"))
    script = next(item["text"] for item in parser.items if item["attrs"].get("type") != "application/json")
    return data, script, parser.items


def _write_child(repo: Path, slug: str, *, manifest: bool = True, hostile: bool = False) -> None:
    child_dir = repo / ".architecture-models" / slug
    child_dir.mkdir(parents=True)
    file_name = "src/<hostile>&.py" if hostile else "src/shared.py"
    (child_dir / ".architecture-model.yaml").write_text(yaml.safe_dump({
        "meta": {"project": slug, "schema_version": "2.0", "source_artifacts": [file_name]},
        "entities": {"components": [{
            "id": "COMP-1", "name": f"{slug} component", "status": "ACTIVE", "files": [file_name],
        }]},
        "relationships": [],
    }))
    if manifest:
        (child_dir / "manifest.json").write_text(json.dumps({"modules": [{
            "file": file_name,
            "name": f"{slug}</script>",
            "docstring": f"{slug} docs </script><script>pwned=1</script>",
            "functions": [{"name": f"run_{slug}", "signature": "(value)", "docstring": "Run."}],
            "classes": [{"name": f"{slug.title()}Class", "methods": ["go"]}],
            "module_constants": {f"{slug.upper()}_VALUE": "1"},
            "routes": [{"path": f"/{slug}", "method": "GET"}],
        }]}))


def _root(*systems: tuple[str, str], inline_files: list[str] | None = None):
    entities = {
        "systems": [{
            "id": system_id,
            "name": slug.title(),
            "status": "ACTIVE",
            "sub_model_ref": f".architecture-models/{slug}/.architecture-model.yaml",
        } for system_id, slug in systems],
        "components": ([{
            "id": "COMP-ROOT", "name": "Root inline", "status": "ACTIVE", "files": inline_files,
        }] if inline_files else []),
    }
    return _parse_raw({
        "meta": {"project": "viewer-project", "schema_version": "2.0"},
        "entities": entities,
        "relationships": [],
    })


def test_adjacent_manifests_embed_distinct_qualified_modules_and_links(tmp_path):
    _write_child(tmp_path, "alpha")
    _write_child(tmp_path, "beta")
    history = tmp_path / ".architecture" / "pipeline-history.jsonl"
    history.parent.mkdir()
    history.write_text(json.dumps({
        "run_id": "run-1", "started_at": "2026-09-02", "completed_at": "2026-09-02",
        "duration_ms": 1, "source": "pipeline", "status": "completed",
        "modules": [{"path": "src/shared.py", "module": "shared", "scope": "alpha"}],
    }) + "\n")

    html = generate_html_viewer(
        _root(("SYS-A", "alpha"), ("SYS-B", "beta")), tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text()
    data, script, scripts = _parts(html)

    alpha_key = "alpha::module::src/shared.py"
    beta_key = "beta::module::src/shared.py"
    assert data["modules"][alpha_key]["funcs"][0]["name"] == "run_alpha"
    assert data["modules"][beta_key]["funcs"][0]["name"] == "run_beta"
    assert data["modules"][alpha_key]["routes"] == [{"path": "/alpha", "method": "GET"}]
    assert data["modules"][alpha_key]["system_scope"] == "alpha"
    assert data["modules"][beta_key]["system_scope"] == "beta"
    assert data["comp_modules"]["alpha::COMP-1"] == [{"path": "src/shared.py", "key": alpha_key}]
    assert data["comp_modules"]["beta::COMP-1"] == [{"path": "src/shared.py", "key": beta_key}]
    assert data["modules"][alpha_key]["canonical_path"] == "src/shared.py"
    assert "item.path === mod.canonical_path" in script
    assert "(!mod.system_scope || item.scope === mod.system_scope)" in script
    assert not any(item["attrs"].get("src") or item["attrs"].get("href") for item in scripts)


def test_nested_same_basename_submodels_have_distinct_stable_namespaces(tmp_path):
    for parent, system_name in (("one", "First"), ("two", "Second")):
        child_dir = tmp_path / ".architecture-models" / parent / "api"
        child_dir.mkdir(parents=True)
        (child_dir / ".architecture-model.yaml").write_text(yaml.safe_dump({
            "meta": {"project": system_name, "schema_version": "2.0"},
            "entities": {"components": [{
                "id": "COMP-1", "name": f"{system_name} API", "status": "ACTIVE", "files": ["src/shared.py"],
            }]},
            "relationships": [],
        }))
        (child_dir / "manifest.json").write_text(json.dumps({"modules": [{
            "file": "src/shared.py", "name": f"{parent}-shared", "functions": [], "classes": [],
        }]}))
    model = _parse_raw({
        "meta": {"project": "root", "schema_version": "2.0"},
        "entities": {"systems": [
            {"id": "SYS-ONE", "name": "One API", "status": "ACTIVE", "sub_model_ref": ".architecture-models/one/api/.architecture-model.yaml"},
            {"id": "SYS-TWO", "name": "Two API", "status": "ACTIVE", "sub_model_ref": ".architecture-models/two/api/.architecture-model.yaml"},
        ]},
        "relationships": [],
    })

    data, script, _ = _parts(generate_html_viewer(
        model, tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text())

    one_module = "one/api::module::src/shared.py"
    two_module = "two/api::module::src/shared.py"
    assert data["viewer_system_namespaces"] == {
        "SYS-ONE": "one/api",
        "SYS-TWO": "two/api",
    }
    assert data["properties"]["one/api::COMP-1"]["name"] == "First API"
    assert data["properties"]["two/api::COMP-1"]["name"] == "Second API"
    assert data["modules"][one_module]["name"] == "one-shared"
    assert data["modules"][two_module]["name"] == "two-shared"
    assert data["modules"][one_module]["system_scope"] == "one/api"
    assert data["modules"][two_module]["system_scope"] == "two/api"
    assert data["comp_modules"]["one/api::COMP-1"][0]["key"] == one_module
    assert data["comp_modules"]["two/api::COMP-1"][0]["key"] == two_module
    assert data["subsystem_entities"]["SYS-ONE"] == ["one/api::COMP-1"]
    assert data["subsystem_entities"]["SYS-TWO"] == ["two/api::COMP-1"]
    assert "commentHtml('module', filepath" in script
    assert "item.scope === mod.system_scope" in script


def test_missing_child_manifest_creates_owned_module_stub(tmp_path):
    _write_child(tmp_path, "alpha", manifest=False)

    data, _, _ = _parts(generate_html_viewer(
        _root(("SYS-A", "alpha")), tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text())

    key = "alpha::module::src/shared.py"
    assert data["modules"][key] == {
        "name": "shared.py", "doc": "", "funcs": [], "classes": [], "consts": [], "routes": [],
        "canonical_path": "src/shared.py",
        "system_scope": "alpha",
    }
    assert data["comp_modules"]["alpha::COMP-1"][0]["key"] == key


def test_child_ownership_is_canonical_and_explicit_root_inline_page_is_retained(tmp_path):
    _write_child(tmp_path, "alpha")
    root_manifest = tmp_path / ".architecture-models" / "manifest.json"
    root_manifest.write_text(json.dumps({"modules": [{
        "file": "src/shared.py", "name": "root-shared", "docstring": "root",
        "functions": [], "classes": [], "module_constants": {},
    }, {
        "file": "tests/unowned.py", "name": "unowned", "functions": [], "classes": [],
    }]}))

    without_inline, _, _ = _parts(generate_html_viewer(
        _root(("SYS-A", "alpha")), tmp_path / "without.html", repo_path=tmp_path,
    ).read_text())
    with_inline, _, _ = _parts(generate_html_viewer(
        _root(("SYS-A", "alpha"), inline_files=["src/shared.py"]),
        tmp_path / "with.html", repo_path=tmp_path,
    ).read_text())

    assert "src/shared.py" not in without_inline["modules"]
    assert "tests/unowned.py" not in without_inline["modules"]
    assert with_inline["modules"]["src/shared.py"]["name"] == "root-shared"
    assert with_inline["comp_modules"]["COMP-ROOT"][0]["key"] == "src/shared.py"


def test_traversing_submodel_and_symlinked_manifest_are_rejected(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / ".architecture-model.yaml").write_text(yaml.safe_dump({
        "meta": {"project": "outside", "schema_version": "2.0"},
        "entities": {"components": [{"id": "BAD", "name": "Bad", "status": "ACTIVE", "files": ["bad.py"]}]},
        "relationships": [],
    }))
    child_dir = tmp_path / ".architecture-models" / "alpha"
    child_dir.mkdir(parents=True)
    (child_dir / ".architecture-model.yaml").write_text(yaml.safe_dump({
        "meta": {"project": "alpha", "schema_version": "2.0"},
        "entities": {"components": [{"id": "COMP-1", "name": "Alpha", "status": "ACTIVE", "files": ["safe.py"]}]},
        "relationships": [],
    }))
    external_manifest = outside / "manifest.json"
    external_manifest.write_text(json.dumps({"modules": [{"file": "safe.py", "name": "leaked"}]}))
    try:
        (child_dir / "manifest.json").symlink_to(external_manifest)
    except OSError:
        pytest.skip("symlinks unavailable")
    model = _parse_raw({
        "meta": {"project": "root", "schema_version": "2.0"},
        "entities": {"systems": [
            {"id": "SYS-BAD", "name": "Bad", "status": "ACTIVE", "sub_model_ref": f"../{outside.name}/.architecture-model.yaml"},
            {"id": "SYS-A", "name": "Alpha", "status": "ACTIVE", "sub_model_ref": ".architecture-models/alpha/.architecture-model.yaml"},
        ]}, "relationships": [],
    })

    data, _, _ = _parts(generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text())

    assert not any("BAD" in key or "leaked" == value["name"] for key, value in data["modules"].items())
    assert data["modules"]["alpha::module::safe.py"]["name"] == "safe.py"


def test_hostile_module_names_remain_safe_and_javascript_valid(tmp_path):
    _write_child(tmp_path, "alpha", hostile=True)
    html = generate_html_viewer(
        _root(("SYS-A", "alpha")), tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text()
    data, script, _ = _parts(html)
    key = "alpha::module::src/<hostile>&.py"

    assert key in data["modules"]
    assert "<script>pwned=1</script>" in data["modules"][key]["doc"]
    assert "</script><script>pwned=1</script>" not in html
    js = tmp_path / "viewer.js"
    js.write_text(script)
    checked = subprocess.run(["node", "--check", js], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
