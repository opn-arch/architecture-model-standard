"""family6.cli_reference reference-doc projector — Phase 4-A Task 13.

Reads promoted Interface entities with ``subkind == "cli_command"`` and
emits a deterministic Markdown reference grouped by framework
(``click`` / ``argparse``). Each command surfaces its ``intent`` (as a
one-line description when present) and an argument table derived from
``metadata["args"]``.

Interfaces without the ``cli_command`` subkind are ignored so the
projector composes cleanly with the mixed-interface fragments produced
by :func:`architecture_model.pipeline.endpoint_promotion.promote_endpoints_to_interfaces`.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.reference_docs import (
    family6_cli_reference,
)
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY


def _model_with_cli(*interfaces):
    return _parse_raw(
        {
            "meta": {"project": "t", "schema_version": "2.1"},
            "entities": {"interfaces": list(interfaces)},
        }
    )


CLI_A = {
    "id": "IF-cli-command-aaaaaaaa",
    "name": "build",
    "status": "ACTIVE",
    "subkind": "cli_command",
    "intent": "Build the project",
    "metadata": {
        "framework": "click",
        "args": [
            {"name": "--target", "type": "str", "required": True, "default": None},
            {"name": "--verbose", "type": "bool", "required": False, "default": False},
        ],
    },
}
CLI_B = {
    "id": "IF-cli-command-bbbbbbbb",
    "name": "test",
    "status": "ACTIVE",
    "subkind": "cli_command",
    "metadata": {"framework": "click", "args": []},
}
CLI_C = {
    "id": "IF-cli-command-cccccccc",
    "name": "migrate",
    "status": "ACTIVE",
    "subkind": "cli_command",
    "intent": "Run DB migrations",
    "metadata": {"framework": "argparse", "args": []},
}
HTTP_D = {
    "id": "IF-http-route-dddddddd",
    "name": "get_user",
    "status": "ACTIVE",
    "subkind": "http_route",
    "metadata": {"framework": "fastapi", "http_method": "GET", "path": "/u", "args": []},
}


def test_returns_prose_diagramspec():
    model = _model_with_cli(CLI_A)
    spec = family6_cli_reference(model, {})
    assert isinstance(spec, DiagramSpec)
    assert spec.id == "prose:family6.cli_reference"
    assert spec.facets["content_kind"] == "markdown"
    assert spec.title == "family6.cli_reference"


def test_groups_by_framework_sorted():
    model = _model_with_cli(CLI_C, CLI_B, CLI_A)
    body = family6_cli_reference(model, {}).facets["body"]
    # argparse group appears before click (alphabetical framework order).
    argp_idx = body.index("## argparse")
    click_idx = body.index("## click")
    assert argp_idx < click_idx
    # Within click, commands sorted by name: build < test
    build_idx = body.index("### build")
    test_idx = body.index("### test")
    assert build_idx < test_idx


def test_renders_intent_and_args_table():
    model = _model_with_cli(CLI_A)
    body = family6_cli_reference(model, {}).facets["body"]
    assert "Build the project" in body
    assert "| Argument | Type | Required | Default |" in body
    assert "| `--target` | str | yes | — |" in body
    assert "| `--verbose` | bool | no | `False` |" in body


def test_command_without_args_omits_table():
    model = _model_with_cli(CLI_B)
    body = family6_cli_reference(model, {}).facets["body"]
    assert "### test" in body
    assert "| Argument |" not in body


def test_ignores_non_cli_interfaces():
    model = _model_with_cli(HTTP_D, CLI_A)
    body = family6_cli_reference(model, {}).facets["body"]
    assert "### build" in body
    assert "get_user" not in body
    assert "http_route" not in body


def test_empty_when_no_cli_interfaces():
    model = _model_with_cli(HTTP_D)
    body = family6_cli_reference(model, {}).facets["body"]
    assert "No CLI commands" in body


def test_registered_in_default_registry():
    assert "family6.cli_reference" in DEFAULT_REGISTRY


def test_deterministic():
    model = _model_with_cli(CLI_C, CLI_B, CLI_A)
    a = family6_cli_reference(model, {})
    b = family6_cli_reference(model, {})
    assert a.facets["body"] == b.facets["body"]
