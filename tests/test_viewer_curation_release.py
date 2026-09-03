from pathlib import Path

import pytest
import yaml

from architecture_model.core.parser import load_model
from architecture_model.core.se_view_projectors import (
    project_conops,
    project_functional_architecture,
    project_logical_architecture,
    project_use_cases,
)
from architecture_model.core.view_context import ArchitectureViewContext
from architecture_model.core.view_curation import (
    ANNOTATION_KEYS,
    ASSOCIATION_KEYS,
    EVIDENCE_KEYS,
    EXTERNAL_KEYS,
    FLOW_KEYS,
    GROUP_KEYS,
    SCENARIO_KEYS,
    SELECTOR_KEYS,
    USE_CASE_ACTOR_KEYS,
    USE_CASE_VIEW_KEYS,
    VIEW_KEYS,
    VIEW_NAMES,
    load_viewer_curation,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/viewer-curation.yaml"
REFERENCE = ROOT / "docs/viewer-curation.md"
LOGS_FIXTURE = ROOT / "tests/fixtures/logs_db-viewer-curation.yaml"
LOGS_DB = Path("/Users/baigm2/Documents/Projects/logs_db")


def test_published_example_loads_against_documented_model_without_diagnostics():
    assert EXAMPLE.is_file()
    model_path = ROOT / "tests/fixtures/viewer-curation-model.yaml"
    model = load_model(model_path)
    context = ArchitectureViewContext(model_path.parent, {"root": model}, [])

    loaded = load_viewer_curation(ROOT, context, EXAMPLE)

    assert loaded.diagnostics == []
    assert loaded.views.conops.scenarios
    assert loaded.views.functional.groups
    assert loaded.views.logical.tiers
    assert loaded.views.use_cases.annotations


def test_logs_db_fixture_has_version_one_supported_schema():
    raw = yaml.safe_load(LOGS_FIXTURE.read_text(encoding="utf-8"))
    assert set(raw) == {"version", "views"}
    assert raw["version"] == 1
    assert set(raw["views"]) == set(VIEW_NAMES)

    nested = {
        "groups": GROUP_KEYS,
        "tiers": GROUP_KEYS,
        "scenarios": SCENARIO_KEYS,
        "externals": EXTERNAL_KEYS,
        "flows": FLOW_KEYS,
        "actors": USE_CASE_ACTOR_KEYS,
        "associations": ASSOCIATION_KEYS,
        "annotations": ANNOTATION_KEYS,
    }
    for view_name, view in raw["views"].items():
        allowed = VIEW_KEYS | (USE_CASE_VIEW_KEYS if view_name == "use_cases" else set())
        assert set(view) <= allowed
        for collection, keys in nested.items():
            assert all(set(record) <= keys for record in view.get(collection, []))


def test_logs_db_fixture_resolves_and_reproduces_accepted_projections_when_available(monkeypatch):
    if not (LOGS_DB / ".architecture-model.yaml").is_file():
        pytest.skip("logs-db canonical model unavailable")
    context = ArchitectureViewContext.from_repo(LOGS_DB)

    from architecture_model.core import view_curation

    def logs_db_evidence(_root, value, *, must_exist=True):
        candidate = (LOGS_DB / str(value)).resolve()
        return candidate if candidate.is_relative_to(LOGS_DB) and (not must_exist or candidate.is_file()) else None

    monkeypatch.setattr(view_curation, "_safe_file", logs_db_evidence)
    loaded = load_viewer_curation(ROOT, context, LOGS_FIXTURE)
    specs = {
        "conops": project_conops(context, loaded.views.conops),
        "functional": project_functional_architecture(context, loaded.views.functional),
        "logical": project_logical_architecture(context, loaded.views.logical),
        "use_cases": project_use_cases(context, loaded.views.use_cases),
    }

    assert loaded.diagnostics == []
    assert {name: (len(spec.nodes), len(spec.edges)) for name, spec in specs.items()} == {
        "conops": (11, 20),
        "functional": (10, 7),
        "logical": (11, 7),
        "use_cases": (12, 10),
    }


def test_actual_logs_db_profile_matches_tracked_fixture_when_available():
    actual = LOGS_DB / ".architecture/viewer-curation.yaml"
    if not actual.is_file():
        pytest.skip("logs-db source profile unavailable")
    tracked = LOGS_FIXTURE.read_text(encoding="utf-8").splitlines(keepends=True)

    assert "logs_db" in tracked[0] and "2026-09-02" in tracked[0]
    assert "".join(tracked[1:]) == actual.read_text(encoding="utf-8")


def test_reference_covers_supported_schema_and_cli_flags(capsys):
    from architecture_model.cli.main import main

    text = REFERENCE.read_text(encoding="utf-8")
    key_sets = (
        VIEW_KEYS,
        USE_CASE_VIEW_KEYS,
        SELECTOR_KEYS,
        GROUP_KEYS,
        SCENARIO_KEYS,
        EXTERNAL_KEYS,
        FLOW_KEYS,
        EVIDENCE_KEYS,
        USE_CASE_ACTOR_KEYS,
        ASSOCIATION_KEYS,
        ANNOTATION_KEYS,
    )
    for key in set().union(*key_sets):
        assert f"`{key}`" in text
    for syntax in (
        "architecture-model viewer <path> --curation <path>",
        "architecture-model viewer <path> --no-curation",
        "architecture-model visualize <path> --curation <path>",
        "architecture-model visualize <path> --no-curation",
    ):
        assert f"`{syntax}`" in text
    assert "[Viewer curation reference](docs/viewer-curation.md)" in (ROOT / "README.md").read_text(encoding="utf-8")
    for command in ("viewer", "visualize"):
        with pytest.raises(SystemExit) as result:
            main([command, "--help"])
        assert result.value.code == 0
        assert "docs/viewer-curation.md" in capsys.readouterr().out


def test_nested_allowed_key_contract_excludes_discarded_fields():
    assert GROUP_KEYS == {"id", "label", "kind", "parent", "order", "members"}
    assert SCENARIO_KEYS == GROUP_KEYS | {"goal", "outcomes", "requirements", "moes", "evidence"}
    assert EXTERNAL_KEYS == {"id", "name", "inferred", "evidence", "kind"}
    assert FLOW_KEYS == {"source", "target", "kind", "label", "inferred", "evidence"}


def test_reference_promises_back_and_breadcrumb_navigation_only():
    text = REFERENCE.read_text(encoding="utf-8").lower()

    assert "back navigation and breadcrumbs" in text
    assert "back/forward" not in text
    assert "forward navigation" not in text
