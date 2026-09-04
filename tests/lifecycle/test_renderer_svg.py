"""Tests for the SVG artifact renderer (T18 commit 1)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from architecture_model.core.diagram_spec import DiagramNode, DiagramSpec
from architecture_model.lifecycle.artifact_spec import ArtifactSpec, ViewRef
from architecture_model.lifecycle.renderers import get_renderer
from architecture_model.lifecycle.renderers.svg import render_svg
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


def _make_artifact(renderer: str = "svg") -> ArtifactSpec:
    return ArtifactSpec(
        id="a.demo",
        renderer=renderer,
        view_ref=ViewRef(view_id="v.demo", model_revision="rev-1"),
    )


def test_render_svg_returns_nonempty_bytes():
    result = render_svg(_make_view(), _make_artifact("svg"))
    assert isinstance(result, bytes)
    assert len(result) > 0
    assert b"<svg" in result


def test_render_svg_rejects_wrong_renderer():
    with pytest.raises(ValueError, match="renderer mismatch"):
        render_svg(_make_view(), _make_artifact("html"))


def test_render_svg_takes_first_of_list():
    v1 = _make_view("v.one")
    v2 = _make_view("v.two")
    got = render_svg([v1, v2], _make_artifact("svg"))
    assert isinstance(got, bytes) and len(got) > 0


def test_render_svg_empty_list_raises():
    with pytest.raises(ValueError, match="no view"):
        render_svg([], _make_artifact("svg"))


def test_render_svg_deterministic():
    v = _make_view()
    a = _make_artifact("svg")
    assert render_svg(v, a) == render_svg(v, a)


def test_render_svg_pure_no_files_created(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = set(Path(tmp_path).iterdir())
    render_svg(_make_view(), _make_artifact("svg"))
    after = set(Path(tmp_path).iterdir())
    assert before == after


def test_registry_get_svg_returns_render_svg():
    assert get_renderer("svg") is render_svg
