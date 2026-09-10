"""Family4UseCasesLLM write-back projector — Phase 4-A Task 6.

Adds NEW ``Behavior`` entities from a use-case base view. Distinct from
Tasks 3-5 (which mutate existing entities with ``replace``): this
projector emits ``{"op": "add", "target_kind": "behaviors", "value": {...}}``
operations. LLM output shape:

    {"authored": [
        {"id": "BEH-NEW-1", "name": "Login flow",
         "narrative": "User submits credentials...",
         "actor_ids": ["ACT-1"]},
        ...
    ]}

Ids that collide with existing entities are skipped so re-runs are
idempotent.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.write_back_variants import (
    Family4UseCasesLLM,
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
        id="prose:family4.use_cases",
        title="family4.use_cases",
        facets={"content_kind": "markdown", "body": "# Use Cases"},
    )


@pytest.fixture
def registry():
    reg = ProjectorRegistry()
    reg.register("family4.use_cases", _base)
    return reg


@pytest.fixture
def fragment():
    return _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "wb4"},
            "entities": {
                "actors": [{"id": "ACT-1", "name": "User"}],
                "behaviors": [{"id": "BEH-EXISTING", "name": "Existing"}],
            },
        }
    )


def test_family4_use_cases_llm_emits_add_operations(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {
                    "id": "BEH-NEW-1",
                    "name": "Login flow",
                    "narrative": "User submits credentials.",
                    "actor_ids": ["ACT-1"],
                },
                {
                    "id": "BEH-NEW-2",
                    "name": "Logout flow",
                    "narrative": "User ends session.",
                    "actor_ids": ["ACT-1"],
                },
            ]
        }
    )
    projector = Family4UseCasesLLM(
        provider=provider, task_class="usecases.author", registry=registry
    )
    result = projector(fragment, {})
    payload = result.facets["proposal"]
    assert payload["kind"] == "model-patch"
    ops = payload["operations"]
    assert len(ops) == 2
    for op in ops:
        assert op["op"] == "add"
        assert op["target_kind"] == "behaviors"
        assert "value" in op
    new_ids = {op["value"]["id"] for op in ops}
    assert new_ids == {"BEH-NEW-1", "BEH-NEW-2"}


def test_family4_use_cases_llm_skips_existing_ids(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {
                    "id": "BEH-EXISTING",  # collision — must be skipped
                    "name": "Duplicate",
                    "narrative": "n/a",
                },
                {
                    "id": "BEH-NEW-9",
                    "name": "Fresh flow",
                    "narrative": "n/a",
                },
            ]
        }
    )
    projector = Family4UseCasesLLM(
        provider=provider, task_class="usecases.author", registry=registry
    )
    result = projector(fragment, {})
    ops = result.facets["proposal"]["operations"]
    new_ids = {op["value"]["id"] for op in ops}
    assert new_ids == {"BEH-NEW-9"}


def test_family4_use_cases_llm_schema_shape():
    provider = _MockProvider({"authored": []})
    projector = Family4UseCasesLLM(provider=provider, task_class="t")
    schema = projector.expected_proposal_schema()
    item = schema["properties"]["authored"]["items"]
    assert set(item["required"]) >= {"id", "name"}


def test_family4_use_cases_llm_prompt_mentions_behavior(fragment, registry):
    captured = {}

    class _Recorder(_MockProvider):
        def structured(self, prompt, schema, *, model=None):
            captured["prompt"] = prompt
            return {"authored": []}

    projector = Family4UseCasesLLM(
        provider=_Recorder({"authored": []}),
        task_class="usecases.author",
        registry=registry,
    )
    projector(fragment, {})
    assert "# Use Cases" in captured["prompt"]
    assert "behavior" in captured["prompt"].lower()
