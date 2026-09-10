"""End-to-end endpoint→Interface promotion — Phase 4-A Task 12.

Verifies that the ``promote_endpoints_to_interfaces`` helper:

1. Runs the three endpoint extractors over a fixture repo.
2. Emits Interface entities with correct ``subkind`` and ``metadata``.
3. Creates ``exposes`` relationships from the owning Component
   (determined by matching the endpoint's file against ``component.files``).
4. Is idempotent — re-running over the same model updates in place
   rather than duplicating Interfaces.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.core.parser import _parse_raw
from architecture_model.pipeline.endpoint_promotion import (
    promote_endpoints_to_interfaces,
)


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    (tmp_path / "src" / "mytool").mkdir(parents=True)
    (tmp_path / "src" / "mytool" / "__init__.py").write_text("")
    (tmp_path / "src" / "mytool" / "cli.py").write_text(
        dedent(
            """
            import click

            @click.group()
            def cli():
                pass

            @cli.command("greet")
            @click.option("--name", default="world")
            def greet(name):
                pass
            """
        ).lstrip()
    )
    (tmp_path / "src" / "mytool" / "api.py").write_text(
        dedent(
            """
            from fastapi import FastAPI
            app = FastAPI()

            @app.get("/health")
            def health():
                pass

            @app.post("/items")
            def create_item():
                pass
            """
        ).lstrip()
    )
    (tmp_path / "pyproject.toml").write_text(
        dedent(
            """
            [project]
            name = "mytool"

            [project.entry-points."opencode_arch.projectors"]
            mission = "mytool.projectors:mission"
            """
        ).lstrip()
    )
    return tmp_path


@pytest.fixture
def model_with_two_components(fixture_repo):
    cli_path = str(fixture_repo / "src" / "mytool" / "cli.py")
    api_path = str(fixture_repo / "src" / "mytool" / "api.py")
    pyproject_path = str(fixture_repo / "pyproject.toml")
    return _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "mytool"},
            "entities": {
                "components": [
                    {
                        "id": "COMP-CLI",
                        "name": "CLI",
                        "status": "ACTIVE",
                        "files": [cli_path, pyproject_path],
                    },
                    {
                        "id": "COMP-API",
                        "name": "API",
                        "status": "ACTIVE",
                        "files": [api_path],
                    },
                ]
            },
        }
    )


def test_promotion_creates_cli_and_http_interfaces(
    fixture_repo, model_with_two_components
):
    result = promote_endpoints_to_interfaces(
        model_with_two_components, fixture_repo
    )
    subkinds = {iface.subkind for iface in result.entities.interfaces}
    assert "cli_command" in subkinds
    assert "http_route" in subkinds
    assert "plugin_hook" in subkinds


def test_promotion_creates_exposes_edges(
    fixture_repo, model_with_two_components
):
    result = promote_endpoints_to_interfaces(
        model_with_two_components, fixture_repo
    )
    exposes = [r for r in result.relationships if r.type == "exposes"]
    from_ids = {r.from_id for r in exposes}
    # Both components should expose at least one endpoint.
    assert "COMP-CLI" in from_ids
    assert "COMP-API" in from_ids
    # Every 'exposes' target must be an Interface id.
    iface_ids = {i.id for i in result.entities.interfaces}
    for r in exposes:
        assert r.to_id in iface_ids


def test_promotion_is_idempotent(fixture_repo, model_with_two_components):
    once = promote_endpoints_to_interfaces(
        model_with_two_components, fixture_repo
    )
    twice = promote_endpoints_to_interfaces(once, fixture_repo)
    assert len(once.entities.interfaces) == len(twice.entities.interfaces)
    exposes_once = [r for r in once.relationships if r.type == "exposes"]
    exposes_twice = [r for r in twice.relationships if r.type == "exposes"]
    assert len(exposes_once) == len(exposes_twice)


def test_promotion_preserves_existing_manual_interfaces(fixture_repo):
    """Manually authored interfaces without a matching endpoint survive."""
    model = _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "mytool"},
            "entities": {
                "interfaces": [
                    {"id": "IF-MANUAL", "name": "Manual", "status": "ACTIVE"}
                ],
                "components": [
                    {"id": "COMP-CLI", "name": "CLI", "status": "ACTIVE",
                     "files": [str(fixture_repo / "src" / "mytool" / "cli.py")]},
                ],
            },
        }
    )
    result = promote_endpoints_to_interfaces(model, fixture_repo)
    ids = {i.id for i in result.entities.interfaces}
    assert "IF-MANUAL" in ids


def test_promotion_no_components_still_extracts_interfaces(fixture_repo):
    """No matching component → interfaces still created, just no exposes."""
    model = _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "mytool"},
            "entities": {"components": []},
        }
    )
    result = promote_endpoints_to_interfaces(model, fixture_repo)
    assert result.entities.interfaces  # non-empty
    assert not [r for r in result.relationships if r.type == "exposes"]


def test_promotion_captures_metadata(fixture_repo, model_with_two_components):
    result = promote_endpoints_to_interfaces(
        model_with_two_components, fixture_repo
    )
    http = [i for i in result.entities.interfaces if i.subkind == "http_route"]
    assert http
    for iface in http:
        assert "http_method" in iface.metadata
        assert "path" in iface.metadata
    cli = [i for i in result.entities.interfaces if i.subkind == "cli_command"]
    assert cli
    for iface in cli:
        assert "args" in iface.metadata  # even if empty list
