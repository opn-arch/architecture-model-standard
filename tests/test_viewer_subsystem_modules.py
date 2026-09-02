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


def _write_history(repo: Path, *records: dict) -> None:
    history = repo / ".architecture" / "pipeline-history.jsonl"
    history.parent.mkdir(exist_ok=True)
    history.write_text("".join(json.dumps(record) + "\n" for record in records))


def _history_run(run_id: str, scope: str, path: str = "src/shared.py") -> dict:
    return {
        "run_id": run_id,
        "started_at": "2026-09-02T01:02:03Z",
        "completed_at": "2026-09-02T01:02:04Z",
        "duration_ms": 1,
        "source": "MCP",
        "invocation": "architect_pipeline",
        "status": "completed",
        "scope": scope,
        "parent_run_id": "parent-run",
        "components": [{
            "component_id": "COMP-1",
            "name": "Shared",
            "timestamp": "2026-09-02T01:02:03Z",
            "invoked_by": "allocate",
            "scope": scope,
            "parent_run_id": "parent-run",
            "stages": ["allocate"],
            "artifacts": [f".architecture-models/{run_id}/structure.yaml"],
        }],
        "modules": [{
            "path": path,
            "module": "shared",
            "timestamp": "2026-09-02T01:02:03Z",
            "invoked_by": "observe",
            "scope": scope,
            "parent_run_id": "parent-run",
            "stage": "observe",
            "produced_functions": [f"produced_{run_id}"],
            "artifacts": [f".architecture-models/{run_id}/inventory.json"],
        }],
    }


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
    assert "item.canonical_path === mod.canonical_path" in script
    assert "item.viewer_namespace === (mod.system_scope || '')" in script
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
    assert "item.viewer_namespace === (mod.system_scope || '')" in script


@pytest.mark.parametrize("scope", ["SYS-models", "models", "Models"])
def test_subsystem_history_scope_aliases_match_qualified_module(tmp_path, scope):
    _write_child(tmp_path, "models")
    _write_history(tmp_path, _history_run(f"run-{scope}", scope))
    model = _parse_raw({
        "meta": {"project": "root", "schema_version": "2.0"},
        "entities": {"systems": [{
            "id": "SYS-models", "name": "Models", "status": "ACTIVE",
            "sub_model_ref": ".architecture-models/models/.architecture-model.yaml",
        }]},
        "relationships": [],
    })

    data, script, _ = _parts(generate_html_viewer(
        model, tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text())

    aliases = data["viewer_system_aliases"]["models"]
    assert aliases["system_id"] == "SYS-models"
    assert aliases["system_name"] == "Models"
    assert aliases["sub_model_ref"] == ".architecture-models/models/.architecture-model.yaml"
    assert {"SYS-models", "models", "Models"} <= set(aliases["scope_aliases"])
    item = data["pipeline_history"][0]["modules"][0]
    assert item["viewer_namespace"] == "models"
    assert item["canonical_path"] == "src/shared.py"
    assert "historyMatchesModule(item, run, mod)" in script
    assert "Entry Timestamp:" in script
    assert "[" + "' + escapeHtml(run.status || '') + '" + "]" in script
    assert "Source / Invoked By:" in script
    assert "Stages:" in script
    assert "Produced Artifacts / Entities:" in script


def test_same_path_scoped_history_does_not_cross_match_subsystems(tmp_path):
    _write_child(tmp_path, "alpha")
    _write_child(tmp_path, "beta")
    _write_history(
        tmp_path,
        _history_run("run-alpha", "SYS-A"),
        _history_run("run-beta", "SYS-B"),
    )

    data, _, _ = _parts(generate_html_viewer(
        _root(("SYS-A", "alpha"), ("SYS-B", "beta")),
        tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text())

    by_run = {run["run_id"]: run["modules"][0]["viewer_namespace"] for run in data["pipeline_history"]}
    assert by_run == {"run-beta": "beta", "run-alpha": "alpha"}
    component_by_run = {
        run["run_id"]: run["components"][0]["viewer_entity_id"]
        for run in data["pipeline_history"]
    }
    assert component_by_run == {"run-beta": "beta::COMP-1", "run-alpha": "alpha::COMP-1"}
    assert all(run["parent_run_id"] == "parent-run" for run in data["pipeline_history"])
    assert data["modules"]["alpha::module::src/shared.py"]["system_scope"] == "alpha"
    assert data["modules"]["beta::module::src/shared.py"]["system_scope"] == "beta"


def test_nested_collision_safe_namespaces_are_explicit_history_aliases(tmp_path):
    child = tmp_path / ".architecture-models" / "teams" / "api"
    child.mkdir(parents=True)
    payload = {
        "meta": {"project": "API", "schema_version": "2.0"},
        "entities": {"components": [{
            "id": "COMP-1", "name": "API", "status": "ACTIVE", "files": ["src/shared.py"],
        }]},
        "relationships": [],
    }
    (child / ".architecture-model.yaml").write_text(yaml.safe_dump(payload))
    _write_history(tmp_path, _history_run("run-nested", "SYS-API-2"))
    model = _parse_raw({
        "meta": {"project": "root", "schema_version": "2.0"},
        "entities": {"systems": [
            {"id": "SYS-API-1", "name": "API One", "status": "ACTIVE", "sub_model_ref": ".architecture-models/teams/api/.architecture-model.yaml"},
            {"id": "SYS-API-2", "name": "API Two", "status": "ACTIVE", "sub_model_ref": ".architecture-models/teams/api/.architecture-model.yaml"},
        ]},
        "relationships": [],
    })

    data, _, _ = _parts(generate_html_viewer(model, tmp_path / "viewer.html", repo_path=tmp_path).read_text())

    namespace = "teams/api::SYS-API-2"
    assert namespace in data["viewer_system_aliases"]
    assert namespace in data["viewer_system_aliases"][namespace]["scope_aliases"]
    assert data["pipeline_history"][0]["modules"][0]["viewer_namespace"] == namespace
    assert f"{namespace}::module::src/shared.py" in data["modules"]


def test_unscoped_root_history_does_not_attach_to_child_only_module(tmp_path):
    _write_child(tmp_path, "alpha")
    _write_history(tmp_path, _history_run("root-run", ""))

    data, script, _ = _parts(generate_html_viewer(
        _root(("SYS-A", "alpha")), tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text())

    item = data["pipeline_history"][0]["modules"][0]
    assert item["viewer_namespace"] == ""
    assert data["modules"]["alpha::module::src/shared.py"]["system_scope"] == "alpha"
    assert "item.viewer_namespace === (mod.system_scope || '')" in script


def test_alias_history_keeps_safe_data_script_and_qualified_comments(tmp_path):
    _write_child(tmp_path, "models", hostile=True)
    hostile = "SYS-models</script><script>pwned=1</script>"
    _write_history(tmp_path, _history_run("run-hostile", hostile, "src/<hostile>&.py"))
    html = generate_html_viewer(
        _root(("SYS-models", "models")), tmp_path / "viewer.html", repo_path=tmp_path,
    ).read_text()
    data, script, _ = _parts(html)

    assert data["pipeline_history"][0]["modules"][0]["viewer_namespace"] is None
    assert "</script><script>pwned=1</script>" not in html
    assert "commentHtml('module', filepath, 'Add notes about this module...')" in script
    js = tmp_path / "viewer.js"
    js.write_text(script)
    checked = subprocess.run(["node", "--check", js], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr


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
