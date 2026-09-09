"""Tests for scope_chain breadcrumb + drill-up link rendering (Phase 3 Task 17).

Markdown emits a `> **Path:** ROOT / A / B / **C**` line at the top when
``ProjectedView.scope_chain`` is non-empty. HTML emits a nav element
with `<a>` links to parent + peer entity pages. Root views (empty
scope_chain) render unchanged for backward compatibility with Phase 1.
"""

from __future__ import annotations

from architecture_model.core.diagram_spec import DiagramNode, DiagramSpec
from architecture_model.lifecycle.artifact_spec import ArtifactSpec, ViewRef
from architecture_model.lifecycle.renderers.html import render_html
from architecture_model.lifecycle.renderers.markdown import render_markdown
from architecture_model.lifecycle.view_projection import ProjectedView


def _spec() -> DiagramSpec:
    return DiagramSpec(
        id="d.demo",
        title="Demo",
        nodes=[DiagramNode(id="n1", label="N1", kind="component")],
    )


def _view(
    *,
    scope_chain: tuple[str, ...] = (),
    parent: str | None = None,
    peers: tuple[str, ...] = (),
) -> ProjectedView:
    return ProjectedView(
        view_id="v.demo",
        slice_id="s.demo",
        model_revision="rev-1",
        diagram_spec=_spec(),
        provenance={"projector": "se.logical", "projector_version": "1.0.0"},
        scope_chain=scope_chain,
        parent=parent,
        peers=peers,
    )


def _artifact(renderer: str) -> ArtifactSpec:
    return ArtifactSpec(
        id="a.demo",
        renderer=renderer,
        view_ref=ViewRef(view_id="v.demo", model_revision="rev-1"),
    )


# --- Markdown --------------------------------------------------------------


def test_markdown_root_view_has_no_breadcrumb():
    text = render_markdown(_view(), _artifact("markdown")).decode("utf-8")
    assert "**Path:**" not in text


def test_markdown_entity_view_emits_breadcrumb():
    text = render_markdown(
        _view(scope_chain=("COMP-1", "COMP-1.2", "COMP-1.2.3")),
        _artifact("markdown"),
    ).decode("utf-8")
    # Format: > **Path:** ROOT / COMP-1 / COMP-1.2 / **COMP-1.2.3**
    assert "> **Path:** ROOT / COMP-1 / COMP-1.2 / **COMP-1.2.3**" in text


def test_markdown_single_element_scope_bolds_current():
    text = render_markdown(
        _view(scope_chain=("COMP-1",)),
        _artifact("markdown"),
    ).decode("utf-8")
    assert "> **Path:** ROOT / **COMP-1**" in text


# --- HTML ------------------------------------------------------------------


def test_html_root_view_has_no_nav():
    text = render_html(_view(), _artifact("html")).decode("utf-8")
    assert "<nav class=\"scope-chain\"" not in text


def test_html_entity_view_emits_nav_with_parent_link():
    text = render_html(
        _view(scope_chain=("COMP-1", "COMP-1.2"), parent="COMP-1"),
        _artifact("html"),
    ).decode("utf-8")
    assert "<nav class=\"scope-chain\"" in text
    # Ancestor gets a link, current is bolded.
    assert 'href="family1.entity_page:COMP-1"' in text
    assert "<strong>COMP-1.2</strong>" in text


def test_html_entity_view_emits_peer_links():
    text = render_html(
        _view(
            scope_chain=("COMP-1", "COMP-1.2"),
            parent="COMP-1",
            peers=("COMP-1.3", "COMP-1.4"),
        ),
        _artifact("html"),
    ).decode("utf-8")
    assert 'href="family1.entity_page:COMP-1.3"' in text
    assert 'href="family1.entity_page:COMP-1.4"' in text
    assert "peers:" in text
