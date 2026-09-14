"""Phase 11 — adapter tests.

Covers the three v3-shaped wrappers over surviving legacy modules:

- ``pipeline_v3.adapters.legacy_pipeline.v3_to_legacy_model`` — converts
  a v3 model dict to a 2.x :class:`ArchitectureModel` for legacy
  consumers.
- ``lifecycle.projectors.legacy.visualize_adapter.render_diagrams_from_v3``
  — thin wrapper: converts + calls legacy diagram generator.
- ``lifecycle.projectors.legacy.docs_adapter.generate_docs_from_v3`` —
  thin wrapper: converts + returns a docs bundle.

The adapters are intentionally minimal — Phase 11 is the last phase
because building adapters before v3 shape stabilized would be wasted
work (per plan). Each adapter is a pure function over the v3 dict.
"""

from __future__ import annotations

import pytest

from architecture_model.pipeline_v3.adapters.legacy_pipeline import (
    v3_to_legacy_model,
)
from architecture_model.lifecycle.projectors.legacy.visualize_adapter import (
    render_diagrams_from_v3,
)
from architecture_model.lifecycle.projectors.legacy.docs_adapter import (
    generate_docs_from_v3,
)


@pytest.fixture()
def v3_model() -> dict:
    return {
        "meta": {
            "schema_version": "3.0",
            "project": "adapter-test",
            "generated_by": "pipeline_v3",
            "generated_at": "2026-09-14T00:00:00Z",
            "source_root": ".",
        },
        "entities": {
            "components": [
                {
                    "id": "COMP-a",
                    "name": "alpha",
                    "root_prefix": "pkg.a",
                    "module_names": ["pkg.a", "pkg.a.sub"],
                    "promises": [
                        {
                            "id": "PR-aaa",
                            "attribute": "delivers",
                            "content": ["fn_a"],
                            "owner_entity": "COMP-a",
                            "delivered_from": None,
                            "verified_by": [],
                            "status": "open",
                            "gap_type": None,
                            "provenance": "test",
                        },
                    ],
                },
                {
                    "id": "COMP-b",
                    "name": "beta",
                    "root_prefix": "pkg.b",
                    "module_names": ["pkg.b"],
                    "promises": [],
                },
            ],
        },
        "relationships": [
            {"from": "COMP-a", "to": "COMP-b", "type": "depends-on"},
        ],
    }


# --- v3_to_legacy_model -----------------------------------------------------


def test_v3_to_legacy_model_returns_architecture_model(v3_model: dict) -> None:
    m = v3_to_legacy_model(v3_model)
    from architecture_model.core.types import ArchitectureModel
    assert isinstance(m, ArchitectureModel)


def test_v3_to_legacy_model_preserves_meta_project(v3_model: dict) -> None:
    m = v3_to_legacy_model(v3_model)
    assert m.meta.project == "adapter-test"


def test_v3_to_legacy_model_translates_components(v3_model: dict) -> None:
    m = v3_to_legacy_model(v3_model)
    assert {c.id for c in m.entities.components} == {"COMP-a", "COMP-b"}
    names = {c.name for c in m.entities.components}
    assert names == {"alpha", "beta"}


def test_v3_to_legacy_model_translates_depends_on(v3_model: dict) -> None:
    m = v3_to_legacy_model(v3_model)
    edges = [(r.from_id, r.to_id, r.type.value) for r in m.relationships]
    assert ("COMP-a", "COMP-b", "depends-on") in edges


def test_v3_to_legacy_model_marks_schema_2_x(v3_model: dict) -> None:
    # legacy consumers expect a 2.x schema_version stamp
    m = v3_to_legacy_model(v3_model)
    assert m.meta.schema_version.startswith("2.")


# --- visualize adapter ------------------------------------------------------


def test_render_diagrams_from_v3_returns_mapping(v3_model: dict) -> None:
    out = render_diagrams_from_v3(v3_model)
    assert isinstance(out, dict)
    # Every value is a string (Markdown/Mermaid body)
    for v in out.values():
        assert isinstance(v, str)


def test_render_diagrams_from_v3_contains_component_ids(v3_model: dict) -> None:
    out = render_diagrams_from_v3(v3_model)
    body = "\n".join(out.values())
    assert "COMP-a" in body or "alpha" in body


# --- docs adapter -----------------------------------------------------------


def test_generate_docs_from_v3_returns_mapping(v3_model: dict) -> None:
    out = generate_docs_from_v3(v3_model)
    assert isinstance(out, dict)
    for v in out.values():
        assert isinstance(v, str)


def test_generate_docs_from_v3_covers_components(v3_model: dict) -> None:
    out = generate_docs_from_v3(v3_model)
    body = "\n".join(out.values())
    assert "alpha" in body or "COMP-a" in body


def test_adapters_do_not_mutate_input(v3_model: dict) -> None:
    orig_ids = {c["id"] for c in v3_model["entities"]["components"]}
    v3_to_legacy_model(v3_model)
    render_diagrams_from_v3(v3_model)
    generate_docs_from_v3(v3_model)
    still = {c["id"] for c in v3_model["entities"]["components"]}
    assert orig_ids == still
