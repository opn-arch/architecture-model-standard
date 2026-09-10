"""Family3ComponentSpecLLM write-back projector — Phase 4-A Task 4.

Authors ``dependencies_rationale`` + ``trade_offs`` on Components from a
deterministic component-spec base view. LLM output shape:

    {"authored": [
        {"entity_id": "COMP-1",
         "dependencies_rationale": "...",
         "trade_offs": ["...", "..."]},
        ...
    ]}

Unknown entity ids and non-Component targets are dropped silently.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.write_back_variants import (
    Family3ComponentSpecLLM,
)
from architecture_model.lifecycle.view_projection import ProjectorRegistry


class _MockProvider:
    name = "mock"

    def __init__(self, response):
        self._response = response

    def structured(self, prompt, schema, *, model=None):
        return dict(self._response)

    def complete(self, *_a, **_kw):  # pragma: no cover
        raise NotImplementedError

    def stream(self, *_a, **_kw):  # pragma: no cover
        raise NotImplementedError

    def tokenize(self, text):  # pragma: no cover
        return len(text)


def _base(fragment, config):
    del fragment, config
    return DiagramSpec(
        id="prose:family3.component_spec",
        title="family3.component_spec",
        facets={"content_kind": "markdown", "body": "# Component Spec"},
    )


@pytest.fixture
def registry():
    reg = ProjectorRegistry()
    reg.register("family3.component_spec", _base)
    return reg


@pytest.fixture
def fragment():
    return _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "wb3"},
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Core"},
                    {"id": "COMP-2", "name": "Pipeline"},
                ],
                "capabilities": [{"id": "CAP-F1", "name": "Alpha"}],
            },
        }
    )


def test_family3_component_spec_llm_emits_rationale_and_trade_offs(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {
                    "entity_id": "COMP-1",
                    "dependencies_rationale": "Depends on parser for AST access.",
                    "trade_offs": ["Simplicity over speed", "Vendor-neutral"],
                },
                {
                    "entity_id": "COMP-2",
                    "dependencies_rationale": "Depends on Core for types.",
                    "trade_offs": ["Batch over streaming"],
                },
            ]
        }
    )
    projector = Family3ComponentSpecLLM(
        provider=provider, task_class="spec.author", registry=registry
    )

    result = projector(fragment, {})

    payload = result.facets["proposal"]
    assert payload["kind"] == "model-patch"
    ops = payload["operations"]
    # 2 components × (rationale + trade_offs) = 4 operations
    assert len(ops) == 4
    rationale_ops = [o for o in ops if o["field"] == "dependencies_rationale"]
    trade_ops = [o for o in ops if o["field"] == "trade_offs"]
    assert {o["target"] for o in rationale_ops} == {"COMP-1", "COMP-2"}
    assert {o["target"] for o in trade_ops} == {"COMP-1", "COMP-2"}
    comp1_trade = next(o for o in trade_ops if o["target"] == "COMP-1")
    assert comp1_trade["value"] == ["Simplicity over speed", "Vendor-neutral"]


def test_family3_component_spec_llm_skips_unknown_and_non_component(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {
                    "entity_id": "COMP-1",
                    "dependencies_rationale": "ok",
                    "trade_offs": ["x"],
                },
                # CAP-F1 exists but is not a Component — must be dropped.
                {
                    "entity_id": "CAP-F1",
                    "dependencies_rationale": "no",
                    "trade_offs": ["y"],
                },
                # Fully unknown id.
                {
                    "entity_id": "GHOST-9",
                    "dependencies_rationale": "no",
                    "trade_offs": ["z"],
                },
            ]
        }
    )
    projector = Family3ComponentSpecLLM(
        provider=provider, task_class="spec.author", registry=registry
    )
    result = projector(fragment, {})
    ops = result.facets["proposal"]["operations"]
    targets = {o["target"] for o in ops}
    assert targets == {"COMP-1"}


def test_family3_component_spec_llm_prompt_includes_base_body(fragment, registry):
    captured = {}

    class _Recorder(_MockProvider):
        def structured(self, prompt, schema, *, model=None):
            captured["prompt"] = prompt
            return {"authored": []}

    projector = Family3ComponentSpecLLM(
        provider=_Recorder({"authored": []}),
        task_class="spec.author",
        registry=registry,
    )
    projector(fragment, {})
    assert "# Component Spec" in captured["prompt"]
    assert "dependencies_rationale" in captured["prompt"]
    assert "trade_offs" in captured["prompt"]


def test_family3_component_spec_llm_schema_shape():
    provider = _MockProvider({"authored": []})
    projector = Family3ComponentSpecLLM(provider=provider, task_class="t")
    schema = projector.expected_proposal_schema()
    assert schema["type"] == "object"
    assert "authored" in schema["properties"]
    item = schema["properties"]["authored"]["items"]
    assert set(item["required"]) >= {"entity_id"}
    assert "dependencies_rationale" in item["properties"]
    assert "trade_offs" in item["properties"]
