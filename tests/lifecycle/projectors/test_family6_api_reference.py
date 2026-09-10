"""family6.api_reference reference-doc projector — Phase 4-A Task 14.

Reads Interface entities with ``subkind == "http_route"`` and emits a
deterministic Markdown reference grouped by HTTP method. Each row lists
method, path, handler name, and any path/query parameters from
``metadata["args"]``.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.reference_docs import (
    family6_api_reference,
)
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY


def _model_with(*interfaces):
    return _parse_raw(
        {
            "meta": {"project": "t", "schema_version": "2.1"},
            "entities": {"interfaces": list(interfaces)},
        }
    )


GET_USER = {
    "id": "IF-http-route-11111111",
    "name": "get_user",
    "status": "ACTIVE",
    "subkind": "http_route",
    "intent": "Fetch user by id",
    "metadata": {
        "framework": "fastapi",
        "http_method": "GET",
        "path": "/users/{id}",
        "args": [{"name": "id", "type": "int", "required": True, "default": None}],
    },
}
POST_USER = {
    "id": "IF-http-route-22222222",
    "name": "create_user",
    "status": "ACTIVE",
    "subkind": "http_route",
    "metadata": {
        "framework": "fastapi",
        "http_method": "POST",
        "path": "/users",
        "args": [],
    },
}
GET_HOME = {
    "id": "IF-http-route-33333333",
    "name": "home",
    "status": "ACTIVE",
    "subkind": "http_route",
    "metadata": {
        "framework": "flask",
        "http_method": "GET",
        "path": "/",
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
    model = _model_with(GET_USER)
    spec = family6_api_reference(model, {})
    assert isinstance(spec, DiagramSpec)
    assert spec.id == "prose:family6.api_reference"
    assert spec.facets["content_kind"] == "markdown"


def test_groups_by_method_sorted():
    model = _model_with(POST_USER, GET_USER, GET_HOME)
    body = family6_api_reference(model, {}).facets["body"]
    get_idx = body.index("## GET")
    post_idx = body.index("## POST")
    assert get_idx < post_idx
    # Within GET, routes sorted by path: "/" < "/users/{id}"
    home_idx = body.index("`/`")
    user_idx = body.index("`/users/{id}`")
    assert home_idx < user_idx


def test_renders_route_row_and_args():
    model = _model_with(GET_USER)
    body = family6_api_reference(model, {}).facets["body"]
    assert "| Path | Handler | Description |" in body
    assert "| `/users/{id}` | `get_user` | Fetch user by id |" in body
    # Args section appears under the row for routes with params.
    assert "**Parameters**" in body
    assert "| `id` | int | yes | — |" in body


def test_route_without_args_omits_parameters():
    model = _model_with(POST_USER)
    body = family6_api_reference(model, {}).facets["body"]
    assert "`/users`" in body
    assert "**Parameters**" not in body


def test_ignores_non_http_interfaces():
    model = _model_with(CLI_X, GET_HOME)
    body = family6_api_reference(model, {}).facets["body"]
    assert "`/`" in body
    assert "build" not in body


def test_empty_when_no_routes():
    model = _model_with(CLI_X)
    body = family6_api_reference(model, {}).facets["body"]
    assert "No HTTP routes" in body


def test_registered_in_default_registry():
    assert "family6.api_reference" in DEFAULT_REGISTRY


def test_deterministic():
    model = _model_with(POST_USER, GET_USER, GET_HOME)
    a = family6_api_reference(model, {}).facets["body"]
    b = family6_api_reference(model, {}).facets["body"]
    assert a == b
