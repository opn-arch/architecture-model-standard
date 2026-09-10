"""Family1MissionLLM write-back projector — Phase 4-A Task 3.

Authors ``intent`` + ``goals`` on top-level Capabilities and Actors from
a deterministic mission base view. LLM output shape:

    {"authored": [
        {"entity_id": "CAP-F1", "intent": "...", "goals": ["...", "..."]},
        ...
    ]}

Each item becomes a ``replace`` operation on the entity's ``intent``
field plus a ``replace`` on ``goals``. Unknown entity_ids are skipped
silently so LLM hallucinations don't produce dangling patches.
"""

from __future__ import annotations

import pytest

from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.write_back_variants import (
    Family1MissionLLM,
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
        id="prose:family1.mission",
        title="family1.mission",
        facets={"content_kind": "markdown", "body": "# Mission"},
    )


@pytest.fixture
def registry():
    reg = ProjectorRegistry()
    reg.register("family1.mission", _base)
    return reg


@pytest.fixture
def fragment():
    return _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "wb1"},
            "entities": {
                "capabilities": [
                    {"id": "CAP-F1", "name": "Alpha"},
                    {"id": "CAP-F2", "name": "Beta"},
                ],
                "actors": [{"id": "ACT-1", "name": "User"}],
            },
        }
    )


def test_family1_mission_llm_emits_intent_and_goals_operations(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {
                    "entity_id": "CAP-F1",
                    "intent": "Deliver Alpha capability.",
                    "goals": ["<= 100ms latency", "99.9% availability"],
                },
                {
                    "entity_id": "ACT-1",
                    "intent": "Interact with the system.",
                    "goals": ["Successful login"],
                },
            ]
        }
    )
    projector = Family1MissionLLM(
        provider=provider, task_class="mission.author", registry=registry
    )

    result = projector(fragment, {})

    payload = result.facets["proposal"]
    assert payload["kind"] == "model-patch"
    ops = payload["operations"]
    # Two entities × two fields (intent + goals) = 4 operations.
    assert len(ops) == 4
    intent_ops = [o for o in ops if o["field"] == "intent"]
    goals_ops = [o for o in ops if o["field"] == "goals"]
    assert {o["target"] for o in intent_ops} == {"CAP-F1", "ACT-1"}
    assert {o["target"] for o in goals_ops} == {"CAP-F1", "ACT-1"}
    cap_goals = next(o for o in goals_ops if o["target"] == "CAP-F1")
    assert cap_goals["value"] == ["<= 100ms latency", "99.9% availability"]


def test_family1_mission_llm_skips_unknown_entity_ids(fragment, registry):
    provider = _MockProvider(
        {
            "authored": [
                {"entity_id": "CAP-F1", "intent": "ok", "goals": ["g"]},
                {"entity_id": "GHOST-9", "intent": "no", "goals": ["nope"]},
            ]
        }
    )
    projector = Family1MissionLLM(
        provider=provider, task_class="mission.author", registry=registry
    )
    result = projector(fragment, {})
    ops = result.facets["proposal"]["operations"]
    targets = {o["target"] for o in ops}
    assert "GHOST-9" not in targets
    assert "CAP-F1" in targets


def test_family1_mission_llm_prompt_includes_base_body(fragment, registry):
    captured = {}

    class _Recorder(_MockProvider):
        def structured(self, prompt, schema, *, model=None):
            captured["prompt"] = prompt
            return {"authored": []}

    projector = Family1MissionLLM(
        provider=_Recorder({"authored": []}),
        task_class="mission.author",
        registry=registry,
    )
    projector(fragment, {})
    assert "# Mission" in captured["prompt"]
    assert "intent" in captured["prompt"]


def test_family1_mission_llm_schema_shape():
    provider = _MockProvider({"authored": []})
    projector = Family1MissionLLM(provider=provider, task_class="t")
    schema = projector.expected_proposal_schema()
    assert schema["type"] == "object"
    assert "authored" in schema["properties"]
    item = schema["properties"]["authored"]["items"]
    assert set(item["required"]) >= {"entity_id", "intent"}
