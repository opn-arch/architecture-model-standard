"""HTTP route endpoint extraction — Phase 4-A Task 9.

Detects:

* FastAPI / APIRouter: ``@app.get("/")``, ``@router.post("/x")``, etc.
* Flask: ``@app.route("/", methods=["GET"])``.
* Starlette: ``Route("/", endpoint, methods=["GET"])``.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.pipeline.endpoint_extract import extract_http_endpoints


@pytest.fixture
def http_source(tmp_path: Path) -> Path:
    src = tmp_path / "api.py"
    src.write_text(
        dedent(
            """
            from fastapi import FastAPI, APIRouter
            from flask import Flask
            from starlette.routing import Route

            app = FastAPI()
            router = APIRouter()
            flask_app = Flask(__name__)

            @app.get("/items/{item_id}")
            def read_item(item_id: int):
                pass

            @app.post("/items")
            def create_item():
                pass

            @router.delete("/items/{item_id}")
            def delete_item(item_id: int):
                pass

            @flask_app.route("/health", methods=["GET"])
            def health():
                pass

            @flask_app.route("/submit", methods=["POST", "PUT"])
            def submit():
                pass

            def build_routes():
                return [
                    Route("/ping", endpoint=lambda r: r, methods=["GET"]),
                ]
            """
        ).lstrip()
    )
    return src


def test_extract_http_endpoints_finds_fastapi_routes(http_source):
    endpoints = extract_http_endpoints([http_source])
    routes = {(e.metadata["http_method"], e.metadata["path"]) for e in endpoints}
    assert ("GET", "/items/{item_id}") in routes
    assert ("POST", "/items") in routes
    assert ("DELETE", "/items/{item_id}") in routes


def test_extract_http_endpoints_finds_flask_routes(http_source):
    endpoints = extract_http_endpoints([http_source])
    methods_for_submit = {
        e.metadata["http_method"]
        for e in endpoints
        if e.metadata.get("path") == "/submit"
    }
    assert methods_for_submit == {"POST", "PUT"}
    health = next(e for e in endpoints if e.metadata.get("path") == "/health")
    assert health.metadata["http_method"] == "GET"


def test_extract_http_endpoints_finds_starlette_route(http_source):
    endpoints = extract_http_endpoints([http_source])
    starlette = [
        e for e in endpoints if e.metadata.get("framework") == "starlette"
    ]
    assert len(starlette) == 1
    assert starlette[0].metadata["path"] == "/ping"
    assert starlette[0].metadata["http_method"] == "GET"


def test_extract_http_endpoints_all_kind_http_route(http_source):
    endpoints = extract_http_endpoints([http_source])
    assert endpoints
    assert all(e.kind == "http_route" for e in endpoints)


def test_extract_http_endpoints_deterministic_order(http_source):
    a = extract_http_endpoints([http_source])
    b = extract_http_endpoints([http_source])
    assert [(e.file, e.lineno, e.name) for e in a] == [
        (e.file, e.lineno, e.name) for e in b
    ]


def test_extract_http_endpoints_captures_path_params(http_source):
    endpoints = extract_http_endpoints([http_source])
    parameterized = [
        e for e in endpoints if "{item_id}" in e.metadata.get("path", "")
    ]
    assert parameterized
    for ep in parameterized:
        param_names = {a.name for a in ep.args}
        assert "item_id" in param_names
