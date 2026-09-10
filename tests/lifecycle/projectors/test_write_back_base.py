"""WriteBackProjector base class — Phase 4-A Task 1.

The base class:
  1. Dispatches through a sibling deterministic projector to compute a
     ``base_view`` DiagramSpec.
  2. Builds a prompt from the base view via ``build_prompt``.
  3. Invokes an injected ``LLMProvider`` via ``structured()``.
  4. Packs the LLM output into an ``ai.ModelPatch`` proposal.
  5. Returns a ``DiagramSpec`` with ``content_kind="ai_proposal"``,
     the serialized proposal, and a ``base_view_id`` pointer.

No provider imports happen at module load — a mock provider is injected
per-test so the tests remain deterministic and offline.
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from architecture_model.ai.proposals import ModelPatch, Provenance
from architecture_model.core.diagram_spec import DiagramSpec
from architecture_model.core.parser import _parse_raw
from architecture_model.lifecycle.projectors.write_back import WriteBackProjector
from architecture_model.lifecycle.view_projection import ProjectorRegistry


class _MockProvider:
    """Canned structured() responses; records the last prompt/schema."""

    name = "mock"

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.last_prompt: str | None = None
        self.last_schema: dict | None = None
        self.calls = 0

    def structured(self, prompt: str, schema: dict, *, model: str | None = None) -> dict:
        self.calls += 1
        self.last_prompt = prompt
        self.last_schema = schema
        return dict(self._response)

    def complete(self, *_a, **_kw):
        raise NotImplementedError

    def stream(self, *_a, **_kw):
        raise NotImplementedError

    def tokenize(self, text: str) -> int:
        return len(text)


def _base_projector(fragment, config):
    del fragment, config
    return DiagramSpec(
        id="prose:family1.mission",
        title="family1.mission",
        facets={"content_kind": "markdown", "body": "# Base view"},
    )


class _ConcreteWriteBack(WriteBackProjector):
    base_projector_name: ClassVar[str] = "family1.mission"
    projector_name: ClassVar[str] = "family1.mission.llm"

    def build_prompt(self, base_view, fragment, config):
        return f"Rewrite intent for base body: {base_view.facets['body']}"

    def expected_proposal_schema(self):
        return {"type": "object", "properties": {"intent": {"type": "string"}}}

    def pack_proposal(self, raw, fragment, config):
        prov = Provenance(
            work_order_id="wo-test",
            model_version="rev-abc",
            prompt_digest="deadbeef",
        )
        return ModelPatch(
            provenance=prov,
            operations=[
                {"op": "replace", "target": "COMP-1", "field": "intent", "value": raw["intent"]},
            ],
        )


@pytest.fixture
def registry_with_base() -> ProjectorRegistry:
    reg = ProjectorRegistry()
    reg.register("family1.mission", _base_projector, version="1.0.0")
    return reg


@pytest.fixture
def fragment():
    return _parse_raw(
        {
            "meta": {"schema_version": "2.1", "project": "wb"},
            "entities": {"components": [{"id": "COMP-1", "name": "Alpha"}]},
        }
    )


def test_writeback_dispatches_base_and_calls_provider(fragment, registry_with_base):
    provider = _MockProvider({"intent": "The refactored intent."})
    projector = _ConcreteWriteBack(
        provider=provider, task_class="wb.test", registry=registry_with_base
    )

    result = projector(fragment, {})

    assert provider.calls == 1
    assert provider.last_prompt is not None
    assert "Rewrite intent" in provider.last_prompt
    assert provider.last_schema is not None
    assert provider.last_schema["type"] == "object"

    assert isinstance(result, DiagramSpec)
    assert result.facets["content_kind"] == "ai_proposal"
    assert result.facets["base_view_id"] == "prose:family1.mission"
    proposal_payload = result.facets["proposal"]
    assert proposal_payload["kind"] == "model-patch"
    ops = proposal_payload["operations"]
    assert ops[0]["field"] == "intent"
    assert ops[0]["value"] == "The refactored intent."
    prov = proposal_payload["provenance"]
    assert prov["proposal_id"].startswith("sha256-v1:")


def test_writeback_id_uses_llm_suffix(fragment, registry_with_base):
    provider = _MockProvider({"intent": "x"})
    projector = _ConcreteWriteBack(
        provider=provider, task_class="wb.test", registry=registry_with_base
    )
    result = projector(fragment, {})
    # DiagramSpec.id must end with .llm so callers can distinguish the
    # write-back variant from its deterministic sibling.
    assert result.id.endswith(".llm")
    assert "family1.mission.llm" in result.id


def test_writeback_raises_when_base_projector_missing(fragment):
    empty_registry = ProjectorRegistry()
    provider = _MockProvider({"intent": "x"})
    projector = _ConcreteWriteBack(
        provider=provider, task_class="wb.test", registry=empty_registry
    )
    with pytest.raises(KeyError):
        projector(fragment, {})


def test_writeback_subclass_must_override_hooks(fragment, registry_with_base):
    provider = _MockProvider({"intent": "x"})

    class _MissingHooks(WriteBackProjector):
        base_projector_name: ClassVar[str] = "family1.mission"
        projector_name: ClassVar[str] = "family1.mission.llm"

    projector = _MissingHooks(
        provider=provider, task_class="wb.test", registry=registry_with_base
    )
    with pytest.raises(NotImplementedError):
        projector(fragment, {})
