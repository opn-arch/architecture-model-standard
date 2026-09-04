"""Tests for the HTML artifact renderer (T18 commit 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.core.diagram_spec import DiagramNode, DiagramSpec
from architecture_model.lifecycle.artifact_spec import ArtifactSpec, ViewRef
from architecture_model.lifecycle.renderers import DEFAULT_RENDERERS, get_renderer
from architecture_model.lifecycle.renderers.html import render_html
from architecture_model.lifecycle.view_projection import ProjectedView


def _make_view(view_id: str = "v.demo") -> ProjectedView:
    spec = DiagramSpec(
        id="d.demo",
        title="Demo",
        nodes=[DiagramNode(id="n1", label="Node One", kind="component")],
    )
    return ProjectedView(
        view_id=view_id,
        slice_id="s.demo",
        model_revision="rev-1",
        diagram_spec=spec,
        provenance={"projector": "se.logical", "projector_version": "1.0.0"},
        warnings=("W_TEST: hello",),
    )


def _make_artifact(renderer: str = "html", **params) -> ArtifactSpec:
    return ArtifactSpec(
        id="a.demo",
        renderer=renderer,
        view_ref=ViewRef(view_id="v.demo", model_revision="rev-1"),
        parameters=params,
    )


def test_render_html_returns_nonempty_bytes():
    got = render_html(_make_view(), _make_artifact("html"))
    assert isinstance(got, bytes) and len(got) > 0
    text = got.decode("utf-8")
    assert "<html" in text.lower()
    assert "<svg" in text
    assert "Demo" in text


def test_render_html_rejects_wrong_renderer():
    with pytest.raises(ValueError, match="renderer mismatch"):
        render_html(_make_view(), _make_artifact("markdown"))


def test_render_html_takes_first_of_list():
    got = render_html([_make_view("v.one"), _make_view("v.two")], _make_artifact("html"))
    assert b"<svg" in got


def test_render_html_empty_list_raises():
    with pytest.raises(ValueError, match="no view"):
        render_html([], _make_artifact("html"))


def test_render_html_deterministic():
    v, a = _make_view(), _make_artifact("html")
    assert render_html(v, a) == render_html(v, a)


def test_render_html_title_override():
    a = _make_artifact("html", title="Custom HTML Title")
    text = render_html(_make_view(), a).decode("utf-8")
    assert "Custom HTML Title" in text


def test_render_html_pure_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = set(Path(tmp_path).iterdir())
    render_html(_make_view(), _make_artifact("html"))
    assert set(Path(tmp_path).iterdir()) == before


def test_registry_defaults_expose_all_three():
    assert {"svg", "markdown", "html"}.issubset(set(DEFAULT_RENDERERS))
    assert get_renderer("html") is render_html


def test_registry_unknown_raises_key_error():
    with pytest.raises(KeyError):
        get_renderer("nope")
