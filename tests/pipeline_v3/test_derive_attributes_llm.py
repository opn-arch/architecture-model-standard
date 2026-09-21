"""Tests for R7: LLM-based Category B attribute inference.

Covers the ``derive_attributes`` stage that proposes goals /
requirements / success_criteria / failure_modes / constraints as
``status=proposed`` promises using an LLMProvider.
"""
from __future__ import annotations

import copy
import json

import pytest

from architecture_model.core.promise import Promise, PromiseStatus
from architecture_model.pipeline_v3.derive_attributes_llm import (
    CATEGORY_B_ATTRIBUTES,
    TARGET_KINDS,
    AttributeInferenceRequest,
    derive_attributes,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


class MockProvider:
    """Provider that returns a canned dict per (kind, attribute) or per call."""

    name = "mock"

    def __init__(self, script):
        # script: callable(prompt: str, schema: dict) -> dict, or a dict of
        # attribute -> list[str] used for every call.
        self._script = script
        self.calls: list[tuple[str, dict]] = []

    def structured(self, prompt: str, schema: dict, *, model=None) -> dict:
        self.calls.append((prompt, schema))
        if callable(self._script):
            return self._script(prompt, schema)
        return dict(self._script)

    def complete(self, prompt, **_kw):  # pragma: no cover - unused
        raise NotImplementedError

    def stream(self, prompt, **_kw):  # pragma: no cover - unused
        raise NotImplementedError

    def tokenize(self, text):  # pragma: no cover - unused
        return len(text.split())


def _mk_promise(owner, attribute, content, status=PromiseStatus.OPEN, gap_type=None):
    return Promise(
        attribute=attribute,
        content=content,
        owner_entity=owner,
        status=status,
        gap_type=gap_type,
    ).to_dict()


@pytest.fixture
def tiny_model():
    """Minimal in-memory v3 model with one behavior, one component, one capability."""
    return {
        "meta": {"schema_version": "3.0"},
        "entities": {
            "behaviors": [
                {
                    "id": "BEH-A",
                    "name": "sample_behavior",
                    "description": "A behavior for testing.",
                    "promises": [_mk_promise("BEH-A", "intent", "do the thing")],
                },
            ],
            "components": [
                {
                    "id": "COMP-A",
                    "name": "sample_component",
                    "module_names": ["src.foo"],
                    "promises": [],
                },
            ],
            "capabilities": [
                {
                    "id": "CAP-A",
                    "name": "sample_capability",
                    "description": "Sample capability.",
                    "promises": [],
                },
            ],
            "actors": [
                {"id": "ACT-A", "name": "sample_actor", "promises": []},
            ],
        },
        "relationships": [],
    }


# --------------------------------------------------------------------------
# Contract tests
# --------------------------------------------------------------------------


def test_module_constants_include_all_five_category_b_attributes():
    assert set(CATEGORY_B_ATTRIBUTES) == {
        "goals",
        "requirements",
        "success_criteria",
        "failure_modes",
        "constraints",
    }


def test_target_kinds_are_three_promotable_kinds():
    assert set(TARGET_KINDS) == {"behaviors", "components", "capabilities"}


# --------------------------------------------------------------------------
# Behavior tests
# --------------------------------------------------------------------------


def test_derive_attributes_returns_new_model_dict(tiny_model):
    """R7 must not mutate the input model."""
    before = copy.deepcopy(tiny_model)
    provider = MockProvider({"goals": []})  # empty proposals
    result = derive_attributes(tiny_model, provider=provider)
    # Input unchanged
    assert tiny_model == before
    # Result is a distinct dict
    assert result is not tiny_model


def test_derive_attributes_emits_proposed_promises_on_target_kinds(tiny_model):
    """A non-empty provider response becomes proposed promises on the target."""
    def script(prompt, schema):
        attr = next(iter(schema["properties"].keys()))
        return {attr: [f"proposed {attr} item 1", f"proposed {attr} item 2"]}

    provider = MockProvider(script)
    result = derive_attributes(tiny_model, provider=provider)

    beh = result["entities"]["behaviors"][0]
    goals = [p for p in beh["promises"] if p["attribute"] == "goals"]
    assert len(goals) == 2
    assert all(p["status"] == PromiseStatus.PROPOSED.value for p in goals)
    # Original intent preserved
    intents = [p for p in beh["promises"] if p["attribute"] == "intent"]
    assert len(intents) == 1


def test_derive_attributes_skips_verified_promises(tiny_model):
    """Entities with a verified promise for an attribute are skipped."""
    tiny_model["entities"]["behaviors"][0]["promises"].append(
        _mk_promise("BEH-A", "goals", "human authored goal", status=PromiseStatus.VERIFIED)
    )

    def script(prompt, schema):
        attr = next(iter(schema["properties"].keys()))
        return {attr: [f"llm {attr}"]}

    provider = MockProvider(script)
    result = derive_attributes(tiny_model, provider=provider)

    beh = result["entities"]["behaviors"][0]
    goals = [p for p in beh["promises"] if p["attribute"] == "goals"]
    # Only the verified goal remains (LLM was not asked)
    assert len(goals) == 1
    assert goals[0]["status"] == PromiseStatus.VERIFIED.value
    # But other attributes were still inferred
    reqs = [p for p in beh["promises"] if p["attribute"] == "requirements"]
    assert len(reqs) == 1


def test_derive_attributes_overwrites_existing_proposed(tiny_model):
    """Re-running R7 should replace stale proposed promises, not duplicate."""
    stale = _mk_promise("BEH-A", "goals", "stale llm output", status=PromiseStatus.PROPOSED)
    tiny_model["entities"]["behaviors"][0]["promises"].append(stale)

    def script(prompt, schema):
        attr = next(iter(schema["properties"].keys()))
        return {attr: [f"fresh {attr}"]}

    provider = MockProvider(script)
    result = derive_attributes(tiny_model, provider=provider)

    beh = result["entities"]["behaviors"][0]
    goals = [p for p in beh["promises"] if p["attribute"] == "goals"]
    contents = {p["content"] for p in goals}
    assert contents == {"fresh goals"}


def test_derive_attributes_ignores_non_target_kinds(tiny_model):
    """Actors, interfaces, layers, constraint-entities are untouched."""
    provider = MockProvider({"goals": ["should not appear"]})
    result = derive_attributes(tiny_model, provider=provider)

    actor = result["entities"]["actors"][0]
    assert actor["promises"] == []


def test_derive_attributes_deterministic_ordering(tiny_model):
    """Two runs with the same provider script produce identical output."""
    def script(prompt, schema):
        attr = next(iter(schema["properties"].keys()))
        return {attr: [f"item for {attr}"]}

    provider1 = MockProvider(script)
    provider2 = MockProvider(script)
    a = derive_attributes(tiny_model, provider=provider1)
    b = derive_attributes(tiny_model, provider=provider2)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_derive_attributes_empty_provider_response_is_not_error(tiny_model):
    """Empty list from provider = no promises emitted, no exception."""
    provider = MockProvider({"goals": []})
    result = derive_attributes(tiny_model, provider=provider)

    beh = result["entities"]["behaviors"][0]
    goals = [p for p in beh["promises"] if p["attribute"] == "goals"]
    assert goals == []


def test_derive_attributes_provider_error_leaves_entity_unchanged(tiny_model):
    """A provider that raises for one attribute must not corrupt the model."""
    call_count = {"n": 0}

    def script(prompt, schema):
        call_count["n"] += 1
        attr = next(iter(schema["properties"].keys()))
        if attr == "goals":
            raise RuntimeError("provider blew up")
        return {attr: [f"ok {attr}"]}

    provider = MockProvider(script)
    result = derive_attributes(tiny_model, provider=provider)

    beh = result["entities"]["behaviors"][0]
    goals = [p for p in beh["promises"] if p["attribute"] == "goals"]
    reqs = [p for p in beh["promises"] if p["attribute"] == "requirements"]
    assert goals == []
    assert len(reqs) == 1  # Other attributes still processed


def test_derive_attributes_respects_target_kinds_override(tiny_model):
    """Passing a narrower target_kinds tuple restricts scope."""
    provider = MockProvider({"goals": ["x"]})
    result = derive_attributes(
        tiny_model, provider=provider, target_kinds=("behaviors",)
    )
    # Components + capabilities NOT touched
    comp = result["entities"]["components"][0]
    cap = result["entities"]["capabilities"][0]
    assert comp["promises"] == []
    assert cap["promises"] == []
    # Behavior WAS touched
    beh = result["entities"]["behaviors"][0]
    assert any(p["attribute"] == "goals" for p in beh["promises"])


def test_derive_attributes_respects_target_attributes_override(tiny_model):
    """Passing a narrower target_attributes tuple restricts which attrs are inferred."""
    provider = MockProvider({"goals": ["x"]})
    result = derive_attributes(
        tiny_model, provider=provider, target_attributes=("goals",)
    )
    beh = result["entities"]["behaviors"][0]
    attr_names = {p["attribute"] for p in beh["promises"]}
    # Only intent (pre-existing) + goals (new); no requirements/success_criteria/etc.
    assert attr_names == {"intent", "goals"}
