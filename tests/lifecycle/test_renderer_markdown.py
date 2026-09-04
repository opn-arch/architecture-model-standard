"""Tests for the Markdown artifact renderer (T18 commit 1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.core.diagram_spec import DiagramNode, DiagramSpec
from architecture_model.lifecycle.artifact_spec import ArtifactSpec, ViewRef
from architecture_model.lifecycle.renderers import get_renderer
from architecture_model.lifecycle.renderers.markdown import render_markdown
from architecture_model.lifecycle.view_projection import ProjectedView


def _make_view(view_id: str = "v.demo") -> ProjectedView:
    spec = DiagramSpec(
        id="d.demo",
        title="Demo Title",
        nodes=[DiagramNode(id="n1", label="Node One", kind="component")],
    )
    return ProjectedView(
        view_id=view_id,
        slice_id="s.demo",
        model_revision="rev-1",
        diagram_spec=spec,
        provenance={"projector": "se.logical", "projector_version": "1.0.0"},
        warnings=("W_ONE: msg1", "W_TWO: msg2"),
    )


def _make_artifact(renderer: str = "markdown", **params) -> ArtifactSpec:
    return ArtifactSpec(
        id="a.demo",
        renderer=renderer,
        view_ref=ViewRef(view_id="v.demo", model_revision="rev-1"),
        parameters=params,
    )


def test_render_markdown_returns_nonempty_bytes():
    got = render_markdown(_make_view(), _make_artifact("markdown"))
    assert isinstance(got, bytes) and len(got) > 0
    text = got.decode("utf-8")
    assert "Demo Title" in text
    assert "se.logical" in text
    assert "W_ONE" in text


def test_render_markdown_rejects_wrong_renderer():
    with pytest.raises(ValueError, match="renderer mismatch"):
        render_markdown(_make_view(), _make_artifact("svg"))


def test_render_markdown_takes_first_of_list():
    v1, v2 = _make_view("v.one"), _make_view("v.two")
    got = render_markdown([v1, v2], _make_artifact("markdown"))
    assert b"Demo Title" in got


def test_render_markdown_empty_list_raises():
    with pytest.raises(ValueError, match="no view"):
        render_markdown([], _make_artifact("markdown"))


def test_render_markdown_deterministic():
    v, a = _make_view(), _make_artifact("markdown")
    assert render_markdown(v, a) == render_markdown(v, a)


def test_render_markdown_title_override():
    a = _make_artifact("markdown", title="Custom Title")
    text = render_markdown(_make_view(), a).decode("utf-8")
    assert "Custom Title" in text


def test_render_markdown_pure_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = set(Path(tmp_path).iterdir())
    render_markdown(_make_view(), _make_artifact("markdown"))
    assert set(Path(tmp_path).iterdir()) == before


def test_registry_get_markdown():
    assert get_renderer("markdown") is render_markdown
