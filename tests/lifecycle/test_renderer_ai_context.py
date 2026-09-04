"""Tests for the AI-context artifact renderer (T18 commit 2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.core.diagram_spec import DiagramEdge, DiagramNode, DiagramSpec
from architecture_model.lifecycle.artifact_spec import ArtifactSpec, ViewRef
from architecture_model.lifecycle.renderers import DEFAULT_RENDERERS, get_renderer
from architecture_model.lifecycle.renderers.ai_context import render_ai_context
from architecture_model.lifecycle.view_projection import ProjectedView


def _make_view(view_id: str = "v.demo") -> ProjectedView:
    spec = DiagramSpec(
        id="d.demo",
        title="Demo View",
        nodes=[
            DiagramNode(id="n1", label="Node One", kind="component"),
            DiagramNode(id="n2", label="Node Two", kind="capability"),
        ],
        edges=[DiagramEdge(source="n1", target="n2", kind="realizes", label="lbl")],
    )
    return ProjectedView(
        view_id=view_id,
        slice_id="s.demo",
        model_revision="rev-1",
        diagram_spec=spec,
        provenance={"projector": "se.logical", "projector_version": "1.2.3"},
        warnings=("W_TEST: careful",),
    )


def _make_artifact(renderer: str = "ai-context", **params) -> ArtifactSpec:
    return ArtifactSpec(
        id="a.ai",
        renderer=renderer,
        view_ref=ViewRef(view_id="v.demo", model_revision="rev-1"),
        parameters=params,
    )


def test_render_ai_context_returns_nonempty_bytes():
    got = render_ai_context(_make_view(), _make_artifact())
    assert isinstance(got, bytes) and len(got) > 0


def test_render_ai_context_contains_identifiable_content():
    text = render_ai_context(_make_view(), _make_artifact()).decode("utf-8")
    assert "v.demo" in text
    assert "se.logical" in text
    assert "n1" in text and "n2" in text
    assert "W_TEST: careful" in text


def test_render_ai_context_rejects_wrong_renderer():
    with pytest.raises(ValueError, match="renderer mismatch"):
        render_ai_context(_make_view(), _make_artifact("html"))


def test_render_ai_context_empty_list_raises():
    with pytest.raises(ValueError, match="no view"):
        render_ai_context([], _make_artifact())


def test_render_ai_context_takes_first_of_list():
    got = render_ai_context([_make_view("v.one"), _make_view("v.two")], _make_artifact())
    assert b"v.one" in got


def test_render_ai_context_deterministic():
    v, a = _make_view(), _make_artifact()
    assert render_ai_context(v, a) == render_ai_context(v, a)


def test_render_ai_context_max_tokens_caps_output():
    a = _make_artifact(max_tokens=5)  # ~20 chars cap
    got = render_ai_context(_make_view(), a)
    assert len(got) <= 20


def test_render_ai_context_unknown_parameter_ignored():
    a = _make_artifact(unknown_param="ignored")
    got = render_ai_context(_make_view(), a)
    assert len(got) > 0


def test_render_ai_context_pure_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = set(Path(tmp_path).iterdir())
    render_ai_context(_make_view(), _make_artifact())
    assert set(Path(tmp_path).iterdir()) == before


def test_ai_context_registered_in_defaults():
    assert "ai-context" in DEFAULT_RENDERERS
    assert get_renderer("ai-context") is render_ai_context
