"""family6.plugin_guide reference-doc projector — Phase 4-A Task 15.

Reads Interface entities with ``subkind == "plugin_hook"`` and emits a
deterministic Markdown guide grouped by entry-point group. Each hook
lists its name and target dotted path from ``metadata``.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.reference_docs import (
    family6_plugin_guide,
)
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY


def _model_with(*interfaces):
    return _parse_raw(
        {
            "meta": {"project": "t", "schema_version": "2.1"},
            "entities": {"interfaces": list(interfaces)},
        }
    )


HOOK_A = {
    "id": "IF-plugin-hook-11111111",
    "name": "my-cli",
    "status": "ACTIVE",
    "subkind": "plugin_hook",
    "intent": "Command-line entry point",
    "metadata": {
        "entry_point_group": "console_scripts",
        "target": "mypkg.cli:main",
        "source": "pyproject",
        "args": [],
    },
}
HOOK_B = {
    "id": "IF-plugin-hook-22222222",
    "name": "validator",
    "status": "ACTIVE",
    "subkind": "plugin_hook",
    "metadata": {
        "entry_point_group": "mypkg.plugins",
        "target": "mypkg.validators:default",
        "args": [],
    },
}
HOOK_C = {
    "id": "IF-plugin-hook-33333333",
    "name": "another",
    "status": "ACTIVE",
    "subkind": "plugin_hook",
    "metadata": {
        "entry_point_group": "console_scripts",
        "target": "mypkg.other:run",
        "args": [],
    },
}
CLI_X = {
    "id": "IF-cli-command-99999999",
    "name": "build",
    "status": "ACTIVE",
    "subkind": "cli_command",
    "metadata": {"framework": "click", "args": []},
}


def test_returns_prose_diagramspec():
    model = _model_with(HOOK_A)
    spec = family6_plugin_guide(model, {})
    assert isinstance(spec, DiagramSpec)
    assert spec.id == "prose:family6.plugin_guide"
    assert spec.facets["content_kind"] == "markdown"


def test_groups_by_entry_point_group_sorted():
    model = _model_with(HOOK_B, HOOK_C, HOOK_A)
    body = family6_plugin_guide(model, {}).facets["body"]
    console_idx = body.index("## console_scripts")
    plugins_idx = body.index("## mypkg.plugins")
    assert console_idx < plugins_idx
    # Within console_scripts, sorted by name: "another" < "my-cli"
    another_idx = body.index("### another")
    mycli_idx = body.index("### my-cli")
    assert another_idx < mycli_idx


def test_renders_target_and_intent():
    model = _model_with(HOOK_A)
    body = family6_plugin_guide(model, {}).facets["body"]
    assert "### my-cli" in body
    assert "Command-line entry point" in body
    assert "**Target:** `mypkg.cli:main`" in body


def test_ignores_non_plugin_interfaces():
    model = _model_with(CLI_X, HOOK_A)
    body = family6_plugin_guide(model, {}).facets["body"]
    assert "### my-cli" in body
    assert "build" not in body


def test_empty_when_no_hooks():
    model = _model_with(CLI_X)
    body = family6_plugin_guide(model, {}).facets["body"]
    assert "No plugin hooks" in body


def test_registered_in_default_registry():
    assert "family6.plugin_guide" in DEFAULT_REGISTRY


def test_deterministic():
    model = _model_with(HOOK_B, HOOK_C, HOOK_A)
    a = family6_plugin_guide(model, {}).facets["body"]
    b = family6_plugin_guide(model, {}).facets["body"]
    assert a == b
